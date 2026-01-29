from rattlesnake.process.abstract_message_process import AbstractMessageProcess
from rattlesnake.utilities import GlobalCommands
from mock_objects.mock_utilities import mock_queue_container
import pytest


# region: Fixtures
@pytest.fixture(params=[True, False], ids=["threaded", "non_threaded"])
def abstract_message_process(request):
    use_thread = request.param
    queue_container = mock_queue_container(use_thread)
    abstract_message_process = AbstractMessageProcess(
        "Process Name", queue_container.log_file_queue, queue_container.controller_command_queue, queue_container.gui_update_queue
    )


# region: AbstractMessageProcess
@pytest.mark.parametrize("use_thread", [True, False])
def test_abstract_message_process_init(use_thread):
    queue_container = mock_queue_container(use_thread)
    abstract_message_process = AbstractMessageProcess(
        "Process Name", queue_container.log_file_queue, queue_container.controller_command_queue, queue_container.gui_update_queue
    )

    assert isinstance(abstract_message_process, AbstractMessageProcess)
    assert abstract_message_process.command_map == {GlobalCommands.QUIT: abstract_message_process.quit}
