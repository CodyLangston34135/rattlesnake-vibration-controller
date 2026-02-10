from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.sdynpy_system import SDynPySystemMetadata
from rattlesnake.environment.time_environment import TimeMetadata
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


def make_time_environment_metadata(hardware_metadata):
    num_rows = 3
    num_samples = 10000
    sample_rate = 1000  # Hz
    frequency = 2  # Hz sine wave

    # Create time vector
    t = np.arange(num_samples) / sample_rate

    # Create signal array
    signal = np.zeros((num_rows, num_samples))
    signal[0, :] = np.sin(2 * np.pi * frequency * t)  # sine wave in first row

    time_metadata = TimeMetadata("Time Environment 1")
    time_metadata.channel_list = hardware_metadata.channel_list
    time_metadata.sample_rate = 1000
    time_metadata.output_signal = signal
    time_metadata.cancel_rampdown_time = 0.5

    return time_metadata
