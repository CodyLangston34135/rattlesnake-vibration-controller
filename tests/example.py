from rattlesnake.mock_objects.mock_utilities import mock_channel_list
from rattlesnake.mock_objects.mock_hardware import MockHardwareMetadata

if __name__ == "__main__":
    channel_list = lambda chan=mock_channel_list(): chan + [chan[0]]

    metadata = MockHardwareMetadata()
    metadata.channel_list = channel_list

    metadata.validate()
