from .abstract_environment import EnvironmentMetadata, EnvironmentInstructions, EnvironmentProcess
from .environment_utilities import ControlTypes
from ..utilities import VerboseMessageQueue, GlobalCommands
from ..hardware.abstract_hardware import HardwareMetadata
from ..user_interface.ui_utilities import ReadUICommands
import copy
import multiprocessing as mp
import multiprocessing.sharedctypes  # pylint: disable=unused-import
import netCDF4 as nc4
import numpy as np

CONTROL_TYPE = ControlTypes.READ


class ReadMetadata(EnvironmentMetadata):
    def __init__(self, environment_name: str = "Read"):
        super().__init__(CONTROL_TYPE, environment_name)

    def validate(self):
        # Prevent duplicate entries
        if len(self.channel_list) != len(set(self.channel_list)):
            raise ValueError("Duplicate channels found in environment channel_list")

        return True

    def store_to_netcdf(
        self,
        netcdf_group_handle: nc4._netCDF4.Group,  # pylint: disable=c-extension-no-member
    ):
        """
        Stores parameters to a netCDF group so they can be recovered.

        Parameters
        ----------
        netcdf_group_handle : nc4._netCDF4.Group
            Reference to the netCDF4 group in which the environment data should
            be stored.

        """


class ReadQueues:
    """A set of queues used by the read environment"""

    def __init__(
        self,
        environment_name: str,
        environment_command_queue: VerboseMessageQueue,
        gui_update_queue: mp.Queue,
        controller_communication_queue: VerboseMessageQueue,
        data_in_queue: mp.Queue,
        data_out_queue: mp.Queue,
        log_file_queue: mp.Queue,
    ):
        self.environment_name = environment_name
        self.environment_command_queue = environment_command_queue
        self.gui_update_queue = gui_update_queue
        self.controller_communication_queue = controller_communication_queue
        self.data_in_queue = data_in_queue
        self.data_out_queue = data_out_queue
        self.log_file_queue = log_file_queue


class ReadEnvironment(EnvironmentProcess):
    def __init__(
        self,
        environment_name: str,
        queue_container: ReadQueues,
        acquisition_active: mp.sharedctypes.Synchronized,
        output_active: mp.sharedctypes.Synchronized,
    ):
        super().__init__(
            environment_name,
            queue_container.environment_command_queue,
            queue_container.gui_update_queue,
            queue_container.controller_communication_queue,
            queue_container.log_file_queue,
            queue_container.data_in_queue,
            queue_container.data_out_queue,
            acquisition_active,
            output_active,
        )
        self.queue_container = queue_container
        self.command_map[GlobalCommands.START_ENVIRONMENT] = self.run_environment
        self.hardware_metadata = None
        self.metadata = None
        self.measurement_channels = None
        self.output_channels = None

    def initialize_hardware(self, hardware_metadata: HardwareMetadata):
        self.log("Initializing Data Acquisition Parameters")
        self.hardware_metadata = hardware_metadata
        self.measurement_channels = [index for index, channel in enumerate(self.hardware_metadata.channel_list) if channel.feedback_device is None]
        self.output_channels = [index for index, channel in enumerate(self.hardware_metadata.channel_list) if not channel.feedback_device is None]

    def initialize_environment(self, metadata: ReadMetadata):
        self.log("Initializing Environment Parameters")
        self.metadata = metadata

    def stop_environment(self, data):
        pass

    def run_environment(self):
        try:
            acquisition_data, last_acquisition = self.queue_container.data_in_queue.get_nowait()
            measurement_data = acquisition_data[self.measurement_channels]
            self.queue_container.gui_update_queue.put((self.environment_name, (ReadUICommands.TIME_DATA, measurement_data)))
        except mp.queues.Empty:
            pass

        self.queue_container.environment_command_queue.put(self.environment_name, (GlobalCommands.START_ENVIRONMENT, None))


def time_process(
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

    queue_container = ReadQueues(input_queue, gui_update_queue, controller_communication_queue, data_in_queue, data_out_queue, log_file_queue)

    process_class = ReadEnvironment(environment_name, queue_container, acquisition_active, output_active)
    process_class.run()
