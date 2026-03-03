from rattlesnake.utilities import VerboseMessageQueue, GlobalCommands, load_csv_matrix, save_csv_matrix
from rattlesnake.hardware.hardware_utilities import HardwareType
from rattlesnake.environment.environment_utilities import ControlTypes
import traceback
import sys
import os
import time
import numpy as np
from scipy.io import loadmat
from enum import Enum
from qtpy import QtWidgets, QtCore, QtGui, uic

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
    SET_ENVIRONMENT_INSTRUCTIONS = 7
    COMPLETED_SYSTEM_ID = 8
    ENVIRONMENT_STARTED = 9
    ENVIRONMENT_ENDED = 10

    @property
    def label(self):
        """Used by UI as names for"""
        return self.name.replace("_", " ").title()


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

ENVIRONMENT_TYPE = {
    "Add Environment": "Select",
    "RANDOM": ControlTypes.RANDOM,
    "TRANSIENT": ControlTypes.TRANSIENT,
    "SINE": ControlTypes.SINE,
    "TIME": ControlTypes.TIME,
    "MODAL": ControlTypes.MODAL,
    # "READ": ControlTypes.READ,
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
# environment_run_ui_paths[ControlTypes.READ] = os.path.join(directory, "ui_files", "read_run.ui")


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


class ProfileTimer(QtCore.QTimer):
    """A timer class that allows storage of controller instruction information"""

    def __init__(self, timestamp: float, environment_name: str, command: str, data: str):
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
        self.timestamp = timestamp
        self.environment_name = environment_name
        self.command = command
        self.data = data


class EditableCombobox(QtWidgets.QComboBox):
    def __init__(self, texts=[], value=None, parent=None):
        super().__init__(parent)

        if "" not in texts:
            texts.insert(0, "")

        value = str(value) if value is not None else ""
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
        value = str(value) if value is not None else ""

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


def blended_scatter_plot(xy, widget=None, curve_list=None, names=None, symbol="o"):
    """Creates a scatter plot with the specified symbols"""
    if widget is not None:
        plot_item = widget.getPlotItem()
        handles = []
        for index, (x, y) in enumerate(xy):
            c = (1 - (index + 1) / len(xy)) * 255
            handles.append(
                plot_item.plot(
                    [x],
                    [y],
                    symbolBrush=(c, c, c),
                    name=None if names is None else names[index],
                    symbol=symbol,
                )
            )
        return handles
    elif curve_list is not None:
        for (x, y), curve in zip(xy, curve_list):
            curve.setData([x], [y])
        return curve_list
    else:
        raise ValueError("Either Widget or list of curves must be specified")


class VaryingNumberOfLinePlot:
    """A plot that can have a dynamic number of lines assigned,
    adding or removing lines as necessary"""

    def __init__(self, plot_item, initial_abscissa=None, initial_ordinate=None):
        self.plot_item = plot_item
        self.lines = []
        if initial_abscissa is not None and initial_ordinate is not None:
            self.set_data(initial_abscissa, initial_ordinate)

    def set_data(self, abscissa, ordinate):
        """Sets the data of the plot

        Parameters
        ----------
        abscissa : np.ndarray
            A 2D dataset where each row is a different plot and the columns are the abscissa values
            of each curve
        ordinate : np.ndarray
            A 2D dataset where each row is a different plot and the columns are the ordinate values
            of each curve
        """
        for i, (this_ordinate, this_abscissa) in enumerate(zip(ordinate, abscissa)):
            try:
                self.lines[i].setData(this_abscissa, this_ordinate)
            except IndexError:
                pen = {"color": colororder[i % len(colororder)]}
                self.lines.append(self.plot_item.plot(this_abscissa, this_ordinate, pen=pen))

        # Remove extra lines
        extra_lines = len(self.lines) - len(ordinate)
        for i in range(extra_lines):
            line = self.lines.pop()
            self.plot_item.removeItem(line)

    def clear(self):
        """Clears all data from the plots"""
        self.lines = []
        self.plot_item.clear()


def get_table_strings(tablewidget: QtWidgets.QTableWidget):
    """Collect a table of strings from a QTableWidget

    Parameters
    ----------
    tablewidget : QtWidgets.QTableWidget
        A table widget to pull the strings from

    Returns
    -------
    string_array : list[list[str]]
        A nested list of strings from the table items

    """
    string_array = []
    for row_idx in range(tablewidget.rowCount()):
        string_array.append([])
        for col_idx in range(tablewidget.columnCount()):
            value = tablewidget.item(row_idx, col_idx).text()
            string_array[-1].append(value)
    return string_array


class TransformationMatrixWindow(QtWidgets.QDialog):
    """Dialog box for specifying transformation matrices"""

    def __init__(
        self,
        parent,
        current_response_transformation_matrix,
        num_responses,
        current_output_transformation_matrix,
        num_outputs,
    ):
        """
        Creates a dialog box for specifying response and output transformations

        Parameters
        ----------
        parent : QWidget
            Parent to the dialog box.
        current_response_transformation_matrix : np.ndarray
            The current value of the transformation matrix that will be used to
            populate the entries in the table.
        num_responses : int
            Number of physical responses in the transformation.
        current_output_transformation_matrix : np.ndarray
            The current value of the transformation matrix that will be used to
            populate the entries in the table.
        num_outputs : int
            Number of physical outputs in the transformation.

        """
        super().__init__(parent)
        uic.loadUi(transformation_matrices_ui_path, self)
        self.setWindowTitle("Transformation Matrix Definition")

        self.response_transformation_matrix.setColumnCount(num_responses)
        self.output_transformation_matrix.setColumnCount(num_outputs)

        if current_response_transformation_matrix is None:
            self.set_response_transformation_identity()
        else:
            self.response_transformation_matrix.setRowCount(current_response_transformation_matrix.shape[0])
            for row_idx, row in enumerate(current_response_transformation_matrix):
                for col_idx, col in enumerate(row):
                    try:
                        self.response_transformation_matrix.item(row_idx, col_idx).setText(str(col))
                    except AttributeError:
                        item = QtWidgets.QTableWidgetItem(str(col))
                        self.response_transformation_matrix.setItem(row_idx, col_idx, item)
        if current_output_transformation_matrix is None:
            self.set_output_transformation_identity()
        else:
            self.output_transformation_matrix.setRowCount(current_output_transformation_matrix.shape[0])
            for row_idx, row in enumerate(current_output_transformation_matrix):
                for col_idx, col in enumerate(row):
                    try:
                        self.output_transformation_matrix.item(row_idx, col_idx).setText(str(col))
                    except AttributeError:
                        item = QtWidgets.QTableWidgetItem(str(col))
                        self.output_transformation_matrix.setItem(row_idx, col_idx, item)

        # Callbacks
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.response_transformation_add_row_button.clicked.connect(self.response_transformation_add_row)
        self.response_transformation_remove_row_button.clicked.connect(self.response_transformation_remove_row)
        self.response_transformation_save_matrix_button.clicked.connect(self.save_response_transformation_matrix)
        self.response_transformation_load_matrix_button.clicked.connect(self.load_response_transformation_matrix)
        self.response_transformation_identity_button.clicked.connect(self.set_response_transformation_identity)
        self.response_transformation_6dof_kinematic_button.clicked.connect(self.set_response_transformation_6dof)
        self.response_transformation_reversed_6dof_kinematic_button.clicked.connect(self.set_response_transformation_6dof_reversed)

        self.output_transformation_add_row_button.clicked.connect(self.output_transformation_add_row)
        self.output_transformation_remove_row_button.clicked.connect(self.output_transformation_remove_row)
        self.output_transformation_save_matrix_button.clicked.connect(self.save_output_transformation_matrix)
        self.output_transformation_load_matrix_button.clicked.connect(self.load_output_transformation_matrix)
        self.output_transformation_identity_button.clicked.connect(self.set_output_transformation_identity)
        self.output_transformation_6dof_kinematic_button.clicked.connect(self.set_output_transformation_6dof)
        self.output_transformation_reversed_6dof_kinematic_button.clicked.connect(self.set_output_transformation_6dof_reversed)

    @staticmethod
    def define_transformation_matrices(
        current_response_transformation_matrix,
        num_responses,
        current_output_transformation_matrix,
        num_outputs,
        parent=None,
    ):
        """
        Shows the dialog and returns the transformation matrices

        Parameters
        ----------
        current_response_transformation_matrix : np.ndarray
            The current value of the transformation matrix that will be used to
            populate the entries in the table.
        num_responses : int
            Number of physical responses in the transformation.
        current_output_transformation_matrix : np.ndarray
            The current value of the transformation matrix that will be used to
            populate the entries in the table.
        num_outputs : int
            Number of physical outputs in the transformation.
        parent : QWidget
            Parent to the dialog box. (Default value = None)

        Returns
        -------
        response_transformation : np.ndarray
            Response transformation (or None if Identity)
        output_transformation : np.ndarray
            Output transformation (or None if Identity)
        result : bool
            True if dialog was accepted, false if cancelled.
        """
        dialog = TransformationMatrixWindow(
            parent,
            current_response_transformation_matrix,
            num_responses,
            current_output_transformation_matrix,
            num_outputs,
        )
        result = dialog.exec_() == QtWidgets.QDialog.Accepted
        response_transformation = np.array([[float(val) for val in row] for row in get_table_strings(dialog.response_transformation_matrix)])
        if all(val == response_transformation.shape[0] for val in response_transformation.shape) and np.allclose(
            response_transformation, np.eye(response_transformation.shape[0])
        ):
            response_transformation = None
        output_transformation = np.array([[float(val) for val in row] for row in get_table_strings(dialog.output_transformation_matrix)])
        if all(val == output_transformation.shape[0] for val in output_transformation.shape) and np.allclose(
            output_transformation, np.eye(output_transformation.shape[0])
        ):
            output_transformation = None
        return (response_transformation, output_transformation, result)

    def response_transformation_add_row(self):
        """Adds a row to the response transformation"""
        num_rows = self.response_transformation_matrix.rowCount()
        self.response_transformation_matrix.insertRow(num_rows)
        for col_idx in range(self.response_transformation_matrix.columnCount()):
            item = QtWidgets.QTableWidgetItem("0.0")
            self.response_transformation_matrix.setItem(num_rows, col_idx, item)

    def response_transformation_remove_row(self):
        """Removes a row from the response transformation"""
        num_rows = self.response_transformation_matrix.rowCount()
        self.response_transformation_matrix.removeRow(num_rows - 1)

    def save_response_transformation_matrix(self):
        """Saves the response transformation matrix to a csv file"""
        string_array = self.get_table_strings(self.response_transformation_matrix)
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Response Transformation",
            filter="Comma-separated Values (*.csv)",
        )
        if filename == "":
            return
        save_csv_matrix(string_array, filename)

    def load_response_transformation_matrix(self):
        """Loads the response transformation from a csv file"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Response Transformation",
            filter="Comma-separated values (*.csv *.txt);;" "Numpy Files (*.npy *.npz);;Matlab Files (*.mat)",
        )
        if filename == "":
            return
        _, extension = os.path.splitext(filename)
        string_array = None
        if extension.lower() == ".npy":
            string_array = np.load(filename).astype("U")
        elif extension.lower() == ".npz":
            data = np.load(filename)
            for key, array in data.items():
                string_array = array.astype("U")
                break
        elif extension.lower() == ".mat":
            data = loadmat(filename)
            for key, array in data.items():
                if "__" in key:
                    continue
                string_array = array.astype("U")
                break
        else:
            string_array = load_csv_matrix(filename)
        if string_array is None:
            return
        # Set the number of rows
        self.response_transformation_matrix.setRowCount(len(string_array))
        num_rows = self.response_transformation_matrix.rowCount()
        num_cols = self.response_transformation_matrix.columnCount()
        for row_idx, row in enumerate(string_array):
            if row_idx == num_rows:
                break
            for col_idx, value in enumerate(row):
                if col_idx == num_cols:
                    break
                try:
                    self.response_transformation_matrix.item(row_idx, col_idx).setText(value)
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(value)
                    self.response_transformation_matrix.setItem(row_idx, col_idx, item)

    def set_response_transformation_identity(self):
        """Sets the response transformation to identity matrix (no transform)"""
        num_columns = self.response_transformation_matrix.columnCount()
        self.response_transformation_matrix.setRowCount(num_columns)
        for row_idx in range(num_columns):
            for col_idx in range(num_columns):
                if row_idx == col_idx:
                    value = 1.0
                else:
                    value = 0.0
                try:
                    self.response_transformation_matrix.item(row_idx, col_idx).setText(str(value))
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.response_transformation_matrix.setItem(row_idx, col_idx, item)

    def set_response_transformation_6dof(self):
        """Sets the response transformation matrix to the 6DoF table"""
        num_columns = self.response_transformation_matrix.columnCount()
        if num_columns != 12:
            error_message_qt(
                "Invalid Number of Control Channels.",
                "Invalid Number of Control Channels.  " "6DoF Transform assumes 12 control accelerometer channels.",
            )
            return
        self.response_transformation_matrix.setRowCount(6)
        matrix = [
            [0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0],
            [0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25, 0.0, 0.0, -0.25],
            [0.0, 0.0, -0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25],
            [
                -0.125,
                0.125,
                0.0,
                -0.125,
                -0.125,
                0.0,
                0.125,
                -0.125,
                0.0,
                0.125,
                0.125,
                0.0,
            ],
        ]
        for row_idx, row in enumerate(matrix):
            for col_idx, value in enumerate(row):
                try:
                    self.response_transformation_matrix.item(row_idx, col_idx).setText(str(value))
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.response_transformation_matrix.setItem(row_idx, col_idx, item)

    def set_response_transformation_6dof_reversed(self):
        """Sets the response transformation matrix to the 6DoF table"""
        num_columns = self.response_transformation_matrix.columnCount()
        if num_columns != 12:
            error_message_qt(
                "Invalid Number of Control Channels.",
                "Invalid Number of Control Channels.  " "6DoF Transform assumes 12 control accelerometer channels.",
            )
            return
        self.response_transformation_matrix.setRowCount(6)
        matrix = [
            [0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0],
            [0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25, 0.0, 0.0, -0.25],
            [0.0, 0.0, -0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25],
            [
                -0.125,
                0.125,
                0.0,
                -0.125,
                -0.125,
                0.0,
                0.125,
                -0.125,
                0.0,
                0.125,
                0.125,
                0.0,
            ],
        ]
        for row_idx, row in enumerate(matrix):
            for col_idx, value in enumerate(row):
                try:
                    self.response_transformation_matrix.item(row_idx, col_idx).setText(str(value))
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.response_transformation_matrix.setItem(row_idx, col_idx, item)

    def output_transformation_add_row(self):
        """Adds a row to the output transformation"""
        num_rows = self.output_transformation_matrix.rowCount()
        self.output_transformation_matrix.insertRow(num_rows)
        for col_idx in range(self.output_transformation_matrix.columnCount()):
            item = QtWidgets.QTableWidgetItem("0.0")
            self.output_transformation_matrix.setItem(num_rows, col_idx, item)

    def output_transformation_remove_row(self):
        """Removes a row from the output tranformation"""
        num_rows = self.output_transformation_matrix.rowCount()
        self.output_transformation_matrix.removeRow(num_rows - 1)

    def save_output_transformation_matrix(self):
        """Saves output transformation matrix to a CSV file"""
        string_array = self.get_table_strings(self.output_transformation_matrix)
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Output Transformation", filter="Comma-separated Values (*.csv)")
        if filename == "":
            return
        save_csv_matrix(string_array, filename)

    def load_output_transformation_matrix(self):
        """Loads the output transformation from a CSV file"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Output Transformation",
            filter="Comma-separated values (*.csv *.txt);;" "Numpy Files (*.npy *.npz);;Matlab Files (*.mat)",
        )
        if filename == "":
            return
        _, extension = os.path.splitext(filename)
        string_array = None
        if extension.lower() == ".npy":
            string_array = np.load(filename).astype("U")
        elif extension.lower() == ".npz":
            data = np.load(filename)
            for key, array in data.items():
                string_array = array.astype("U")
                break
        elif extension.lower() == ".mat":
            data = loadmat(filename)
            for key, array in data.items():
                if "__" in key:
                    continue
                string_array = array.astype("U")
                break
        else:
            string_array = load_csv_matrix(filename)
        if string_array is None:
            return
        # Set the number of rows
        self.output_transformation_matrix.setRowCount(len(string_array))
        num_rows = self.output_transformation_matrix.rowCount()
        num_cols = self.output_transformation_matrix.columnCount()
        for row_idx, row in enumerate(string_array):
            if row_idx == num_rows:
                break
            for col_idx, value in enumerate(row):
                if col_idx == num_cols:
                    break
                try:
                    self.output_transformation_matrix.item(row_idx, col_idx).setText(value)
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(value)
                    self.output_transformation_matrix.setItem(row_idx, col_idx, item)

    def set_output_transformation_identity(self):
        """Sets the output transformation to identity (no transform)"""
        num_columns = self.output_transformation_matrix.columnCount()
        self.output_transformation_matrix.setRowCount(num_columns)
        for row_idx in range(num_columns):
            for col_idx in range(num_columns):
                if row_idx == col_idx:
                    value = 1.0
                else:
                    value = 0.0
                try:
                    self.output_transformation_matrix.item(row_idx, col_idx).setText(str(value))
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.output_transformation_matrix.setItem(row_idx, col_idx, item)

    def set_output_transformation_6dof(self):
        """Sets the output transformation matrix to the 6DoF table"""
        num_columns = self.output_transformation_matrix.columnCount()
        if num_columns != 12:
            error_message_qt(
                "Invalid Number of Output Signals.",
                "Invalid Number of Output Signals.  6DoF Transform assumes 12 drive channels.",
            )
            return
        self.output_transformation_matrix.setRowCount(6)
        matrix = [
            [0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0],
            [0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25, 0.0, 0.0, -0.25],
            [0.0, 0.0, -0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25],
            [
                -0.125,
                0.125,
                0.0,
                -0.125,
                -0.125,
                0.0,
                0.125,
                -0.125,
                0.0,
                0.125,
                0.125,
                0.0,
            ],
        ]
        for row_idx, row in enumerate(matrix):
            for col_idx, value in enumerate(row):
                try:
                    self.output_transformation_matrix.item(row_idx, col_idx).setText(str(value))
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.output_transformation_matrix.setItem(row_idx, col_idx, item)

    def set_output_transformation_6dof_reversed(self):
        """Sets the output transformation matrix to the 6DoF table"""
        num_columns = self.output_transformation_matrix.columnCount()
        if num_columns != 12:
            error_message_qt(
                "Invalid Number of Output Signals.",
                "Invalid Number of Output Signals.  6DoF Transform assumes 12 drive channels.",
            )
            return
        self.output_transformation_matrix.setRowCount(6)
        matrix = [
            [0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0],
            [0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25],
            [0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25, 0.0, 0.0, -0.25],
            [0.0, 0.0, -0.25, 0.0, 0.0, 0.25, 0.0, 0.0, 0.25, 0.0, 0.0, -0.25],
            [
                -0.125,
                0.125,
                0.0,
                -0.125,
                -0.125,
                0.0,
                0.125,
                -0.125,
                0.0,
                0.125,
                0.125,
                0.0,
            ],
        ]
        for row_idx, row in enumerate(matrix):
            for col_idx, value in enumerate(row):
                try:
                    self.output_transformation_matrix.item(row_idx, col_idx).setText(str(value))
                except AttributeError:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.output_transformation_matrix.setItem(row_idx, col_idx, item)
