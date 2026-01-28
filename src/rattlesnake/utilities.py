# DO NOT import from other files in utilities.py
import multiprocessing as mp
import time
from qtpy import QtCore
from datetime import datetime
from enum import Enum
from typing import Dict


class GlobalCommands(Enum):
    QUIT = 0  # Stop individual processes
    INITIALIZE_HARDWARE = 1  # Store hardware metadata to processes
    RUN_HARDWARE = 2  # Start running acquisition/output process
    STOP_HARDWARE = 3  # Stops running acquisition/output process
    INITIALIZE_ENVIRONMENT = 4  # Stores metadata to processes
    START_ENVIRONMENT = 5  # Tells output to start that environment
    STOP_ENVIRONMENT = 6  # Tells output to stop that environment
    INITIALIZE_STREAMING = 7  # Creates stream file to store to
    CREATE_NEW_STREAM = 8  # Create new stream of data in file
    START_STREAMING = 9  # Acquisition sends data to stream process
    STREAMING_DATA = 10  # Continue storing data
    STOP_STREAMING = 11  # Acquisition stops sending data to stream process
    FINALIZE_STREAMING = 12  # Close out of stream file
    INITIALIZE_INSTRUCTION = 13  # Send EnvironmentInstructions to controller
    INITIALIZE_PROFILE = 15  # Send profile metadata to controller
    START_PROFILE = 16  # Start test from profile
    STOP_PROFILE = 17  # Stop test from profile
    AT_TARGET_LEVEL = 18  # REMOVE LATER


def log_file_task(queue: mp.Queue):
    """A multiprocessing function that collects logging data and writes to file

    Parameters
    ----------
    queue : mp.queues.Queue
        The multiprocessing queue to collect logging messages from
    """
    with open("Rattlesnake.log", "w") as f:
        while True:
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

    def __init__(self, log_queue, name_manager, base_name: str = ""):
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
        self.base_name = base_name
        self.environment_name = name_manager.Value(str, "")
        self.last_put_message = None
        self.last_put_time = -float("inf")
        self.last_get_message = None
        self.last_get_time = -float("inf")
        self.last_flush = -float("inf")
        self.time_threshold = 1.0

    @property
    def log_name(self):
        env = self.environment_name.value
        return f"{self.base_name} | {env}" if env else self.base_name

    def assign_environment(self, env_name: str):
        self.environment_name.value = env_name

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
        if self.last_put_message != message_data_tuple[0] or put_time - self.last_put_time > self.time_threshold:
            self.log_queue.put("{:}: {:} put {:} to {:}\n".format(datetime.now(), task_name, message_data_tuple[0].name, self.log_name))
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
        if self.last_get_message != message_data_tuple[0] or get_time - self.last_get_time > self.time_threshold:
            self.log_queue.put("{:}: {:} got {:} from {:}\n".format(datetime.now(), task_name, message_data_tuple[0].name, self.log_name))
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
            self.log_queue.put("{:}: {:} flushed {:}\n".format(datetime.now(), task_name, self.log_name))
            self.last_flush = flush_time
        data = []
        while True:
            try:
                data.append(self.queue.get(False))
                self.log_queue.put("{:}: {:} got {:} from {:} during flush\n".format(datetime.now(), task_name, data[-1][0].name, self.log_name))
            except mp.queues.Empty:
                return data

    def empty(self):
        """Return true if the queue is empty."""
        return self.queue.empty()

    def close(self):
        """Closes queue"""
        self.queue.close()

    def join_thread(self):
        """Joins thread"""
        self.queue.join_thread()


class QueueContainer:
    """A container class for the queues that the controller will manage"""

    def __init__(
        self,
        controller_command_queue: VerboseMessageQueue,
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
        controller_command_queue : VerboseMessageQueue
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
        self.controller_command_queue = controller_command_queue
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


def flush_queue(queue, timeout=None):
    """Flushes a queue by getting all the data currently in it.

    Parameters
    ----------
    queue : mp.queues.Queue or VerboseMessageQueue:
        The queue to flush


    Returns
    -------
    data : iterable
        A list of all data that were in the queue at flush

    """
    data = []
    while True:
        try:
            if isinstance(queue, VerboseMessageQueue):
                data.append(
                    queue.get(
                        "Flush",
                        block=False if timeout is None else True,
                        timeout=timeout,
                    )
                )
            else:
                data.append(queue.get(block=False if timeout is None else True, timeout=timeout))
        except mp.queues.Empty:
            return data
