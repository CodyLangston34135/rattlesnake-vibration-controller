from .utilities import GlobalCommands, VerboseMessageQueue, QueueContainer, EventContainer, log_file_task
from .process.controller import controller_process
from .process.acquisition import acquisition_process
from .process.output import output_process
from .process.streaming import StreamMetadata, streaming_process
from .profile_manager import ProfileManager, ProfileEvent
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


# region: RattlesnakeState
class RattlesnakeState(Enum):
    # We don't check for stored stream/profiles because they can be left blank
    INIT = 0  # Nothing is stored yet
    HARDWARE_STORE = 1  # Hardware has been stored
    ENVIRONMENT_STORE = 2  # Environments have been stored
    ACQUISITION_START = 3  # Acquisition has started
    OUTPUT_START = 4  # Profile/Environment output has started


# region: Rattlesnake
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
        log_close_event = mp.Event()
        self.log_file_process = mp.Process(
            target=log_file_task,
            args=(log_file_queue, log_close_event),
        )
        self.log_file_process.start()

        # Start up command queues and processes
        self.controller_queue_name_manager = mp.Manager()  # Adds minor overhead which is reasonable for COMMAND queues only
        controller_close_event = new_event()
        controller_ready_event = new_event()
        controller_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), self.controller_queue_name_manager, "Controller Command Queue")
        acquisition_close_event = new_event()
        acquisition_ready_event = new_event()
        acquisition_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), self.controller_queue_name_manager, "Acquisition Command Queue")
        output_close_event = new_event()
        output_ready_event = new_event()
        output_command_queue = VerboseMessageQueue(log_file_queue, mp.Queue(), self.controller_queue_name_manager, "Output Command Queue")
        streaming_close_event = new_event()
        streaming_ready_event = new_event()
        streaming_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), self.controller_queue_name_manager, "Streaming Command Queue")

        # Set up data queue
        input_output_sync_queue = new_queue()
        single_process_hardware_queue = new_queue()

        # Set up environment queues
        max_environments = 16
        environment_close_events = {}
        environment_ready_events = {}
        environment_command_queues = {}
        environment_data_in_queues = {}
        environment_data_out_queues = {}
        for env_idx in range(max_environments):
            environment_name = "Environment {:}".format(env_idx)
            environment_close_events[environment_name] = new_event()
            environment_ready_events = new_event()
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
        self.event_container = EventContainer(
            log_close_event,
            controller_close_event,
            acquisition_close_event,
            output_close_event,
            streaming_close_event,
            environment_close_events,
            controller_ready_event,
            acquisition_ready_event,
            output_ready_event,
            streaming_ready_event,
            environment_ready_events,
        )

        # Controller
        self.controller_proc = new_process(
            target=controller_process,
            args=(self.queue_container, self.event_container.controller_close_event),
        )
        self.controller_proc.start()
        # Acquisition
        self.acquisition_proc = new_process(
            target=acquisition_process,
            args=(self.queue_container, self.acquisition_active, self.event_container.acquisition_close_event),
        )
        self.acquisition_proc.start()
        # Output

        self.output_proc = new_process(
            target=output_process, args=(self.queue_container, self.output_active, self.event_container.output_close_event)
        )
        self.output_proc.start()
        # Streaming
        self.streaming_proc = new_process(target=streaming_process, args=(self.queue_container, self.event_container.streaming_close_event))
        self.streaming_proc.start()

        # Set up managers that will setup processes and store metadata
        self.environment_manager = EnvironmentManager(  # Contains hardware/environment metadata
            self.queue_container, self.event_container.environment_ready_events, self.event_container.environment_close_events, THREADING
        )
        self._stream_metadata = StreamMetadata()  # Default to StreamType.NO_STREAM
        self.profile_manager = ProfileManager(  # Contains instructions/profile events
            self.queue_container.log_file_queue, self.queue_container.controller_command_queue
        )

    # Metadata properties
    @property
    def hardware_metadata(self):
        return self.environment_manager.hardware_metadata

    @property
    def environment_metadata_dict(self):
        return self.environment_manager.environment_metadata

    @property
    def stream_metadata(self):
        return self._stream_metadata

    @property
    def environment_instructions_list(self):
        return self.profile_manager.environment_instructions

    @property
    def profile_event_list(self):
        return self.profile_manager.profile_event_list

    def set_hardware(self, hardware_metadata: HardwareMetadata) -> None:
        """Validates hardware_metadata and sends data to relevant processes"""
        # Validate Rattlesnake State
        if self.state not in (RattlesnakeState.INIT, RattlesnakeState.HARDWARE_STORE, RattlesnakeState.ENVIRONMENT_STORE):
            raise RuntimeError(f"Invalid state for this setting hardware: {self.state}")
        # Validate hardware
        if not isinstance(hardware_metadata, HardwareMetadata):
            raise TypeError("Rattlesnake.set_hardware requires a valid HardwareMetadata class")
        valid_hardware = hardware_metadata.validate()
        if not valid_hardware:
            raise TypeError("Rattlesnake.set_hardware requires a valid HardwareMetadata class")

        # Send hardware metadata to the correct processes
        self.log("Setting Hardware")
        self.environment_manager.initialize_hardware(hardware_metadata)
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))

        self.state = RattlesnakeState.HARDWARE_STORE

    def set_environments(self, environment_metadata_list: List[EnvironmentMetadata]):
        """Validates environment_metadata, starts up environment processes, assigns queues,
        and sends data to relevant processes"""
        # Validate Rattlesnake State
        if self.state not in (RattlesnakeState.HARDWARE_STORE, RattlesnakeState.ENVIRONMENT_STORE):
            raise RuntimeError(f"Invalid state for setting environment: {self.state}")
        # Validate environment metadata list
        self.environment_manager.validate_environment_metadata(environment_metadata_list)

        # Send environment meetadata to correct processes
        self.log("Setting Environment")
        self.environment_manager.initialize_environments(environment_metadata_list, self.acquisition_active, self.output_active)
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, self.environment_metadata_dict))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, self.environment_metadata_dict))

        # Check if this removed all the environmetns or not
        if not self.environment_metadata_dict:
            self.state = RattlesnakeState.HARDWARE_STORE
        else:
            self.state = RattlesnakeState.ENVIRONMENT_STORE

    def start_acquisition(self, stream_metadata: StreamMetadata):
        # Validate Rattlesnake State
        if self.state != RattlesnakeState.ENVIRONMENT_STORE:
            raise RuntimeError(f"Invalid state for starting acquisition: {self.state}")
        # Validate stream metadata
        if not isinstance(self.stream_metadata, StreamMetadata):
            raise TypeError("Rattlesnake.set_stream requires a valid StreamMetadata class")
        valid_stream = stream_metadata.validate()
        if not valid_stream:
            raise TypeError("Rattlesnake.set_stream requires a valid StreamMetadata class")

        # Store streaming metadata to controller (side note: ControllerProcess decides when/why to stream not StreamingProcess)
        self.log("Setting Stream Metadata")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_STREAMING, stream_metadata))
        self.queue_container.streaming_command_queue.put(
            TASK_NAME,
            (GlobalCommands.INITIALIZE_STREAMING, (self.stream_metadata, self.hardware_metadata, self.environment_metadata_dict)),
        )
        self._stream_metadata = stream_metadata

        # Tell controller to start up the hardware, controller takes over logic from here
        self.log("Arming Test Hardware")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, None))

        self.state = RattlesnakeState.ACQUISITION_START

    def stop_acquisition(self):
        # Validate rattlesnake state (rattlesnake was acquiring data)
        if self.state not in (RattlesnakeState.ACQUISITION_START, RattlesnakeState.OUTPUT_START):
            raise RuntimeError(f"Invalid state for stopping acquisition: {self.state}")

        self.log("Disarming Test Hardware")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, None))
        for queue_name in self.environment_metadata_dict.keys():
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, None))

        self.state = RattlesnakeState.ENVIRONMENT_STORE

    def start_profile(self, profile_event_list: List[ProfileEvent], environment_instructions_list: List[EnvironmentInstructions]):
        self.log("Settting Profile Event List")
        if self.state != RattlesnakeState.ACQUISITION_START:
            raise RuntimeError(f"Invalid state to start profile: {self.state}")

        # Validate and assign queue_names to events and instructions
        environment_instructions_dict = self.environment_manager.validate_environment_instructions(environment_instructions_list)
        self.environment_manager.validate_profile_events(profile_event_list)
        self.profile_manager.validate_profile_list(profile_event_list, environment_instructions_dict)

        # Start profile
        self.log("Starting Profile")
        self.profile_manager.start_profile(profile_event_list, environment_instructions_dict)

    def stop_profile(self):
        self.log("Stopping Profile")
        self.profile_manager.stop_profile()

    def shutdown(self):
        # Close out of acquisition, output, streaming process
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Controller Process\n")
        self.queue_container.controller_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.controller_proc.join(timeout=CLOSE_TIMEOUT)
        if self.controller_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Controller Process\n")
            self.event_container.controller_close_event.set()
            self.controller_proc.join(timeout=CLOSE_TIMEOUT)
            if self.controller_proc.is_alive() and not THREADING:
                self.controller_proc.terminate()
                self.controller_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Acquisition Process\n")
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.acquisition_proc.join(timeout=CLOSE_TIMEOUT)
        if self.acquisition_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Acquisition Process\n")
            self.event_container.acquisition_close_event.set()
            self.acquisition_proc.join(timeout=CLOSE_TIMEOUT)
            if self.acquisition_proc.is_alive() and not THREADING:
                self.acquisition_proc.terminate()
                self.acquisition_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Output Process\n")
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.output_proc.join(timeout=CLOSE_TIMEOUT)
        if self.output_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Output Process\n")
            self.event_container.output_close_event.set()
            self.output_proc.join(timeout=CLOSE_TIMEOUT)
            if self.output_proc.is_alive() and not THREADING:
                self.output_proc.terminate()
                self.output_proc.join()
        self.queue_container.log_file_queue.put(f"{datetime.now()}: Joining Streaming Process\n")
        self.queue_container.streaming_command_queue.put(TASK_NAME, (GlobalCommands.QUIT, None))
        self.streaming_proc.join(timeout=CLOSE_TIMEOUT)
        if self.streaming_proc.is_alive():
            self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing Streaming Process\n")
            self.event_container.streaming_close_event.set()
            self.streaming_proc.join(timeout=CLOSE_TIMEOUT)
            if self.streaming_proc.is_alive() and not THREADING:
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
