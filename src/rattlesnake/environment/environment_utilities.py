from enum import Enum


class ControlTypes(Enum):
    """Enumeration of the possible control types"""

    COMBINED = 0
    RANDOM = 1
    TRANSIENT = 2
    SINE = 3
    TIME = 4
    # NONLINEAR = 5
    MODAL = 6
    # Add new environment types here


environment_long_names = {}
environment_long_names[ControlTypes.RANDOM] = "MIMO Random Vibration"
environment_long_names[ControlTypes.TRANSIENT] = "MIMO Transient"
environment_long_names[ControlTypes.SINE] = "MIMO Sine Vibration"
environment_long_names[ControlTypes.TIME] = "Time Signal Generation"
environment_long_names[ControlTypes.MODAL] = "Modal Testing"
