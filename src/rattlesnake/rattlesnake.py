from .utilities import GlobalCommands, VerboseMessageQueue, QueueContainer, log_file_task
from .process.acquisition import acquisition_process
from .process.output import output_process
from .hardware.abstract_hardware import HardwareMetadata
from .environment.abstract_environment import EnvironmentMetadata
from .environment_manager import EnvironmentManager
import multiprocessing as mp
from datetime import datetime
from typing import List


class Rattlesnake:
    def __init__(self):
        # Initialize values for checking state
        self.shutdown_event = mp.Event()
        self.acquisition_active = mp.Value("i", 0)
        self.output_active = mp.Value("i", 0)

        # Start up log file process
        log_file_queue = mp.Queue()
        self.log_file_process = mp.Process()
        self.log_file_process = mp.Process(
            target=log_file_task,
            args=(
                log_file_queue,
                self.shutdown_event,
            ),
        )
        self.log_file_process.start()

        # Start up command queues and processes
        controller_command_queue = VerboseMessageQueue(log_file_queue, "Controller Communication Queue")
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
        self.acquisition_proc = mp.Process(
            target=acquisition_process,
            args=(self.queue_container, self.acquisition_active),
        )
        self.acquisition_proc.start()

        self.output_proc = mp.Process(target=output_process, args=(self.queue_container, self.output_active))
        self.output_proc.start()

        self.environment_manager = EnvironmentManager(self.queue_container)

    def set_hardware(self, hardware_metadata: HardwareMetadata) -> None:
        valid_hardware = hardware_metadata.validate()
        if not valid_hardware:
            raise TypeError("Rattlesnake.set_hardware requires a valid HardwareMetadata class")

        self.hardware_metadata = hardware_metadata

    def set_environments(self, environment_metadata_list: List[EnvironmentMetadata]):
        self.environment_manager.initialize_environments(environment_metadata_list, self.acquisition_active, self.output_active)

    def shutdown(self):
        # Close out of acquisition, output, streaming process
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

        # Close out of environment processes
        self.environment_manager.close_environments()

        # Close out log file process
        self.queue_container.log_file_queue.put("{:}: Joining Log File Process\n".format(datetime.now()))
        self.queue_container.log_file_queue.put(GlobalCommands.QUIT)
        self.log_file_process.join()
