import matplotlib.pyplot as plt
from enum import Enum


class UICommands:
    ENABLE = 0
    DISABLE = 1
    DATA = 2


class DebugPlot:
    def __init__(self, gui_update_queue):
        self.gui_update_queue = gui_update_queue
        pass

    def run(self):
        pass
