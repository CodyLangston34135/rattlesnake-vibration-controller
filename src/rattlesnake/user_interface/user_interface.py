from ..rattlesnake import Rattlesnake
from .ui_utilities import ui_path
from qtpy import QtWidgets, uic


class RattlesnakeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(RattlesnakeUI, self).__init__()

        uic.loadUi(ui_path, self)

        self.rattlesnake = Rattlesnake(blocking=False, threaded=True)

    def closeEvent(self, event):
        self.rattlesnake.shutdown()
