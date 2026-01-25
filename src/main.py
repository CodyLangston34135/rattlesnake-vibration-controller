from rattlesnake.rattlesnake import Rattlesnake
from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.nidqaqmx import NIDAQmxMetadata, TaskTrigger


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
    rattlesnake.shutdown()


if __name__ == "__main__":
    main()
