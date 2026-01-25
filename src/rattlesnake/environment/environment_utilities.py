from enum import Enum


class ControlTypes(Enum):
    """Enumeration of the possible control types"""

    COMBINED = 0
    RANDOM = 1
    TRANSIENT = 2
    SINE = 3
    TIME = 4
    # NONLINEAR = 5
    MODAL = 6
    # Add new environment types here


environment_long_names = {}
environment_long_names[ControlTypes.RANDOM] = "MIMO Random Vibration"
environment_long_names[ControlTypes.TRANSIENT] = "MIMO Transient"
environment_long_names[ControlTypes.SINE] = "MIMO Sine Vibration"
environment_long_names[ControlTypes.TIME] = "Time Signal Generation"
environment_long_names[ControlTypes.MODAL] = "Modal Testing"


class EnvironmentManager:
    """A container class that stores the environment information"""

    def __init__(self, queue_container: QueueContainer):
        self.control_names = []  # Static name for dictionary keys, process names, etc
        self.environment_names = {}  # Name of environment for Ui purposes
        self.environment_types = {}
        self.environment_channels = {}
        self.environment_processes = {}
        self.environment_uis = {}
        self.daq_parameters = {}
        self.environment_metadata = {}
        self.queue_container = queue_container
        self.available_queues = list(queue_container.environment_command_queues.keys())

    @property
    def attributes(self):
        """Lists the attributes for looping through container"""
        attributes = ["environment_types", "environment_uis", "environment_channels"]
        return attributes

    @property
    def sysid_environments(self):
        return [ControlTypes.RANDOM, ControlTypes.TRANSIENT]

    @property
    def sysid_names(self):
        sysid_names = [control_name for control_name in self.control_names if self.environment_types[control_name] in self.sysid_environments]
        return sysid_names

    @property
    def row_count(self):
        row_count = 0
        # Find length of environment channels list for first environment
        if self.control_names:
            control_name = self.control_names[0]
            row_count = len(self.environment_channels[control_name])
        return row_count

    @property
    def environment_channel_indices(self):
        environment_channel_indices = {}
        for control_name in self.control_names:
            environment_channel_indices[control_name] = [
                index for index, environment_bool in enumerate(self.environment_channels[control_name]) if environment_bool
            ]

        return environment_channel_indices

    """
    Environment Container Callback Section:
    """

    def clear_environments(self):
        self.control_names = []
        self.environment_names = {}
        self.environment_types = {}
        self.environment_channels = {}
        self.environment_uis = {}
        self.daq_parameters = {}
        self.environment_metadata = {}

        self.close_environments()
        self.environment_processes = {}

    def add_environment(self, environment_type: ControlTypes, valid_channels: list[bool]):
        """Adds environment to container with unique name"""
        # Find the first available queue for the environment
        control_name = None
        for queue_name in self.available_queues:
            if queue_name not in self.control_names:
                control_name = queue_name
                break

        if control_name == None:
            raise KeyError("Not enough environment command queues. Increase max_environments in rattlesnake.py")

        environment_name = environment_type.name

        # Figure out what type of environment to add
        if environment_type == ControlTypes.RANDOM:
            environment_process = mp.Process(
                target=random_vibration_process,
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
            environment_ui = RandomVibrationUI(
                control_name,
                self.queue_container.environment_command_queues[control_name],
                self.queue_container.controller_communication_queue,
                self.queue_container.log_file_queue,
            )
        elif environment_type == ControlTypes.TRANSIENT:
            environment_process = mp.Process(
                target=transient_process,
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
            environment_ui = TransientUI(
                control_name,
                self.queue_container.environment_command_queues[control_name],
                self.queue_container.controller_communication_queue,
                self.queue_container.log_file_queue,
            )
        elif environment_type == ControlTypes.TIME:
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
            environment_ui = TimeUI(
                control_name,
                self.queue_container.environment_command_queues[control_name],
                self.queue_container.controller_communication_queue,
                self.queue_container.log_file_queue,
            )
        elif environment_type == ControlTypes.MODAL:
            environment_process = mp.Process(
                target=modal_process,
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
            environment_ui = ModalUI(
                control_name,
                self.queue_container.environment_command_queues[control_name],
                self.queue_container.controller_communication_queue,
                self.queue_container.log_file_queue,
            )
        else:  # If "Select Environment" was chosen
            return

        # Store the environment to the container
        self.control_names.append(control_name)
        self.environment_names[control_name] = environment_name
        self.environment_types[control_name] = environment_type
        self.environment_processes[control_name] = environment_process
        self.environment_uis[control_name] = environment_ui
        self.environment_channels[control_name] = valid_channels
        self.daq_parameters[control_name] = None
        self.environment_metadata[control_name] = None

    def remove_environment(self, index: int):
        """Removes environment from container"""
        # Check if index corresponds to an existing environment
        if 0 <= index < len(self.control_names):
            control_name = self.control_names[index]
            self.control_names.pop(index)
            self.environment_names.pop(control_name, None)
            self.environment_types.pop(control_name, None)
            self.environment_uis.pop(control_name, None)
            self.environment_channels.pop(control_name, None)
            self.daq_parameters.pop(control_name, None)
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
            raise IndexError(f"Invalid index: {index}. Must be between 0 and {len(self.control_names) - 1}.")

    def change_environment_order(self, to_idx: int, from_idx: int):
        """Changes the control_names list order"""
        # Validate indices
        if not (0 <= from_idx < len(self.control_names)):
            raise IndexError(f"Invalid from_idx: {from_idx}. Must be between 0 and {len(self.control_names) - 1}.")
        if not (0 <= to_idx <= len(self.control_names)):  # Allow inserting at the end
            raise IndexError(f"Invalid to_idx: {to_idx}. Must be between 0 and {len(self.control_names)}.")

        # Reorder the environment names list to match the tabs positioning
        environment_move = self.control_names.pop(from_idx)
        self.control_names.insert(to_idx, environment_move)

    def rename_environment(self, control_name: str, new_name: str):
        """Renames an environment in the container

        Parameters
        ----------
        index : int :
        The index of the environment to rename
        new_name : str :
        The name of the new index to display
        """
        # Check if the index corresponds to an environment in the container
        if control_name in self.control_names:
            # Rename environment and update dictionary keys
            self.environment_names[control_name] = str(new_name)
        else:
            raise IndexError(f"Invalid environment name")

    def change_environment_checkbox(self, state: bool, row: int, col: int):
        """Edits the state of a checkbox in the enviornment_channels list

        Parameters
        ----------
        state : bool :
        The state to change the checkbox to (checked/unchecked)
        row : int :
        The row of the checkbox
        col : int :
        The column of the checkbox
        """
        # Change the boolean in the environment_channels list to the state
        control_name = self.control_names[col]
        environment_channel = self.environment_channels[control_name]
        environment_channel[row] = state

        # Update the list
        self.environment_channels[control_name] = environment_channel

    def update_channel_rows(self, row_count: int):
        """Updates the number of empty rows at the end of the environment_channels list

        Parameters
        ----------
        row_count : int :
        The total number of rows that the environment_channels_table should have
        """
        # Loop through environments
        for control_name in self.control_names:
            environment_channel = self.environment_channels[control_name]

            # Check if we need to add or remove empty checkboxes at end of list
            prev_len = len(environment_channel)
            add_len = row_count - prev_len
            # If adding empty checkboxes, add to end of list
            if add_len > 0:
                environment_channel.extend([False] * add_len)
            # If removing empty checkboxes, delete end of list
            elif add_len < 0:
                del environment_channel[add_len:]

            # Store new environment_channel list
            self.environment_channels[control_name] = environment_channel

    def delete_channel_row(self, row: int):
        """Removes a row in the environment_channels list

        Parameters
        ----------
        row : int :
        The row to delete
        """
        # Loop through environments and delete that row
        for control_name in self.control_names:
            self.environment_channels[control_name].pop(row)

    def insert_channel_row(self, row: int):
        """Inserts a row into the environment_channels list

        Parameters
        ----------
        row : int :
        The row index that the new row should be inserted above
        """
        for control_name in self.control_names:
            self.environment_channels[control_name].insert(row, False)

    """
    Environment Ui Callback Section:
    """

    def close_environments(self):
        for control_name, environment_process in self.environment_processes.items():
            self.queue_container.environment_command_queues[control_name].put("Environments", (GlobalCommands.QUIT, None))
            self.queue_container.log_file_queue.put("{:}: Joining {:} Process\n".format(datetime.datetime.now(), control_name))
            environment_process.join(timeout=5)
            if environment_process.is_alive():
                environment_process.terminate()
                environment_process.join()
                self.queue_container.environment_command_queues[control_name].flush("force close")
