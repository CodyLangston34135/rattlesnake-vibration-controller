from rattlesnake.hardware.hardware_utilities import Channel
from rattlesnake.utilities import QueueContainer, VerboseMessageQueue
import multiprocessing as mp
import queue as thqueue


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


def mock_queue_container(threading):
    if threading:
        new_queue = thqueue.Queue
    else:
        new_queue = mp.Queue

    controller_queue_name_manager = mp.Manager()
    log_file_queue = mp.Queue()
    controller_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), controller_queue_name_manager, "Controller Command Queue")
    acquisition_command_queue = VerboseMessageQueue(log_file_queue, mp.Queue(), controller_queue_name_manager, "Acquisition Command Queue")
    output_command_queue = VerboseMessageQueue(log_file_queue, mp.Queue(), controller_queue_name_manager, "Output Command Queue")
    streaming_command_queue = VerboseMessageQueue(log_file_queue, new_queue(), controller_queue_name_manager, "Streaming Command Queue")
    environment_command_queues = {}
    environment_data_in_queues = {}
    environment_data_out_queues = {}
    for env_idx in range(10):
        environment_name = "Environment {:}".format(env_idx)
        environment_command_queues[environment_name] = VerboseMessageQueue(
            log_file_queue, mp.Queue(), controller_queue_name_manager, environment_name + " Command Queue"
        )
        environment_data_in_queues[environment_name] = new_queue()
        environment_data_out_queues[environment_name] = new_queue()

    input_output_sync_queue = new_queue()
    single_process_hardware_queue = new_queue()
    gui_update_queue = new_queue()
    queue_container = QueueContainer(
        controller_command_queue,
        acquisition_command_queue,
        output_command_queue,
        streaming_command_queue,
        log_file_queue,
        input_output_sync_queue,
        single_process_hardware_queue,
        gui_update_queue,
        environment_command_queues,
        environment_data_in_queues,
        environment_data_out_queues,
    )

    return queue_container


def fake_time():
    return "Datetime"
