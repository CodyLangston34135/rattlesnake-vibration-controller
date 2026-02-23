from rattlesnake.environment.environment_utilities import ControlTypes
from rattlesnake.user_interface.sine_ui import SineUI
from rattlesnake.user_interface.time_ui import TimeUI

ENVIRONMENT_UIS = {}

ENVIRONMENT_UIS[ControlTypes.TIME] = TimeUI
ENVIRONMENT_UIS[ControlTypes.SINE] = SineUI
