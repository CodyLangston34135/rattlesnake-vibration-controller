from .abstract_user_interface import AbstractUI
from .ui_utilities import ReadUICommands, environment_run_ui_paths, multiline_plotter
from ..utilities import VerboseMessageQueue, GlobalCommands
from ..hardware.abstract_hardware import HardwareMetadata
from ..environment.environment_utilities import ControlTypes
from ..environment.abstract_environment import EnvironmentMetadata
from ..environment.read_environment import ReadMetadata
from qtpy import QtCore, QtWidgets, uic
import multiprocessing as mp

CONTROL_TYPE = ControlTypes.TIME


class ReadUI(AbstractUI):
    def __init__(
        self,
        environment_name: str,
        definition_tabwidget: QtWidgets.QTabWidget,
        system_id_tabwidget: QtWidgets.QTabWidget,  # pylint: disable=unused-argument
        test_predictions_tabwidget: QtWidgets.QTabWidget,  # pylint: disable=unused-argument
        run_tabwidget: QtWidgets.QTabWidget,
        environment_command_queue: VerboseMessageQueue,
        controller_communication_queue: VerboseMessageQueue,
        log_file_queue: mp.Queue,
    ):

        super().__init__(
            environment_name,
            environment_command_queue,
            controller_communication_queue,
            log_file_queue,
        )
        self.run_widget = QtWidgets.QWidget()
        uic.loadUi(environment_run_ui_paths[CONTROL_TYPE], self.run_widget)
        run_tabwidget.addTab(self.run_widget, self.environment_name)

        self.hardware_metadata = None
        self.environment_metadata = None

    def connect_callbacks(self):
        """Helper function to connect callbacks to functions in the class"""
        self.run_widget.start_test_button.clicked.connect(self.start_control)
        self.run_widget.stop_test_button.clicked.connect(self.stop_control)
        self.run_widget.add_device_button.clicked.connect(self.add_device)
        self.run_widget.remove_device_button.clicked.connect(self.remove_device)

    def start_control(self):
        pass

    def stop_control(self):
        pass

    def collect_environment_definition_parameters(self) -> ReadMetadata:
        return ReadMetadata()

    def initialize_hardware(self, hardware_metadata: HardwareMetadata):
        pass

    def initialize_environment(self) -> EnvironmentMetadata:
        pass

    def add_device(self):
        pass

    def remove_device(self):
        pass
