from ..utilities import VerboseMessageQueue, GlobalCommands
from ..hardware.abstract_hardware import HardwareMetadata
from abc import ABC, abstractmethod
import traceback
import os
import netCDF4 as nc4
import multiprocessing as mp
import multiprocessing.sharedctypes  # pylint: disable=unused-import
import multiprocessing.queues as mpqueue
import queue as thqueue
from datetime import datetime

PICKLE_ON_ERROR = False

if PICKLE_ON_ERROR:
    import pickle


class EnvironmentMetadata(ABC):
    """Abstract class for storing metadata for an environment.

    This class is used as a storage container for parameters used by an
    environment.  It is returned by the environment UI's
    ``collect_environment_definition_parameters`` function as well as its
    ``initialize_environment`` function.  Various parts of the controller and
    environment will query the class's data members for parameter values.

    Classes inheriting from EnvironmentMetadata must define:
      1. store_to_netcdf - A function defining the way the parameters are
         stored to a netCDF file saved during streaming operations.
    """

    def __init__(self, environment_type, environment_name):
        self.environment_type = environment_type
        self.environment_name = environment_name
        self.queue_name = None  # Name used to assign environment to queues
        self.channel_list = []

    def map_channel_bools(self, hardware_channel_list):
        # Prevent non-existing channels
        hardware_channel_set = set(hardware_channel_list)
        missing_channels = set(self.channel_list) - hardware_channel_set
        if missing_channels:
            raise ValueError(f"channel_list contains channels not in hardware_channel_list: " f"{missing_channels}")

        # Create boolean map
        channel_set = set(self.channel_list)
        channel_list_bools = [channel in channel_set for channel in hardware_channel_list]

        return channel_list_bools

    def map_channel_indices(self, hardware_channel_list):
        # Prevent non-existing channels
        hardware_channel_set = set(hardware_channel_list)
        missing_channels = set(self.channel_list) - hardware_channel_set
        if missing_channels:
            raise ValueError(f"channel_list contains channels not in hardware_channel_list: " f"{missing_channels}")

        # Create boolean map
        channel_set = set(self.channel_list)
        channel_bools = [channel in channel_set for channel in hardware_channel_list]

        channel_indices = [index for index, environment_bool in enumerate(channel_bools) if environment_bool]
        return channel_indices

    @abstractmethod
    def validate(self):
        """Validate whether the metadata will work for that environment. Return True if valid

        Throw errors if metadata is invalid. This should contain checks for
        things like duplicate channel_list entries, valid control channels,
        etc.
        """
        pass

    @abstractmethod
    def store_to_netcdf(self, netcdf_group_handle: nc4._netCDF4.Group):
        """Store parameters to a group in a netCDF streaming file.

        This function stores parameters from the environment into the netCDF
        file in a group with the environment's name as its name.  The function
        will receive a reference to the group within the dataset and should
        store the environment's parameters into that group in the form of
        attributes, dimensions, or variables.

        This function is the "write" counterpart to the retrieve_metadata
        function in the AbstractUI class, which will read parameters from
        the netCDF file to populate the parameters in the user interface.

        Parameters
        ----------
        netcdf_group_handle : nc4._netCDF4.Group
            A reference to the Group within the netCDF dataset where the
            environment's metadata is stored.

        """
        pass


class EnvironmentInstructions(ABC):
    """Environment Instructions class that defines startup of environment

    This is an class given to the controller as input to the
    intial start_control function call for that environment. It is
    used to define aspects such as test_level or repeating_signals that
    need to be defined quickly without needing to be stored to netcdf4 file.

    If no instructions are given to controller for an environment, the
    first start_control function call will be given with a None as the
    datatype.

    If profile events are being used, this will be given to the controller
    when "Start Profile" button is clicked. If a profile is not being used,
    you are responsible for sending this to the controller with:

    queue_container.controller_command_queue.put(
        TASK_NAME,
        (GlobalCommands.INITIALIZE_INSTRUCTIONS, (EnvironmentInstructions,))
    )

    when the "Start" button on your run tab is pressed, most likely
    right before the GlobalCommand.START_ENVIRONMENT for that environment
    would be called.

    Parameters
    ---------
    environment_name : str
        This is the environment name used in the metadata as it is easier
        to lookup from existing UI (NOT the queue_name). The queue_name
        will be looked up from the existing environment_metadata list
        when this is stored to the controller
    """

    def __init__(self, environment_name):
        self.environment_name = environment_name


