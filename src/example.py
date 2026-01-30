from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.utilities import GlobalCommands
from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.nidaqmx import NIDAQmxMetadata
from rattlesnake.hardware.sdynpy_system import SDynPySystemMetadata
from rattlesnake.environment.time_environment import TimeMetadata, TimeInstructions
from rattlesnake.environment.read_environment import ReadMetadata
from rattlesnake.process.streaming import StreamType, StreamMetadata
from rattlesnake.profile_manager import ProfileEvent, TimeCommands
from rattlesnake.user_interface.headless_ui import HeadlessUI
from rattlesnake.math_operations import db2scale
import sys
import time
import numpy as np
from qtpy import QtWidgets

BUFFER_SIZE = 0.01


def test_nidaq_metadata():
    channel = Channel()
    channel.sensitivity = 1000
    channel.unit = "V"
    channel.physical_device = "dev1"
    channel.physical_channel = "ai0"
    channel.channel_type = "Voltage"
    channel.minimum_value = -10
    channel.maximum_value = 10
    channel.coupling = "DC"
    channel.excitation_source = "Internal"
    channel.excitation = 0.004
    channel_list = [channel]

    hardware_metadata = NIDAQmxMetadata()
    hardware_metadata.channel_list = channel_list
    hardware_metadata.sample_rate = 1000
    hardware_metadata.time_per_read = BUFFER_SIZE
    hardware_metadata.time_per_write = BUFFER_SIZE
    hardware_metadata.task_trigger = 0
    hardware_metadata.output_trigger_generator = ""

    return hardware_metadata


def test_sdynpy_metadata():
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
    hardware_metadata.hardware_file = "E:/Rattlesnake/SampleData/stiff_plate_system.npz"

    return hardware_metadata


def create_sdynpy_signal():
    num_rows = 3
    num_samples = 10000
    sample_rate = 1000  # Hz
    frequency = 5  # Hz sine wave

    # Create time vector
    t = np.arange(num_samples) / sample_rate

    # Create signal array
    signal = np.zeros((num_rows, num_samples))
    signal[0, :] = np.sin(2 * np.pi * frequency * t)  # sine wave in first row

    return signal


def build_profile_event_list(environment_queue_name):
    timestamp = 1
    queue_name = environment_queue_name
    command = GlobalCommands.START_STREAMING
    profile_event_1 = ProfileEvent(timestamp, queue_name, command)

    timestamp = 2
    queue_name = environment_queue_name
    command = GlobalCommands.START_ENVIRONMENT
    profile_event_2 = ProfileEvent(timestamp, queue_name, command)

    timestamp = 5
    queue_name = environment_queue_name
    command = GlobalCommands.STOP_ENVIRONMENT
    profile_event_3 = ProfileEvent(timestamp, queue_name, command)

    timestamp = 8
    queue_name = "Global"
    command = GlobalCommands.STOP_STREAMING
    profile_event_4 = ProfileEvent(timestamp, queue_name, command)

    # timestamp = 8
    # queue_name = "Global"
    # command = GlobalCommands.STOP_HARDWARE
    # profile_event_5 = ProfileEvent(timestamp, queue_name, command)

    profile_event_list = [profile_event_1, profile_event_2, profile_event_3, profile_event_4]
    return profile_event_list


def main():
    rattlesnake = Rattlesnake()

    # hardware_metadata = test_nidaq_metadata()
    hardware_metadata = test_sdynpy_metadata()

    rattlesnake.set_hardware(hardware_metadata)
    # time.sleep(2)

    # Time Environment
    time_metadata = TimeMetadata("Time Environment 1")
    time_metadata.channel_list = hardware_metadata.channel_list
    time_metadata.sample_rate = 1000
    time_metadata.output_signal = create_sdynpy_signal()
    time_metadata.cancel_rampdown_time = 0.5

    read_metadata = ReadMetadata("Read Environment 1")
    read_metadata.channel_list = hardware_metadata.channel_list

    envrionment_metadata_list = [time_metadata]

    rattlesnake.set_environments(envrionment_metadata_list)
    environment_queue_name = "Environment 0"

    stream_metadata = StreamMetadata()
    stream_metadata.stream_type = StreamType.NO_STREAM
    stream_metadata.stream_file = None
    stream_metadata.test_level_environment_name = None

    rattlesnake.set_stream(stream_metadata)

    time_instructions = TimeInstructions(environment_queue_name)
    time_instructions.current_test_level = db2scale(0)
    time_instructions.repeat = False
    environment_instruction_list = [time_instructions]

    profile_event_list = build_profile_event_list(environment_queue_name)

    rattlesnake.set_profile(profile_event_list, environment_instruction_list)

    rattlesnake.start_acquisition()

    rattlesnake.start_profile()

    app = QtWidgets.QApplication(sys.argv)
    _ = HeadlessUI(rattlesnake.queue_container, rattlesnake.hardware_metadata, rattlesnake.environment_metadata_dict, "Dark", True)
    app.exec_()
    # time.sleep(12)

    rattlesnake.stop_acquisition()

    rattlesnake.shutdown()


if __name__ == "__main__":
    main()
