from rattlesnake.environment.environment_utilities import ControlTypes
from rattlesnake.user_interface.sine_ui import SineUI
from rattlesnake.user_interface.time_ui import TimeUI
from rattlesnake.user_interface.modal_ui import ModalUI

ENVIRONMENT_UIS = {}

ENVIRONMENT_UIS[ControlTypes.TIME] = TimeUI
ENVIRONMENT_UIS[ControlTypes.MODAL] = ModalUI
ENVIRONMENT_UIS[ControlTypes.SINE] = SineUI
