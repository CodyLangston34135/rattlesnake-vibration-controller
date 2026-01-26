from .utilities import QueueContainer, GlobalCommands
from .environment.abstract_environment import EnvironmentMetadata
from .environment.environment_utilities import ControlTypes
from .environment.time_environment import TimeEnvironment, time_process
import multiprocessing as mp
from datetime import datetime
from typing import List

TASK_NAME = "Environment Manager"


class EnvironmentManager:
    """A container class that stores the environment information"""

    def __init__(self, queue_container: QueueContainer):
        self.control_names = []  # Static name for dictionary keys, process names, etc
        self.environment_names = {}  # Name of environment for Ui purposes
        self.environment_types = {}
        self.environment_metadata = {}
        self.environment_processes = {}
        self.queue_container = queue_container
        self.available_queues = list(queue_container.environment_command_queues.keys())

    @property
    def sysid_environments(self):
        return [ControlTypes.RANDOM, ControlTypes.TRANSIENT]

    @property
    def sysid_names(self):
        sysid_names = [control_name for control_name in self.control_names if self.environment_types[control_name] in self.sysid_environments]
        return sysid_names

    def initialize_environments(self, metadata_list: List[EnvironmentMetadata]):
        mapped_control_names = set()
        extra_metadata = []

        # Check if there is an existing process that maps to this environment type
        # If there is, hijack it and give it new metadata
        for metadata in metadata_list:
            environment_type = metadata.environment_type
            environment_name = metadata.environment_name

            control_name = next(
                (name for name, env_type in self.environment_types.items() if env_type == environment_type),
                None,
            )

            if control_name is None:
                extra_metadata.append(metadata)
                continue

            self.environment_names[control_name] = environment_name
            self.environment_metadata[control_name] = metadata
            self.queue_container.environment_command_queues[control_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, metadata))

            mapped_control_names.add(control_name)

        # Close existing processes that dont have metadata associated with them
        unmapped_control_names = set(self.environment_types.keys()) - mapped_control_names
        for control_name in unmapped_control_names:
            self.remove_environment(control_name)

        # Add process for metadata that needs a new process. Could do this in loop above
        # but I want to clear up control_names before assigning new ones
        for metadata in extra_metadata:
            self.add_environment(metadata)

    def clear_environments(self):
        self.control_names = []
        self.environment_names = {}
        self.environment_types = {}
        self.environment_metadata = {}
        self.close_environments()
        self.environment_processes = {}

    def add_environment(self, metadata: EnvironmentMetadata):
        """Adds environment to container with unique name"""
        # Find the first available queue for the environment
        control_name = None
        for queue_name in self.available_queues:
            if queue_name not in self.control_names:
                control_name = queue_name
                break

        if control_name == None:
            raise KeyError("Not enough environment command queues. Increase max_environments in rattlesnake.py")

        environment_type = metadata.environment_type
        environment_name = metadata.environment_name

        # Figure out what type of environment to add
        if environment_type == ControlTypes.TIME:
            environment_process = mp.Process(
                target=time_process,
                args=(
                    control_name,
                    self.queue_container.environment_command_queues[control_name],
                    self.queue_container.gui_update_queue,
                    self.queue_container.controller_communication_queue,
                    self.queue_container.log_file_queue,
                    self.queue_container.environment_data_in_queues[control_name],
                    self.queue_container.environment_data_out_queues[control_name],
                    self.queue_container.acquisition_active,
                    self.queue_container.output_active,
                ),
            )
            environment_process.start()
        else:  # If "Select Environment" was chosen
            return

        # Store the environment to the container
        self.control_names.append(control_name)
        self.environment_names[control_name] = environment_name
        self.environment_types[control_name] = environment_type
        self.environment_processes[control_name] = environment_process
        self.environment_metadata[control_name] = metadata

    def remove_environment(self, control_name):
        """Removes environment from container"""
        # Check if index corresponds to an existing environment
        if control_name in self.control_names:
            self.control_names.remove[control_name]
            self.environment_names.pop(control_name, None)
            self.environment_types.pop(control_name, None)
            self.environment_metadata.pop(control_name, None)

            # Join environment process
            self.environment_processes[control_name].join(timeout=5)
            if self.environment_processes[control_name].is_alive():
                self.queue_container.environment_command_queues[control_name].put("Environments", (GlobalCommands.QUIT, None))
                self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.datetime.now(), control_name))
                self.environment_processes[control_name].terminate()
                self.environment_processes[control_name].join()

            # Remove environment queue and process
            self.environment_processes.pop(control_name, None)

        else:
            raise IndexError(f"Invalid control name: {control_name}. Must be mapped to available queue")

    def close_environments(self):
        for control_name, environment_process in self.environment_processes.items():
            self.queue_container.environment_command_queues[control_name].put("Environments", (GlobalCommands.QUIT, None))
            self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.datetime.now(), control_name))
            environment_process.join(timeout=5)
            if environment_process.is_alive():
                environment_process.terminate()
                environment_process.join()
                self.queue_container.environment_command_queues[control_name].flush("force close")
