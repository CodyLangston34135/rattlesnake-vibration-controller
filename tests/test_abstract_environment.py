from rattlesnake.environment.abstract_environment import EnvironmentMetadata, EnvironmentInstructions, EnvironmentProcess
from rattlesnake.mock_objects.mock_environment import MockEnvironmentMetadata, MockEnvironmentInstructions, MockEnvironmentType


def test_environment_metadata_init():
    environment_metadata = MockEnvironmentMetadata()

    assert isinstance(environment_metadata, EnvironmentMetadata)
    assert hasattr(environment_metadata, "channel_list")
    assert hasattr(environment_metadata, "environment_name")
    assert hasattr(environment_metadata, "environment_type")
    assert hasattr(environment_metadata, "queue_name")


def test_environment_instructions_init():
    environment_instructions = MockEnvironmentInstructions()

    assert isinstance(environment_instructions, EnvironmentInstructions)
    assert hasattr(environment_instructions, "environment_type")
    assert hasattr(environment_instructions, "queue_name")