class EnvironmentProcess(ABC):
    """Abstract Environment class defining the interface with the controller

    This class is used to define the operation of an environment within the
    controller, which must be completed by subclasses inheriting from this
    class.  Children of this class will sit in a While loop in the
    ``AbstractEnvironment.run()`` function.  While in this loop, the
    Environment will pull instructions and data from the
    ``command_queue`` and then use the ``command_map`` to map those instructions
    to functions in the class.

    All child classes inheriting from AbstractEnvironment will require functions
    to be defined for global operations of the controller, which are already
    mapped in the ``command_map``.  Any additional operations must be defined
    by functions and then added to the command_map when initilizing the child
    class.

    All functions called via the ``command_map`` must accept one input argument
    which is the data passed along with the command.  For functions that do not
    require additional data, this argument can be ignored, but it must still be
    present in the function's calling signature.

    The run function will continue until one of the functions called by
    ``command_map`` returns a truthy value, which signifies the controller to
    quit.  Therefore, any functions mapped to ``command_map`` that should not
    instruct the program to quit should not return any value that could be
    interpreted as true."""

    def dump_to_dict(self):
        """Dumps the environment to a dictionary to be pickled if an error occurs"""
        if PICKLE_ON_ERROR:
            state = self.__dict__.copy()
            for key, value in state.items():
                try:
                    pickle.dumps(value)
                    print(f"{key} is pickleable")
                except Exception:  # pylint: disable=broad-exception-caught
                    print(f"{key} is not pickleable")
                    state[key] = None
            return state
        else:
            return self.__dict__.copy()

    def __init__(
        self,
        environment_name: str,
        queue_name: str,
        command_queue: VerboseMessageQueue,
        gui_update_queue: mp.Queue,
        controller_communication_queue: VerboseMessageQueue,
        log_file_queue: mp.Queue,
        data_in_queue: mp.Queue,
        data_out_queue: mp.Queue,
        acquisition_active: mp.sharedctypes.Synchronized,
        output_active: mp.sharedctypes.Synchronized,
    ):
        self.environment_name = environment_name  # Used for TASK_NAME/logging purposes, can change adaptively
        self._queue_name = queue_name  # Used whenever you need a unique id for the environment, stays the same
        self._command_queue = command_queue
        self._gui_update_queue = gui_update_queue
        self._controller_communication_queue = controller_communication_queue
        self._log_file_queue = log_file_queue
        self._data_in_queue = data_in_queue
        self._data_out_queue = data_out_queue
        self._command_map = {
            GlobalCommands.QUIT: self.quit,
            GlobalCommands.INITIALIZE_HARDWARE: self.initialize_hardware,
            GlobalCommands.INITIALIZE_ENVIRONMENT: self.initialize_environment,
            GlobalCommands.STOP_ENVIRONMENT: self.stop_environment,
        }
        self._acquisition_active = acquisition_active
        self._output_active = output_active

    @property
    def acquisition_active(self):
        """Flag to check if acquisition is active"""
        # print('Checking if Acquisition Active: {:}'.format(bool(self._acquisition_active.value)))
        return bool(self._acquisition_active.value)

    @property
    def output_active(self):
        """Flag to check if output is active"""
        # print('Checking if Output Active: {:}'.format(bool(self._output_active.value)))
        return bool(self._output_active.value)

    @abstractmethod
    def initialize_hardware(self, hardware_metadata: HardwareMetadata):
        """Initialize the data acquisition parameters in the environment.

        The environment will receive the global data acquisition parameters from
        the controller, and must set itself up accordingly.

        Parameters
        ----------
        data_acquisition_parameters : DataAcquisitionParameters :
            A container containing data acquisition parameters, including
            channels active in the environment as well as sampling parameters.
        """

    @abstractmethod
    def initialize_environment(self, environment_metadata: EnvironmentMetadata):
        """
        Initialize the environment parameters specific to this environment

        The environment will recieve parameters defining itself from the
        user interface and must set itself up accordingly.

        Parameters
        ----------
        environment_parameters : AbstractMetadata
            A container containing the parameters defining the environment

        """

    @abstractmethod
    def stop_environment(self, data):
        """Stop the environment gracefully

        This function defines the operations to shut down the environment
        gracefully so there is no hard stop that might damage test equipment
        or parts.

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``

        """

    @property
    def environment_command_queue(self) -> VerboseMessageQueue:
        """The queue that provides commands to the environment."""
        return self._command_queue

    @property
    def data_in_queue(self) -> mp.Queue:
        """The queue from which data is delivered to the environment"""
        return self._data_in_queue

    @property
    def data_out_queue(self) -> mp.Queue:
        """The queue to which data is written that will be output to exciters"""
        return self._data_out_queue

    @property
    def gui_update_queue(self) -> mp.Queue:
        """The queue that GUI update instructions are written to"""
        return self._gui_update_queue

    @property
    def controller_communication_queue(self) -> mp.Queue:
        """The queue that global controller updates are written to"""
        return self._controller_communication_queue

    @property
    def log_file_queue(self) -> mp.Queue:
        """The queue that log file messages are written to"""
        return self._log_file_queue

    def log(self, message: str):
        """Write a message to the log file

        This function puts a message onto the ``log_file_queue`` so it will
        eventually be written to the log file.

        When written to the log file, the message will include the date and
        time that the message was queued, the name of the environment, and
        then the message itself.

        Parameters
        ----------
        message : str :
            A message that will be written to the log file.
        """
        self.log_file_queue.put(f"{datetime.now()}: {self.environment_name} -- {message}\n")

    @property
    def queue_name(self) -> str:
        """A string defining the queue name asigned to the environment"""
        return self._queue_name

    @property
    def command_map(self) -> dict:
        """A dictionary that maps commands received by the ``command_queue`` to functions in the class"""
        return self._command_map

    def map_command(self, key, function):
        """A function that maps an instruction to a function in the ``command_map``

        Parameters
        ----------
        key :
            The instruction that will be pulled from the ``command_queue``

        function :
            A reference to the function that will be called when the ``key``
            message is received.

        """
        self._command_map[key] = function

    def run(self, shutdown_event):
        """The main function that is run by the environment's process

        A function that is called by the environment's process function that
        sits in a while loop waiting for instructions on the command queue.

        When the instructions are recieved, they are separated into
        ``(message,data)`` pairs.  The ``message`` is used in conjuction with
        the ``command_map`` to identify which function should be called, and
        the ``data`` is passed to that function as the argument.  If the
        function returns a truthy value, it signals to the ``run`` function
        that it is time to stop the loop and exit.


        """
        self.log(f"Starting Process with PID {os.getpid()}")
        while not shutdown_event.is_set():
            # Get the message from the queue
            try:
                message, data = self.environment_command_queue.get(self.environment_name)
            except (thqueue.Empty, mpqueue.Empty):
                continue
            # Call the function corresponding to that message with the data as argument
            try:
                function = self.command_map[message]
            except KeyError:
                self.log(f"Undefined Message {message}, acceptable messages are {[key for key in self.command_map]}")
                continue
            try:
                halt_flag = function(data)
            except Exception:  # pylint: disable=broad-exception-caught
                tb = traceback.format_exc()
                self.log(f"ERROR\n\n {tb}")
                self.gui_update_queue.put(
                    (
                        "error",
                        (
                            f"{self.environment_name} Error",
                            f"!!!UNKNOWN ERROR!!!\n\n{tb}",
                        ),
                    )
                )
                if PICKLE_ON_ERROR:
                    with open(f"debug_data/{self.environment_name}_error_state.txt", "w", encoding="utf-8") as f:
                        f.write(f"{tb}")
                    with open(f"debug_data/{self.environment_name}_error_state.pkl", "wb") as f:
                        dic = self.dump_to_dict()
                        pickle.dump(dic, f)
                    print("Done Writing Pickle File from Error...")
                halt_flag = False
            # If we get a true value, stop.
            if halt_flag:
                self.log("Stopping Process")
                break

    def quit(self, data):  # pylint: disable=unused-argument
        """Returns True to stop the ``run`` while loop and exit the process

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``

        Returns
        -------
        True :
            This function returns True to signal to the ``run`` while loop
            that it is time to close down the environment.

        """
        return True


