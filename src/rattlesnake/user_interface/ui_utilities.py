from rattlesnake.utilities import VerboseMessageQueue, GlobalCommands
from rattlesnake.hardware.hardware_utilities import HardwareType
from rattlesnake.environment.environment_utilities import ControlTypes
import traceback
import sys
import os
import time
from enum import Enum
from qtpy import QtWidgets, QtCore, QtGui

this_path = os.path.split(__file__)[0]

TASK_NAME = "UI"


class UICommands(Enum):
    ERROR = -1
    ENABLE = 0
    DISABLE = 1
    MONITOR = 2
    ENABLE_TAB = 3
    DISABLE_TAB = 4
    SET_ATTR = 5
    STOP = 6


class TimeUICommands(Enum):
    TIME_DATA = 0


class ReadUICommands(Enum):
    TIME_DATA = 0


VISIBLE_HARDWARE_WIDGETS = {
    "Select Hardware": {"hardware_selector"},
    "NI DAQmx": {"hardware_selector", "sample_rate", "buffer_size", "task_trigger", "trigger_output"},
    "HBK LAN-XI": {"hardware_selector", "lanxi_sample_rate", "buffer_size", "lanxi_processes", "lanxi_ip"},
    "Data Physics Quattro": {"hardware_selector", "sample_rate", "buffer_size", "integration_oversample", "select_file"},
    "Data Physics 900 Series": {"hardware_selector", "sample_rate", "buffer_size", "integration_oversample", "select_file"},
    "Exodus Modal Solution...": {"hardware_selector", "sample_rate", "buffer_size", "integration_oversample", "damping_ratio", "select_file"},
    "State Space Integration...": {"hardware_selector", "sample_rate", "buffer_size", "integration_oversample", "select_file"},
    "SDynPy System Integration...": {"hardware_selector", "sample_rate", "buffer_size", "integration_oversample", "select_file"},
    "SDynPy FRF Convolution...": {"hardware_selector", "sample_rate", "buffer_size", "integration_oversample", "select_file"},
}

HARDWARE_TYPE = {
    "Select Hardware": "Select",
    "NI DAQmx": HardwareType.NI_DAQMX,
    "HBK LAN-XI": HardwareType.LAN_XI,
    "Data Physics Quattro": HardwareType.DP_QUATTRO,
    "Data Physics 900 Series": HardwareType.DP_900,
    "Exodus Modal Solution...": HardwareType.EXODUS,
    "State Space Integration...": HardwareType.STATE_SPACE,
    "SDynPy System Integration...": HardwareType.SDYNPY_SYSTEM,
    "SDynPy FRF Convolution...": HardwareType.SDYNPY_FRF,
}


# Define paths to the User Interface UI Files
environment_definition_ui_paths = {}
environment_prediction_ui_paths = {}
environment_run_ui_paths = {}
# This is true if running from an executable and the UI is embedded in the executable
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    directory = sys._MEIPASS  # pylint: disable=protected-access
else:
    directory = this_path
