from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.user_interface.ui_utilities import UICommands
from rattlesnake.hardware.abstract_hardware import HardwareMetadata
from rattlesnake.environment.abstract_environment import EnvironmentMetadata
import multiprocessing as mp
import netCDF4 as nc4
import openpyxl
from abc import ABC, abstractmethod
from datetime import datetime


class AbstractUI(ABC):
    """Abstract User Interface class defining the interface with the controller

    This class is used to define the interface between the User Interface of a
    environment in the controller and the main controller."""

    @abstractmethod
    def __init__(
        self,
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
        self.environment_name = environment_name
        self.rattlesnake = rattlesnake
        self.definition_widget = None
        self.system_id_widget = None
        self.prediction_widget = None
        self.run_widget = None
        self._command_map = {
            "Start Control": self.start_control,
            "Stop Control": self.stop_control,
        }

    @property
    def command_map(self) -> dict:
        """Dictionary mapping profile instructions to functions of the UI that
        are called when the instruction is executed."""
        return self._command_map

    ## Store/Export metadata methods
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

    @abstractmethod
    def get_environment_metadata(self) -> EnvironmentMetadata:
        """
        Collect the parameters from the user interface defining the environment

        Returns
        -------
        AbstractMetadata
            A metadata or parameters object containing the parameters defining
            the corresponding environment.

        """

    @abstractmethod
    def store_metadata(self) -> EnvironmentMetadata:
        """
        Update the user interface with environment parameters

        This function is called when the Environment parameters are initialized.
        This function should set up the user interface accordingly.  It must
        return the parameters class of the environment that inherits from
        AbstractMetadata.

        Returns
        -------
        AbstractMetadata
            An AbstractMetadata-inheriting object that contains the parameters
            defining the environment.

        """

    ## Callbacks
    @abstractmethod
    def start_control(self):
        """Runs the corresponding environment in the controller"""

    @abstractmethod
    def stop_control(self):
        """Stops the corresponding environment in the controller"""

    @abstractmethod
    def update_gui(self, queue_data: tuple):
        """Update the environment's graphical user interface

        This function will receive data from the gui_update_queue that
        specifies how the user interface should be updated.  Data will usually
        be received as ``(instruction,data)`` pairs, where the ``instruction`` notes
        what operation should be taken or which widget should be modified, and
        the ``data`` notes what data should be used in the update.

        Parameters
        ----------
        queue_data : tuple
            A tuple containing ``(instruction,data)`` pairs where ``instruction``
            defines and operation or widget to be modified and ``data`` contains
            the data used to perform the operation.
        """

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

    def display_error(self, error_message):
        self.log(f"ERROR\n\n {error_message}")
        self.gui_update_queue.put(
            (
                UICommands.ERROR,
                (f"{self.log_name} Error", f"ERROR:\n\n{error_message}"),
            )
        )
