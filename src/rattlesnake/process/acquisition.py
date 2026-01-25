from abstract_message_process import AbstractMessageProcess
from ..utilities import VerboseMessageQueue, GlobalCommands
from ..hardware.hardware_utilities import HardwareMetadata, HardwareType
import multiprocessing as mp
import numpy as np
from time import time, sleep

DEBUG = False
if DEBUG:
    from glob import glob

    FILE_OUTPUT = "debug_data/acquisition_{:}.npz"


class AcquisitionProcess(AbstractMessageProcess):
    """Class defining the acquisition behavior of the controller

    This class will handle reading data from the hardware and then sending it
    to the individual environment processes.

    See AbstractMesssageProcess for inherited class members.
    """

    def __init__(
        self,
        process_name: str,
        log_file_queue: mp.Queue,
        acquisition_command_queue: mp.Queue,
        gui_update_queue: mp.Queue,
        acquisition_to_environment_queue: VerboseMessageQueue,
        output_to_acquisition_sync_queue: VerboseMessageQueue,
        streaming_command_queue: VerboseMessageQueue,
        acquisition_active: mp.Value,
    ):
        """
        Constructor for the AcquisitionProcess class

        Sets up the ``command_map`` and initializes all data members.

        Parameters
        ----------
        process_name : str
            The name of the process.
        environments : list
            A list of ``(ControlType,environment_name)`` pairs that define the
            environments in the controller.


        """
        super().__init__(process_name, log_file_queue, acquisition_command_queue, gui_update_queue)
        self.map_command(GlobalCommands.INITIALIZE_HARDWARE, self.initialize_hardware)
        # self.map_command(GlobalCommands.INITIALIZE_ENVIRONMENT, self.initialize_environment)
        # self.map_command(GlobalCommands.RUN_HARDWARE, self.acquire_signal)
        # self.map_command(GlobalCommands.STOP_HARDWARE, self.stop_acquisition)
        # self.map_command(GlobalCommands.STOP_ENVIRONMENT, self.stop_environment)
        # self.map_command(GlobalCommands.START_STREAMING, self.start_streaming)
        # self.map_command(GlobalCommands.STOP_STREAMING, self.stop_streaming)

        # Communication
        self.log_file_queue = log_file_queue
        self.acquisition_command_queue = acquisition_command_queue
        self.gui_update_queue = gui_update_queue
        self.acquisition_to_environment_queue = acquisition_to_environment_queue
        self.output_to_acquisition_sync_queue = output_to_acquisition_sync_queue
        self.streaming_command_queue = streaming_command_queue

        self.startup = True
        self.shutdown_flag = False
        self.any_environments_started = False
        # Sampling data
        self.sample_rate = None
        self.read_size = None
        # Environment Data
        self.environment_list = []
        self.environment_acquisition_channels = None
        self.environment_active_flags = {}
        self.environment_last_data = {}
        self.environment_samples_remaining_to_read = {}
        self.environment_first_data = {}
        # self.environment_list = [environment[1] for environment in environments]
        # self.environment_acquisition_channels = None
        # self.environment_active_flags = {environment:False for environment in self.environment_list}
        # self.environment_last_data = {environment:False for environment in self.environment_list}
        # self.environment_samples_remaining_to_read = {environment:0 for environment in self.environment_list}
        # self.environment_first_data = {environment:None for environment in self.environment_list}
        # Hardware data
        self.hardware = None
        # Streaming Information
        self.streaming = False
        self.has_streamed = False
        # Persistent data
        self.read_data = None
        self.output_indices = None
        # Abort and Warning Limits
        self.abort_limits = None
        self.warning_limits = None
        self._acquisition_active = acquisition_active

    @property
    def acquisition_active(self):
        return bool(self._acquisition_active.value)

    @acquisition_active.setter
    def acquisition_active(self, val):
        if val:
            self._acquisition_active.value = 1
        else:
            self._acquisition_active.value = 0

    def initialize_hardware(self, metadata: HardwareMetadata):
        if self.hardware is not None:
            self.hardware.close()
        if metadata.hardware_type == HardwareType.NI_DAQmx:
            from ..hardware.nidqaqmx import NIDAQmxAcquisition

            self.hardware = NIDAQmxAcquisition()
        # Initialize hardware and create channels
        self.hardware.set_up_data_acquisition_parameters_and_channels(metadata)
        # Set up warning and abort limits
        self.abort_limits = []
        self.warning_limits = []
        for channel in metadata.channel_list:
            try:
                warning_limit = float(channel.warning_level)
            except (ValueError, TypeError):
                warning_limit = float("inf")  # Never warn on this channel
            try:
                abort_limit = float(channel.abort_level)
            except (ValueError, TypeError):
                abort_limit = float("inf")  # Never abort on this channel if not specified
            self.warning_limits.append(warning_limit)
            self.abort_limits.append(abort_limit)
        self.abort_limits = np.array(self.abort_limits)
        self.warning_limits = np.array(self.warning_limits)
        self.output_indices = [
            index
            for index, channel in enumerate(metadata.channel_list)
            if not (channel.feedback_device is None) and not (channel.feedback_device.strip() == "")
        ]
        self.read_data = np.zeros(
            (
                len(metadata.channel_list),
                4
                * np.max(
                    [
                        metadata.samples_per_read,
                        metadata.samples_per_write // metadata.output_oversample,
                    ]
                ),
            )
        )

    def acquire_signal(self, data):
        """The main acquisition loop of the controller.

        If it is the first time through this loop, startup will be set to True
        and the hardware will be started.

        If it is the last time through this loop, the hardware will be shut
        down.

        The function will simply read the data from the hardware and pass it
        to any active environment and to the streaming process if the process
        is active.

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``

        """
        if self.startup:
            self.any_environments_started = False
            self.log("Waiting for Output to Start")
            start_wait_time = time()
            while True:
                # Try to get data from the measurement if we can
                try:
                    environment, data = self.output_to_acquisition_sync_queue.get_nowait()
                except mp.queues.Empty:
                    if time() - start_wait_time > 30:
                        self.gui_update_queue.put(
                            (
                                "error",
                                (
                                    "Acquisition Error",
                                    "Acquisition timed out waiting for output to start.  Check output task for errors!",
                                ),
                            )
                        )
                        break
                    sleep(0.1)
                    continue
                if environment is None:
                    self.log("Detected Output Started")
                    break
                else:
                    self.log("Listening for first data for environment {:}".format(environment))
                    self.environment_first_data[environment] = data
                    self.any_environments_started = True
            self.log("Starting Hardware Acquisition")
            self.hardware.start()
            self.startup = False
            self.acquisition_active = True
            # print('started acquisition')
        self.get_first_output_data()
        if (
            self.shutdown_flag  # We're shutting down
            and all([not flag for environment, flag in self.environment_active_flags.items()])  # All the environments are inactive
            and all([flag is None for environment, flag in self.environment_first_data.items()])  # All the environments are not starting
            and all([not flag for environment, flag in self.environment_last_data.items()])  # None of the environments are expecting their last data
        ):
            self.log("Acquiring Remaining Data")
            read_data = self.hardware.read_remaining()
            self.add_data_to_buffer(read_data)
            if read_data.shape[-1] != 0:
                max_vals = np.max(np.abs(read_data), axis=-1)
                self.gui_update_queue.put(("monitor", max_vals))
                warn_channels = max_vals > self.warning_limits
                if np.any(warn_channels):
                    print("Channels {:} Reached Warning Limit".format([i + 1 for i in range(len(warn_channels)) if warn_channels[i]]))
                    self.log("Channels {:} Reached Warning Limit".format([i + 1 for i in range(len(warn_channels)) if warn_channels[i]]))
                abort_channels = max_vals > self.abort_limits
                if np.any(abort_channels):
                    print("Channels {:} Reached Abort Limit".format([i + 1 for i in range(len(abort_channels)) if abort_channels[i]]))
                    self.log("Channels {:} Reached Abort Limit".format([i + 1 for i in range(len(abort_channels)) if abort_channels[i]]))
                    # Don't stop because we're already shutting down.
            self.hardware.stop()
            self.shutdown_flag = False
            self.startup = True
            self.acquisition_active = False
            self.log("Acquisition Shut Down")
            # print('{:} {:}'.format(self.streaming,self.any_environments_started))
            if self.streaming and self.any_environments_started:
                self.streaming_command_queue.put(self.process_name, (GlobalCommands.STREAMING_DATA, read_data.copy()))
                self.streaming = False
            if self.has_streamed and self.any_environments_started:
                self.streaming_command_queue.put(self.process_name, (GlobalCommands.FINALIZE_STREAMING, None))
                self.has_streamed = False
        else:
            self.log("Acquiring Data for {:} environments".format([name for name, flag in self.environment_active_flags.items() if flag]))
            read_data = self.hardware.read()
            self.add_data_to_buffer(read_data)
            if read_data.shape[-1] != 0:
                max_vals = np.max(np.abs(read_data), axis=-1)
                self.gui_update_queue.put(("monitor", max_vals))
                warn_channels = max_vals > self.warning_limits
                if np.any(warn_channels):
                    print("Channels {:} Reached Warning Limit".format([i + 1 for i in range(len(warn_channels)) if warn_channels[i]]))
                    self.log("Channels {:} Reached Warning Limit".format([i + 1 for i in range(len(warn_channels)) if warn_channels[i]]))
                abort_channels = max_vals > self.abort_limits
                if np.any(abort_channels):
                    print("Channels {:} Reached Abort Limit".format([i + 1 for i in range(len(abort_channels)) if abort_channels[i]]))
                    self.log("Channels {:} Reached Abort Limit".format([i + 1 for i in range(len(abort_channels)) if abort_channels[i]]))
                    self.gui_update_queue.put(("stop", None))

            # Send the data to the different channels
            for environment in self.environment_list:
                # Check to see if we're waiting for the first data for this environment
                if self.environment_first_data[environment] is not None:
                    if np.all(np.abs(self.environment_first_data[environment]) < 1e-10):
                        delay = -self.read_size
                    else:
                        correlation_start_time = time()
                        if DEBUG:
                            num_files = len(glob(FILE_OUTPUT.format("*")))
                            np.savez(
                                FILE_OUTPUT.format(num_files),
                                read_data_buffer=self.read_data,
                                read_data=read_data,
                                output_indices=self.output_indices,
                                first_data=self.environment_first_data[environment],
                            )
                        _, delay, _ = align_signals(
                            self.read_data[self.output_indices],
                            self.environment_first_data[environment],
                            perform_subsample=False,
                            correlation_threshold=0.5,
                        )
                        correlation_end_time = time()
                        self.log(
                            "Correlation check for environment {:} took {:0.2f} seconds".format(
                                environment, correlation_end_time - correlation_start_time
                            )
                        )
                        if delay is None:
                            continue
                    self.log("Found First Data for Environment {:}".format(environment))
                    environment_data = self.read_data[self.environment_acquisition_channels[environment], delay:]
                    self.environment_first_data[environment] = None
                    if not self.environment_last_data[environment]:
                        self.environment_active_flags[environment] = True
                    else:
                        self.log("Already received environment {:} shutdown signal, not starting".format(environment))
                # Check to see if the environment is active
                elif self.environment_active_flags[environment] or self.environment_last_data[environment]:
                    environment_data = read_data[self.environment_acquisition_channels[environment]].copy()
                # Otherwise the environment isn't active
                else:
                    continue
                if self.environment_last_data[environment]:
                    self.environment_samples_remaining_to_read[environment] -= self.read_size
                    self.log(
                        "Reading last data for {:}, {:} samples remaining".format(
                            environment, self.environment_samples_remaining_to_read[environment]
                        )
                    )
                environment_finished = self.environment_last_data[environment] and self.environment_samples_remaining_to_read[environment] <= 0
                self.log("Sending {:} data to {:} environment".format(environment_data.shape, environment))
                self.queue_container.environment_data_in_queues[environment].put((environment_data, environment_finished))
                if environment_finished:
                    self.environment_last_data[environment] = False
                    self.log("Delivered last data to {:}".format(environment))

            #                    np.savez('test_data/acquisition_data_check.npz',read_data = self.read_data,environment_data = environment_data,environment_channels = self.environment_acquisition_channels[environment])
            self.acquisition_command_queue.put(self.process_name, (GlobalCommands.RUN_HARDWARE, None))
            # print('{:} {:}'.format(self.streaming,self.any_environments_started))
            if self.streaming and self.any_environments_started:
                self.streaming_command_queue.put(self.process_name, (GlobalCommands.STREAMING_DATA, read_data.copy()))

    def stop_environment(self, data):
        """Sets flags stating that the specified environment will be ending.

        Parameters
        ----------
        data : str
            The environment name that should be deactivated

        """
        self.log("Deactivating Environment {:}".format(data))
        self.environment_active_flags[data] = False
        self.environment_last_data[data] = True
        self.environment_samples_remaining_to_read[data] = self.hardware.get_acquisition_delay()

    def start_streaming(self, data):
        """Sets the flag to tell the acquisition to write data to disk

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``

        """
        self.streaming = True
        if self.has_streamed:
            self.streaming_command_queue.put(self.process_name, (GlobalCommands.CREATE_NEW_STREAM, None))
        else:
            self.has_streamed = True

    def stop_streaming(self, data):
        """Sets the flag to tell the acquisition to not write data to disk

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``

        """
        self.streaming = False

    def stop_acquisition(self, data):
        """Sets a flag telling the acquisition that it should start shutting down

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``

        """
        self.shutdown_flag = True

    def quit(self, data):
        """Stops the process and shuts down the hardware if necessary.

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``
        """
        # Pull any data off the queues that have been put to
        queue_flush_sum = 0
        for queue in [q for name, q in self.queue_container.environment_data_in_queues.items()] + [self.acquisition_command_queue]:
            queue_flush_sum += len(flush_queue(queue))
        self.log("Flushed {:} items out of queues".format(queue_flush_sum))
        if not self.hardware is None:
            self.hardware.close()
        return True


