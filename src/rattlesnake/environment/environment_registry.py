from rattlesnake.environment.environment_utilities import ControlTypes
from rattlesnake.environment.time_environment import TimeCommands, TimeMetadata, TimeInstructions, TimeEnvironment, time_process

ENVIRONMENT_COMMANDS = {}
ENVIRONMENT_METADATA = {}
ENVIRONMENT_INSTRUCTIONS = {}
ENVIRONMENT_CLASS = {}
ENVIRONMENT_PROCESS = {}

# Time Environment
ENVIRONMENT_COMMANDS[ControlTypes.TIME] = TimeCommands
ENVIRONMENT_METADATA[ControlTypes.TIME] = TimeMetadata
ENVIRONMENT_INSTRUCTIONS[ControlTypes.TIME] = TimeInstructions
ENVIRONMENT_CLASS[ControlTypes.TIME] = TimeEnvironment
ENVIRONMENT_PROCESS[ControlTypes.TIME] = time_process
