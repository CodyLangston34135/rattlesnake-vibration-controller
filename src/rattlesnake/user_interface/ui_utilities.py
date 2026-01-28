from ..utilities import VerboseMessageQueue, GlobalCommands
from ..environment.environment_utilities import ControlTypes
import sys
import os
import time
from enum import Enum
from qtpy import QtCore

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


class TimeUICommands(Enum):
    ENABLE = 0
    DISABLE = 1
    TIME_DATA = 2


class ReadUICommands(Enum):
    TIME_DATA = 0


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
