from rattlesnake.utilities import GlobalCommands
from rattlesnake.profile_manager import ProfileEvent
from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.sdynpy_system import SDynPySystemMetadata
from rattlesnake.environment.time_environment import TimeMetadata, TimeInstructions, TimeCommands
import numpy as np

BUFFER_SIZE = 0.05


def make_sdynpy_system_metadata():
    excitation_1 = Channel()
    excitation_1.node_number = 2000038
    excitation_1.node_direction = "X+"
    excitation_1.comment = "2000038X+"
    excitation_1.physical_device = "Virtual"
    excitation_1.channel_type = "Acceleration"
    excitation_2 = Channel()
    excitation_2.node_number = 2000038
    excitation_2.node_direction = "Y+"
    excitation_2.comment = "2000038Y+"
    excitation_2.physical_device = "Virtual"
    excitation_2.channel_type = "Acceleration"
    excitation_3 = Channel()
    excitation_3.node_number = 2000038
    excitation_3.node_direction = "Z+"
    excitation_3.comment = "2000038Z+"
    excitation_3.physical_device = "Virtual"
    excitation_3.channel_type = "Acceleration"
    force_1 = Channel()
    force_1.node_number = 201
    force_1.node_direction = "X+"
    force_1.comment = "Force"
    force_1.physical_device = "Virtual"
    force_1.channel_type = "Force"
    force_1.feedback_device = "Virtual"
    force_2 = Channel()
    force_2.node_number = 201
    force_2.node_direction = "Y+"
    force_2.comment = "Force"
    force_2.physical_device = "Virtual"
    force_2.channel_type = "Force"
    force_2.feedback_device = "Virtual"
    force_3 = Channel()
    force_3.node_number = 201
    force_3.node_direction = "Z+"
    force_3.comment = "Force"
    force_3.physical_device = "Virtual"
    force_3.channel_type = "Force"
    force_3.feedback_device = "Virtual"
    channel_list = [excitation_1, excitation_2, excitation_3, force_1, force_2, force_3]

    hardware_metadata = SDynPySystemMetadata()
    hardware_metadata.channel_list = channel_list
    hardware_metadata.sample_rate = 1000
    hardware_metadata.time_per_read = BUFFER_SIZE
    hardware_metadata.time_per_write = BUFFER_SIZE
    hardware_metadata.hardware_file = "E:/Rattlesnake/SampleData/sample_system.npz"

    return hardware_metadata


def make_time_environment_metadata(hardware_metadata, environment_name="My Time"):
    num_rows = 3
    num_samples = 10000
    sample_rate = 1000  # Hz
    frequency = 2  # Hz sine wave

    # Create time vector
    t = np.arange(num_samples) / sample_rate

    # Create signal array
    signal = np.zeros((num_rows, num_samples))
    signal[0, :] = np.sin(2 * np.pi * frequency * t)  # sine wave in first row

    time_metadata = TimeMetadata(environment_name)
    time_metadata.channel_list = hardware_metadata.channel_list
    time_metadata.sample_rate = 1000
    time_metadata.output_signal = signal
    time_metadata.cancel_rampdown_time = 0.5

    return time_metadata


def make_time_environment_event_list(environment_name="My Time"):
    timestamp = 0
    command = GlobalCommands.START_STREAMING
    start_stream_event = ProfileEvent(timestamp, "Global", command)

    timestamp = 2
    command = GlobalCommands.START_ENVIRONMENT
    time_instructions = TimeInstructions(environment_name)
    time_instructions.current_test_level = 1
    time_instructions.repeat = True
    start_environment_event = ProfileEvent(timestamp, environment_name, command, time_instructions)

    timestamp = 4
    command = TimeCommands.SET_TEST_LEVEL
    data = 2
    set_level_event = ProfileEvent(timestamp, environment_name, command, data)

    timestamp = 6
    command = GlobalCommands.STOP_ENVIRONMENT
    stop_environment_event = ProfileEvent(timestamp, environment_name, command)

    timestamp = 8
    command = GlobalCommands.STOP_STREAMING
    stop_stream_event = ProfileEvent(timestamp, "Global", command)

    profile_event_list = [start_stream_event, start_environment_event, set_level_event, stop_environment_event, stop_stream_event]
    return profile_event_list
