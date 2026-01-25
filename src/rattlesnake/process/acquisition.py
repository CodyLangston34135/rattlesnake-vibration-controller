from abstract_message_process import AbstractMessageProcess
from ..utilities import VerboseMessageQueue, GlobalCommands
from ..hardware.hardware_utilities import HardwareMetadata, HardwareType
import multiprocessing as mp
import numpy as np


class AcquisitionProcess(AbstractMessageProcess):
    """Class defining the acquisition behavior of the controller

    This class will handle reading data from the hardware and then sending it
    to the individual environment processes.

    See AbstractMesssageProcess for inherited class members.
    """

    def __init__(
        self,
        process_name: str,
        log_file_queue: mp.Queue,
        acquisition_command_queue: mp.Queue,
        gui_update_queue: mp.Queue,
        acquisition_to_environment_queue: VerboseMessageQueue,
        output_to_acquisition_sync_queue: VerboseMessageQueue,
        streaming_command_queue: VerboseMessageQueue,
        acquisition_active: mp.Value,
    ):
        """
        Constructor for the AcquisitionProcess class

        Sets up the ``command_map`` and initializes all data members.

        Parameters
        ----------
        process_name : str
            The name of the process.
        queue_container : QueueContainer
            A container containing the queues used to communicate between
            controller processes
        environments : list
            A list of ``(ControlType,environment_name)`` pairs that define the
            environments in the controller.


        """
        super().__init__(process_name, log_file_queue, acquisition_command_queue, gui_update_queue)
        self.map_command(GlobalCommands.INITIALIZE_HARDWARE, self.initialize_hardware)
        # self.map_command(GlobalCommands.INITIALIZE_ENVIRONMENT, self.initialize_environment)
        # self.map_command(GlobalCommands.RUN_HARDWARE, self.acquire_signal)
        # self.map_command(GlobalCommands.STOP_HARDWARE, self.stop_acquisition)
        # self.map_command(GlobalCommands.STOP_ENVIRONMENT, self.stop_environment)
        # self.map_command(GlobalCommands.START_STREAMING, self.start_streaming)
        # self.map_command(GlobalCommands.STOP_STREAMING, self.stop_streaming)

        # Communication
        self.log_file_queue = log_file_queue
        self.acquisition_command_queue = acquisition_command_queue
        self.gui_update_queue = gui_update_queue
        self.acquisition_to_environment_queue = acquisition_to_environment_queue
        self.output_to_acquisition_sync_queue = output_to_acquisition_sync_queue
        self.streaming_command_queue = streaming_command_queue

        self.startup = True
        self.shutdown_flag = False
        self.any_environments_started = False
        # Sampling data
        self.sample_rate = None
        self.read_size = None
        # Environment Data
        self.environment_list = []
        self.environment_acquisition_channels = None
        self.environment_active_flags = {}
        self.environment_last_data = {}
        self.environment_samples_remaining_to_read = {}
        self.environment_first_data = {}
        # self.environment_list = [environment[1] for environment in environments]
        # self.environment_acquisition_channels = None
        # self.environment_active_flags = {environment:False for environment in self.environment_list}
        # self.environment_last_data = {environment:False for environment in self.environment_list}
        # self.environment_samples_remaining_to_read = {environment:0 for environment in self.environment_list}
        # self.environment_first_data = {environment:None for environment in self.environment_list}
        # Hardware data
        self.hardware = None
        # Streaming Information
        self.streaming = False
        self.has_streamed = False
        # Persistent data
        self.read_data = None
        self.output_indices = None
        # Abort and Warning Limits
        self.abort_limits = None
        self.warning_limits = None
        self._acquisition_active = acquisition_active

    @property
    def acquisition_active(self):
        return bool(self._acquisition_active.value)

    @acquisition_active.setter
    def acquisition_active(self, val):
        if val:
            self._acquisition_active.value = 1
        else:
            self._acquisition_active.value = 0

    def initialize_hardware(self, metadata: HardwareMetadata):
        if self.hardware is not None:
            self.hardware.close()
        if metadata.hardware_type == HardwareType.NI_DAQmx:
            from ..hardware.nidqaqmx import NIDAQmxAcquisition

            self.hardware = NIDAQmxAcquisition()
        # Initialize hardware and create channels
        self.hardware.set_up_data_acquisition_parameters_and_channels(metadata)
        # Set up warning and abort limits
        self.abort_limits = []
        self.warning_limits = []
        for channel in metadata.channel_list:
            try:
                warning_limit = float(channel.warning_level)
            except (ValueError, TypeError):
                warning_limit = float("inf")  # Never warn on this channel
            try:
                abort_limit = float(channel.abort_level)
            except (ValueError, TypeError):
                abort_limit = float("inf")  # Never abort on this channel if not specified
            self.warning_limits.append(warning_limit)
            self.abort_limits.append(abort_limit)
        self.abort_limits = np.array(self.abort_limits)
        self.warning_limits = np.array(self.warning_limits)
        self.output_indices = [
            index
            for index, channel in enumerate(metadata.channel_list)
            if not (channel.feedback_device is None) and not (channel.feedback_device.strip() == "")
        ]
        self.read_data = np.zeros(
            (
                len(metadata.channel_list),
                4
                * np.max(
                    [
                        metadata.samples_per_read,
                        metadata.samples_per_write // metadata.output_oversample,
                    ]
                ),
            )
        )
