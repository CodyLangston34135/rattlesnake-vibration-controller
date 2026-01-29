from rattlesnake.hardware.abstract_hardware import HardwareMetadata, HardwareAcquisition, HardwareOutput
from .mock_utilities import mock_channel_list
import numpy as np
from unittest import mock
from enum import Enum


class MockHardwareType(Enum):
    HARDWARE = 0


class MockHardwareMetadata(HardwareMetadata):
    def __init__(self):
        super().__init__(MockHardwareType.HARDWARE)
        self.channel_list = mock_channel_list()
        self.sample_rate = 1000
        self.time_per_read = 0.25
        self.time_per_write = 0.25
        self.output_oversample = 1
        self.extra_attr = "attr"

    def validate(self):
        super().validate()
        return True

    def extra_attr_list(self):
        super().extra_attr_list()
        return ["extra_attr"]


class MockHardwareAcquisition(HardwareAcquisition):
    def __init__(self):
        super().__init__()

    def initialize_hardware(self, metadata):
        super().initialize_hardware(metadata)
        return None

    def start(self):
        super().start()
        return None

    def read(self):
        super().read()
        return np.zeros((2, 100))

    def read_remaining(self):
        super().read_remaining()
        return np.zeros((2, 100))

    def stop(self):
        super().stop()
        return None

    def close(self):
        super().close()
        return None

    def get_acquisition_delay(self):
        super().get_acquisition_delay()
        return 0


class MockHardwareOutput(HardwareOutput):
    def __init__(self):
        super().__init__()

    def initialize_hardware(self, metadata):
        super().initialize_hardware(metadata)
        return None

    def start(self):
        super().start()
        return None

    def write(self, data):
        super().write(data)
        return None

    def stop(self):
        super().stop()
        return None

    def close(self):
        super().close()
        return None

    def ready_for_new_output(self):
        super().ready_for_new_output()
        return True
