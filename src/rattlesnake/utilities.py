# DO NOT import from other files in utilities.py
import os
import string
import random
import time
import importlib.util
import numpy as np
import multiprocessing as mp
import multiprocessing.queues as mpqueue
import multiprocessing.synchronize  # pylint: disable=unused-import
import queue as thqueue
import scipy.signal as sig
from scipy.interpolate import interp1d
from scipy.io import loadmat
from datetime import datetime
from enum import Enum
from typing import Dict


# region: Error
class RattlesnakeError(Exception):
    pass


# region: GlobalCommands
class GlobalCommands(Enum):
    QUIT = 0  # Stop individual processes
    INITIALIZE_HARDWARE = 1  # Store hardware metadata to processes
    RUN_HARDWARE = 2  # Start running acquisition/output process
    STOP_HARDWARE = 3  # Stops running acquisition/output process
    INITIALIZE_ENVIRONMENT = 4  # Stores metadata to processes
    START_ENVIRONMENT = 5  # Tells output to start that environment
    STOP_ENVIRONMENT = 6  # Tells output to stop that environment
    INITIALIZE_SYSTEM_ID = 7  # Stores system id metadata to environment and system id process
    START_SYSTEM_ID_NOISE = 8  # Start up system identification noise
    START_SYSTEM_ID_TRANSFER = 9  # Start up system identification transfer function
    STOP_SYSTEM_ID = 10  # Stop system identification process
    INITIALIZE_STREAMING = 11  # Creates stream file to store to
    CREATE_NEW_STREAM = 12  # Create new stream of data in file
    START_STREAMING = 13  # Acquisition sends data to stream process
    STREAMING_DATA = 14  # Continue storing data
    STOP_STREAMING = 15  # Acquisition stops sending data to stream process
    FINALIZE_STREAMING = 16  # Close out of stream file
    INITIALIZE_PROFILE = 17  # Send profile metadata to controller
    START_PROFILE = 18  # Start test from profile
    STOP_PROFILE = 19  # Stop test from profile
    PROFILE_CLOSEOUT = 20  # Tells controller the profile events are over
    STREAM_AT_TARGET_LEVEL = 21  # Notifies controller that environment has hit its target level
    STREAM_MANUAL = 22  # Notifies controller that manual streaming has been enabled
    SEND_ENVIRONMENT_COMMAND = 23  # Sends environment specific command to environment

    @property
    def label(self):
        """Used by UI as names for"""
        return self.name.replace("_", " ").title()


def log_file_task(queue: mp.Queue, shutdown_event):
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


# region: VerboseMessageQueue
class VerboseMessageQueue:
    """A queue class that contains automatic logging information"""

    def __init__(self, log_queue, base_queue, base_name: str = "", name_manager=None):
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
        self.base_queue = base_queue
        self.log_queue = log_queue
        self.base_name = base_name
        if name_manager:
            self.environment_name = name_manager.Value(str, "")
        else:
            self.environment_name = None
        self.last_put_message = None
        self.last_put_time = -float("inf")
        self.last_get_message = None
        self.last_get_time = -float("inf")
        self.last_flush = -float("inf")
        self.time_threshold = 1.0

    @property
    def log_name(self):
        if self.environment_name:
            env = self.environment_name.value
            return f"{self.base_name} | {env}" if env else self.base_name
        else:
            return {self.base_name}

    def assign_environment(self, env_name: str):
        self.environment_name.value = env_name

    def generate_message_id(self, size=6, chars=string.ascii_letters + string.digits):
        """Generates a random identifier for log file messages"""
        return "".join(random.choice(chars) for _ in range(size))

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
            message_id = self.generate_message_id(8)
            self.log_queue.put(f"{datetime.now()}: {task_name} put " f"{message_data_tuple[0].name} ({message_id}) to {self.log_name}\n")
            self.last_put_message = message_data_tuple[0]
            self.last_put_time = put_time
        else:
            message_id = ""
        self.base_queue.put((message_id, message_data_tuple), *args, **kwargs)

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
        (message_id, message_data_tuple) = self.base_queue.get(*args, **kwargs)
        if message_id != "":
            self.log_queue.put(f"{datetime.now()}: {task_name} got " f"{message_data_tuple[0].name} ({message_id}) from {self.log_name}\n")
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
            self.log_queue.put(f"{datetime.now()}: {task_name} flushed {self.log_name}\n")
            self.last_flush = flush_time
        data = []
        while True:
            try:
                message_id, this_data = self.base_queue.get(False)
                data.append(this_data)
                if message_id != "":
                    self.log_queue.put(
                        f"{datetime.now()}: {task_name} got {data[-1][0].name} ("
                        f"{message_id if message_id != '' else 'put not logged'})"
                        f" from {self.log_name} during flush\n"
                    )
            except mp.queues.Empty:
                return data

    def empty(self):
        """Return true if the queue is empty."""
        return self.base_queue.empty()

    def close(self):
        """Closes queue"""
        if hasattr(self.base_queue, "close"):
            self.base_queue.close()

    def join_thread(self):
        """Joins thread"""
        if hasattr(self.base_queue, "join_thread"):
            self.base_queue.join_thread()


