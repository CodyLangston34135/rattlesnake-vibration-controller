from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.nidqaqmx import NIDAQmxMetadata, TaskTrigger
from rattlesnake.environment.time_environment import TimeMetadata
from rattlesnake.user_interface.headless_ui import HeadlessUi
from rattlesnake.process.streaming import StreamType, StreamMetadata
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

    streaming_metadata = StreamMetadata()
    streaming_metadata.stream_type = StreamType.NO_STREAM
    streaming_metadata.stream_file = None
    streaming_metadata.test_level = None

    rattlesnake.arm_test(streaming_metadata)

    app = QtWidgets.QApplication(sys.argv)
    _ = HeadlessUi(rattlesnake.queue_container, rattlesnake.environment_metadata_list, "Dark")
    app.exec_()

    rattlesnake.shutdown()


if __name__ == "__main__":
    main()
