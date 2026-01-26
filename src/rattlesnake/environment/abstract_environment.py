from ..utilities import VerboseMessageQueue, GlobalCommands
from abc import ABC, abstractmethod
import traceback
import os
import netCDF4 as nc4
import multiprocessing as mp
import multiprocessing.sharedctypes  # pylint: disable=unused-import
import datetime as datetime


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

    @property
    def channel_list_bools(self):
        return self._channel_list_bools

    @channel_list_bools.setter
    def channel_list_bools(self, value):
        if not isinstance(value, list):
            raise TypeError("channel_list_bools must be a list.")

        # Ensure all elements are strictly booleans
        if not all(isinstance(v, bool) for v in value):
            raise ValueError("All elements in channel_list_bools must be True or False.")

        self._channel_list_bools = value

    def map_channel_bools(self, hardware_channel_list):

        # Prevent duplicate entries
        if len(self.channel_list) != len(set(self.channel_list)):
            raise ValueError("Duplicate channels found in environment channel_list")

        # Prevent non-existing channels
        hardware_channel_set = set(hardware_channel_list)
        missing_channels = set(self.channel_list) - hardware_channel_set
        if missing_channels:
            raise ValueError(f"channel_list contains channels not in hardware_channel_list: " f"{missing_channels}")

        # Create boolean map
        channel_set = set(self.channel_list)
        return [channel in channel_set for channel in hardware_channel_list]

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

    def __init__(
        self,
        environment_name: str,
        log_file_queue: mp.Queue,
        from_command_queue: VerboseMessageQueue,
        to_gui_queue: mp.Queue,
        from_acquisition_queue: mp.Queue,
        to_output_queue: mp.Queue,
        acquisition_active: mp.sharedctypes.Synchronized,
        output_active: mp.sharedctypes.Synchronized,
    ):
        self._environment_name = environment_name
        self._log_file_queue = log_file_queue
        self._from_command_queue = from_command_queue
        self._to_gui_queue = to_gui_queue
        self._from_acquisition_queue = from_acquisition_queue
        self._to_output_queue = to_output_queue
        self._command_map = {
            GlobalCommands.QUIT: self.quit,
            GlobalCommands.INITIALIZE_HARDWARE: self.initialize_hardware,
            GlobalCommands.INITIALIZE_ENVIRONMENT: self.initialize_environment,
            GlobalCommands.RUN_ENVIRONMENT: self.run_environment,
            GlobalCommands.STOP_ENVIRONMENT: self.stop_environment,
        }
        self._acquisition_active = acquisition_active
        self._output_active = output_active

    @property
    def acquisition_active(self):
        return bool(self._acquisition_active.value)

    @property
    def output_active(self):
        return bool(self._output_active.value)

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
        self.log_file_queue.put("{:}: {:} -- {:}\n".format(datetime.now(), self.environment_name, message))

    @abstractmethod
    def initialize_hardware(self, data):
        """Initialize the data acquisition parameters in the environment.

        The environment will receive the global data acquisition parameters from
        the controller, and must set itself up accordingly.

        Parameters
        ----------
        data_acquisition_parameters : DataAcquisitionParameters :
            A container containing data acquisition parameters, including
            channels active in the environment as well as sampling parameters.
        """
        pass

    @abstractmethod
    def initialize_environment(self, data):
        """
        Initialize the environment parameters specific to this environment

        The environment will recieve parameters defining itself from the
        user interface and must set itself up accordingly.

        Parameters
        ----------
        environment_parameters : EnvironmentMetadata
            A container containing the parameters defining the environment

        """
        pass

    @abstractmethod
    def start_environment(self, data):
        pass

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
        pass

    def run(self):
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
        self.log("Starting Process with PID {:}".format(os.getpid()))
        while True:
            # Get the message from the queue
            message, data = self.environment_command_queue.get(self.environment_name)
            # Call the function corresponding to that message with the data as argument
            try:
                function = self.command_map[message]
            except KeyError:
                self.log("Undefined Message {:}, acceptable messages are {:}".format(message, [key for key in self.command_map]))
                continue
            try:
                halt_flag = function(data)
            except Exception:
                tb = traceback.format_exc()
                self.log("ERROR\n\n {:}".format(tb))
                self.gui_update_queue.put(("error", ("{:} Error".format(self.environment_name), "!!!UNKNOWN ERROR!!!\n\n{:}".format(tb))))
                halt_flag = False
            # If we get a true value, stop.
            if halt_flag:
                self.log("Stopping Process")
                break


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
    process_class.run()
