from .ui_utilities import Updater, UICommands, headless_ui_path, debug_ui_path
from .ui_registry import environment_uis
from ..utilities import QueueContainer, GlobalCommands
from ..hardware.abstract_hardware import HardwareMetadata
from ..environment.abstract_environment import EnvironmentMetadata
import os
from qtpy import QtCore, QtWidgets, uic
from typing import Dict

directory = os.path.split(__file__)[0]
QtCore.QDir.addSearchPath("images", os.path.join(directory, "themes", "images"))

TASK_NAME = "UI"


class HeadlessUI(QtWidgets.QMainWindow):
    def __init__(
        self,
        queue_container: QueueContainer,
        hardware_metadata: HardwareMetadata,
        environment_metadata_dict: Dict[str, EnvironmentMetadata],
        theme: str = "Light",
        debug: bool = False,
    ):
        super(HeadlessUI, self).__init__()

        self.queue_container = queue_container
        self.environment_queues = []
        self.environment_uis = {}

        if debug:
            uic.loadUi(debug_ui_path, self)
            # Build environment ui
            for queue_name, metadata in environment_metadata_dict.items():
                environment_name = metadata.environment_name
                self.environment_queues.append(queue_name)
                environment_ui = environment_uis[metadata.environment_type]
                self.environment_uis[queue_name] = environment_ui(
                    environment_name,
                    queue_name,
                    self.environment_definition_environment_tabs,
                    self.system_id_environment_tabs,
                    self.test_prediction_environment_tabs,
                    self.run_environment_tabs,
                    self.queue_container.environment_command_queues[queue_name],
                    self.queue_container.controller_command_queue,
                    self.queue_container.log_file_queue,
                )
                self.environment_uis[queue_name].initialize_hardware(hardware_metadata)
                self.environment_uis[queue_name].store_metadata(metadata)
        else:
            uic.loadUi(headless_ui_path, self)
            self._dummy_definition_tabs = QtWidgets.QTabWidget()
            self._dummy_system_tabs = QtWidgets.QTabWidget()
            self._dummy_prediction_tabs = QtWidgets.QTabWidget()
            for queue_name, metadata in environment_metadata_dict.items():
                environment_name = metadata.environment_name
                self.environment_queues.append(queue_name)
                environment_ui = environment_uis[metadata.environment_type]
                self.environment_uis[queue_name] = environment_ui(
                    environment_name,
                    queue_name,
                    self._dummy_definition_tabs,
                    self._dummy_system_tabs,
                    self._dummy_prediction_tabs,
                    self.run_environment_tabs,
                    self.queue_container.environment_command_queues[queue_name],
                    self.queue_container.controller_command_queue,
                    self.queue_container.log_file_queue,
                )
                self.environment_uis[queue_name].initialize_hardware(hardware_metadata)
                self.environment_uis[queue_name].store_metadata(metadata)

        self.threadpool = QtCore.QThreadPool()
        self.gui_updater = Updater(self.queue_container.gui_update_queue)
        self.threadpool.start(self.gui_updater)
        self.gui_updater.signals.update.connect(self.update_gui)

        self.show()

        # Change color theme
        self.change_color_theme(theme)

    def update_gui(self, queue_data):
        message, data = queue_data
        if message == UICommands.ERROR:
            pass
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
        self.queue_container.gui_update_queue.put((GlobalCommands.QUIT, None))

        event.accept()

    def change_color_theme(self, text: str):
        """Updates the color scheme of the UI"""
        if text == "Light":
            self.setStyleSheet("")
        elif text == "Dark":
            dark_theme_path = os.path.join(directory, "themes", "dark_theme.txt")
            with open(dark_theme_path, encoding="utf-8") as file:
                stylesheet = file.read()
            images_path = os.path.join(directory, "themes", "images").replace("\\", "/")
            print(f"Images Path: {images_path}")
            stylesheet.replace(r"%%IMAGES_PATH%%", images_path)
            self.setStyleSheet(stylesheet)