def acquisition_process(
    log_file_queue: mp.Queue,
    acquisition_command_queue: mp.Queue,
    gui_update_queue: mp.Queue,
    acquisition_to_environment_queue: VerboseMessageQueue,
    output_to_acquisition_sync_queue: VerboseMessageQueue,
    streaming_command_queue: VerboseMessageQueue,
    acquisition_active: mp.Value,
):
    """Function passed to multiprocessing as the acquisition process

    This process creates the ``AcquisitionProcess`` object and calls the ``run``
    command.

    Parameters
    ----------
    queue_container : QueueContainer
        A container containing the queues used to communicate between
        controller processes
    environments : list
        A list of ``(ControlType,environment_name)`` pairs that define the
        environments in the controller.

    """

    acquisition_instance = AcquisitionProcess(
        "Acquisition",
        log_file_queue,
        acquisition_command_queue,
        gui_update_queue,
        acquisition_to_environment_queue,
        output_to_acquisition_sync_queue,
        streaming_command_queue,
        acquisition_active,
    )

    acquisition_instance.run()


def align_signals(measurement_buffer, specification, correlation_threshold=0.9, perform_subsample=True):
    maximum_possible_correlation = np.sum(specification**2)
    correlation = sig.correlate(measurement_buffer, specification, mode="valid").squeeze()
    delay = np.argmax(correlation)
    print("Max Correlation: {:}".format(np.max(correlation) / maximum_possible_correlation))
    if correlation[delay] < correlation_threshold * maximum_possible_correlation:
        return None, None, None
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
    return spec_portion_aligned, delay, mean_phase_slope


def shift_signal(signal, samples_to_keep, sample_delay, phase_slope):
    # np.savez('shift_debug.npz',signal=signal,
    #          samples_to_keep = samples_to_keep,
    #          sample_delay = sample_delay,
    #          phase_slope=phase_slope)
    signal_sample_aligned = signal[..., sample_delay : sample_delay + samples_to_keep]
    sample_aligned_fft = np.fft.rfft(signal_sample_aligned, axis=-1)
    subsample_aligned_fft = sample_aligned_fft * np.exp(-1j * phase_slope * np.arange(sample_aligned_fft.shape[-1]))
    return np.fft.irfft(subsample_aligned_fft)
