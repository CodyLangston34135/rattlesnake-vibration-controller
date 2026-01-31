from .utilities import QueueContainer, GlobalCommands
from .profile_manager import ProfileEvent
from .environment.abstract_environment import EnvironmentMetadata, EnvironmentInstructions
from .environment.environment_utilities import ControlTypes
from .hardware.abstract_hardware import HardwareMetadata
import multiprocessing as mp
import threading
from datetime import datetime
from typing import List

TASK_NAME = "Environment Manager"
CLOSE_TIMEOUT = 5


# region: EnvironmentManager
class EnvironmentManager:
    """
    A container class that stores the environment information.

    This class is responsible for spinning up and shutting down environment
    processes given a list of environments needed for the controller. This
    class should mainly deal with putting and getting data from
    environment_command_queues and let the main Rattlesnake() class deal
    with the other queues.
    """

    def __init__(self, queue_container: QueueContainer, threading_bool):
        self.hardware_metadata = None
        self.queue_names = []  # Static name for dictionary keys, process names, etc
        self.environment_names = {}  # Name of environment for Ui purposes
        self.environment_types = {}
        self.environment_metadata = {}
        self.environment_processes = {}
        self.environment_events = {}
        self.queue_container = queue_container
        self._threading = threading_bool
        if threading_bool:
            self.new_process = threading.Thread
            self.new_event = threading.Event
        else:
            self.new_process = mp.Process
            self.new_event = mp.Event

    @property
    def available_queues(self):
        all_queue_names = list(self.queue_container.environment_command_queues.keys())
        return [queue_name for queue_name in all_queue_names if queue_name not in self.queue_names]

    @property
    def num_queues(self):
        return len(self.queue_names) + len(self.available_queues)

    @property
    def queue_names_dict(self):
        return {self.environment_names[queue_name]: queue_name for queue_name in self.queue_names}

    @property
    def threading(self):
        return self._threading

    def log(self, message):
        """Write a message to the log file

        This function puts a message onto the ``log_file_queue`` so it will
        eventually be written to the log file.

        When written to the log file, the message will include the date and
        time that the message was queued, the name of the environment, and
        then the message itself.

        Parameters
        ----------
        message : str :
            A message that will be written to the log file.

        """
        self.queue_container.log_file_queue.put(f"{datetime.now()}: {TASK_NAME} -- {message}\n")

    def initialize_hardware(self, hardware_metadata: HardwareMetadata):
        self.log("Initializing Hardware")
        for queue_name in self.queue_names:
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))

        self.hardware_metadata = hardware_metadata

    def initialize_environments(self, metadata_list: List[EnvironmentMetadata], acquisition_active, output_active):
        self.log("Initializing Environments")
        mapped_queue_names = set()
        extra_metadata = []

        # Check if there is an existing process that maps to this environment type
        # If there is, hijack it and give it new metadata
        for metadata in metadata_list:
            valid_environment = metadata.validate()
            if not valid_environment:
                raise TypeError("Rattlesnake.set_environment requires a valid EnvironmentMetadata class")

            environment_type = metadata.environment_type
            environment_name = metadata.environment_name

            queue_name = next(
                (name for name, env_type in self.environment_types.items() if env_type == environment_type and name not in mapped_queue_names),
                None,
            )

            if queue_name is None:
                extra_metadata.append(metadata)
                continue

            self.log(f"Assigning {environment_name} to {queue_name} Queue")
            self.environment_types[queue_name] = environment_type
            self.environment_names[queue_name] = environment_name
            self.environment_metadata[queue_name] = metadata
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, self.hardware_metadata))
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, metadata))

            mapped_queue_names.add(queue_name)

        # Close existing processes that dont have metadata associated with them
        unmapped_queue_names = set(self.environment_types.keys()) - mapped_queue_names
        for queue_name in unmapped_queue_names:
            self.remove_environment(queue_name)

        # Add process for metadata that needs a new process. Could do this in loop above
        # but I want to clear up queue_names before assigning new ones
        for metadata in extra_metadata:
            self.add_environment(metadata, acquisition_active, output_active)

    def validate_environment_metadata(self, metadata_list: List[EnvironmentMetadata]):
        # Check if there are available queues
        if len(metadata_list) > self.num_queues:
            raise IndexError("Not enough environment command queues. Increase max_environments in rattlesnake.py")

        # Validate individual environments
        environment_name_set = set()
        for metadata in metadata_list:
            # Check for valid class
            if not isinstance(metadata, EnvironmentMetadata):
                raise TypeError("Rattlesnake.set_environment was given an object that is not an EnvironmentMetadata class")
            # Check for unique name
            environment_name = metadata.environment_name
            if environment_name in environment_name_set:
                raise ValueError("Environment names must be unique")
            environment_name_set.add(environment_name)
            # Validate metadata
            valid_metadata = metadata.validate()
            if not valid_metadata:
                raise ValueError(f"Invalid metadata for {environment_name}")

    def validate_environment_instructions(self, environment_instructions_list: List[EnvironmentInstructions]):
        """Since the instructions will come from the UI/Termina which has
        no idea which queue was assigned to an environment, the validation of
        the environment_names is performed by the environment manager"""
        # Initialize dictionary with None for instructions
        environment_instructions_dict = {}
        for queue_name in self.queue_names:
            environment_instructions_dict[queue_name] = None

        # Validate instructions
        for instructions in environment_instructions_list:
            # Validate class
            if not isinstance(instructions, EnvironmentInstructions):
                raise TypeError("The environment_instructions_list contains an object that is not an EnvironmentInstructions type")
            # Validate name
            environment_name = instructions.environment_name
            try:
                queue_name = self.queue_names_dict[environment_name]
            except KeyError:
                raise KeyError(f"No environments exist for {environment_name} instruction")
            # Validate type
            environment_type = instructions.environment_type
            if environment_type != self.environment_types[queue_name]:
                raise TypeError(
                    f"Instructions for {environment_name} is the wrong type for {environment_type} vs {self.environment_types[queue_name]}"
                )
            # Validate instruction
            valid_instruction = instructions.validate()
            if not valid_instruction:
                raise ValueError(f"Invalid instruction for {environment_name}")

            # Add instructions to dict
            environment_instructions_dict[queue_name] = instructions
        return environment_instructions_dict

    def validate_profile_events(self, profile_events_list: List[ProfileEvent]):
        """Since the profile events are comming form the UI/Terminal which has
        no idea which queue was assigned to an environment, the validation of
        the environment_names is performed by the environment manager"""
        for profile_event in profile_events_list:
            # Validate class
            if not isinstance(profile_event, ProfileEvent):
                raise TypeError("The profile_events_list contains an object that is not a ProfileEvent type")
            # Validate environment_name and assign queue_name and type
            environment_name = profile_event.environment_name
            if environment_name == "Global":
                profile_event._queue_name = "Global"
                profile_event._environment_type = "Global"
            else:
                try:
                    queue_name = self.queue_names_dict[environment_name]
                except KeyError:
                    raise KeyError(f"No environments exist for {environment_name} instruction")
                profile_event._queue_name = queue_name
                profile_event._environment_type = self.environment_types[queue_name]

    def clear_environments(self):
        self.queue_names = []
        self.environment_types = {}
        self.environment_names = {}
        self.environment_metadata = {}
        self.close_environments()
        self.environment_processes = {}
        self.environment_events = {}

    def add_environment(self, metadata: EnvironmentMetadata, acquisition_active, output_active):
        """Adds environment to container with unique name"""
        # Find the first available queue for the environment
        queue_name = None
        for queue_name in self.available_queues:
            if queue_name not in self.queue_names:
                queue_name = str(queue_name)
                break

        if queue_name is None:
            raise KeyError("Not enough environment command queues. Increase max_environments in rattlesnake.py")

        environment_type = metadata.environment_type
        environment_name = metadata.environment_name

        self.queue_container.environment_command_queues[queue_name].assign_environment(environment_name)
        environment_event = self.new_event()

        # Figure out what type of environment to add
        if environment_type == ControlTypes.TIME:
            from .environment.time_environment import time_process

            self.queue_container.environment_command_queues[queue_name].assign_environment(environment_name)
            environment_process = self.new_process(
                target=time_process,
                args=(
                    environment_name,
                    queue_name,
                    self.queue_container.environment_command_queues[queue_name],
                    self.queue_container.gui_update_queue,
                    self.queue_container.controller_command_queue,
                    self.queue_container.log_file_queue,
                    self.queue_container.environment_data_in_queues[queue_name],
                    self.queue_container.environment_data_out_queues[queue_name],
                    acquisition_active,
                    output_active,
                    environment_event,
                ),
            )
            environment_process.start()
        elif environment_type == ControlTypes.READ:
            from .environment.read_environment import read_process

            environment_process = self.new_process(
                target=read_process,
                args=(
                    queue_name,
                    self.queue_container.environment_command_queues[queue_name],
                    self.queue_container.gui_update_queue,
                    self.queue_container.controller_command_queue,
                    self.queue_container.log_file_queue,
                    self.queue_container.environment_data_in_queues[queue_name],
                    self.queue_container.environment_data_out_queues[queue_name],
                    acquisition_active,
                    output_active,
                    environment_event,
                ),
            )
            environment_process.start()
        else:  # If "Select Environment" was chosen
            return

        # Store the environment to the container
        self.log(f"Assigning {environment_name} to {queue_name} Queue")
        self.queue_names.append(queue_name)
        self.environment_names[queue_name] = environment_name
        self.environment_types[queue_name] = environment_type
        self.environment_processes[queue_name] = environment_process
        self.environment_events[queue_name] = environment_event
        self.environment_metadata[queue_name] = metadata
        self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_HARDWARE, self.hardware_metadata))
        self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, metadata))

    def remove_environment(self, queue_name):
        """Removes environment from container"""
        # Check if index corresponds to an existing environment
        if queue_name in self.queue_names:
            self.log(f"Removing {self.environment_names[queue_name]}, Clearing up {queue_name} Queue")
            self.queue_names.remove(queue_name)
            self.environment_names.pop(queue_name, None)
            self.environment_types.pop(queue_name, None)
            self.environment_metadata.pop(queue_name, None)

            # Join environment process
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.QUIT, None))
            self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.datetime.now(), queue_name))
            self.environment_processes[queue_name].join(timeout=5)
            if self.environment_processes[queue_name].is_alive():
                self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing {queue_name} Process\n")
                self.environment_events[queue_name].set()
                self.environment_processes[queue_name].join(timeout=CLOSE_TIMEOUT)
                if self.environment_processes[queue_name].is_alive() and not self.threading:
                    self.environment_processes[queue_name].terminate()
                    self.environment_processes[queue_name].join()

            # Remove environment queue and process
            self.environment_processes.pop(queue_name, None)
            self.environment_events.pop(queue_name, None)

        else:
            raise IndexError(f"Invalid control name: {queue_name}. Must be mapped to available queue")

    def close_environments(self):
        for queue_name, environment_process in self.environment_processes.items():
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.QUIT, None))
            self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.now(), queue_name))
            environment_process.join(timeout=CLOSE_TIMEOUT)
            if environment_process.is_alive():
                self.queue_container.log_file_queue.put(f"{datetime.now()}: Force Closing {queue_name} Process\n")
                self.environment_events[queue_name].set()
                environment_process.join(timeout=CLOSE_TIMEOUT)
                if environment_process.is_alive() and not self.threading:
                    environment_process.terminate()
                    environment_process.join()
            self.queue_container.environment_command_queues[queue_name].flush(TASK_NAME)
