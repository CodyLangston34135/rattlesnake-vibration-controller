from rattlesnake.mock_objects. import MockHardwareMetadata, MockHardwareAcquisition, MockHardwareOutput
from rattlesnake.hardware.abstract_hardware import HardwareMetadata, HardwareAcquisition, HardwareOutput


def test_hardware_metadata_init():
    hardware_metadata = MockHardwareMetadata()

    assert isinstance(hardware_metadata, HardwareMetadata)


def test_hardware_acquisition_init():
    hardware_acquistion = MockHardwareAcquisition()

    assert isinstance(hardware_acquistion, HardwareAcquisition)


def test_hardware_output_init():
    hardware_output = MockHardwareOutput()

    assert isinstance(hardware_output, HardwareOutput)
