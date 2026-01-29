from .utilities import GlobalCommands
from .environment.abstract_environment import EnvironmentInstructions
from .environment.time_environment import TimeCommands
import threading
from typing import List, Dict
from datetime import datetime

TASK_NAME = "Profile Manager"


class ProfileEvent:
    def __init__(self, timestamp: float, queue_name: str, command, data):
        try:
            self.timestamp = float(timestamp)
            self.environment_name = str(queue_name)
            self.command = command
            self.data = data
        except ValueError as e:
            print(f"Invalid type provided: {e}")


class ProfileManager:
    def __init__(self, log_file_queue, controller_command_queue):
        self.log_file_queue = log_file_queue
        self.controller_command_queue = controller_command_queue

        self.environment_instructions = {}
        self.profile_event_list = []
        self.profile_timers = []
        self.gui_timer = None

        self.command_map = {}
        self.command_map[GlobalCommands.STOP_HARDWARE] = self.stop_hardware
        self.command_map[GlobalCommands.START_STREAMING] = self.start_streaming
        self.command_map[GlobalCommands.STOP_STREAMING] = self.stop_streaming
        self.command_map[GlobalCommands.START_ENVIRONMENT] = self.start_environment
        self.command_map[GlobalCommands.STOP_ENVIRONMENT] = self.stop_environment
        self.command_map[TimeCommands.SET_TEST_LEVEL] = self.change_test_level
        self.command_map[TimeCommands.SET_REPEAT] = self.set_repeat
        self.command_map[TimeCommands.SET_NO_REPEAT] = self.set_norepeat

        self._global_commands = [GlobalCommands.STOP_HARDWARE, GlobalCommands.START_STREAMING, GlobalCommands.STOP_STREAMING]
        self._instruction_commands = [TimeCommands.SET_TEST_LEVEL, TimeCommands.SET_REPEAT, TimeCommands.SET_NO_REPEAT]

    @property
    def global_commands(self):
        return self._global_commands

    def set_instruction(self, data: Dict[str:EnvironmentInstructions]):
        self.log("Setting Environment Instructions")
        self.environment_instructions = data

    def set_profile_list(self, data: List[ProfileEvent]):
        self.log("Setting Profile List")
        profile_event_list = data
        valid_profile = self.validate_profile_list(profile_event_list)

        if not valid_profile:
            raise TypeError("Rattlesnake.set_profile requires a valid list of ProfileEvents")

        self.profile_event_list = profile_event_list

    def validate_profile_list(self, profile_event_list):
        for profile_event in profile_event_list:
            # Check if environments are assigned to commands that require them
            if profile_event.environment_name == "Global":
                if profile_event.command in self._global_commands:
                    continue
                else:
                    raise KeyError(f"No environment assigned for {profile_event.command.name}")
            # Check if instructions exist for that environment
            if profile_event.command in self._instruction_commands:
                command = profile_event.command
                queue_name = profile_event.queue_name
                try:
                    instruction = self.environment_instructions[queue_name]
                except KeyError:
                    raise KeyError(f"There are no instructions for {queue_name} environment")
                if instruction is None:
                    raise TypeError(f"Invalid instructions for {queue_name} to complete {command} command.")

        return True

    def start_profile(self):
        self.log("Starting Profile")
        self.profile_timers = []
        for profile_event in self.profile_event_list:
            timestamp = profile_event.timestamp
            queue_name = profile_event.queue_name
            command = profile_event.command
            data = profile_event.data
            timer = threading.Timer(timestamp, self.fire_profile_event, args=(queue_name, command, data))
            timer.start()
            self.profile_timers.append(timer)

    def fire_profile_event(self, queue_name, command, data):
        self.log(f"Profile Firing Event {queue_name} {command} {data}")
        self.command_map[command](queue_name, data)

    def stop_profile(self):
        self.log("Stopping Profile")
        for timer in self.profile_timers:
            timer.cancel()

    def stop_hardware(self, queue_name: str = "Global", data: None = None):
        self.controller_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, None))
        for queue_name in self.environment_instructions.key():
            self.controller_command_queue.put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, queue_name))

    def start_streaming(self, queue_name: str = "Global", data: None = None):
        self.controller_command_queue.put(TASK_NAME, (GlobalCommands.START_STREAMING, None))

    def stop_streaming(self, queue_name: str = "Global", data: None = None):
        self.controller_command_queue.put(TASK_NAME, (GlobalCommands.STOP_STREAMING, None))

    def start_environment(self, queue_name, data):
        instructions = self.environment_instructions[queue_name]
        self.controller_command_queue.put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, (queue_name, instructions)))

    def stop_environment(self, queue_name, data):
        self.controller_command_queue.put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, queue_name))

    def change_test_level(self, queue_name, test_level):
        """Sets the test level from a profile instruction

        Parameters
        ----------
        test_level :
            Value to set the test level to.
        """
        if hasattr(self.environment_instructions[queue_name], "test_level"):
            self.environment_instructions[queue_name].test_level = test_level

    def set_repeat(self, queue_name, data):  # pylint: disable=unused-argument
        """Sets the the signal to repeat from a profile instruction

        Parameters
        ----------
        data : Ignored
            Parameter is ignored but required by the ``command_map``
        """
        if hasattr(self.environment_instructions[queue_name], "repeat"):
            self.environment_instructions[queue_name].repeat = True

    def set_norepeat(self, queue_name, data):  # pylint: disable=unused-argument
        """Sets the the signal to not repeat from a profile instruction

        Parameters
        ----------
        data : Ignored
            Parameter is ignored but required by the ``command_map``

        """
        if hasattr(self.environment_instructions[queue_name], "repeat"):
            self.environment_instructions[queue_name].repeat = False

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
        self.log_file_queue.put(f"{datetime.now()}: {TASK_NAME} -- {message}\n")
