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
        except ValueError as e:
            print(f"Invalid type provided: {e}")


class ProfileManager:
    def __init__(self):
        pass
