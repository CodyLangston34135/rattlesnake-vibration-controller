from ..hardware.hardware_utilities import Channel


def mock_channel_list():
    response_channel = Channel()
    for attr in response_channel.channel_attr_list:
        setattr(response_channel, attr, attr)
    response_channel.feedback_channel = None
    response_channel.feedback_device = None

    excitation_channel = Channel()
    for attr in excitation_channel.channel_attr_list:
        setattr(excitation_channel, attr, attr)

    return [response_channel, excitation_channel]
