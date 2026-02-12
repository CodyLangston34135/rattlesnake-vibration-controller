from rattlesnake.environment.environment_utilities import ControlTypes
from rattlesnake.environment.time_environment import TimeCommands, TimeMetadata, TimeInstructions, TimeEnvironment

ENVIRONMENT_COMMANDS = {}
ENVIRONMENT_METADATA = {}
ENVIRONMENT_INSTRUCTIONS = {}
ENVIRONMENT_PROCESS = {}

ENVIRONMENT_COMMANDS[ControlTypes.TIME] = TimeCommands
ENVIRONMENT_METADATA[ControlTypes.TIME] = TimeMetadata
ENVIRONMENT_INSTRUCTIONS[ControlTypes.TIME] = TimeInstructions
ENVIRONMENT_PROCESS[ControlTypes.TIME] = TimeEnvironment
