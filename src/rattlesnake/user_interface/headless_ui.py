from .ui_utilities import Updater, UICommands, headless_ui_path
from .ui_registry import environment_uis
from ..utilities import QueueContainer, GlobalCommands
from ..environment.abstract_environment import EnvironmentMetadata
import os
from qtpy import QtCore, QtWidgets, uic
from typing import List

directory = os.path.split(__file__)[0]
QtCore.QDir.addSearchPath("images", os.path.join(directory, "themes", "images"))

TASK_NAME = "UI"


class HeadlessUi(QtWidgets.QMainWindow):
    def __init__(self, queue_container: QueueContainer, environment_metadata_list: List[EnvironmentMetadata], theme: str = "Light"):
        super(HeadlessUi, self).__init__()
        uic.loadUi(headless_ui_path, self)

        self.queue_container = queue_container
        self.environments = []

        self._dummy_definition_tabs = QtWidgets.QTabWidget()
        self._dummy_system_tabs = QtWidgets.QTabWidget()
        self._dummy_prediction_tabs = QtWidgets.QTabWidget()

        # Build environment ui
        self.environment_uis = {}
        for metadata in environment_metadata_list:
            environment_name = metadata.queue_name
            self.environments.append(environment_name)
            environment_ui = environment_uis[metadata.environment_type]
            self.environment_uis[environment_name] = environment_ui(
                environment_name,
                self._dummy_definition_tabs,
                self._dummy_system_tabs,
                self._dummy_prediction_tabs,
                self.run_environment_tabs,
                self.queue_container.environment_command_queues[environment_name],
                self.queue_container.controller_command_queue,
                self.queue_container.log_file_queue,
            )

        self.threadpool = QtCore.QThreadPool()
        self.gui_updater = Updater(self.queue_container.gui_update_queue)
        self.gui_updater.signals.update.connect(self.update_gui)

        self.show()

        # Change color theme
        self.change_color_theme(theme)

    def update_gui(self, queue_data):
        message, data = queue_data
        if message == UICommands.ERROR:
            pass
        elif message in self.environments:
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
