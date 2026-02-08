from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.user_interface.ui_utilities import ui_path
from qtpy import QtWidgets, QtGui, uic
import sys


class RattlesnakeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(RattlesnakeUI, self).__init__()

        uic.loadUi(ui_path, self)

        self.rattlesnake = Rattlesnake(blocking=False, threaded=True)

        self.setWindowIcon(QtGui.QIcon("logo/Rattlesnake_Icon.png"))
        self.setWindowTitle("Rattlesnake Vibration Controller")
        self.show()

    def closeEvent(self, event):
        self.rattlesnake.shutdown()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    _ = RattlesnakeUI()
    app.exec_()
