from rattlesnake.environment.environment_utilities import ControlTypes
from rattlesnake.environment.time_environment import TimeMetadata, TimeInstructions, TimeEnvironment

ENVIRONMENT_METADATA = {}
ENVIRONMENT_INSTRUCTIONS = {}
ENVIRONMENT_PROCESS = {}

ENVIRONMENT_METADATA[ControlTypes.TIME] = TimeMetadata
ENVIRONMENT_INSTRUCTIONS[ControlTypes.TIME] = TimeInstructions
ENVIRONMENT_PROCESS[ControlTypes.TIME] = TimeEnvironment
