from .hardware.abstract_hardware import HardwareMetadata
from .environment.abstract_environment import EnvironmentMetadata
from .utilities import GlobalCommands, VerboseMessageQueue, QueueContainer, log_file_task
import multiprocessing as mp
from datetime import datetime
from typing import List


class Rattlesnake:
    def __init__(self):
        # Initialize values for checking state
        self.shutdown_event = mp.Event()
        acquistion_ready = mp.Value("i", 0)
        output_ready = mp.Value("i", 0)
        acquisition_active = mp.Value("i", 0)
        output_active = mp.Value("i", 0)

        # Start up log file process
        log_file_queue = mp.Queue()
        self.log_file_process = mp.Process()
        self.log_file_process = mp.Process(
            target=log_file_task,
            args=(
                self.log_file_queue,
                self.shutdown_event,
            ),
        )
        self.log_file_process.start()

        # Start up command queues and processes
        acquisition_command_queue = VerboseMessageQueue(self.log_file_queue, "Acquisition Command Queue")
        output_command_queue = VerboseMessageQueue(self.log_file_queue, "Output Command Queue")
        streaming_command_queue = VerboseMessageQueue(self.log_file_queue, "Streaming Command Queue")
        self.acquisition_process = mp.Process()
        self.output_process = mp.Process()
        self.streaming_process = mp.Process()

        # Set up data queue
        input_output_sync_queue = mp.Queue()
        acquisition_to_streaming_queue = mp.Queue()
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
        queue_container = QueueContainer(
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

    def set_hardware(self, hardware_metadata: HardwareMetadata) -> None:
        if not isinstance(hardware_metadata, HardwareMetadata):
            raise TypeError("Rattlesnake.set_hardware requires a HardwareMetadata class")
        self.hardware_metadata = hardware_metadata

    def set_environments(self, environment_metadata_list: List[EnvironmentMetadata]) -> None:
        # For environment stuff
        # Acquisition needs: List of environment names, correct environment queue dict
        for metadata in environment_metadata_list:
            if metadata.environment_name in self.environment_names:
                # This is going to be sending environment metadata to the stuff
                pass

    def shutdown(self):
        self.log_file_queue.put("{:}: Joining Log File Process\n".format(datetime.now()))
        self.log_file_queue.put(GlobalCommands.QUIT)
        self.log_file_process.join()
