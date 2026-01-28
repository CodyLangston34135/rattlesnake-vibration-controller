from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.nidqaqmx import NIDAQmxMetadata, TaskTrigger
from rattlesnake.environment.time_environment import TimeMetadata, TimeInstructions
from rattlesnake.user_interface.headless_ui import HeadlessUi
from rattlesnake.process.streaming import StreamType, StreamMetadata
from rattlesnake.math_operations import db2scale
import sys
import numpy as np
from qtpy import QtWidgets


def main():
    rattlesnake = Rattlesnake()

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
    hardware_metadata.time_per_read = 0.25
    hardware_metadata.time_per_write = 0.25
    hardware_metadata.task_trigger = TaskTrigger.INTERNAL

    rattlesnake.set_hardware(hardware_metadata)

    envrionment_metadata = TimeMetadata("Time Environment 1")
    envrionment_metadata.channel_list = channel_list
    envrionment_metadata.sample_rate = 1000
    envrionment_metadata.output_signal = np.ones(1000)
    envrionment_metadata.cancel_rampdown_time = 500
    envrionment_metadata_list = [envrionment_metadata]

    rattlesnake.set_environments(envrionment_metadata_list)

    stream_metadata = StreamMetadata()
    stream_metadata.stream_type = StreamType.NO_STREAM
    stream_metadata.stream_file = None
    stream_metadata.test_level = None

    rattlesnake.set_stream(stream_metadata)

    instructions = TimeInstructions("Time Environment 1")
    instructions.current_test_level = db2scale(0)
    instructions.repeat = True

    rattlesnake.set_instructions([instructions])

    rattlesnake.arm_test()

    app = QtWidgets.QApplication(sys.argv)
    _ = HeadlessUi(rattlesnake.queue_container, rattlesnake.environment_metadata_list, "Dark")
    app.exec_()

    rattlesnake.shutdown()


if __name__ == "__main__":
    main()
