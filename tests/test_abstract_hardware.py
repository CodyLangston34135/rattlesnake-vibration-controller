from rattlesnake.hardware.abstract_hardware import HardwareMetadata, HardwareAcquisition, HardwareOutput
from rattlesnake.mock_objects.mock_hardware import MockHardwareMetadata, MockHardwareAcquisition, MockHardwareOutput
from rattlesnake.mock_objects.mock_utilities import mock_channel_list
import pytest

channel_list = mock_channel_list()


## Hardware Metadata
def test_hardware_metadata_init():
    hardware_metadata = MockHardwareMetadata()

    assert isinstance(hardware_metadata, HardwareMetadata)
    assert hasattr(hardware_metadata, "hardware_type")
    assert hasattr(hardware_metadata, "channel_list")
    assert hasattr(hardware_metadata, "sample_rate")
    assert hasattr(hardware_metadata, "time_per_read")
    assert hasattr(hardware_metadata, "time_per_write")
    assert hasattr(hardware_metadata, "output_oversample")


def test_hardware_metadata_samples_per_read():
    hardware_metadata = MockHardwareMetadata()
    hardware_metadata.sample_rate = 1000
    hardware_metadata.time_per_read = 0.25

    assert hardware_metadata.samples_per_read == 250


def test_hardware_metadata_samples_per_write():
    hardware_metadata = MockHardwareMetadata()
    hardware_metadata.sample_rate = 1000
    hardware_metadata.time_per_write = 0.25

    assert hardware_metadata.samples_per_write == 250


def test_hardware_metadata_nyquist_frequency():
    hardware_metadata = MockHardwareMetadata()
    hardware_metadata.sample_rate = 1000

    assert hardware_metadata.nyquist_frequency == 500


def test_hardware_metadata_output_sample_rate():
    hardware_metadata = MockHardwareMetadata()
    hardware_metadata.sample_rate = 1000
    hardware_metadata.output_oversample = 10

    assert hardware_metadata.output_sample_rate == 10000


@pytest.mark.parametrize(
    "channel_list, error_type",
    [
        (channel_list, "None"),
        (channel_list + [channel_list[0]], "ValueError"),
    ],
)
def test_hardware_metadata_validate(channel_list, error_type):
    hardware_metadata = MockHardwareMetadata()
    hardware_metadata.channel_list = channel_list

    if error_type == "ValueError":
        with pytest.raises(ValueError):
            valid_hardware = hardware_metadata.validate()
    elif error_type == "None":
        valid_hardware = hardware_metadata.validate()
        assert valid_hardware == True


def test_hardware_metadata_extra_attr_list():
    hardware_metadata = MockHardwareMetadata()
    attr_list = hardware_metadata.extra_attr_list()

    assert attr_list[0] == "extra_attr"


def test_hardware_acquisition_init():
    hardware_acquistion = MockHardwareAcquisition()

    assert isinstance(hardware_acquistion, HardwareAcquisition)


def test_hardware_output_init():
    hardware_output = MockHardwareOutput()

    assert isinstance(hardware_output, HardwareOutput)