def run_process(
    environment_name: str,
    input_queue: VerboseMessageQueue,
    gui_update_queue: mp.Queue,
    controller_communication_queue: VerboseMessageQueue,
    log_file_queue: mp.Queue,
    data_in_queue: mp.Queue,
    data_out_queue: mp.Queue,
    acquisition_active: mp.sharedctypes.Synchronized,
    output_active: mp.sharedctypes.Synchronized,
    shutdown_event,
):
    """A function called by ``multiprocessing.Process`` to start the environment

    This function should not be called directly, but used as a template for
    other environments to start up.

    Parameters
    ----------
    environment_name : str :
        The name of the environment

    input_queue : VerboseMessageQueue :
        The command queue for the environment

    gui_update_queue : Queue :
        The queue that accepts GUI update ``(message,data)`` pairs.

    controller_communication_queue : VerboseMessageQueue :
        The queue where global instructions to the controller can be written

    log_file_queue : Queue :
        The queue where logging messages can be written

    data_in_queue : Queue :
        The queue from which the environment will receive data from the
        acquisition hardware

    data_out_queue : Queue :
        The queue to which the environment should write data so it will be output
        to the excitation devices in the output hardware

    """
    process_class = EnvironmentProcess(
        environment_name,
        input_queue,
        gui_update_queue,
        controller_communication_queue,
        log_file_queue,
        data_in_queue,
        data_out_queue,
        acquisition_active,
        output_active,
    )
    process_class.run(shutdown_event)
