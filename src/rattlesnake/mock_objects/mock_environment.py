from ..environment.abstract_environment import EnvironmentMetadata, EnvironmentInstructions, EnvironmentProcess
from .mock_utilities import mock_channel_list
from unittest import mock
from enum import Enum


class MockEnvironmentType(Enum):
    ENVIRONMENT = 0


class MockEnvironmentMetadata(EnvironmentMetadata):
    def __init__(self):
        super().__init__(MockEnvironmentType.ENVIRONMENT, "Mock Environment")
        self.queue_name = "Environment 0"
        self.channel_list = mock_channel_list()
