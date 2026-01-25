from .hardware.abstract_hardware import HardwareMetadata
from .utilities import GlobalCommands, VerboseMessageQueue, QueueContainer, log_file_task
import multiprocessing as mp
from datetime import datetime


class Rattlesnake:
    def __init__(self):
        # Initialize values for checking state
        self.shutdown_event = mp.Event()
        self.acquistion_ready = mp.Value("b", False)
        self.output_ready = mp.Value("b", False)
        self.acquisition_active = mp.Value("i", 0)
        self.output_active = mp.Value("i", 0)

        # Start up log file process
        self.log_file_queue = mp.Queue()
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
        self.environment_command_queues = {}
        self.acquisition_command_queue = VerboseMessageQueue(
            self.log_file_queue, "Acquisition Command Queue"
        )
        self.output_command_queue = VerboseMessageQueue(self.log_file_queue, "Output Command Queue")
        self.streaming_command_queue = VerboseMessageQueue(
            self.log_file_queue, "Streaming Command Queue"
        )
        self.acquisition_process = mp.Process()
        self.output_process = mp.Process()
        self.streaming_process = mp.Process()

        # Set up output queue
        self.gui_update_queue = mp.Queue()

    def set_hardware(self, hardware_metadata: HardwareMetadata):
        if not isinstance(hardware_metadata, HardwareMetadata):
            raise TypeError("Rattlesnake.set_hardware requires a HardwareMetadata class")
        self.hardware_metadata = hardware_metadata

    def shutdown(self):
        self.log_file_queue.put("{:}: Joining Log File Process\n".format(datetime.now()))
        self.log_file_queue.put(GlobalCommands.QUIT)
        self.log_file_process.join()
