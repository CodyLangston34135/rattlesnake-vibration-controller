from .utilities import GlobalCommands, VerboseMessageQueue, QueueContainer, log_file_task
from .process.controller import controller_process
from .process.acquisition import acquisition_process
from .process.output import output_process
from .process.streaming import StreamType, StreamMetadata, streaming_process
from .hardware.abstract_hardware import HardwareMetadata
from .environment.abstract_environment import EnvironmentMetadata
from .environment_manager import EnvironmentManager
import multiprocessing as mp
from enum import Enum
from datetime import datetime
from typing import List

TASK_NAME = "Rattlesnake"


class RattlesnakeState(Enum):
    INIT = 0
    HARDWARE_STORE = 1
    ENVIRONMENT_STORE = 2
    ACQUISITION_START = 3
    OUTPUT_START = 4


class Rattlesnake:
    def __init__(self):
        # Initialize values for checking state
        self.state = mp.Value("i", RattlesnakeState.INIT.value)
        self.acquisition_active = mp.Value("i", 0)
        self.output_active = mp.Value("i", 0)

        # Start up log file process
        log_file_queue = mp.Queue()
        self.log_file_process = mp.Process()
        self.log_file_process = mp.Process(
            target=log_file_task,
            args=(log_file_queue),
        )
        self.log_file_process.start()

        # Start up command queues and processes
        controller_command_queue = VerboseMessageQueue(log_file_queue, "Controller Command Queue")
        acquisition_command_queue = VerboseMessageQueue(log_file_queue, "Acquisition Command Queue")
        output_command_queue = VerboseMessageQueue(log_file_queue, "Output Command Queue")
        streaming_command_queue = VerboseMessageQueue(log_file_queue, "Streaming Command Queue")
        self.acquisition_process = mp.Process()
        self.output_process = mp.Process()
        self.streaming_process = mp.Process()

        # Set up data queue
        input_output_sync_queue = mp.Queue()
        single_process_hardware_queue = mp.Queue()

        # Set up environment queues
        max_environments = 16
        self.environment_metadata_list = []
        environment_command_queues = {}
        environment_data_in_queues = {}
        environment_data_out_queues = {}
        for env_idx in range(max_environments):
            environment_name = "Environment {:}".format(env_idx)
            environment_command_queues[environment_name] = VerboseMessageQueue(log_file_queue, environment_name + " Command Queue")
            environment_data_in_queues[environment_name] = mp.Queue()
            environment_data_out_queues[environment_name] = mp.Queue()

        # Set up output queue
        gui_update_queue = mp.Queue()

        # Build queue container
        self.queue_container = QueueContainer(
            controller_command_queue,
            acquisition_command_queue,
            output_command_queue,
            streaming_command_queue,
            log_file_queue,
            input_output_sync_queue,
            single_process_hardware_queue,
            gui_update_queue,
            environment_command_queues,
            environment_data_in_queues,
            environment_data_out_queues,
        )

        # Start up acquisition, output, streaming processes
        self.controller_proc = mp.Process(target=controller_process, args=(self.queue_container,))
        self.acquisition_proc = mp.Process(
            target=acquisition_process,
            args=(self.queue_container, self.acquisition_active),
        )
        self.acquisition_proc.start()
        self.output_proc = mp.Process(target=output_process, args=(self.queue_container, self.output_active))
        self.output_proc.start()
        self.streaming_proc = mp.Process(target=streaming_process, args=(self.queue_container,))
        self.streaming_proc.start()

        # Set up environment manager for future environment processes
        self.environment_manager = EnvironmentManager(self.queue_container)

        self.hardware_metadata = None
        self.environment_metadata_list = []
        self.stream_metadata = None
        self.profile_metadata = None

    def set_hardware(self, hardware_metadata: HardwareMetadata) -> None:
        # Check for valid states
        if not self.state == RattlesnakeState.INIT or self.state == RattlesnakeState.ENVIRONMENT_STORE:
            raise RuntimeError(f"Invalid state for this setting hardware: {self.state}")

        valid_hardware = hardware_metadata.validate()
        if not valid_hardware:
            raise TypeError("Rattlesnake.set_hardware requires a valid HardwareMetadata class")

        self.log("Setting Hardware")
        self.hardware_metadata = hardware_metadata

        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))

        self.state = RattlesnakeState.HARDWARE_STORE

    def set_environments(self, environment_metadata_list: List[EnvironmentMetadata]):
        # Check for valid states
        if self.state != RattlesnakeState.HARDWARE_STORE or self.state != RattlesnakeState.ENVIRONMENT_STORE:
            raise RuntimeError(f"Invalid state for setting environment: {self.state}")

        self.log("Setting Environment")

        self.environment_metadata_list = self.environment_manager.initialize_environments(
            environment_metadata_list, self.acquisition_active, self.output_active
        )

    def set_stream(self, stream_metadata: StreamMetadata):
        valid_stream = stream_metadata.validate()
        if not valid_stream:
            raise TypeError("Rattlesnake.set_stream requires a valid StreamMetadata class")

        self.stream_metadata = stream_metadata

    def set_profile(self, profile_metadata):
        pass

    def start_acquisition(self):
        # Check for basic issues
        if self.state != RattlesnakeState.ENVIRONMENT_STORE or self.state != RattlesnakeState.OUTPUT_START:
            raise RuntimeError(f"Invalid state for starting acquisition: {self.state}")
        if not isinstance(self.stream_metadata, StreamMetadata):
            raise TypeError(f"Stream metadata must be defined before arming data acquisition")

        self.log("Arming Test Hardware")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, None))

        if self.stream_metadata.stream_type != StreamType.NO_STREAM:
            self.queue_container.streaming_command_queue.put(
                TASK_NAME,
                (GlobalCommands.INITIALIZE_STREAMING, (self.stream_metadata.stream_file, self.hardware_metadata, self.environment_metadata_list)),
            )

        if self.stream_metadata.stream_type == StreamType.STREAM_IMMEDIATELY:
            self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.START_STREAMING, None))

    def stop_acquisition(self):
        self.log("Disarming Test Hardware")
        for metadata in self.environment_metadata_list:
            self.queue_container.controller_command_queue.put(
                TASK_NAME,
            )
        self.queue_container.controller_communication_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, None))

    def shutdown(self):
        # Close out of acquisition, output, streaming process
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Controller Process\n")
        self.controller_proc.join(timeout=5)
        if self.controller_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Controller Process\n")
            self.controller_proc.terminate()
            self.controller_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Acquisition Process\n")
        self.acquisition_proc.join(timeout=5)
        if self.acquisition_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Acquisition Process\n")
            self.acquisition_proc.terminate()
            self.acquisition_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Output Process\n")
        self.output_proc.join(timeout=5)
        if self.output_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Output Process\n")
            self.output_proc.terminate()
            self.output_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Streaming Process\n")
        self.streaming_proc.join(timeout=5)
        if self.streaming_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Streaming Process\n")
            self.streaming_proc.terminate()
            self.streaming_proc.join()

        # Close out of environment processes
        self.environment_manager.close_environments()

        # Close out log file process
        self.queue_container.log_file_queue.put("{:}: Joining Log File Process\n".format(datetime.now()))
        self.queue_container.log_file_queue.put(GlobalCommands.QUIT)
        self.log_file_process.join()

    def log(self, string):
        """Pass a message to the log_file_queue along with date/time and task name

        Parameters
        ----------
        string : str
            Message that will be written to the queue

        """
        self.queue_container.log_file_queue.put(f"{datetime.now()}: {TASK_NAME} -- {string}\n")
