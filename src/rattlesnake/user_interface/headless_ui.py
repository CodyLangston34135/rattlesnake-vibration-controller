from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.user_interface.ui_utilities import Updater, UICommands, headless_ui_path, debug_ui_path
from rattlesnake.utilities import QueueContainer, GlobalCommands
from rattlesnake.hardware.abstract_hardware import HardwareMetadata
from rattlesnake.environment.abstract_environment import EnvironmentMetadata
import os
from qtpy import QtCore, QtWidgets, uic
from typing import Dict

directory = os.path.split(__file__)[0]
QtCore.QDir.addSearchPath("images", os.path.join(directory, "themes", "images"))

TASK_NAME = "UI"


class HeadlessUI(QtWidgets.QMainWindow):
    def __init__(
        self,
        rattlesnake: Rattlesnake,
        *,
        theme: str = "Light",
        debug: bool = False,
    ):
        super(HeadlessUI, self).__init__()

        self.rattlesnake = rattlesnake
        self.environment_uis = {}

        if debug:
            uic.loadUi(debug_ui_path, self)
            # Build environment ui
            for metadata in self.rattlesnake.environment_metadata_dict.values():
                environment_name = metadata.environment_name
                environment_ui = environment_uis[metadata.environment_type]
                self.environment_uis[environment_name] = environment_ui(
                    environment_name,
                    self.rattlesnake,
                    self.environment_definition_environment_tabs,
                    self.system_id_environment_tabs,
                    self.test_prediction_environment_tabs,
                    self.run_environment_tabs,
                )
                self.environment_uis[environment_name].initialize_hardware(self.rattlesnake.hardware_metadata)
                self.environment_uis[environment_name].store_metadata(metadata)
        else:
            uic.loadUi(headless_ui_path, self)
            self._dummy_definition_tabs = QtWidgets.QTabWidget()
            self._dummy_system_tabs = QtWidgets.QTabWidget()
            self._dummy_prediction_tabs = QtWidgets.QTabWidget()
            for metadata in self.rattlesnake.environment_metadata.values():
                environment_name = metadata.environment_name
                environment_ui = environment_uis[metadata.environment_type]
                self.environment_uis[environment_name] = environment_ui(
                    environment_name,
                    self.rattlesnake,
                    self._dummy_definition_tabs,
                    self._dummy_system_tabs,
                    self._dummy_prediction_tabs,
                    self.run_environment_tabs,
                )
                self.environment_uis[environment_name].initialize_hardware(self.rattlesnake.hardware_metadata)
                self.environment_uis[environment_name].store_metadata(metadata)

        self.threadpool = QtCore.QThreadPool()
        self.gui_updater = Updater(self.gui_update_queue)
        self.threadpool.start(self.gui_updater)
        self.gui_updater.signals.update.connect(self.update_gui)

        self.show()

        # Change color theme
        self.change_color_theme(theme)

    @property
    def gui_update_queue(self):
        return self.rattlesnake.queue_container.gui_update_queue

    @property
    def log_file_queue(self):
        return self.rattlesnake.queue_container.log_file_queue

    @property
    def environment_names(self):
        return list(self.environment_uis.keys())

    def update_gui(self, queue_data):
        message, data = queue_data
        if message == UICommands.ERROR:
            pass
        elif message in self.environment_names:
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
