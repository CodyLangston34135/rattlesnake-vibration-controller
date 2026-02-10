from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.hardware.abstract_hardware import HardwareMetadata


class NullHardwareMetadata(HardwareMetadata):
    def __init__(self):
        super().__init__("Select")

    @property
    def extra_attr_list(self):
        return []

    def validate(self):
        return False  # or True, depending on UI logic

    def valid_channel_dict(self, channel: Channel):
        return super().valid_channel_dict(channel)

    @property
    def assist_mode_modules(self):
        return super().assist_mode_modules
