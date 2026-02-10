from rattlesnake.rattlesnake import Rattlesnake, RattlesnakeState
from rattlesnake.utilities import GlobalCommands
from rattlesnake.user_interface.ui_utilities import (
    UICommands,
    Updater,
    EventWatcher,
    EditableCombobox,
    EditableSpinBox,
    error_message_qt,
    VISIBLE_HARDWARE_WIDGETS,
    HARDWARE_TYPE,
    ENVIRONMENT_TYPE,
    ui_path,
)
from rattlesnake.hardware.hardware_utilities import HardwareType, HardwareModules, Channel
from rattlesnake.environment.environment_utilities import ControlTypes, environment_long_names
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
        self.rattlesnake.clear_blocking()
        self.environment_uis = {}

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

        # Store any presets to the UI
        self.load_from_rattlesnake_state()

        self.show()

    def complete_ui(self):

        # Rattlesnake
        self.setMinimumWidth(500)
        # Disable all tabs except the first
        for i in range(1, self.rattlesnake_tabs.count() - 1):
            self.rattlesnake_tabs.setTabEnabled(i, False)
        self.rattlesnake_tabs.tabBar().setTabVisible(2, False)
        self.rattlesnake_tabs.tabBar().setTabVisible(3, False)

        # Data Setup Tab
        # Channel Table
        self.table_layout.setStretch(0, 5)  # Channel table
        self.table_layout.setStretch(1, 1)  # Environments table
        self.channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # Environment Channel Table
        self.environment_channel_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.environment_channel_table.horizontalHeader().setVisible(True)
        self.environment_channel_table.verticalHeader().setVisible(True)
        self.environment_channel_table.setColumnCount(0)
        self.environment_channel_table.hide()
        for control in ControlTypes:
            self.add_environment_combobox.addItem(control.name)
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
        self.update_hardware_widget_visibility()

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

    # region: Callbacks
    def connect_callbacks(self):
        # Universal
        self.color_theme_combobox.currentTextChanged.connect(self.change_color_theme)

        # Data Setup Tab
        # Channel Table
        channel_table_scroll = self.channel_table.verticalScrollBar()
        channel_table_scroll.valueChanged.connect(self.sync_environment_table)
        self.assist_channel_table_checkbox.stateChanged.connect(self.assist_channel_table_init)
        # Copy
        self.channel_table_action_copy = QtWidgets.QAction("Copy", self.channel_table)
        self.channel_table_action_copy.setShortcut("Ctrl+C")
        self.channel_table_action_copy.triggered.connect(self.copy_channel_table)
        self.channel_table.addAction(self.channel_table_action_copy)
        # Paste
        self.channel_table_action_paste = QtWidgets.QAction("Paste", self.channel_table)
        self.channel_table_action_paste.setShortcut("Ctrl+V")
        self.channel_table_action_paste.triggered.connect(self.paste_channel_table)
        self.channel_table.addAction(self.channel_table_action_paste)
        # Delete
        self.channel_table_action_delete = QtWidgets.QAction("Delete", self.channel_table)
        self.channel_table_action_delete.setShortcut("Del")
        self.channel_table_action_delete.triggered.connect(self.delete_channel_table)
        self.channel_table.addAction(self.channel_table_action_delete)
        # Hardware
        self.hardware_selector.currentTextChanged.connect(self.update_hardware)
        self.initialize_hardware_button.clicked.connect(self.initialize_hardware)
        self.select_file_button.clicked.connect(self.select_hardware_file)
        # Environment Channel Table
        environment_table_scroll = self.environment_channel_table.verticalScrollBar()
        environment_table_scroll.valueChanged.connect(self.sync_channel_table)
        self.add_environment_combobox.currentTextChanged.connect(self.add_environment)
        self.remove_environment_button.clicked.connect(self.remove_environment)
        self.environment_channel_table.horizontalHeader().sectionDoubleClicked.connect(self.rename_environment)

        # Environment Definition Tab
        self.initialize_environments_button.clicked.connect(self.initialize_environments)

    @property
    def gui_update_queue(self):
        return self.rattlesnake.queue_container.gui_update_queue

    @property
    def log_file_queue(self):
        return self.rattlesnake.queue_container.log_file_queue

    @property
    def timeout(self):
        return self.rattlesnake.timeout

    @property
    def has_system_id(self):
        if self.system_id_environment_tabs.count() != 0:
            return True
        return False

    @property
    def has_test_pred(self):
        if self.test_prediction_environment_tabs.count() != 0:
            return True
        return False

    # region: Data Loading
    def load_from_rattlesnake_state(self):
        state = self.rattlesnake.state

        match state:
            case RattlesnakeState.INIT:
                return
            case RattlesnakeState.HARDWARE_STORE:
                self.load_hardware_stored()
            case RattlesnakeState.ENVIRONMENT_STORE:
                self.load_hardware_stored()
                self.load_enviroment_store()

    def load_hardware_stored(self):
        hardware_metadata = self.rattlesnake.hardware_metadata

        # Fill out channel table
        channel_list = hardware_metadata.channel_list
        attr_list = Channel().channel_attr_list
        for row, channel in enumerate(channel_list):
            for col, attr_name in enumerate(attr_list):
                value = getattr(channel, attr_name)
                value = str(value) if value else None

                item = QtWidgets.QTableWidgetItem(value)
                self.channel_table.setItem(row, col, item)

        match hardware_metadata.hardware_type:
            case HardwareType.SDYNPY_SYSTEM:
                self.hardware_selector.blockSignals(True)
                self.hardware_selector.setCurrentText("SDynPy System Integration...")
                self.hardware_selector.blockSignals(False)
                self.update_hardware_widget_visibility()
                self.hardware_file = hardware_metadata.hardware_file
                self.sample_rate_selector.setValue(hardware_metadata.sample_rate)
                self.buffer_size_selector.setValue(hardware_metadata.samples_per_read)
                self.integration_oversample_selector.setValue(hardware_metadata.output_oversample)
            case _:
                self.display_error(f"{hardware_metadata.hardware_type} is not yet implemented")

    def load_enviroment_store(self):
        hardware_metadata = self.rattlesnake.hardware_metadata
        environment_metadata_dict = self.rattlesnake.environment_metadata

        for environment_idx, environment_metadata in enumerate(environment_metadata_dict.values()):
            # Add environments
            environment_type = environment_metadata.environment_type
            self.add_environment(environment_type)

            environment_name = environment_metadata.environment_name
            self.rename_environment(environment_idx, environment_name)

            self.environment_uis[environment_name].initialize_hardware(hardware_metadata)
            self.environment_uis[environment_name].store_metadata(environment_metadata)

        self.update_environment_tabs()
        self.rattlesnake_tabs.setTabEnabled(1, True)
        self.rattlesnake_tabs.setCurrentIndex(1)

    # region: Channel Table
    def get_channel(self, row):
        channel = Channel()
        channel_attr_list = channel.channel_attr_list
        for col in range(self.channel_table.columnCount()):
            attr = channel_attr_list[col]
            item = self.channel_table.item(row, col)
            # Check if item exists and has text
            if item and item.text().strip():
                setattr(channel, attr, item.text())

        return channel

    def get_channel_list(self):
        channel_list = []
        channel_attr_list = Channel().channel_attr_list
        for row in range(self.channel_table.rowCount()):
            channel = Channel()
            for col in range(self.channel_table.columnCount()):
                attr = channel_attr_list[col]
                item = self.channel_table.item(row, col)
                # Check if item exists and has text
                if item and item.text().strip():
                    setattr(channel, attr, item.text())

            if channel.is_empty:
                break

            channel_list.append(channel)

        return channel_list

    def sync_channel_table(self):
        """Callback to synchronize scrolling between channel tables"""
        self.channel_table.verticalScrollBar().setValue(self.environment_channel_table.verticalScrollBar().value())

    def copy_channel_table(self):
        """Function to copy text from channel table in a format that Excel recognizes"""
        if self.assist_channel_table_checkbox.isChecked():
            self.display_error("Please remove assist mode for copy functionality")
            return

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

    def paste_channel_table(self):
        """Function to paste clipboard starting from top left cell"""
        if self.assist_channel_table_checkbox.isChecked():
            self.display_error("Please remove assist mode for paste functionality")
            return

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

    def delete_channel_table(self):
        """Function to delete text from a channel table when delete is pressed"""
        if self.assist_channel_table_checkbox.isChecked():
            self.display_error("Please remove assist mode for delete functionality")
            return

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

    def assist_channel_table_init(self, assist_checked):
        # Clear out old widgets:
        num_rows = self.channel_table.rowCount()
        num_cols = self.channel_table.columnCount()
        for row in range(num_rows):
            for col in range(num_cols):
                self.channel_table.removeCellWidget(row, col)

        # Should be fine
        if not assist_checked:
            return

        # Build new modules
        hardware_metadata = self.get_hardware_metadata_no_channels()
        channel_list = self.get_channel_list()
        hardware_modules = hardware_metadata.assist_mode_modules
        for row, channel in enumerate(channel_list):
            channel_dict = hardware_metadata.valid_channel_dict(channel)
            for col, (attr, module) in enumerate(hardware_modules.items()):
                attr_value = getattr(channel, attr)
                valid_values = channel_dict[attr]
                match module:
                    case HardwareModules.NONE:
                        pass
                    case HardwareModules.COMBOBOX:
                        combobox = EditableCombobox(valid_values, attr_value)
                        combobox.currentTextChanged.connect(lambda text, row=row, col=col: self.assist_channel_table_update(text, row, col))
                        self.channel_table.setCellWidget(row, col, combobox)
                    case HardwareModules.SPINBOX:
                        pass

        # Fill out empty modules
        empty_channel_dict = hardware_metadata.valid_channel_dict(Channel())
        for row in range(len(channel_list), num_rows):
            for col, (attr, module) in enumerate(hardware_modules.items()):
                valid_values = empty_channel_dict[attr]
                match module:
                    case HardwareModules.NONE:
                        # item = QtWidgets.QTableWidgetItem(attr_value)
                        # self.channel_table.setItem(row, col, item)
                        pass
                    case HardwareModules.COMBOBOX:
                        combobox = EditableCombobox(valid_values)
                        combobox.currentTextChanged.connect(lambda text, row=row, col=col: self.assist_channel_table_update(text, row, col))
                        self.channel_table.setCellWidget(row, col, combobox)
                    case HardwareModules.SPINBOX:
                        pass

    def assist_channel_table_update(self, text, row, col):
        # Assign text to channel table item
        item = QtWidgets.QTableWidgetItem(text)
        self.channel_table.setItem(row, col, item)

        hardware_metadata = self.get_hardware_metadata_no_channels()
        channel = self.get_channel(row)
        hardware_modules = hardware_metadata.assist_mode_modules
        channel_dict = hardware_metadata.valid_channel_dict(channel)
        for col, (attr, module) in enumerate(hardware_modules.items()):
            attr_value = getattr(channel, attr)
            valid_values = channel_dict[attr]
            match module:
                case HardwareModules.NONE:
                    pass
                case HardwareModules.COMBOBOX:
                    combobox = EditableCombobox(valid_values, attr_value)
                    combobox.currentTextChanged.connect(lambda text, row=row, col=col: self.assist_channel_table_update(text, row, col))
                    self.channel_table.setCellWidget(row, col, combobox)
                case HardwareModules.SPINBOX:
                    pass

    # region: Hardware
    def get_hardware_metadata_no_channels(self):

        hardware_text = self.hardware_selector.currentText()
        hardware_type = HARDWARE_TYPE[hardware_text]
        match hardware_type:
            case "Select":
                from rattlesnake.hardware.abstract_hardware import NullHardwareMetadata

                hardware_metadata = NullHardwareMetadata("Select")
            case HardwareType.NI_DAQMX:
                from rattlesnake.hardware.nidaqmx import NIDAQmxMetadata

                hardware_metadata = NIDAQmxMetadata()
                hardware_metadata.sample_rate = self.sample_rate_selector.value()
                hardware_metadata.time_per_read = self.buffer_size_selector.value()
                hardware_metadata.time_per_write = self.buffer_size_selector.value()
                hardware_metadata.task_trigger = self.task_trigger_selector.text()
                hardware_metadata.output_trigger_generator = self.trigger_output_selector.value()
            case HardwareType.LAN_XI:
                return
            case HardwareType.DP_QUATTRO:
                return
            case HardwareType.DP_900:
                return
            case HardwareType.EXODUS:
                return
            case HardwareType.STATE_SPACE:
                return
            case HardwareType.SDYNPY_SYSTEM:
                from rattlesnake.hardware.sdynpy_system import SDynPySystemMetadata

                hardware_metadata = SDynPySystemMetadata()
                hardware_metadata.sample_rate = self.sample_rate_selector.value()
                hardware_metadata.time_per_read = self.buffer_size_selector.value()
                hardware_metadata.time_per_write = self.buffer_size_selector.value()
                hardware_metadata.output_oversample = self.integration_oversample_selector.value()
                hardware_metadata.hardware_file = self.hardware_file
            case HardwareType.SDYNPY_FRF:
                return

        return hardware_metadata

    def update_hardware(self, hardware_text):
        self.update_hardware_widget_visibility()

        hardware_type = HARDWARE_TYPE[hardware_text]
        match hardware_type:
            case HardwareType.SDYNPY_SYSTEM:
                filename, file_filter = QtWidgets.QFileDialog.getOpenFileName(self, "Load a SDynPy System", filter="Numpy File (*.npz)")
                # Check for 'cancel' dialog
                if filename == "" or filename is None:
                    self.hardware_selector.blockSignals(True)
                    self.hardware_selector.setCurrentText("Select Hardware")
                    self.hardware_selector.blockSignals(False)
                    return
                self.hardware_file = filename

        if self.assist_channel_table_checkbox.isChecked():
            self.assist_channel_table_init(True)

    def update_hardware_widget_visibility(self):
        """Helper function to update the visibility of the sampling parameters group box"""
        current_hardware = self.hardware_selector.currentText()
        visible_widgets = VISIBLE_HARDWARE_WIDGETS.get(current_hardware, set())

        for name, widgets in self.hardware_widgets.items():
            for widget in widgets:
                widget.setVisible(name in visible_widgets)

    def select_hardware_file(self):
        filename, file_filter = QtWidgets.QFileDialog.getOpenFileName(self, "Load a SDynPy System", filter="Numpy File (*.npz)")
        # Check for 'cancel' dialog
        if filename == "" or filename is None:
            return
        self.hardware_file = filename

    def initialize_hardware(self):
        self.log("Initializing Hardware")

        # Prevent user from initializing multiple times
        self.initialize_hardware_button.setEnabled(False)

        try:
            # Build hardware metadata
            hardware_metadata = self.get_hardware_metadata_no_channels()
            channel_list = self.get_channel_list()
            hardware_metadata.channel_list = channel_list
            if hardware_metadata.hardware_type == "Select":
                self.initialize_hardware_error("Please select a hardware type.")

            # Send hardware metadata to rattlesnake
            self.rattlesnake.set_hardware(hardware_metadata)

            environment_channel_list = self.get_environment_channel_list()
            for environment_name, environment_ui in self.environment_uis.items():
                hardware_metadata.channel_list = environment_channel_list[environment_name]
                environment_ui.initialize_hardware(hardware_metadata)

        except Exception as e:
            self.initialize_hardware_error(e)
            return

        # Block until hardware metadata has been stored
        ready_event_list = [
            self.rattlesnake.event_container.acquisition_ready_event,
            self.rattlesnake.event_container.output_ready_event,
            *self.rattlesnake.environment_manager.ready_event_list,
        ]
        active_event_list = []
        self.create_event_watcher(ready_event_list, active_event_list)
        self.event_watcher.ready.connect(self.initialize_hardware_ready)
        self.event_watcher.error.connect(self.initialize_hardware_error)
        self.event_thread.start()

    def initialize_hardware_ready(self):
        # Clear QThread
        self.cleanup_event_watcher()

        # Unlock UI
        self.initialize_hardware_button.setEnabled(True)
        self.update_environment_tabs()
        num_environments = len(self.environment_uis)
        if num_environments == 0:
            self.rattlesnake_tabs.setTabEnabled(1, False)
        else:
            self.rattlesnake_tabs.setTabEnabled(1, True)
            self.rattlesnake_tabs.setCurrentIndex(1)

    def initialize_hardware_error(self, error_message):
        # Clear QThread
        self.cleanup_event_watcher()

        # Unlock UI
        self.initialize_hardware_button.setEnabled(True)
        self.display_error(error_message)

    # region: Environment
    def get_environment_channel_list(self):
        channel_list = self.get_channel_list()
        environment_channel_list = {}
        num_rows = self.environment_channel_table.rowCount()
        num_cols = self.environment_channel_table.columnCount()
        for col in range(num_cols):
            header_item = self.environment_channel_table.horizontalHeaderItem(col)
            environment_name = header_item.text()
            selected_channels = []

            for row in range(num_rows):
                checkbox = self.environment_channel_table.cellWidget(row, col)
                if checkbox is None:
                    continue
                if checkbox.isChecked():
                    if row < len(channel_list):
                        selected_channels.append(channel_list[row])
            environment_channel_list[environment_name] = selected_channels

        return environment_channel_list

    def sync_environment_table(self):
        """Callback to synchronize scrolling between channel tables"""
        self.environment_channel_table.verticalScrollBar().setValue(self.channel_table.verticalScrollBar().value())

    def add_environment(self, environment_type: str | ControlTypes):
        """Function used to add an environment"""
        # If comming from UI, environment_type will be text in combobox
        if isinstance(environment_type, str):
            environment_type = ENVIRONMENT_TYPE[environment_type]

        match environment_type:
            case "Select":
                return
            case ControlTypes.RANDOM:
                return
            case ControlTypes.TRANSIENT:
                return
            case ControlTypes.SINE:
                return
            case ControlTypes.TIME:
                from rattlesnake.user_interface.time_ui import TimeUI

                # Create a unique name
                idx = 0
                environment_name = f"Time Environment {idx}"
                while environment_name in self.environment_uis.keys():
                    idx += 1
                    environment_name = f"Time Environment {idx}"

                environment_ui = TimeUI(environment_name, self.rattlesnake)
            case ControlTypes.MODAL:
                return
            case ControlTypes.READ:
                return
            case _:
                self.display_error("Environment type does not exist. How did you get here?")
                return

        # Update environment UIs and channel table
        self.environment_uis[environment_name] = environment_ui
        new_col = self.environment_channel_table.columnCount()
        self.environment_channel_table.insertColumn(new_col)
        self.environment_channel_table.setHorizontalHeaderItem(new_col, QtWidgets.QTableWidgetItem(environment_name))
        self.environment_channel_table.show()

        # Set checkboxes
        channel_list = self.get_channel_list()
        num_channels = len(channel_list)
        num_rows = self.environment_channel_table.rowCount()
        for row in range(num_rows):
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(row < num_channels)
            self.environment_channel_table.setCellWidget(row, new_col, checkbox)

        # Reset add environment combobox
        self.add_environment_combobox.setCurrentIndex(0)

    def remove_environment(self, index):
        # Find selected ranges on the environment channel table
        selected_ranges = self.environment_channel_table.selectedRanges()
        if not selected_ranges:
            self.display_error("Please select an environment in environment channel table to remove")
            return

        # Remove selected columns from environment table and environment_uis
        selected_range = selected_ranges[0]
        columns = range(selected_range.leftColumn(), selected_range.rightColumn() + 1)
        for col in sorted(columns, reverse=True):
            header_item = self.environment_channel_table.horizontalHeaderItem(col)
            environment_name = header_item.text()
            self.environment_uis.pop(environment_name)
            self.environment_channel_table.removeColumn(col)

        # If all environments are removed, hide environment channel table
        if len(self.environment_uis) == 0:
            self.environment_channel_table.hide()

    def rename_environment(self, col_idx: int, new_name: str):
        """Function to rename an environment

        Parameters
        ----------
        index : int :
            The index of the environment to rename
        """

        # Pull header text from environment_channel_table
        header_item = self.environment_channel_table.horizontalHeaderItem(col_idx)
        current_name = header_item.text()

        # If name not given, ask user for a name
        if not new_name:
            # Create dialog box to get a new name
            new_name, ok_chosen = QtWidgets.QInputDialog.getText(self, "Rename Tab", "Enter new tab name:", text=current_name)
            if not ok_chosen:
                return
            new_name = new_name.strip()
            if not new_name:
                return

        # Make sure name does not already exist
        if new_name in self.environment_uis:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "The new name already exists. Please choose a different name.",
            )
            return

        # Replace old name in dict with new name while keeping order
        # This is scuffed but is very specific to this case
        ordered_dict = {}
        for environment_name, environment_ui in self.environment_uis.items():
            if environment_name == current_name:
                ordered_dict[new_name] = environment_ui
            else:
                ordered_dict[environment_name] = environment_ui
        self.environment_uis = ordered_dict
        header_item.setText(new_name)

    def update_environment_tabs(self):

        # Definition tabs
        self.environment_definition_environment_tabs.setCurrentIndex(-1)
        self.environment_definition_environment_tabs.clear()
        for environment_name, environment_ui in self.environment_uis.items():
            definition_widget = environment_ui.definition_widget
            if definition_widget is not None:
                self.environment_definition_environment_tabs.addTab(definition_widget, environment_name)

        # System Identification tab
        self.rattlesnake_tabs.tabBar().setTabVisible(2, False)
        self.system_id_environment_tabs.setCurrentIndex(-1)
        self.system_id_environment_tabs.clear()
        for environment_name, environment_ui in self.environment_uis.items():
            system_id_widget = environment_ui.system_id_widget
            if system_id_widget is not None:
                self.system_id_environment_tabs.addTab(system_id_widget, environment_name)
                self.rattlesnake_tabs.tabBar().setTabVisible(2, True)

        # Prediction tab
        self.rattlesnake_tabs.tabBar().setTabVisible(3, False)
        self.test_prediction_environment_tabs.setCurrentIndex(-1)
        self.test_prediction_environment_tabs.clear()
        for environment_name, environment_ui in self.environment_uis.items():
            prediction_widget = environment_ui.prediction_widget
            if prediction_widget is not None:
                self.test_prediction_environment_tabs.addTab(prediction_widget, environment_name)
                self.rattlesnake_tabs.tabBar().setTabVisible(3, True)

        # Run tab
        self.run_environment_tabs.setCurrentIndex(-1)
        self.run_environment_tabs.clear()
        for environment_name, environment_ui in self.environment_uis.items():
            run_widget = environment_ui.run_widget
            if run_widget is not None:
                self.run_environment_tabs.addTab(run_widget, environment_name)

    def initialize_environments(self):
        self.log("Initializing Environment")

        # Prevent user from initializing multiple times
        self.initialize_environments_button.setEnabled(False)

        try:
            # Build environment metadata list
            environment_metadata_list = []
            for environment_ui in self.environment_uis.values():
                metadata = environment_ui.get_environment_metadata()
                environment_metadata_list.append(metadata)

            # Send hardware metadata to rattlesnake
            self.rattlesnake.set_environments(environment_metadata_list)

        except Exception as e:
            self.initialize_environments_error(e)
            return

        # Block until environment metadata has been stored
        ready_event_list = [
            self.rattlesnake.event_container.acquisition_ready_event,
            self.rattlesnake.event_container.output_ready_event,
            *self.rattlesnake.environment_manager.ready_event_list,
        ]
        active_event_list = []
        active_event_list = []
        self.create_event_watcher(ready_event_list, active_event_list)
        self.event_watcher.ready.connect(self.initialize_environments_ready)
        self.event_watcher.error.connect(self.initialize_environments_error)
        self.event_thread.start()

    def initialize_environments_ready(self):
        # Clear QThread
        self.cleanup_event_watcher()

        # Unlock UI
        self.initialize_environments_button.setEnabled(True)

        if self.has_system_id:
            self.rattlesnake_tabs.setTabEnabled(2, True)
            self.rattlesnake_tabs.setCurrentIndex(2)
        elif self.has_test_pred:
            self.rattlesnake_tabs.setTabEnabled(3, True)
            self.rattlesnake_tabs.setCurrentIndex(3)
        else:
            self.rattlesnake_tabs.setTabEnabled(4, True)
            self.rattlesnake_tabs.setCurrentIndex(4)

    def initialize_environments_error(self, error_message):
        # Clear QThread
        self.cleanup_event_watcher()

        # Unlock UI
        self.initialize_environments_button.setEnabled(True)
        self.display_error(error_message)

    # region: Global
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

    # region: Events
    def create_event_watcher(self, ready_event_list, active_event_list, active_event_check: bool = None):
        if getattr(self, "event_thread", None) or getattr(self, "event_watcher", None):
            self.initialize_hardware_error("Event watcher is still active")
            return
        self.event_thread = QtCore.QThread()
        self.event_watcher = EventWatcher(ready_event_list, active_event_list, active_event_check=active_event_check, timeout=self.timeout)
        self.event_watcher.moveToThread(self.event_thread)
        self.event_thread.started.connect(self.event_watcher.run)

    def cleanup_event_watcher(self):
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

    def closeEvent(self, event):
        self.gui_update_queue.put((GlobalCommands.QUIT, None))
        self.threadpool.waitForDone()

        event.accept()


if __name__ == "__main__":
    from rattlesnake.user_interface.example_files.metadata import make_sdynpy_system_metadata, make_time_environment_metadata

    hardware_metadata = make_sdynpy_system_metadata()
    environment_metadata = make_time_environment_metadata(hardware_metadata)

    rattlesnake = Rattlesnake(threaded=True, timeout=10)
    rattlesnake.set_hardware(hardware_metadata)
    rattlesnake.set_environments([environment_metadata])

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
