from rattlesnake.environment_manager import EnvironmentManager
from rattlesnake.utilities import GlobalCommands
from rattlesnake.environment.environment_utilities import ControlTypes
from mock_objects.mock_hardware import MockHardwareMetadata
from mock_objects.mock_environment import MockEnvironmentType, MockEnvironmentMetadata, MockEnvironmentInstructions, IMPLEMENTED_ENVIRONMENT
from mock_objects.mock_utilities import mock_queue_container, mock_event_container, fake_time
import pytest
import multiprocessing as mp
from unittest import mock


# region: Fixtures
@pytest.fixture(params=[True, False], ids=["threaded", "non_threaded"])
def environment_manager(request):
    use_thread = request.param
    queue_container = mock_queue_container(use_thread)
    event_container = mock_event_container(use_thread)
    environment_manager = EnvironmentManager(
        queue_container, event_container.environment_ready_events, event_container.environment_close_events, use_thread
    )

    return environment_manager


# region: EnvironmentManager
@pytest.mark.parametrize("use_thread", [True, False])
def test_environment_manager_init(use_thread):
    queue_container = mock_queue_container(use_thread)
    event_container = mock_event_container(use_thread)
    environment_manager = EnvironmentManager(
        queue_container, event_container.environment_ready_events, event_container.environment_close_events, use_thread
    )

    assert isinstance(environment_manager, EnvironmentManager)
    assert environment_manager.threading == use_thread


@pytest.mark.parametrize(
    "queue_names, expected",
    [
        (["Environment 0", "Environment 1"], ["Environment 2", "Environment 3"]),
        ([], ["Environment 0", "Environment 1", "Environment 2", "Environment 3"]),
    ],
)
def test_environment_manager_available_queues(queue_names, expected, environment_manager):
    environment_manager.queue_names = queue_names

    assert environment_manager.available_queues == expected


def test_environment_manager_queue_names_dict(environment_manager):
    environment_manager.queue_names = ["Environment 0"]
    environment_manager.environment_names["Environment 0"] = "Environment Name"

    queue_names_dict = environment_manager.queue_names_dict
    assert queue_names_dict["Environment Name"] == "Environment 0"


def test_environment_manager_initialize_hardware(environment_manager):
    hardware_metadata = MockHardwareMetadata()
    environment_manager.queue_names = ["Environment 0"]
    mock_command_queue = mock.MagicMock()
    environment_manager.queue_container.environment_command_queues["Environment 0"] = mock_command_queue
    environment_manager.initialize_hardware(hardware_metadata)

    mock_command_queue.put.assert_called_with("Environment Manager", (GlobalCommands.INITIALIZE_HARDWARE, hardware_metadata))
    assert environment_manager.hardware_metadata == hardware_metadata


@pytest.mark.parametrize(
    "existing_metadata, valid_metadata, expected",
    [
        (({"Environment 0": MockEnvironmentMetadata()}, {"Environment 0": MockEnvironmentType.ENVIRONMENT}, ["Environment 0"]), True, "Put"),
        (({}, {}, []), False, TypeError),
        (({}, {}, []), True, "Add"),
        (
            (
                {"Environment 0": MockEnvironmentMetadata(), "Environment 1": MockEnvironmentMetadata()},
                {"Environment 0": MockEnvironmentType.ENVIRONMENT, "Environment 1": MockEnvironmentType.ENVIRONMENT},
                ["Environment 0", "Environment 1"],
            ),
            True,
            "Remove",
        ),
    ],
)
def test_environment_manager_initialize_environment(existing_metadata, valid_metadata, expected, environment_manager):
    metadata_dict, type_dict, queue_names = existing_metadata

    hardware_metadata = MockHardwareMetadata()
    environment_manager.hardware_metadata = hardware_metadata
    acquisition_active = mp.Value("i", 0)
    output_active = mp.Value("i", 0)

    environment_metadata = MockEnvironmentMetadata()
    environment_metadata.validate = mock.MagicMock(return_value=valid_metadata)
    metadata_list = [environment_metadata]

    environment_manager.queue_names = queue_names
    environment_manager.environment_types = type_dict
    environment_manager.environment_metadata = metadata_dict

    mock_command_queue = mock.MagicMock()
    environment_manager.queue_container.environment_command_queues["Environment 0"] = mock_command_queue

    environment_manager.add_environment = mock.MagicMock()
    environment_manager.remove_environment = mock.MagicMock()

    if expected is TypeError:
        with pytest.raises(TypeError):
            environment_manager.initialize_environments(metadata_list, acquisition_active, output_active)
    else:
        environment_manager.initialize_environments(metadata_list, acquisition_active, output_active)
        if expected == "Put":
            expected_environment_calls = [
                mock.call.put("Environment Manager", (GlobalCommands.INITIALIZE_HARDWARE, environment_manager.hardware_metadata)),
                mock.call.put("Environment Manager", (GlobalCommands.INITIALIZE_ENVIRONMENT, environment_metadata)),
            ]
            mock_command_queue.assert_has_calls(expected_environment_calls)
        elif expected == "Add":
            environment_manager.add_environment.assert_called_with(environment_metadata, acquisition_active, output_active)
        elif expected == "Remove":
            environment_manager.remove_environment.assert_called_with("Environment 1")


