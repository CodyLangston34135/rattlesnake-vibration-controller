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
        self.queue_names = []  # Static name for dictionary keys, process names, etc
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
        sysid_names = [queue_name for queue_name in self.queue_names if self.environment_types[queue_name] in self.sysid_environments]
        return sysid_names

    def initialize_environments(self, metadata_list: List[EnvironmentMetadata]):
        mapped_queue_names = set()
        extra_metadata = []

        # Check if there is an existing process that maps to this environment type
        # If there is, hijack it and give it new metadata
        for metadata in metadata_list:
            metadata.validate()

            environment_type = metadata.environment_type
            environment_name = metadata.environment_name

            queue_name = next(
                (name for name, env_type in self.environment_types.items() if env_type == environment_type and name not in mapped_queue_names),
                None,
            )

            if queue_name is None:
                extra_metadata.append(metadata)
                continue

            metadata.queue_name = queue_name
            self.environment_types[queue_name] = environment_type
            self.environment_names[queue_name] = environment_name
            self.environment_metadata[queue_name] = metadata
            self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, metadata))

            mapped_queue_names.add(queue_name)

        # Close existing processes that dont have metadata associated with them
        unmapped_queue_names = set(self.environment_types.keys()) - mapped_queue_names
        for queue_name in unmapped_queue_names:
            self.remove_environment(queue_name)

        # Add process for metadata that needs a new process. Could do this in loop above
        # but I want to clear up queue_names before assigning new ones
        for metadata in extra_metadata:
            self.add_environment(metadata)

        # Send metadata information to associated processes
        metadata_list = list(self.environment_metadata.values())
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.INITIALIZE_ENVIRONMENT, metadata_list))

    def clear_environments(self):
        self.queue_names = []
        self.environment_types = {}
        self.environment_names = {}
        self.environment_metadata = {}
        self.close_environments()
        self.environment_processes = {}

    def add_environment(self, metadata: EnvironmentMetadata):
        """Adds environment to container with unique name"""
        # Find the first available queue for the environment
        queue_name = None
        for queue_name in self.available_queues:
            if queue_name not in self.queue_names:
                queue_name = queue_name
                break

        if queue_name == None:
            raise KeyError("Not enough environment command queues. Increase max_environments in rattlesnake.py")

        environment_type = metadata.environment_type
        environment_name = metadata.environment_name

        # Figure out what type of environment to add
        if environment_type == ControlTypes.TIME:
            environment_process = mp.Process(
                target=time_process,
                args=(
                    queue_name,
                    self.queue_container.environment_command_queues[queue_name],
                    self.queue_container.gui_update_queue,
                    self.queue_container.controller_communication_queue,
                    self.queue_container.log_file_queue,
                    self.queue_container.environment_data_in_queues[queue_name],
                    self.queue_container.environment_data_out_queues[queue_name],
                    self.queue_container.acquisition_active,
                    self.queue_container.output_active,
                ),
            )
            environment_process.start()
        else:  # If "Select Environment" was chosen
            return

        # Store the environment to the container
        self.queue_names.append(queue_name)
        self.environment_names[queue_name] = environment_name
        self.environment_types[queue_name] = environment_type
        self.environment_processes[queue_name] = environment_process
        metadata.queue_name = queue_name
        self.environment_metadata[queue_name] = metadata

    def remove_environment(self, queue_name):
        """Removes environment from container"""
        # Check if index corresponds to an existing environment
        if queue_name in self.queue_names:
            self.queue_names.remove[queue_name]
            self.environment_names.pop(queue_name, None)
            self.environment_types.pop(queue_name, None)
            self.environment_metadata.pop(queue_name, None)

            # Join environment process
            self.environment_processes[queue_name].join(timeout=5)
            if self.environment_processes[queue_name].is_alive():
                self.queue_container.environment_command_queues[queue_name].put("Environments", (GlobalCommands.QUIT, None))
                self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.datetime.now(), queue_name))
                self.environment_processes[queue_name].terminate()
                self.environment_processes[queue_name].join()

            # Remove environment queue and process
            self.environment_processes.pop(queue_name, None)

        else:
            raise IndexError(f"Invalid control name: {queue_name}. Must be mapped to available queue")

    def close_environments(self):
        for queue_name, environment_process in self.environment_processes.items():
            self.queue_container.environment_command_queues[queue_name].put("Environments", (GlobalCommands.QUIT, None))
            self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.datetime.now(), queue_name))
            environment_process.join(timeout=5)
            if environment_process.is_alive():
                environment_process.terminate()
                environment_process.join()
                self.queue_container.environment_command_queues[queue_name].flush("force close")
