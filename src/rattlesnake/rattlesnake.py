from .utilities import GlobalCommands, VerboseMessageQueue, QueueContainer, log_file_task
from .process.controller import controller_process
from .process.acquisition import acquisition_process
from .process.output import output_process
from .process.streaming import StreamType, StreamMetadata, streaming_process
from .hardware.abstract_hardware import HardwareMetadata
from .environment.abstract_environment import EnvironmentMetadata, EnvironmentInstructions
from .environment_manager import EnvironmentManager
import multiprocessing as mp
import threading
import queue as thqueue
from enum import Enum
from datetime import datetime
from typing import List

TASK_NAME = "Rattlesnake"
CLOSE_TIMEOUT = 5
THREADING = True


class RattlesnakeState(Enum):
    # We don't check for stored stream/profiles because they can be left blank
    INIT = 0  # Nothing is stored yet
    HARDWARE_STORE = 1  # Hardware has been stored
    ENVIRONMENT_STORE = 2  # Environments have been stored
    ACQUISITION_START = 3  # Acquisition has started
    OUTPUT_START = 4  # Profile/Environment output has started


class Rattlesnake:
    def __init__(self):
        # Initialize values for checking state
        self.state = RattlesnakeState.INIT
        self.acquisition_active = mp.Value("i", 0)
        self.output_active = mp.Value("i", 0)

        if THREADING:
            new_queue = thqueue.Queue  # threading-safe in-memory queue
            new_process = threading.Thread  # worker threads
            new_event = threading.Event  # optional stop flag
        else:
            new_queue = mp.Queue  # multiprocessing queue
            new_process = mp.Process  # worker processes
            new_event = mp.Event  # optional stop flag

        # Start up log file process
        log_file_queue = mp.Queue()
        self.log_file_process = mp.Process(target=log_file_task, args=(log_file_queue,))
        self.log_file_process.start()

        # Start up command queues and processes
        self.controller_queue_name_manager = mp.Manager()  # Adds minor overhead which is reasonable for COMMAND queues only
        controller_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), self.controller_queue_name_manager, "Controller Command Queue")
        acquisition_command_queue = VerboseMessageQueue(log_file_queue, mp.Queue(), self.controller_queue_name_manager, "Acquisition Command Queue")
        output_command_queue = VerboseMessageQueue(log_file_queue, mp.Queue(), self.controller_queue_name_manager, "Output Command Queue")
        streaming_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), self.controller_queue_name_manager, "Streaming Command Queue")

        # Set up data queue
        input_output_sync_queue = new_queue()
        single_process_hardware_queue = new_queue()

        # Set up environment queues
        max_environments = 16
        self.environment_metadata_list = []
        environment_command_queues = {}
        environment_data_in_queues = {}
        environment_data_out_queues = {}
        for env_idx in range(max_environments):
            environment_name = "Environment {:}".format(env_idx)
            environment_command_queues[environment_name] = VerboseMessageQueue(
                log_file_queue, mp.Queue(), self.controller_queue_name_manager, environment_name + " Command Queue"
            )
            environment_data_in_queues[environment_name] = new_queue()
            environment_data_out_queues[environment_name] = new_queue()

        # Set up output queue
        gui_update_queue = new_queue()

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

        self.controller_proc = new_process(target=controller_process, args=(self.queue_container,))
        self.controller_proc.start()
        self.acquisition_proc = new_process(
            target=acquisition_process,
            args=(self.queue_container, self.acquisition_active),
        )
        self.acquisition_proc.start()
        self.output_proc = new_process(target=output_process, args=(self.queue_container, self.output_active))
        self.output_proc.start()
        self.streaming_proc = new_process(target=streaming_process, args=(self.queue_container,))
        self.streaming_proc.start()

        # Set up environment manager for future environment processes
        self.environment_manager = EnvironmentManager(self.queue_container, THREADING)

        self.hardware_metadata = None
        self.environment_metadata_list = []
        self.stream_metadata = StreamMetadata()  # Default to no stream
        self.profile_event_list = []

    def set_hardware(self, hardware_metadata: HardwareMetadata) -> None:
        # Check for valid states
        if not self.state == RattlesnakeState.INIT or self.state == RattlesnakeState.ENVIRONMENT_STORE:
            raise RuntimeError(f"Invalid state for this setting hardware: {self.state}")

        valid_hardware = hardware_metadata.validate()
        if not valid_hardware:
            raise TypeError("Rattlesnake.set_hardware requires a valid HardwareMetadata class")

        self.log("Setting Hardware")
        self.hardware_metadata = hardware_metadata

        self.environment_manager.initialize_hardware(hardware_metadata)

        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))

        self.state = RattlesnakeState.HARDWARE_STORE

    def set_environments(self, environment_metadata_list: List[EnvironmentMetadata]):
        # Check for valid states
        if not self.state == RattlesnakeState.HARDWARE_STORE or self.state == RattlesnakeState.ENVIRONMENT_STORE:
            raise RuntimeError(f"Invalid state for setting environment: {self.state}")

        self.log("Setting Environment")

        environment_metadata_list = self.environment_manager.initialize_environments(
            environment_metadata_list, self.acquisition_active, self.output_active
        )

        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, environment_metadata_list))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, environment_metadata_list))

        self.environment_metadata_list = environment_metadata_list
        self.state = RattlesnakeState.ENVIRONMENT_STORE

    def set_stream(self, stream_metadata: StreamMetadata):
        valid_stream = stream_metadata.validate()
        if not valid_stream:
            raise TypeError("Rattlesnake.set_stream requires a valid StreamMetadata class")

        self.log("Setting Stream Metadata")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_STREAMING, stream_metadata))
        self.stream_metadata = stream_metadata

    def set_instructions(self, environment_instructions_list: List[EnvironmentInstructions]):
        # This is something that will be called when "Start Test From Profile" is called.
        # Will mainly validate the list of instructions and map it onto the profile manager
        # so that it has an initial state for when the profile events change the instructions
        pass
        # self.log("Setting Instructions")
        # queue_names_dict = self.environment_manager.queue_names_dict

        # for instruction in environment_instructions_list:
        #     try:
        #         instruction.queue_name = queue_names_dict[instruction.environment_name]
        #     except KeyError:
        #         raise KeyError(f"No environment found for {instruction.environment_name}")
        #     self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_INSTRUCTION, instruction))

    def set_profile(self, profile_event_list):
        self.log("Settting Profile Event List")

        queue_names_dict = self.environment_manager.queue_names_dict

        for profile_event in self.profile_event_list:
            try:
                profile_event.queue_name = queue_names_dict[profile_event.environment_name]
            except KeyError:
                raise KeyError(f"No environment found for {profile_event.environment_name}")

            if profile_event.operation not in self.command_map:
                pass

        self.profile_event_list = profile_event_list

    def start_acquisition(self):
        # Check for basic issues
        if not self.state == RattlesnakeState.ENVIRONMENT_STORE or self.state == RattlesnakeState.OUTPUT_START:
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

        self.state = RattlesnakeState.ACQUISITION_START

    def stop_acquisition(self):
        if not self.state == RattlesnakeState.ACQUISITION_START or self.state == RattlesnakeState.OUTPUT_START:
            raise RuntimeError(f"Invalid state for stopping acquisition: {self.state}")

        self.log("Disarming Test Hardware")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, None))
        for metadata in self.environment_metadata_list:
            self.queue_container.environment_command_queues[metadata.queue_name].put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, None))

        self.state = RattlesnakeState.ENVIRONMENT_STORE

    def start_profile(self):
        pass

    def shutdown(self):
        # Close out of acquisition, output, streaming process
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Controller Process\n")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.controller_proc.join(timeout=CLOSE_TIMEOUT)
        if self.controller_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Controller Process\n")
            self.controller_proc.terminate()
            self.controller_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Acquisition Process\n")
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.acquisition_proc.join(timeout=CLOSE_TIMEOUT)
        if self.acquisition_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Acquisition Process\n")
            self.acquisition_proc.terminate()
            self.acquisition_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Output Process\n")
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.output_proc.join(timeout=CLOSE_TIMEOUT)
        if self.output_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Output Process\n")
            self.output_proc.terminate()
            self.output_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Streaming Process\n")
        self.queue_container.streaming_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.streaming_proc.join(timeout=CLOSE_TIMEOUT)
        if self.streaming_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Streaming Process\n")
            self.streaming_proc.terminate()
            self.streaming_proc.join()

        # Close out of environment processes
        self.environment_manager.close_environments(CLOSE_TIMEOUT)

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
