from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.utilities import GlobalCommands
from rattlesnake.user_interface.ui_utilities import UICommands, Updater, EventWatcher, error_message_qt, VISIBLE_HARDWARE_WIDGETS, ui_path
from rattlesnake.hardware.hardware_utilities import HardwareType, Channel
from rattlesnake.environment.environment_utilities import ControlTypes
from qtpy import QtWidgets, QtGui, QtCore, uic
import traceback
import ctypes
import sys
import os
from datetime import datetime


TASK_NAME = "UI"
VERSION = "3.1.1"
directory = os.path.split(__file__)[0]
QtCore.QDir.addSearchPath("images", os.path.join(directory, "themes", "images"))


# region: Init
class RattlesnakeUI(QtWidgets.QMainWindow):
    def __init__(self, rattlesnake: Rattlesnake):
        super(RattlesnakeUI, self).__init__()

        uic.loadUi(ui_path, self)

        # Communication objects
        self.rattlesnake = rattlesnake
        self.gui_update_queue = rattlesnake.queue_container.gui_update_queue
        self.log_file_queue = rattlesnake.queue_container.log_file_queue
        self.timeout = rattlesnake.timeout

        # Updater process
        self.event_thread = None
        self.event_watcher = None
        self.threadpool = QtCore.QThreadPool()
        self.gui_updater = Updater(self.gui_update_queue)
        self.threadpool.start(self.gui_updater)
        self.gui_updater.signals.update.connect(self.update_gui)

        # Storage properties
        self.hardware_file = None

        # Complete UI layout
        self.connect_callbacks()
        self.complete_ui()

        self.show()

    def complete_ui(self):

        # Rattlesnake
        self.setMinimumWidth(500)

        # Data Setup Tab
        # Channel Table
        self.table_layout.setStretch(0, 5)  # Channel table
        self.table_layout.setStretch(1, 1)  # Environments table
        self.channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # Hardware Widgets
        self.hardware_widgets = {
            "hardware_selector": [self.hardware_selector_label, self.hardware_selector],
            "sample_rate": [self.sample_rate_label, self.sample_rate_selector],
            "lanxi_ip": [self.lanxi_ip_address_button],
            "lanxi_sample_rate": [self.lanxi_sample_rate_selector],
            "buffer_size": [self.buffer_size_label, self.buffer_size_selector],
            "lanxi_processes": [self.lanxi_maximum_acquisition_processes_label, self.lanxi_maximum_acquisition_processes_selector],
            "integration_oversample": [self.integration_oversample_label, self.integration_oversample_selector],
            "damping_ratio": [self.damping_ratio_label, self.damping_ratio_selector],
            "task_trigger": [self.task_trigger_label, self.task_trigger_selector],
            "trigger_output": [self.trigger_output_label, self.trigger_output_selector],
            "select_file": [self.select_file_button],
        }
        self.update_sampling_parameters_visibility()

        # Environments table
        self.environment_channel_table.horizontalHeader().setVisible(True)
        self.environment_channel_table.verticalHeader().setVisible(True)
        self.environment_channel_table.setColumnCount(1)
        self.environment_channel_table.hide()
        for control in ControlTypes:
            self.add_environment_combobox.addItem(control.name)

        # Set icons and window
        icon = QtGui.QIcon("logo/Rattlesnake_Icon.png")
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.show()
        if sys.platform.startswith("win"):  # This fixes windows treating taskbar icon as python.exe
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"sandia.rattlesnake.{VERSION}")
        self.setWindowIcon(icon)
        self.setWindowTitle("Rattlesnake Vibration Controller")
        self.change_color_theme("Light")

    def connect_callbacks(self):
        # Universal
        self.color_theme_combobox.currentTextChanged.connect(self.change_color_theme)

        # Data Setup Tab
        # Channel table
        channel_table_scroll = self.channel_table.verticalScrollBar()
        channel_table_scroll.valueChanged.connect(self.sync_environment_table)
        environment_table_scroll = self.environment_channel_table.verticalScrollBar()
        environment_table_scroll.valueChanged.connect(self.sync_channel_table)
        # Copy
        self.channel_table_action_copy = QtWidgets.QAction("Copy", self.channel_table)
        self.channel_table_action_copy.setShortcut("Ctrl+C")
        self.channel_table_action_copy.triggered.connect(self.channel_table_copy)
        self.channel_table.addAction(self.channel_table_action_copy)
        # Paste
        self.channel_table_action_paste = QtWidgets.QAction("Paste", self.channel_table)
        self.channel_table_action_paste.setShortcut("Ctrl+V")
        self.channel_table_action_paste.triggered.connect(self.channel_table_paste)
        self.channel_table.addAction(self.channel_table_action_paste)
        # Delete
        self.channel_table_action_delete = QtWidgets.QAction("Delete", self.channel_table)
        self.channel_table_action_delete.setShortcut("Del")
        self.channel_table_action_delete.triggered.connect(self.channel_table_delete)
        self.channel_table.addAction(self.channel_table_action_delete)
        # Hardware
        self.hardware_selector.currentTextChanged.connect(self.hardware_update)
        self.initialize_hardware_button.clicked.connect(self.initialize_hardware)

    # region: Utility Functions
    def update_sampling_parameters_visibility(self):
        """Helper function to update the visibility of the sampling parameters group box"""
        current_hardware = self.hardware_selector.currentText()
        visible_widgets = VISIBLE_HARDWARE_WIDGETS.get(current_hardware, set())

        for name, widgets in self.hardware_widgets.items():
            for widget in widgets:
                widget.setVisible(name in visible_widgets)

    def get_channel_list(self):
        channel_list = []
        channel_attr_list = Channel().channel_attr_list
        for row_idx in range(self.channel_table.rowCount()):
            channel = Channel()
            for col_idx in range(self.channel_table.columnCount()):
                attr = channel_attr_list[col_idx]
                item = self.channel_table.item(row_idx, col_idx)
                if item is not None:
                    setattr(channel, attr, item.text())

            if channel.is_empty:
                break

            channel_list.append(channel)

        return channel_list

    def get_hardware_metadata(self):
        pass

    # region: Data Setup Tab Callbacks
    def channel_table_copy(self):
        """Function to copy text from channel table in a format that Excel recognizes"""
        clipboard = QtWidgets.QApplication.clipboard()
        selected_ranges = self.channel_table.selectedRanges()
        if selected_ranges:
            # Get selected range
            selected_range = selected_ranges[0]
            copied_text = ""
            rows = range(selected_range.topRow(), selected_range.bottomRow() + 1)
            columns = range(selected_range.leftColumn(), selected_range.rightColumn() + 1)
            # Put tabs inbetween columns, newlines inbetween rows
            copied_text = []
            for row in rows:
                row_data = []
                for column in columns:
                    item = self.channel_table.item(row, column)
                    row_data.append(item.text() if item else "")  # Empty cells should be "" not None
                copied_text.append("\t".join(row_data))  # Tab betewen columns
            copied_text = "\n".join(copied_text)  # Newline between rows
            clipboard.setText(copied_text)

    def channel_table_paste(self):
        """Function to paste clipboard starting from top left cell"""
        selection_range = self.channel_table.selectedRanges()
        self.channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        if selection_range:
            # Get top left cell
            top_left_row = selection_range[0].topRow()
            top_left_column = selection_range[0].leftColumn()
            # Get clipboard text
            clipboard = QtWidgets.QApplication.clipboard()
            if clipboard.mimeData().hasText():
                clipboard_text = clipboard.text()
                # Split clipboard text with newlines between rows
                rows = clipboard_text.splitlines()
                # Split clipboard text with tabs between columns
                array_text = [row.split("\t") for row in rows]
                # Paste the text into the table
                for i, row in enumerate(array_text):
                    for j, cell_text in enumerate(row):
                        cell_text = cell_text if cell_text is not None else ""
                        item = QtWidgets.QTableWidgetItem(cell_text)
                        self.channel_table.setItem(top_left_row + i, top_left_column + j, item)
        self.channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def channel_table_delete(self):
        """Function to delete text from a channel table when delete is pressed"""
        selection_range = self.channel_table.selectedRanges()
        self.channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        if selection_range:
            # Get the selected range
            selected_range = selection_range[0]
            rows = range(selected_range.topRow(), selected_range.bottomRow() + 1)
            columns = range(selected_range.leftColumn(), selected_range.rightColumn() + 1)
            # Clear the selected cells
            for row in rows:
                for column in columns:
                    clear_item = QtWidgets.QTableWidgetItem("")
                    self.channel_table.setItem(row, column, clear_item)
        self.channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def sync_environment_table(self):
        """Callback to synchronize scrolling between channel tables"""
        self.environment_channel_table.verticalScrollBar().setValue(self.channel_table.verticalScrollBar().value())

    def sync_channel_table(self):
        """Callback to synchronize scrolling between channel tables"""
        self.channel_table.verticalScrollBar().setValue(self.environment_channel_table.verticalScrollBar().value())

    def hardware_update(self, hardware_text):
        self.update_sampling_parameters_visibility()

        match hardware_text:
            case "SDynPy System Integration...":
                filename, file_filter = QtWidgets.QFileDialog.getOpenFileName(self, "Load a SDynPy System", filter="Numpy File (*.npz)")
                # Check for 'cancel' dialog
                if filename == "" or filename is None:
                    self.hardware_selector.blockSignals(True)
                    self.hardware_selector.setCurrentText("Select Hardware")
                    self.hardware_selector.blockSignals(False)
                    return
                self.hardware_file = filename

    def initialize_hardware(self):
        self.log("Initializing Hardware")

        # Prevent user from initializing multiple times
        self.initialize_hardware_button.setEnabled(False)

        try:
            # Build hardware metadata
            channel_list = self.get_channel_list()
            hardware_text = self.hardware_selector.currentText()
            match hardware_text:
                case "Select Hardware":
                    self.initialize_hardware_error("Please select a hardware type.")
                    return
                case "NI DAQmx":
                    from rattlesnake.hardware.nidaqmx import NIDAQmxMetadata

                    hardware_metadata = NIDAQmxMetadata()
                    hardware_metadata.channel_list = channel_list
                    hardware_metadata.sample_rate = self.sample_rate_selector.value()
                    hardware_metadata.time_per_read = self.buffer_size_selector.value()
                    hardware_metadata.time_per_write = self.buffer_size_selector.value()
                    hardware_metadata.task_trigger = self.task_trigger_selector.text()
                    hardware_metadata.output_trigger_generator = self.trigger_output_selector.value()

                case "HBK LAN-XI":
                    self.initialize_hardware_error(f"{hardware_text} has not been implemented yet")
                    return
                case "Data Physics Quattro":
                    self.initialize_hardware_error(f"{hardware_text} has not been implemented yet")
                    return
                case "Data Physics 900 Series":
                    self.initialize_hardware_error(f"{hardware_text} has not been implemented yet")
                    return
                case "Exodus Modal Solution...":
                    self.initialize_hardware_error(f"{hardware_text} has not been implemented yet")
                    return
                case "State Space Integration...":
                    self.initialize_hardware_error(f"{hardware_text} has not been implemented yet")
                    return
                case "SDynPy System Integration...":
                    from rattlesnake.hardware.sdynpy_system import SDynPySystemMetadata

                    hardware_metadata = SDynPySystemMetadata()
                    hardware_metadata.channel_list = channel_list
                    hardware_metadata.sample_rate = self.sample_rate_selector.value()
                    hardware_metadata.time_per_read = self.buffer_size_selector.value()
                    hardware_metadata.time_per_write = self.buffer_size_selector.value()
                    hardware_metadata.output_oversample = self.integration_oversample_selector.value()
                    hardware_metadata.hardware_file = self.hardware_file

                case "SDynPy FRF Convolution...":
                    self.initialize_hardware_error(f"{hardware_text} has not been implemented yet")
                    return

            # Send hardware metadata to rattlesnake
            self.rattlesnake.set_hardware(hardware_metadata)
        except Exception:
            tb = traceback.format_exc()
            self.initialize_hardware_error(tb)
            return

        # Block until hardware metadata has been stored
        ready_event_list = [
            self.rattlesnake.event_container.acquisition_ready_event,
            self.rattlesnake.event_container.output_ready_event,
            *self.rattlesnake.environment_manager.ready_event_list,
        ]
        active_event_list = []
        if getattr(self, "event_thread", None) or getattr(self, "event_watcher", None):
            self.initialize_hardware_error("Event watcher is still active")
            return
        self.event_thread = QtCore.QThread()
        self.event_watcher = EventWatcher(ready_event_list, active_event_list, timeout=self.timeout)
        self.event_watcher.moveToThread(self.event_thread)
        self.event_thread.started.connect(self.event_watcher.run)
        self.event_watcher.ready.connect(self.initialize_hardware_ready)
        self.event_watcher.error.connect(self.initialize_hardware_error)
        self.event_thread.start()

    def initialize_hardware_ready(self):
        # Clear QThread
        self.cleanup_event_thread()

        # Unlock UI
        self.initialize_hardware_button.setEnabled(True)
        self.rattlesnake_tabs.setTabEnabled(1, True)
        self.rattlesnake_tabs.setCurrentIndex(1)

    def initialize_hardware_error(self, error_message):
        # Clear QThread
        self.cleanup_event_thread()

        # Unlock UI
        self.initialize_hardware_button.setEnabled(True)
        self.display_error(error_message)

    # region: Environment callbacks
    def add_environment(self):
        """Function used to add an environment"""
        # Check whether it was added from Data Setup tab or Definitions tab
        if self.rattlesnake_tabs.currentIndex() == 0:  # Data setup tab
            environment_str = self.add_environment_combobox.currentText()
        elif self.rattlesnake_tabs.currentIndex() == 1:  # Definitions tab
            environment_str = self.definition_tab_combobox.currentText()

        # If an environment was not selected, return
        if environment_str == "Add Environment" or environment_str == "+":
            return

        # Add environment to container
        channel_list = self.get_channel_list()

        match environment_str:
            case "Add Environment":
                return
            case "+":
                return
            case "RANDOM":
                return
            case "TRANSIENT":
                return
            case "SINE":
                return
            case "TIME":
                from rattlesnake.user_interface.time_ui import TimeUI

                pass
            case "MODAL":
                return
            case "READ":
                return

        self.update_run_environment_list(self.environments.control_names)

        # Refresh the Ui
        self.environments.update_channel_rows(self.channels.row_count)
        self.update_environment_table()
        self.update_environment_tabs()

    # region: Global callbacks
    def change_color_theme(self, text: str):
        """Updates the color scheme of the UI"""
        if text == "Light":
            self.setStyleSheet("")
        elif text == "Dark":
            dark_theme_path = os.path.join(directory, "themes", "dark_theme.txt")
            with open(dark_theme_path, encoding="utf-8") as file:
                stylesheet = file.read()
            images_path = os.path.join(directory, "themes", "images").replace("\\", "/")
            # print(f"Images Path: {images_path}")
            stylesheet.replace(r"%%IMAGES_PATH%%", images_path)
            self.setStyleSheet(stylesheet)

    # region: QThread Functions
    def cleanup_event_thread(self):
        if getattr(self, "event_thread", None):
            self.event_thread.quit()
            self.event_thread.wait()
            self.event_thread.deleteLater()
            self.event_thread = None
        if getattr(self, "event_watcher", None):
            self.event_watcher.deleteLater()
            self.event_watcher = None

    def update_gui(self, queue_data):
        message, data = queue_data
        if message == UICommands.ERROR:
            dialog_title, error_message = data
            error_message_qt(dialog_title, error_message)
        elif message in self.environment_queues:
            self.environment_uis[message].update_gui(data)
        elif message == UICommands.MONITOR:
            pass
        elif message == UICommands.ENABLE:
            pass
        elif message == UICommands.DISABLE:
            pass
        elif message == UICommands.ENABLE_TAB:
            pass
        elif message == UICommands.DISABLE_TAB:
            pass
        elif message == UICommands.SET_ATTR:
            pass
        else:
            pass

    def log(self, string):
        """Pass a message to the log_file_queue along with date/time and task name

        Parameters
        ----------
        string : str
            Message that will be written to the queue

        """
        self.log_file_queue.put(f"{datetime.now()}: {TASK_NAME} -- {string}\n")

    def display_error(self, error_message):
        self.log(f"ERROR\n\n {error_message}")
        self.gui_update_queue.put(
            (
                UICommands.ERROR,
                (f"Rattlesnake Error", f"ERROR:\n\n{error_message}"),
            )
        )

    def closeEvent(self, event):
        self.gui_update_queue.put((GlobalCommands.QUIT, None))
        self.threadpool.waitForDone()

        event.accept()


if __name__ == "__main__":
    rattlesnake = Rattlesnake(threaded=True, blocking=False, timeout=10)

    # This is a fix for scaling Rattlesnake to different resolution monitors
    font_size = 10  # pt size
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QtWidgets.QApplication(sys.argv)
    screen = app.primaryScreen()
    dpi = screen.logicalDotsPerInch()
    scale_factor = dpi / 96  # 96 DPI = standard
    font = app.font()
    font.setPointSizeF(font_size * scale_factor)  # base font 12pt
    app.setFont(font)
    _ = RattlesnakeUI(rattlesnake)
    app.exec_()

    rattlesnake.shutdown()
