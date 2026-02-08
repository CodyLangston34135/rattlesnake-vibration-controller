from rattlesnake.user_interface.user_interface import RattlesnakeUI
from qtpy import QtWidgets
import sys


def main():
    app = QtWidgets.QApplication(sys.argv)
    _ = RattlesnakeUI()
    app.exec_()


if __name__ == "__main__":
    main()
