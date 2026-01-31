from rattlesnake.environment.abstract_environment import EnvironmentMetadata, EnvironmentInstructions, EnvironmentProcess, run_process
from rattlesnake.environment.environment_utilities import ControlTypes
from rattlesnake.hardware.hardware_utilities import Channel
from mock_objects.mock_environment import MockEnvironmentMetadata, MockEnvironmentInstructions, MockEnvironmentProcess
from mock_objects.mock_hardware import MockHardwareMetadata
from mock_objects.mock_utilities import mock_channel_list, mock_queue_container, fake_time
import pytest
import netCDF4 as nc4
import multiprocessing as mp
from unittest import mock

# region: Fixtures
channel_list = mock_channel_list()


@pytest.fixture
def environment_metadata():
    return MockEnvironmentMetadata()


@pytest.fixture(params=[True, False], ids=["threaded", "non_threaded"])
def environment_process(request):
    use_thread = request.param
    queue_container = mock_queue_container(use_thread)
    acquisition_active = mp.Value("i", 0)
    output_active = mp.Value("i", 0)
    environment_process = MockEnvironmentProcess(
        "Environment Name",
        "Environment 0",
        queue_container.environment_command_queues["Environment 0"],
        queue_container.gui_update_queue,
        queue_container.controller_command_queue,
        queue_container.log_file_queue,
        queue_container.environment_data_in_queues["Environment 0"],
        queue_container.environment_data_out_queues["Environment 0"],
        acquisition_active,
        output_active,
    )

    return environment_process


# region: EnvironmentMetadata
def test_environment_metadata_init():
    environment_metadata = MockEnvironmentMetadata()

    assert isinstance(environment_metadata, EnvironmentMetadata)
    assert hasattr(environment_metadata, "channel_list")
    assert hasattr(environment_metadata, "environment_name")
    assert hasattr(environment_metadata, "environment_type")
    assert hasattr(environment_metadata, "queue_name")


@pytest.mark.parametrize(
    "channel_list, expected",
    [(channel_list, [True, True]), ([channel_list[0]], [True, False]), ([Channel()], ValueError)],
)
def test_environment_metadata_channel_bools(channel_list, expected, environment_metadata):
    environment_metadata.channel_list = channel_list
    hardware_channel_list = mock_channel_list()

    if expected is ValueError:
        with pytest.raises(ValueError):
            channel_list_bools = environment_metadata.map_channel_bools(hardware_channel_list)
    else:
        channel_list_bools = environment_metadata.map_channel_bools(hardware_channel_list)
        assert channel_list_bools == expected


@pytest.mark.parametrize(
    "channel_list, expected",
    [(channel_list, [0, 1]), ([channel_list[0]], [0]), ([Channel()], ValueError)],
)
def test_environment_metadata_channel_indices(channel_list, expected, environment_metadata):
    environment_metadata.channel_list = channel_list
    hardware_channel_list = mock_channel_list()

    if expected is ValueError:
        with pytest.raises(ValueError):
            channel_list_bools = environment_metadata.map_channel_indices(hardware_channel_list)
    else:
        channel_list_bools = environment_metadata.map_channel_indices(hardware_channel_list)
        assert channel_list_bools == expected


@pytest.mark.parametrize(
    "environment_name, environment_type, expected",
    [("Environment Name", ControlTypes.TIME, True), (0, ControlTypes.TIME, TypeError), ("Environment Name", 0, TypeError)],
)
def test_environment_metadata_validate(environment_name, environment_type, expected, environment_metadata):
    environment_metadata.environment_name = environment_name
    environment_metadata.environment_type = environment_type

    if expected == True:
        valid_metadata = environment_metadata.validate()
        assert valid_metadata
    elif expected == TypeError:
        with pytest.raises(TypeError):
            environment_metadata.validate()


def test_environment_metadata_store_to_netcdf(environment_metadata):
    dataset = nc4.Dataset("temp.nc", mode="w", diskless=True, persist=False)
    netcdf_group = dataset.createGroup("temp_group")

    environment_metadata.store_to_netcdf(netcdf_group)

    assert True


# region: EnvironmentInstructinos
def test_environment_instructions_init():
    environment_instructions = MockEnvironmentInstructions()

    assert isinstance(environment_instructions, EnvironmentInstructions)
    assert hasattr(environment_instructions, "environment_type")
    assert hasattr(environment_instructions, "environment_name")