# Base Controller UI
ui_path = os.path.join(directory, "ui_files", "combined_environments_controller.ui")
headless_ui_path = os.path.join(directory, "ui_files", "headless.ui")
debug_ui_path = os.path.join(directory, "ui_files", "debug.ui")
environment_select_ui_path = os.path.join(directory, "ui_files", "environment_selector.ui")
control_select_ui_path = os.path.join(directory, "ui_files", "control_select.ui")
# Random Vibration Environment
environment_definition_ui_paths[ControlTypes.RANDOM] = os.path.join(directory, "ui_files", "random_vibration_definition.ui")
environment_prediction_ui_paths[ControlTypes.RANDOM] = os.path.join(directory, "ui_files", "random_vibration_prediction.ui")
environment_run_ui_paths[ControlTypes.RANDOM] = os.path.join(directory, "ui_files", "random_vibration_run.ui")
system_identification_ui_path = os.path.join(directory, "ui_files", "system_identification.ui")
transformation_matrices_ui_path = os.path.join(directory, "ui_files", "transformation_matrices.ui")
# Time Environment
environment_definition_ui_paths[ControlTypes.TIME] = os.path.join(directory, "ui_files", "time_definition.ui")
environment_run_ui_paths[ControlTypes.TIME] = os.path.join(directory, "ui_files", "time_run.ui")
# Transient Environment
environment_definition_ui_paths[ControlTypes.TRANSIENT] = os.path.join(directory, "ui_files", "transient_definition.ui")
environment_prediction_ui_paths[ControlTypes.TRANSIENT] = os.path.join(directory, "ui_files", "transient_prediction.ui")
environment_run_ui_paths[ControlTypes.TRANSIENT] = os.path.join(directory, "ui_files", "transient_run.ui")
# Sine Environment
environment_definition_ui_paths[ControlTypes.SINE] = os.path.join(directory, "ui_files", "sine_definition.ui")
environment_prediction_ui_paths[ControlTypes.SINE] = os.path.join(directory, "ui_files", "sine_prediction.ui")
environment_run_ui_paths[ControlTypes.SINE] = os.path.join(directory, "ui_files", "sine_run.ui")
sine_sweep_table_ui_path = os.path.join(directory, "ui_files", "sine_sweep_table.ui")
filter_explorer_ui_path = os.path.join(directory, "ui_files", "sine_filter_explorer.ui")
# Modal Environments
environment_definition_ui_paths[ControlTypes.MODAL] = os.path.join(directory, "ui_files", "modal_definition.ui")
environment_run_ui_paths[ControlTypes.MODAL] = os.path.join(directory, "ui_files", "modal_run.ui")
modal_mdi_ui_path = os.path.join(directory, "ui_files", "modal_acquisition_window.ui")
# Read Environment
environment_run_ui_paths[ControlTypes.READ] = os.path.join(directory, "ui_files", "read_run.ui")


class UpdaterSignals(QtCore.QObject):
    """Defines the signals that will be sent from the GUI Updater to the GUI

    Supported signals are:

    finished
        empty

    update
        `tuple` (widget_id,data)
    """

    finished = QtCore.Signal()
    update = QtCore.Signal(tuple)


class Updater(QtCore.QRunnable):
    """Updater thread to collect results from the subsystems and reflect the
    changes in the GUI
    """

    def __init__(self, update_queue):
        """
        Initializes the updater with the queue and signals that will be emitted
        when the queue has data in it.

        Parameters
        ----------
        update_queue : mp.queues.Queue
            Queue from which events will be captured.

        """
        super(Updater, self).__init__()
        self.update_queue = update_queue
        self.signals = UpdaterSignals()
        self.verbose_queue = isinstance(self.update_queue, VerboseMessageQueue)

    @QtCore.Slot()
    def run(self):
        """Continually capture update events from the queue"""
        while True:
            if self.verbose_queue:
                queue_data = self.update_queue.get(TASK_NAME)
            else:
                queue_data = self.update_queue.get()
            if queue_data[0] == GlobalCommands.QUIT:
                break
            self.signals.update.emit(queue_data)
        self.signals.finished.emit()
        time.sleep(1)


class EventWatcher(QtCore.QObject):
    ready = QtCore.Signal()
    error = QtCore.Signal(str)

    def __init__(self, ready_event_list, active_event_list, *, active_event_check: bool = None, timeout=None):
        super().__init__()
        self.ready_event_list = ready_event_list
        self.active_event_list = active_event_list
        self.active_event_check = active_event_check
        self.timeout = timeout

    def run(self):
        start = time.time()

        try:
            while True:

                ready_ok = all(event.is_set() for event in self.ready_event_list)
                active_ok = all(event.is_set() == self.active_event_check for event in self.active_event_list)

                if ready_ok and active_ok:
                    self.ready.emit()
                    return

                if self.timeout and (time.time() - start) > self.timeout:
                    for event in self.ready_event_list:
                        event.set()

                    self.error.emit("EventWatcher has timed out while waiting for a response")
                    return

                time.sleep(0.05)
        except Exception:
            tb = traceback.format_exc()
            self.error.emit(tb)


class EditableCombobox(QtWidgets.QComboBox):
    def __init__(self, texts=[], value=None, parent=None):
        super().__init__(parent)

        if "" not in texts:
            texts.insert(0, "")

        value = str(value) if not value is None else ""
        if value not in texts:
            texts.insert(0, value)

        self.setItems(texts)
        self.setCurrentText(value)

    def setItems(self, texts: list[str]):
        if "" not in texts:
            texts.insert(0, "")

        super().clear()
        super().addItems(texts)

    def setCurrentText(self, value: str):
        value = str(value) if not value is None else ""

        super().blockSignals(True)
        super().setCurrentText(value)
        super().blockSignals(False)

    def blockSignals(self, block: bool):
        return super().blockSignals(block)


