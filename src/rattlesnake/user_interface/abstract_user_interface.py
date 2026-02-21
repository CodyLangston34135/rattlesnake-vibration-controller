from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.profile_manager import ProfileEvent
from rattlesnake.utilities import GlobalCommands
from rattlesnake.user_interface.ui_utilities import UICommands, EventWatcher
from rattlesnake.hardware.abstract_hardware import HardwareMetadata
from rattlesnake.environment.abstract_environment import ControlTypes, EnvironmentMetadata, EnvironmentInstructions
import multiprocessing as mp
import netCDF4 as nc4
import openpyxl
from abc import ABC, abstractmethod
from datetime import datetime
from qtpy import QtCore


class AbstractUI(ABC):
    """Abstract User Interface class defining the interface with the controller

    This class is used to define the interface between the User Interface of a
    environment in the controller and the main controller."""

    @abstractmethod
    def __init__(
        self,
        environment_type: ControlTypes,
        environment_name: str,
        rattlesnake: Rattlesnake,
    ):
        """
        Stores data required by the controller to interact with the UI

        This class stores data required by the controller to interact with the
        user interface for a given environment.  This includes the environment
        name and queues to pass information between the controller and
        environment.  It additionally initializes the ``command_map`` which is
        used by the Test Profile functionality to map profile instructions to
        operations on the user interface.


        Parameters
        ----------
        environment_name : str
            The name of the environment
        environment_command_queue : VerboseMessageQueue
            A queue that will provide instructions to the corresponding
            environment
        controller_communication_queue : VerboseMessageQueue
            The queue that relays global communication messages to the controller
        log_file_queue : Queue
            The queue that will be used to put messages to the log file.


        """
        self.environment_type = environment_type
        self.environment_name = environment_name
        self.rattlesnake = rattlesnake
        self.hardware_metadata = None
        self.definition_widget = None
        self.system_id_widget = None
        self.prediction_widget = None
        self.run_widget = None
        self.event_thread = None
        self.event_watcher = None
        self._command_map = {
            UICommands.ENVIRONMENT_STARTED: self.display_environment_started,
            UICommands.ENVIRONMENT_ENDED: self.display_environment_ended,
            UICommands.SET_ENVIRONMENT_INSTRUCTIONS: self.display_environment_instructions,
        }

    @property
    def active(self):
        try:
            queue_name = self.rattlesnake.environment_manager.queue_names_dict[self.environment_name]
            return self.rattlesnake.environment_manager.event_container.environment_active_events[queue_name].is_set()
        except:
            return False

    @property
    def command_map(self) -> dict:
        """Dictionary mapping profile instructions to functions of the UI that
        are called when the instruction is executed."""
        return self._command_map

    # region: Metadata
    @abstractmethod
    def initialize_hardware(self, hardware_metadata: HardwareMetadata):
        """Update the user interface with data acquisition parameters

        This function is called when the Data Acquisition parameters are
        initialized.  This function should set up the environment user interface
        accordingly.

        Parameters
        ----------
        hardware_metadata : HardwareMetadata :
            Container containing the data acquisition parameters, including
            channel table and sampling information.

        """
        self.hardware_metadata = hardware_metadata

    def get_channel_list_bools(self, hardware_channel_list):
        channel_set = set(self.hardware_metadata.channel_list)
        channel_list_bools = [channel in channel_set for channel in hardware_channel_list]
        return channel_list_bools

    @abstractmethod
    def get_environment_metadata(self, hardware_metadata: HardwareMetadata) -> EnvironmentMetadata:
        """
        Collect the parameters from the user interface defining the environment

        Returns
        -------
        EnvironmentMetadata
            An EnvironmentMetadata-inheriting object that contains the parameters
            defining the environment.
        """

    @abstractmethod
    def display_metadata(self, metadata: EnvironmentMetadata):
        """
        Update the user interface from environment metadata

        This function is called when the Environment parameters are initialized.
        This function should set up the user interface accordingly.  It must
        return the parameters class of the environment that inherits from
        AbstractMetadata.
        """

    @abstractmethod
    def get_environment_instructions(self) -> EnvironmentInstructions:
        """
        Compiles environment instructions to give to the main environment class
        when start_environment is called

        Returns
        -------
        EnvironmentInstructions
            An EnvironmentInstructions-inheriting object that contians parameters
            in the environment likely to change between runs
        """

    # region: Commands
    @abstractmethod
    def display_environment_instructions(self, instructions: EnvironmentInstructions):
        """
        Updates the user interface with environment instructions

        This function is called when wanting to sync the environment ui with an
        EnvironmentInstructions object. This will most likely set widgets in the
        environment's run_tab to the values in the EnvironmentInstructions
        """

    @abstractmethod
    def display_environment_started(self):
        """
        This command is called when the environment process officially
        starts up. Needs to prevent user from starting environment again until
        display_environment ended has been called.
        """

    @abstractmethod
    def display_environment_ended(self):
        """
        This command is called when the environment process has officially
        shut down. Needs to enable the user to start up the process again.
        """

    def map_command(self, key, function):
        """Maps commands to instructions

        Maps the instruction ``key`` to the function ``function`` so when
        ``(key,data)`` pairs are pulled from the ``command_queue``, the function
        ``function`` is called with argument ``data``.

        Parameters
        ----------
        key :
            Instruction pulled from the command queue

        function :
            Function to be called when the given ``key`` is pulled from the
            ``command_queue``

        """
        self._command_map[key] = function

    @property
    def command_map(self) -> dict:
        """A dictionary that maps commands received by the ``command_queue`` to functions in the class."""
        return self._command_map

    # region: Processes
    @abstractmethod
    def start_environment(self):
        """
        This method in the UI class should follow this structure:
        1. Disable start_environment button
        2. Call super().start_environment
        """
        try:
            instructions = self.get_environment_instructions()
            queue_name = self.rattlesnake.environment_manager.queue_names_dict[self.environment_name]
            self.rattlesnake.start_environment(instructions)
        except Exception as e:
            self.start_environment_error(e)
            return

        ready_event_list = []
        active_event_list = [self.rattlesnake.event_container.environment_active_events[queue_name]]
        self.create_event_watcher(ready_event_list, active_event_list, active_event_check=True)
        self.event_watcher.ready.connect(self.start_environment_ready)
        self.event_watcher.error.connect(self.start_environment_error)
        self.event_thread.start()

    @abstractmethod
    def start_environment_ready(self):
        self.clean_up_event_watcher()

    @abstractmethod
    def start_environment_error(self, error):
        """
        This method defines how to recover UI if the instruction/environment did
        not start up correctly. Should follow this structure:
        1. Enable stop_environment and start_environment button
        2. Call super().start_environment_error or display error some other way
        """
        self.clean_up_event_watcher()
        self.display_error(error)

    @abstractmethod
    def stop_environment(self):
        """
        This method in the UI class should follow this structure:
        1. Disable stop_environment button
        2. Call super().stop_environment
        """
        try:
            queue_name = self.rattlesnake.environment_manager.queue_names_dict[self.environment_name]
            self.rattlesnake.stop_environment(self.environment_name)
        except Exception as e:
            self.stop_environment_error(e)
            return

        ready_event_list = []
        active_event_list = [self.rattlesnake.event_container.environment_active_events[queue_name]]
        self.create_event_watcher(ready_event_list, active_event_list, active_event_check=False)
        self.event_watcher.ready.connect(self.stop_environment_ready)
        self.event_watcher.error.connect(self.stop_environment_error)
        self.event_thread.start()

    @abstractmethod
    def stop_environment_ready(self):
        self.clean_up_event_watcher()

    @abstractmethod
    def stop_environment_error(self, error):
        """
        This method defines how to recover UI if the instruction/environment did
        not start up correctly. Should follow this structure:
        1. Enable stop_environment and start_environment button
        2. Call super().start_environment_error or display error some other way
        """
        self.clean_up_event_watcher()
        self.display_error(error)

    @property
    def log_file_queue(self) -> mp.Queue:
        """A property containing a reference to the queue accepting messages
        that will be written to the log file"""
        return self.rattlesnake.queue_container.log_file_queue

    @property
    def gui_update_queue(self) -> mp.Queue:
        return self.rattlesnake.queue_container.gui_update_queue

    @property
    def log_name(self):
        """A property containing the name that the UI will be referenced by in
        the log file, which will typically be ``self.environment_name + ' UI'``"""
        return self.environment_name + " UI"

    def log(self, message: str):
        """Write a message to the log file

        This function puts a message onto the ``log_file_queue`` so it will
        eventually be written to the log file.

        When written to the log file, the message will include the date and
        time that the message was queued, the name that the UI uses in the log
        file (``self.log_file``), and then the message itself.

        Parameters
        ----------
        message : str :
            A message that will be written to the log file.

        """
        self.log_file_queue.put(f"{datetime.now()}: {self.log_name} -- {message}\n")

    def create_event_watcher(self, ready_event_list, active_event_list, *, active_event_check: bool = None):
        if getattr(self, "event_thread", None) or getattr(self, "event_watcher", None):
            self.display_error("Event watcher is still active")
            return
        self.event_thread = QtCore.QThread()
        self.event_watcher = EventWatcher(
            ready_event_list, active_event_list, active_event_check=active_event_check, timeout=self.rattlesnake.timeout
        )
        self.event_watcher.moveToThread(self.event_thread)
        self.event_thread.started.connect(self.event_watcher.run)

    def clean_up_event_watcher(self):
        if getattr(self, "event_thread", None):
            self.event_thread.quit()
            self.event_thread.wait()
            self.event_thread.deleteLater()
            self.event_thread = None
        if getattr(self, "event_watcher", None):
            self.event_watcher.deleteLater()
            self.event_watcher = None

    def display_error(self, error_message):
        self.log(f"ERROR\n\n {error_message}")
        self.gui_update_queue.put(
            (
                UICommands.ERROR,
                (f"{self.log_name} Error", f"ERROR:\n\n{error_message}"),
            )
        )