@pytest.mark.parametrize(
    "environment_name, environment_type, expected",
    [
        ("Mock Environment", MockEnvironmentType.ENVIRONMENT, True),
        ("Wrong Name", MockEnvironmentType.ENVIRONMENT, KeyError),
        ("Mock Environment", None, TypeError),
    ],
)
def test_environment_manager_validate_instructions(environment_name, environment_type, expected, environment_manager):
    environment_instructions = MockEnvironmentInstructions()
    environment_instructions.environment_name = environment_name
    environment_instructions.environment_type = environment_type
    environment_instructions_list = [environment_instructions]
    environment_manager.queue_names = ["Environment 0"]
    environment_manager.environment_names = {"Environment 0": "Mock Environment"}
    environment_manager.environment_types = {"Environment 0": MockEnvironmentType.ENVIRONMENT}

    if expected is True:
        valid_instruction = environment_manager.validate_environment_instructions(environment_instructions_list)
        assert valid_instruction
    elif expected is KeyError:
        with pytest.raises(KeyError):
            environment_manager.validate_environment_instructions(environment_instructions_list)
    elif expected is TypeError:
        with pytest.raises(TypeError):
            environment_manager.validate_environment_instructions(environment_instructions_list)


def test_environment_manager_clear_environment(environment_manager):
    environment_manager.queue_names = ["Environment 0"]
    environment_manager.environment_names = {"Environment 0": "Environment Name"}
    environment_manager.environment_types = {"Environment 0": MockEnvironmentType.ENVIRONMENT}
    environment_manager.environment_metadata = {"Environment 0": MockEnvironmentMetadata()}
    environment_manager.environment_processes = {"Environment 0": mp.Process()}
    environment_manager.environment_events = {"Environment 0": mp.Event()}
    mock_close_process = mock.MagicMock()
    environment_manager.close_environments = mock_close_process
    environment_manager.clear_environments()

    assert environment_manager.queue_names == []
    assert environment_manager.environment_names == {}
    assert environment_manager.environment_types == {}
    assert environment_manager.environment_metadata == {}
    assert environment_manager.environment_processes == {}
    mock_close_process.assert_called()


@pytest.mark.parametrize("environment_type", [None, *IMPLEMENTED_ENVIRONMENT])
def test_environment_manager_add_environment(environment_type, environment_manager):
    metadata = MockEnvironmentMetadata()
    metadata.environment_type = environment_type
    acquisition_active = mp.Value("i", 0)
    output_active = mp.Value("i", 0)

    mock_process = mock.MagicMock()
    mock_event = mock.MagicMock()
    environment_manager.new_process = mock.MagicMock(return_value=mock_process)
    environment_manager.new_event = mock.MagicMock(return_value=mock_event)

    environment_manager.add_environment(metadata, acquisition_active, output_active)

    if environment_type == None:
        assert True
    else:
        assert environment_manager.queue_names == ["Environment 0"]
        assert environment_manager.environment_names["Environment 0"] == "Mock Environment"
        assert environment_manager.environment_types["Environment 0"] == environment_type
        assert environment_manager.environment_processes["Environment 0"] == mock_process
        assert not environment_manager.environment_close_events["Environment 0"].is_set()
        assert environment_manager.environment_metadata["Environment 0"] == metadata
        assert metadata.queue_name == "Environment 0"


@mock.patch("rattlesnake.environment_manager.datetime")
@pytest.mark.parametrize("is_alive", [True, False])
def test_environment_manager_remove_environment(mock_time, is_alive, environment_manager):
    environment_manager.queue_names = ["Environment 0"]
    environment_manager.environment_names = {"Environment 0": "Environment Name"}
    environment_manager.environment_types = {"Environment 0": MockEnvironmentType.ENVIRONMENT}
    environment_manager.environment_metadata = {"Environment 0": MockEnvironmentMetadata()}

    mock_log_file_queue = mock.MagicMock()
    mock_command_queue = mock.MagicMock()
    mock_process = mock.MagicMock()
    mock_process.is_alive.return_value = is_alive
    mock_event = mock.MagicMock()
    environment_manager.queue_container.log_file_queue = mock_log_file_queue
    environment_manager.queue_container.environment_command_queues["Environment 0"] = mock_command_queue
    environment_manager.environment_processes = {"Environment 0": mock_process}
    environment_manager.environment_close_events = {"Environment 0": mock_event}
    mock_time.now = fake_time

    environment_manager.remove_environment("Environment 0")
    assert environment_manager.queue_names == []
    assert environment_manager.environment_names == {}
    assert environment_manager.environment_types == {}
    assert environment_manager.environment_metadata == {}
    assert environment_manager.environment_processes == {}

    mock_command_queue.put.assert_called_with("Environment Manager", (GlobalCommands.QUIT, None))
    mock_process.join.assert_called()
    if is_alive:
        mock_event.set.assert_called()


@pytest.mark.parametrize("is_alive", [True, False])
@mock.patch("rattlesnake.environment_manager.datetime")
def test_environment_mananger_close_environment(mock_time, is_alive, environment_manager):
    environment_manager.queue_names = ["Environment 0"]
    environment_manager.environment_names = {"Environment 0": "Environment Name"}
    environment_manager.environment_types = {"Environment 0": MockEnvironmentType.ENVIRONMENT}
    environment_manager.environment_metadata = {"Environment 0": MockEnvironmentMetadata()}

    mock_log_file_queue = mock.MagicMock()
    mock_command_queue = mock.MagicMock()
    mock_process = mock.MagicMock()
    mock_process.is_alive.return_value = is_alive
    mock_event = mock.MagicMock()
    environment_manager.queue_container.log_file_queue = mock_log_file_queue
    environment_manager.queue_container.environment_command_queues["Environment 0"] = mock_command_queue
    environment_manager.environment_processes = {"Environment 0": mock_process}
    environment_manager.environment_close_events = {"Environment 0": mock_event}
    mock_time.now = fake_time

    environment_manager.close_environments()

    mock_command_queue.put.assert_called_with("Environment Manager", (GlobalCommands.QUIT, None))
    mock_process.join.assert_called()
    if is_alive:
        mock_event.set.assert_called()
