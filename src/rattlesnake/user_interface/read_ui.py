from .abstract_user_interface import AbstractUI
from .ui_utilities import ReadUICommands, environment_run_ui_paths, multiline_plotter
from ..utilities import VerboseMessageQueue, GlobalCommands
from ..hardware.abstract_hardware import HardwareMetadata
from ..environment.environment_utilities import ControlTypes
from ..environment.abstract_environment import EnvironmentMetadata
from ..environment.read_environment import ReadMetadata
from qtpy import QtCore, QtWidgets, uic
import multiprocessing as mp
import numpy as np

CONTROL_TYPE = ControlTypes.READ
TASK_NAME = "Read UI"


class ReadUI(AbstractUI):
    def __init__(
        self,
        environment_name: str,
        definition_tabwidget: QtWidgets.QTabWidget,
        system_id_tabwidget: QtWidgets.QTabWidget,  # pylint: disable=unused-argument
        test_predictions_tabwidget: QtWidgets.QTabWidget,  # pylint: disable=unused-argument
        run_tabwidget: QtWidgets.QTabWidget,
        environment_command_queue: VerboseMessageQueue,
        controller_command_queue: VerboseMessageQueue,
        log_file_queue: mp.Queue,
    ):

        super().__init__(
            environment_name,
            environment_command_queue,
            controller_command_queue,
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

    def complete_ui(self):
        """Helper Function to continue setting up the user interface"""
        # Set common look and feel for plots
        plot_widgets = [
            self.run_widget.response_signal_plot,
        ]
        for plot_widget in plot_widgets:
            plot_item = plot_widget.getPlotItem()
            plot_item.showGrid(True, True, 0.25)
            plot_item.enableAutoRange()
            plot_item.getViewBox().enableAutoRange(enable=True)

    def start_control(self):
        self.controller_communication_queue.put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, self.environment_name))

    def stop_control(self):
        pass

    def collect_environment_definition_parameters(self) -> ReadMetadata:
        return ReadMetadata()

    def initialize_hardware(self, hardware_metadata: HardwareMetadata):
        channels = hardware_metadata.channel_list
        num_measurements = len([channel for channel in channels if channel.feedback_device is None])

        self.physical_measurement_names = [
            f"{'' if channel.channel_type is None else channel.channel_type} " "{channel.node_number}{channel.node_direction}"
            for channel in channels
            if channel.feedback_device is None
        ]

        self.plot_data_items["response_signal_measurement"] = multiline_plotter(
            np.arange(2),
            np.zeros(
                (
                    (num_measurements),
                    2,
                )
            ),
            widget=self.run_widget.response_signal_plot,
            other_pen_options={"width": 1},
            names=self.physical_measurement_names,
        )

    def initialize_environment(self) -> EnvironmentMetadata:
        pass

    def add_device(self):
        pass

    def remove_device(self):
        pass

    def update_gui(self, queue_data):
        """Update the graphical interface for the environment

        Parameters
        ----------
        queue_data :
            A 2-tuple consisting of ``(message,data)`` pairs where the message
            denotes what to change and the data contains the information needed
            to be displayed.
        """
        message, data = queue_data
        if message == ReadUICommands.TIME_DATA:
            response_data = data
            for curve, this_data in zip(self.plot_data_items["response_signal_measurement"], response_data):
                x, y = curve.getData()
                y = np.concatenate((y[this_data.size :], this_data[-x.size :]), axis=0)
                curve.setData(x, y)