class EditableSpinBox(QtWidgets.QSpinBox):
    stringValueChanged = QtCore.Signal(str)

    def __init__(self, parent=None, text=""):
        super().__init__(parent)

        # Initialize attributes
        self.pause_signals = False
        self.int_value = 0
        self.str_value = ""

        # If text is number, assign to number
        text = str(text) if text is not None else ""
        self.valueFromText(text)

        self.setRange(-1000000, 1000000)
        self.setValue(self.str_value)

    def valueFromText(self, text):
        """Convert text to a value."""

        self.str_value = str(text)
        # Try to convert text to digit, if so check if its in range
        try:
            self.int_value = int(self.str_value)
            min_value = self.minimum()
            max_value = self.maximum()
            # If out of range, store the max/min range to int_value
            if self.int_value > max_value:
                self.int_value = max_value
            elif self.int_value < min_value:
                self.int_value = min_value
        # If text wasnt an integer, keep previous value
        except ValueError:
            pass

        if not self.pause_signals:
            self.stringValueChanged.emit(self.str_value)

        return self.int_value

    def textFromValue(self, value):
        """Convert a value to text."""
        if self.int_value != value:
            self.int_value = value
            self.str_value = str(value)

        if not self.pause_signals:
            self.stringValueChanged.emit(self.str_value)

        return self.str_value

    def setValue(self, text):
        text = str(text) if text is not None else ""
        self.str_value = text

        prev_pause_state = self.pause_signals
        self.blockSignals(True)
        value = self.valueFromText(text)
        self.blockSignals(prev_pause_state)

        return super().setValue(value)

    def validate(self, text, pos):
        """Allow letters and numbers in the input."""
        return QtGui.QValidator.Acceptable, text, pos

    def blockSignals(self, state: bool):
        """Blocks or enables signals"""
        self.pause_signals = state
        return super().blockSignals(state)


def error_message_qt(title, message):
    """Helper class to create an error dialog.

    Parameters
    ----------
    title : str :
        Title of the window that the error message will appear in.
    message : str :
        Error message that will be displayed.

    """
    QtWidgets.QMessageBox.critical(None, title, message)


colororder = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


def multiline_plotter(
    x,
    y,
    widget=None,
    curve_list=None,
    names=None,
    other_pen_options=None,
    legend=False,
    downsample=None,
    clip_to_view=False,
):
    """Helper function for PyQtGraph to deal with plots with multiple curves

    Parameters
    ----------
    x : np.ndarray
        Abscissa for the data that will be plotted, 1D array with shape n_samples
    y : np.ndarray
        Ordinates for the data that will be plotted.  2D array with shape
        n_curves x n_samples
    widget :
        The plot widget on which the curves will be drawn. (Default value = None)
    curve_list :
        Alternatively to specifying the widget, a curve list can be specified
        directly.  (Default value = None)
    names :
        Names of the curves that will appear in the legend. (Default value = None)
    other_pen_options : dict
        Additional options besides color that will be applied to the curves.
        (Default value = {'width':1})
    legend :
        Whether or not to draw a legend (Default value = False)

    Returns
    -------

    """
    if other_pen_options is None:
        other_pen_options = {"width": 1}
    if downsample is None:
        downsample = {"ds": 1, "auto": False, "mode": "peak"}
    if widget is not None:
        plot_item = widget.getPlotItem()
        plot_item.setDownsampling(**downsample)
        plot_item.setClipToView(clip_to_view)
        if legend:
            plot_item.addLegend(colCount=len(y) // 10)
        handles = []
        for i, this_y in enumerate(y):
            pen = {"color": colororder[i % len(colororder)]}
            pen.update(other_pen_options)
            handles.append(plot_item.plot(x, this_y, pen=pen, name=None if names is None else names[i]))
        return handles
    elif curve_list is not None:
        for this_y, curve in zip(y, curve_list):
            curve.setData(x, y)
        return curve_list
    else:
        raise ValueError("Either Widget or list of curves must be specified")
