from .ui_utilities import Updater, UICommands, headless_ui_path
from .ui_registry import environment_uis
from ..utilities import QueueContainer
from ..environment.abstract_environment import EnvironmentMetadata
from qtpy import QtCore, QtWidgets, uic
from typing import List


class HeadlessUi(QtWidgets.QMainWindow):
    def __init__(self, queue_container: QueueContainer, environment_metadata_list: List[EnvironmentMetadata]):
        super(HeadlessUi, self).__init__()
        uic.loadUi(headless_ui_path, self)

        self.queue_container = queue_container
        self.environments = []

        # Build environment ui
        self.environment_uis = {}
        for metadata in environment_metadata_list:
            environment_name = metadata.queue_name
            self.environments.append[environment_name]
            environment_ui = environment_uis[metadata.environment_type]
            self.environment_uis[environment_name] = environment_ui(
                environment_name,
                self.environment_definition_environment_tabs,
                self.system_id_environment_tabs,
                self.test_prediction_environment_tabs,
                self.run_environment_tabs,
                self.queue_container.environment_command_queues[environment_name],
                self.queue_container.controller_communication_queue,
                self.queue_container.log_file_queue,
            )

        # Remove unused tabs
        self.rattlesnake_tabs.removeTab(self.rattlesnake_tabs.indexOf(self.environment_definition_environment_tabs))
        self.rattlesnake_tabs.removeTab(self.rattlesnake_tabs.indexOf(self.system_id_tab))
        self.rattlesnake_tabs.removeTab(self.rattlesnake_tabs.indexOf(self.test_prediction_environment_tabs))

        self.threadpool = QtCore.QThreadPool()
        self.gui_updater = Updater(self.queue_container.gui_update_queue)
        self.gui_updater.signals.update.connect(self.update_gui)

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
