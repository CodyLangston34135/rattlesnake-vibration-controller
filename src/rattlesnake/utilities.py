import multiprocessing as mp
import time
from datetime import datetime
from enum import Enum
from typing import Dict


class GlobalCommands(Enum):
    QUIT = 0


def log_file_task(queue: mp.Queue, shutdown_event: mp.Event):
    """A multiprocessing function that collects logging data and writes to file

    Parameters
    ----------
    queue : mp.queues.Queue
        The multiprocessing queue to collect logging messages from
    """
    with open("Rattlesnake.log", "w") as f:
        while not shutdown_event.is_set():
            output = queue.get()
            if output == GlobalCommands.QUIT:
                f.write("Program quitting, logging terminated.")
                break
            num_newlines = output.count("\n")
            if num_newlines > 1:
                output = output.replace("\n", "////", num_newlines - 1)
            f.write(output)
            f.flush()


class VerboseMessageQueue:
    """A queue class that contains automatic logging information"""

    def __init__(self, log_queue, queue_name):
        """
        A queue class that contains automatic logging information

        Parameters
        ----------
        log_queue : mp.queues.Queue :
            A queue that a logging task will read from where the operations of
            the queue will be logged.
        queue_name : str :
            The name of the queue that will be included in the logging information

        """
        self.queue = mp.Queue()
        self.log_queue = log_queue
        self.queue_name = queue_name
        self.last_put_message = None
        self.last_put_time = -float("inf")
        self.last_get_message = None
        self.last_get_time = -float("inf")
        self.last_flush = -float("inf")
        self.time_threshold = 1.0

    def put(self, task_name, message_data_tuple, *args, **kwargs):
        """Puts data to a verbose queue

        Parameters
        ----------
        task_name : str
            Task name that is performing the put operation
        message_data_tuple : Tuple
            A (message,data) tuple where message is the instruction and data is
            any optional data to be passed along with the instruction.
        *args :
            Additional arguments that will be passed to the mp.queues.Queue.put
            function
        **kwargs :
            Additional arguments that will be passed to the mp.queues.Queue.put
            function

        """
        put_time = time.time()
        if (
            self.last_put_message != message_data_tuple[0]
            or put_time - self.last_put_time > self.time_threshold
        ):
            self.log_queue.put(
                "{:}: {:} put {:} to {:}\n".format(
                    datetime.now(),
                    task_name,
                    message_data_tuple[0].name,
                    self.queue_name,
                )
            )
            self.last_put_message = message_data_tuple[0]
            self.last_put_time = put_time
        self.queue.put(message_data_tuple, *args, **kwargs)

    def get(self, task_name, *args, **kwargs):
        """Gets data from a verbose queue

        Parameters
        ----------
        task_name : str :
            Name of the task that is retrieving data from the queue
        *args :
            Additional arguments that will be passed to the mp.queues.Queue.get
            function
        **kwargs :
            Additional arguments that will be passed to the mp.queues.Queue.get
            function


        Returns
        -------
        message_data_tuple :
            A (message,data) tuple

        """
        get_time = time.time()
        message_data_tuple = self.queue.get(*args, **kwargs)
        if (
            self.last_get_message != message_data_tuple[0]
            or get_time - self.last_get_time > self.time_threshold
        ):
            self.log_queue.put(
                "{:}: {:} got {:} from {:}\n".format(
                    datetime.now(),
                    task_name,
                    message_data_tuple[0].name,
                    self.queue_name,
                )
            )
            self.last_get_message = message_data_tuple[0]
            self.last_get_time = get_time
        return message_data_tuple

    def flush(self, task_name):
        """Flushes a verbose queue getting all data currently in the queue

        After execution the queue should be empty barring race conditions.

        Parameters
        ----------
        task_name : str :
            Name of the task that is flushing the queue


        Returns
        -------
        data : iterable of message_data_tuples :
            A list of all (message,data) tuples currently in the queue.

        """
        flush_time = time.time()
        if flush_time - self.last_flush > 0.1:
            self.log_queue.put(
                "{:}: {:} flushed {:}\n".format(datetime.now(), task_name, self.queue_name)
            )
            self.last_flush = flush_time
        data = []
        while True:
            try:
                data.append(self.queue.get(False))
                self.log_queue.put(
                    "{:}: {:} got {:} from {:} during flush\n".format(
                        datetime.now(), task_name, data[-1][0].name, self.queue_name
                    )
                )
            except mp.queues.Empty:
                return data

    def empty(self):
        """Return true if the queue is empty."""
        return self.queue.empty()


class QueueContainer:
    """A container class for the queues that the controller will manage"""

    def __init__(
        self,
        controller_communication_queue: VerboseMessageQueue,
        acquisition_command_queue: VerboseMessageQueue,
        output_command_queue: VerboseMessageQueue,
        streaming_command_queue: VerboseMessageQueue,
        log_file_queue: mp.Queue,
        input_output_sync_queue: mp.Queue,
        single_process_hardware_queue: mp.Queue,
        gui_update_queue: mp.Queue,
        environment_command_queues: Dict[str, VerboseMessageQueue],
        environment_data_in_queues: Dict[str, mp.Queue],
        environment_data_out_queues: Dict[str, mp.Queue],
    ):
        """A container class for the queues that the controller will manage.

        The controller uses many queues to pass data between the various pieces.
        This class organizes those queues into one common namespace.

        Parameters
        ----------
        controller_communication_queue : VerboseMessageQueue
            Queue that is read by the controller for global controller commands
        acquisition_command_queue : VerboseMessageQueue
            Queue that is read by the acquisition subtask for acquisition commands
        output_command_queue : VerboseMessageQueue
            Queue that is read by the output subtask for output commands
        streaming_command_queue : VerboseMessageQueue
            Queue that is read by the streaming subtask for streaming commands
        log_file_queue : mp_queues.Queue
            Queue for putting logging messages that will be read by the logging
            subtask and written to a file.
        input_output_sync_queue : mp_queues.Queue
            Queue that is used to synchronize input and output signals
        single_process_hardware_queue : mp_queues.Queue
            Queue that is used to connect the acquisition and output subtasks
            for hardware implementations that cannot have acquisition and
            output in separate processes.
        gui_update_queue : mp_queues.Queue
            Queue where various subtasks put instructions for updating the
            widgets in the user interface
        environment_command_queues : Dict[str,VerboseMessageQueue]
            A dictionary where the keys are environment names and the values are
            VerboseMessageQueues that connect the main controller to the
            environment subtasks for sending instructions.
        environment_data_in_queues : Dict[str,multiprocessing.queues.Queue]
            A dictionary where the keys are environment names and the values are
            multiprocessing queues that connect the acquisition subtask to the
            environment subtask.  Each environment will retrieve acquired data
            from this queue.
        environment_data_out_queues : Dict[str,multiprocessing.queues.Queue]
            A dictionary where the keys are environment names and the values are
            multiprocessing queues that connect the output subtask to the
            environment subtask.  Each environment will put data that it wants
            the controller to generate in this queue.

        """
        self.controller_communication_queue = controller_communication_queue
        self.acquisition_command_queue = acquisition_command_queue
        self.output_command_queue = output_command_queue
        self.streaming_command_queue = streaming_command_queue
        self.log_file_queue = log_file_queue
        self.input_output_sync_queue = input_output_sync_queue
        self.single_process_hardware_queue = single_process_hardware_queue
        self.gui_update_queue = gui_update_queue
        self.environment_command_queues = environment_command_queues
        self.environment_data_in_queues = environment_data_in_queues
        self.environment_data_out_queues = environment_data_out_queues
