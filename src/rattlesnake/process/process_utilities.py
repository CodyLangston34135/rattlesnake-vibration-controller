from ..environment.time_environment import TimeCommands
from qtpy import QtCore


class ProfileTimer(QtCore.QTimer):
    """A timer class that allows storage of controller instruction information"""

    def __init__(self, environment: str, operation: str, data: str):
        """
        A timer class that allows storage of controller instruction information

        When the timer times out, the environment, operation, and any data can
        be collected by the callback by accessing the self.sender().environment,
        .operation, or .data attributes.

        Parameters
        ----------
        environment : str
            The name of the environment (or 'Global') that the instruction will
            be sent to
        operation : str
            The operation that the environment will be instructed to perform
        data : str
            Any data corresponding to that operation that is required


        """
        super().__init__()
        self.environment = environment
        self.operation = operation
        self.data = data


class ProfileEvent:
    def __init__(self, timestamp: float, environment_name: str, operation: str, data):
        try:
            self.timestamp = float(timestamp)
            self.environment_name = str(environment_name)
            self.operation = str(operation)
            self.data = data
            self.queue_name = None
            self.environment_type = None
        except ValueError as e:
            print(f"Invalid type provided: {e}")


class ProfileManager:
    def __init__(self):
        self.command_map = {}
        self.command_map[TimeCommands.SET_TEST_LEVEL] = self.change_test_level_from_profile
        self.command_map[TimeCommands.SET_REPEAT] = self.set_repeat_from_profile
        self.command_map[TimeCommands.SET_NO_REPEAT] = self.set_norepeat_from_profile

    def set_instruction(self, data):
        self.environment_instructions[data.queue_name] = data

    def change_test_level_from_profile(self, test_level, environment_name):
        """Sets the test level from a profile instruction

        Parameters
        ----------
        test_level :
            Value to set the test level to.
        """
        self.run_widget.test_level_selector.setValue(int(test_level))

    def set_repeat_from_profile(self, data):  # pylint: disable=unused-argument
        """Sets the the signal to repeat from a profile instruction

        Parameters
        ----------
        data : Ignored
            Parameter is ignored but required by the ``command_map``

        """
        self.run_widget.repeat_signal_checkbox.setChecked(True)

    def set_norepeat_from_profile(self, data):  # pylint: disable=unused-argument
        """Sets the the signal to not repeat from a profile instruction

        Parameters
        ----------
        data : Ignored
            Parameter is ignored but required by the ``command_map``

        """
        self.run_widget.repeat_signal_checkbox.setChecked(False)