# region: QueueContainer
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


class EventContainer:
    def __init__(
        self,
        controller_ready_event: mp.synchronize.Event,
        acquisition_ready_event: mp.synchronize.Event,
        output_ready_event: mp.synchronize.Event,
        streaming_ready_event: mp.synchronize.Event,
        environment_ready_events: Dict[str, mp.synchronize.Event],
        log_close_event: mp.synchronize.Event,
        controller_close_event: mp.synchronize.Event,
        acquisition_close_event: mp.synchronize.Event,
        output_close_event: mp.synchronize.Event,
        streaming_close_event: mp.synchronize.Event,
        environment_close_events: Dict[str, mp.synchronize.Event],
        acquisition_active_event: mp.synchronize.Event,
        output_active_event: mp.synchronize.Event,
        streaming_active_event: mp.synchronize.Event,
        environment_active_events: Dict[str, mp.synchronize.Event],
        environment_sysid_events: Dict[str, mp.synchronize.Event],
    ):
        # Ready Events
        self.controller_ready_event = controller_ready_event
        self.acquisition_ready_event = acquisition_ready_event
        self.output_ready_event = output_ready_event
        self.streaming_ready_event = streaming_ready_event
        self.environment_ready_events = environment_ready_events
        # Close Events
        self.log_close_event = log_close_event
        self.controller_close_event = controller_close_event
        self.acquisition_close_event = acquisition_close_event
        self.output_close_event = output_close_event
        self.streaming_close_event = streaming_close_event
        self.environment_close_events = environment_close_events
        # Active Events
        self.acquisition_active_event = acquisition_active_event
        self.output_active_event = output_active_event
        self.streaming_active_event = streaming_active_event
        self.environment_active_events = environment_active_events
        self.environment_sysid_events = environment_sysid_events


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
        except (thqueue.Empty, mpqueue.Empty):
            return data


