from .abstract_message_process import AbstractMessageProcess
from ..utilities import QueueContainer, GlobalCommands
from ..environment.abstract_environment import EnvironmentInstructions
from .streaming import StreamMetadata, StreamType


TASK_NAME = "Controller"


class Controller(AbstractMessageProcess):
    """Class defining behavior during the ACQUISITION_START/OUTPUT_START states of Rattlesnake

    This class mainly recieves commands from controller_communication_queue and sends those
    commands to the correct processes that need them. This basically handles profile events
    so that the main controller is not caught up in a processing loop while data is being
    collected.

    See AbstractMesssageProcess for inherited class members.
    """

    def __init__(self, process_name: str, queue_container: QueueContainer):
        """Constructor for the Controller class

        Sets up the ``command_map`` and initializes all data members.

        Parameters
        ----------
        process_name : str
            The name of the process.
        queue_container : QueueContainer
            A container containing the queues used to communicate between
            controller processes

        """
        super().__init__(
            process_name,
            queue_container.log_file_queue,
            queue_container.controller_command_queue,
            queue_container.gui_update_queue,
        )
        self.queue_container = queue_container
        self.environment_instructions = {}
        self.stream_metadata = StreamMetadata()
        self.map_command(GlobalCommands.RUN_HARDWARE, self.run_hardware)
        self.map_command(GlobalCommands.STOP_HARDWARE, self.stop_hardware)
        self.map_command(GlobalCommands.START_ENVIRONMENT, self.start_environment)
        self.map_command(GlobalCommands.STOP_ENVIRONMENT, self.stop_environment)
        self.map_command(GlobalCommands.INITIALIZE_STREAMING, self.initialize_streaming)
        self.map_command(GlobalCommands.START_STREAMING, self.start_streaming)
        self.map_command(GlobalCommands.STOP_STREAMING, self.stop_streaming)
        self.map_command(GlobalCommands.AT_TARGET_LEVEL, self.at_target_level)

    def run_hardware(self, data: None):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, None))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, None))

    def stop_hardware(self, data: None):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, None))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, None))

    def start_environment(self, data: tuple[str, EnvironmentInstructions]):
        queue_name, instruction = data
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, queue_name))
        self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, instruction))

    def stop_environment(self, data: str):
        queue_name = data
        self.queue_container.environment_command_queues[queue_name].put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, None))
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, queue_name))

    def initialize_streaming(self, data: StreamMetadata):
        self.stream_metadata = data

    def start_streaming(self, data: None):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.START_STREAMING, None))

    def stop_streaming(self, data: None):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_STREAMING, None))

    def at_target_level(self, data: str):
        environment_name = data
        if self.stream_metadata.stream_type == StreamType.TEST_LEVEL and self.stream_metadata.test_level_environment_name == environment_name:
            self.start_streaming()


def controller_process(queue_container: QueueContainer, shutdown_event):
    """Function passed to multiprocessing as the controller process

    This process creates the ``Controller`` object and calls the ``run``
    command.

    Parameters
    ----------
    queue_container : QueueContainer
        A container containing the queues used to communicate between
        controller processes

    """

    acquisition_instance = Controller(TASK_NAME, queue_container)

    acquisition_instance.run(shutdown_event)
