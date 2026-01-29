from rattlesnake.utilities import VerboseMessageQueue, GlobalCommands
import multiprocessing as mp
import queue as thqueue
import random
import string
import pytest
from unittest import mock


# Create a log file queue
@pytest.fixture
def log_file_queue():
    return mp.Queue()


# Create a queue name manager
@pytest.fixture
def name_manager():
    return mp.Manager()


# Initialize the verbose message queue
@pytest.fixture(params=[True, False], ids=["threaded", "non_threaded"])
def verbose_queue(request, log_file_queue, name_manager):
    threading = request.param

    if threading:
        queue = thqueue.Queue()
    else:
        queue = mp.Queue()

    return VerboseMessageQueue(log_file_queue, queue, name_manager, "VerboseQueue")


# Test the initialization of the verbose mesage queue
def test_verbose_queue_init(log_file_queue, name_manager):
    verbose_queue = VerboseMessageQueue(log_file_queue, mp.Queue(), name_manager, "VerboseQueue")

    assert isinstance(verbose_queue, VerboseMessageQueue)


# Test message_id generation
def test_verbose_message_id(verbose_queue, random_seed=42):
    # Seed the message id
    random.seed(random_seed)
    message_id = verbose_queue.generate_message_id()
    random.seed(random_seed)
    assert_id = "".join(random.choice(string.ascii_letters) for _ in range(6))

    # Test if the message id matches the template
    assert message_id == assert_id


# Test verbose message queue put
# Mock the message id return string
@mock.patch("rattlesnake.components.utilities.VerboseMessageQueue.generate_message_id")
# Prevent the Queue object form putting stuff into it
@mock.patch("rattlesnake.components.utilities.mp.queues.Queue.put")
def test_verbose_message_queue_put(mock_put, mock_id, verbose_queue):
    # Mock message id
    message_id = "1"
    mock_id.return_value = message_id
    # Create objects to put into queue
    task_name = "Test verbose queue"
    message_data_tuple = (GlobalCommands.QUIT, "Information")

    verbose_queue.put(task_name, message_data_tuple)

    # Test if objects were put into queue
    mock_put.assert_called_with((message_id, message_data_tuple))


# Test verbose message queue get
# Prevent the Queue object from getting from an empty queue
@mock.patch("rattlesnake.components.utilities.mp.queues.Queue.get")
def test_verbose_message_queue_get(mock_get, verbose_queue):
    # Mock the data to get from the queue
    message_id = "1"
    task_name = "Test verbose queue"
    message_data_tuple = (GlobalCommands.QUIT, "Information")
    mock_get.return_value = (message_id, message_data_tuple)

    data = verbose_queue.get(task_name)

    # Test if data from get matches mock return value
    assert data == message_data_tuple
