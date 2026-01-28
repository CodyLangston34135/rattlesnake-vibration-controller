# This exists to prevent a circular import that arises from importing EnvironmentUI classes into ui_utilities.py
# If anyone knows how to fix this issue cleaner please do so
from .time_ui import TimeUI
from .read_ui import ReadUI
from ..environment.environment_utilities import ControlTypes

environment_uis = {}
environment_uis[ControlTypes.TIME] = TimeUI
environment_uis[ControlTypes.READ] = ReadUI