def test_environment_instructions_validate():
    environment_instructions = MockEnvironmentInstructions()

    valid_instructions = environment_instructions.validate()
    assert valid_instructions


# region: EnvironmentProcess
@pytest.mark.parametrize("use_thread", [True, False])
def test_environment_process_init(use_thread):
    queue_container = mock_queue_container(use_thread)
    acquisition_active = mp.Value("i", 0)
    output_active = mp.Value("i", 0)
    environment_process = MockEnvironmentProcess(
        "environment_name",
        "Environment 0",
        queue_container.environment_command_queues["Environment 0"],
        queue_container.gui_update_queue,
        queue_container.controller_command_queue,
        queue_container.log_file_queue,
        queue_container.environment_data_in_queues["Environment 0"],
        queue_container.environment_data_out_queues["Environment 0"],
        acquisition_active,
        output_active,
    )

    assert isinstance(environment_process, EnvironmentProcess)


def test_environment_process_properties(environment_process):
    environment_process.acquisition_active
    environment_process.output_active
    environment_process.environment_command_queue
    environment_process.data_in_queue
    environment_process.data_out_queue
    environment_process.gui_update_queue
    environment_process.controller_command_queue
    environment_process.log_file_queue
    environment_process.queue_name
    environment_process.command_map

    assert True


def test_environment_process_functions(environment_process, environment_metadata):
    hardware_metadata = MockHardwareMetadata()

    environment_process.initialize_hardware(hardware_metadata)
    environment_process.initialize_environment(environment_metadata)
    environment_process.stop_environment(None)
    environment_process.quit(None)

    assert True


@mock.patch("rattlesnake.environment.abstract_environment.datetime")
def test_environment_process_log(mock_time, environment_process):
    mock_log_file_queue = mock.MagicMock()
    environment_process._log_file_queue = mock_log_file_queue
    mock_time.now = fake_time
    environment_process.log("Test Message")

    mock_log_file_queue.put.assert_called_once_with("Datetime: Environment Name -- Test Message\n")


def test_environment_process_map_command(environment_process):
    key = "Test Key"

    def function():
        return "Test Function"

    environment_process.map_command(key, function)

    # Test that the key maps to the function
    data = environment_process.command_map[key]
    assert data == function


@pytest.mark.parametrize(
    "mock_function, mock_key",
    [
        (mock.MagicMock(return_value=False), "Test Key"),
        (mock.MagicMock(side_effect=KeyError), "Test Key"),
        (mock.MagicMock(return_value=False), "Not a key"),
    ],
)
# Force get command to return values
@mock.patch("rattlesnake.utilities.VerboseMessageQueue.get")
# Prevent from writing to log_file_queue
@mock.patch("rattlesnake.environment.abstract_environment.EnvironmentProcess.log")
def test_environment_process_run(mock_log, mock_get, mock_function, mock_key, environment_process):
    # Add the key function and quit function to the command map
    environment_process._command_map = {
        mock_key: mock_function,
        "Quit Key": environment_process.quit,
    }

    # Make the get command return "Test Key", then "Quit Key"
    mock_get.side_effect = [("Test Key", None), ("Quit Key", None)]
    mock_shutdown = mock.MagicMock()
    mock_shutdown.is_set.return_value = False

    environment_process.run(mock_shutdown)

    # Test that the function was called if the key exists
    if mock_key == "Test Key":
        mock_function.assert_called()
    # Test that the quit command was ran
    mock_log.assert_called_with("Stopping Process")


# region: run_process
@pytest.mark.parametrize("use_thread", [True, False])
@mock.patch("rattlesnake.environment.abstract_environment.EnvironmentProcess")
def test_run_process(mock_process_class, use_thread):
    queue_container = mock_queue_container(use_thread)
    acquisition_active = mp.Value("i", 0)
    output_active = mp.Value("i", 0)
    shutdown_event = mp.Event()
    run_process(
        "Environment Name",
        "Environment 0",
        queue_container.environment_command_queues["Environment 0"],
        queue_container.gui_update_queue,
        queue_container.controller_command_queue,
        queue_container.log_file_queue,
        queue_container.environment_data_in_queues["Environment 0"],
        queue_container.environment_data_out_queues["Environment 0"],
        acquisition_active,
        output_active,
        shutdown_event,
    )

    mock_instance = mock_process_class.return_value
    mock_instance.run.assert_called()