# region: Loading
def load_python_module(module_path):
    """Loads in the Python file at the specified path as a module at runtime

    Parameters
    ----------
    module_path : str:
        Path to the module to be loaded


    Returns
    -------
    module : module:
        A reference to the loaded module
    """
    _, file = os.path.split(module_path)
    file, _ = os.path.splitext(file)
    spec = importlib.util.spec_from_file_location(file, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_time_history(signal_path, sample_rate):
    """Loads a time history from a given file

    The signal can be loaded from numpy files (.npz, .npy) or matlab files (.mat).
    For .mat and .npz files, the time data can be included in the file in the
    't' field, or it can be excluded and the sample_rate input argument will
    be used.  If time data is specified, it will be linearly interpolated to the
    sample rate of the controller.
    For these file types, the signal should be stored in the 'signal'
    field.  For .npy files, only one array is stored, so it is treated as the
    signal, and the sample_rate input argument is used to construct the time
    data.

    Parameters
    ----------
    signal_path : str:
        Path to the file from which to load the time history

    sample_rate : str:
        The sample rate of the loaded signal.

    Returns
    -------
    signal : np.ndarray:
        A signal loaded from the file

    """
    _, extension = os.path.splitext(signal_path)
    if extension.lower() == ".npy":
        signal = np.load(signal_path)
    elif extension.lower() == ".npz":
        data = np.load(signal_path)
        signal = data["signal"]
        try:
            times = data["t"].squeeze()
            fn = interp1d(times, signal)
            abscissa = np.arange(0, max(times) + 1 / sample_rate - 1e-10, 1 / sample_rate)
            abscissa = abscissa[abscissa <= max(times)]
            signal = fn(abscissa)
        except KeyError:
            pass
    elif extension.lower() == ".mat":
        data = loadmat(signal_path)
        signal = data["signal"]
        try:
            times = data["t"].squeeze()
            fn = interp1d(times, signal)
            abscissa = np.arange(0, max(times) + 1 / sample_rate - 1e-10, 1 / sample_rate)
            abscissa = abscissa[abscissa <= max(times)]
            signal = fn(abscissa)
        except KeyError:
            pass
    else:
        raise ValueError(f"Could Not Determine the file type from the filename {signal_path}: {extension}")
    if signal.shape[-1] % 2 == 1:
        signal = signal[..., :-1]
    return signal


def load_csv_matrix(file):
    """Loads a matrix from a CSV file

    Parameters
    ----------
    file : str :
        Path to the file that will be loaded


    Returns
    -------
    data : list[list[str]]
        A 2D nested list of strings containing the matrix in the CSV file.

    """
    with open(file, "r", encoding="utf-8") as f:
        data = []
        for line in f:
            data.append([])
            for v in line.split(","):
                data[-1].append(v.strip())
    return data


def save_csv_matrix(data, file):
    """Saves 2D matrix data to a file

    Parameters
    ----------
    data : 2D iterable of str:
        A 2D nested iterable of strings that will be written to a file
    file : str :
        The path to a file where the data will be written.

    """
    text = "\n".join([",".join(row) for row in data])
    with open(file, "w", encoding="utf-8") as f:
        f.write(text)


# region: Math
def align_signals(
    measurement_buffer,
    specification,
    correlation_threshold=0.9,
    perform_subsample=True,
    correlation_metric=None,
):
    """Computes the time shift between two signals in time

    Parameters
    ----------
    measurement_buffer : np.ndarray
        Signal coming from the measurement
    specification : np.ndarray
        Signal to align the measurement to
    correlation_threshold : float, optional
        Threshold for a "good" correlation, by default 0.9
    perform_subsample : bool, optional
        If True, computes a time shift that could be between samples using the phase of the FFT of
        the signals, by default True
    correlation_metric : function, optional
        An optional function to use to change the matching criterion, by default A simple
        correlation is used

    Returns
    -------
    spec_portion_aligned : np.ndarray
        The portion of the measurement that lines up with the specification
    delay : float
        The time difference between the measurement and specification
    mean_phase_slope : float
        The slope of the phase computed in the FFT from the subsample alignment.  Will be None
        if subsample matching is not used
    found_correlation : float
        The value of the correlation metric used to find the match
    """
    if correlation_metric is None:
        maximum_possible_correlation = np.sum(specification**2)
        correlation = sig.correlate(measurement_buffer, specification, mode="valid").squeeze() / maximum_possible_correlation
    else:
        correlation = correlation_metric(measurement_buffer, specification)
    delay = np.argmax(correlation)
    found_correlation = correlation[delay]
    print(f"Max Correlation: {found_correlation}")
    if found_correlation < correlation_threshold:
        return None, None, None, None
    # np.savez('alignment_debug.npz',measurement_buffer=measurement_buffer,
    #          specification = specification,
    #          correlation_threshold = correlation_threshold)
    specification_portion = measurement_buffer[:, delay : delay + specification.shape[-1]]

    if perform_subsample:
        # Compute ffts for subsample alignment
        spec_fft = np.fft.rfft(specification, axis=-1)
        spec_portion_fft = np.fft.rfft(specification_portion, axis=-1)

        # Compute phase angle differences for subpixel alignment
        phase_difference = np.angle(spec_portion_fft / spec_fft)
        phase_slope = phase_difference[..., 1:-1] / np.arange(phase_difference.shape[-1])[1:-1]
        mean_phase_slope = np.median(phase_slope)  # Use Median to discard outliers due to potentially noisy phase

        spec_portion_aligned_fft = spec_portion_fft * np.exp(-1j * mean_phase_slope * np.arange(spec_portion_fft.shape[-1]))
        spec_portion_aligned = np.fft.irfft(spec_portion_aligned_fft)
    else:
        spec_portion_aligned = specification_portion.copy()
        mean_phase_slope = None
    return spec_portion_aligned, delay, mean_phase_slope, found_correlation


def shift_signal(signal, samples_to_keep, sample_delay, phase_slope):
    """Applies a time shift to a signal by modifying the phase of the FFT

    Parameters
    ----------
    signal : np.ndarray
        The signal to shift
    samples_to_keep : int
        The number of samples to keep in the shifted signal
    sample_delay : int
        The number of samples to delay
    phase_slope : float
        The slope of the phase if subsample shift is used

    Returns
    -------
    np.ndarray
        The shifted signal
    """
    signal_sample_aligned = signal[..., sample_delay : sample_delay + samples_to_keep]
    sample_aligned_fft = np.fft.rfft(signal_sample_aligned, axis=-1)
    subsample_aligned_fft = sample_aligned_fft * np.exp(-1j * phase_slope * np.arange(sample_aligned_fft.shape[-1]))
    return np.fft.irfft(subsample_aligned_fft)


def correlation_norm_signal_spec_ratio(signal, specification):
    """Computes correlation weighted by the ratio of the norms of the signals

    Parameters
    ----------
    signal : np.ndarray
        The signal to compute the correlation on
    specification : np.ndarray
        The signal to compute the correlation against

    Returns
    -------
    np.ndarray
        The weighted correlation signal
    """
    correlation = sig.correlate(signal, specification, mode="valid").squeeze()
    norm_specification = np.linalg.norm(specification)
    norm_signal = np.sqrt(np.sum(moving_sum(signal**2, specification.shape[-1]), axis=0))
    norm_signal_divide = norm_signal.copy()
    norm_signal_divide[norm_signal_divide == 0] = 1e14
    return correlation / norm_specification / norm_signal_divide - abs(1 - (norm_signal / norm_specification) ** 2)


def moving_sum(signal, n):
    """Computes a moving sum of the specified number of items

    Parameters
    ----------
    signal : np.ndarray
        The signal(s) to compute the moving sum on
    n : int
        The number of items to use in the moving sum

    Returns
    -------
    np.array
        The moving sum computed at each time step in the signal
    """
    return_value = np.cumsum(signal, axis=-1)
    return_value[..., n:] = return_value[..., n:] - return_value[..., :-n]
    return return_value[..., n - 1 :]


def rms_time(signal, axis=None, keepdims=False):
    """Computes RMS over a time signal

    Parameters
    ----------
    signal : np.ndarray :
        Signal over which to compute the root-mean-square value
    axis : int :
        The dimension over which the mean is performed (Default value = None)
    keepdims : bool :
        Whether to keep the dimension over which mean is computed (Default value = False)

    Returns
    -------
    rms : numpy scalar or numpy.ndarray
        The root-mean-square value of signal

    """
    return np.sqrt(np.mean(signal**2, axis=axis, keepdims=keepdims))


def db2scale(decibel):
    """Converts a decibel value to a scale factor

    Parameters
    ----------
    decibel : float :
        Value in decibels


    Returns
    -------
    scale : float :
        Value in linear

    """
    return 10 ** (decibel / 20)


def scale2db(scale):
    """Converts a scale quantity to decibels"""
    return 20 * np.log10(scale)


def wrap(data, period=2 * np.pi):
    """Wraps angle data between -pi/2 and pi/2"""
    return (data + period / 2) % period - period / 2
