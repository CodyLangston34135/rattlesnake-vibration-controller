import multiprocessing as mp
from abstract_message_process import AbstractMessageProcess
from ..utilities import VerboseMessageQueue, GlobalCommands


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
        acquisition_command_queue: VerboseMessageQueue,
        gui_update_queue: mp.Queue,
        environments: list,
        acquisition_active: mp.sharedctypes.Synchronized,
    ):
        """
        Constructor for the AcquisitionProcess class

        Sets up the ``command_map`` and initializes all data members.

        Parameters
        ----------
        process_name : str
            The name of the process.
        queue_container : QueueContainer
            A container containing the queues used to communicate between
            controller processes
        environments : list
            A list of ``(ControlType,environment_name)`` pairs that define the
            environments in the controller.


        """
        super().__init__(
            process_name,
            log_file_queue,
            acquisition_command_queue,
            gui_update_queue,
        )
        # Communication
        self.queue_container = queue_container
        self.startup = True
        self.shutdown_flag = False
        self.any_environments_started = False
        # Sampling data
        self.sample_rate = None
        self.read_size = None
        # Environment Data
        self.environment_list = [environment[1] for environment in environments]
        self.environment_acquisition_channels = None
        self.environment_active_flags = {
            environment: False for environment in self.environment_list
        }
        self.environment_last_data = {
            environment: False for environment in self.environment_list
        }
        self.environment_samples_remaining_to_read = {
            environment: 0 for environment in self.environment_list
        }
        self.environment_first_data = {
            environment: None for environment in self.environment_list
        }
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
        # print('acquisition setup')
