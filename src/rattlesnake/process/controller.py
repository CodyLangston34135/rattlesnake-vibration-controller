from .abstract_message_process import AbstractMessageProcess
from ..utilities import QueueContainer, GlobalCommands
from ..environment.abstract_environment import EnvironmentInstructions


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
        self.map_command(GlobalCommands.RUN_HARDWARE, self.run_hardware)
        self.map_command(GlobalCommands.STOP_HARDWARE, self.stop_hardware)
        self.map_command(GlobalCommands.INITIALIZE_ENVIRONMENT, self.initialize_environment)
        self.map_command(GlobalCommands.START_ENVIRONMENT, self.start_environment)
        self.map_command(GlobalCommands.STOP_ENVIRONMENT, self.stop_environment)
        self.map_command(GlobalCommands.START_STREAMING, self.start_streaming)
        self.map_command(GlobalCommands.STOP_STREAMING, self.stop_streaming)
        self.map_command(GlobalCommands.INITIALIZE_INSTRUCTION, self.set_instruction)
        self.map_command(GlobalCommands.AT_TARGET_LEVEL, self.at_target_level)

    def run_hardware(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, data))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, data))

    def stop_hardware(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, data))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, data))

    def initialize_environment(self, data):
        # This just clears the instructions so that you are not starting with problematic queue_names if
        # the environment order switched around
        self.environment_instructions = {}
        for metadata in data:
            self.environment_instructions[metadata.queue_name] = None

    def start_environment(self, data):
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, data))
        self.queue_container.environment_command_queues[data].put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, self.environment_instructions[data]))

    def stop_environment(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, data))

    def start_streaming(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.START_STREAMING, None))

    def stop_streaming(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_STREAMING, None))

    def set_instruction(self, data):
        self.environment_instructions[data.queue_name] = data

    def at_target_level(self, data):
        pass


def controller_process(queue_container: QueueContainer):
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

    acquisition_instance.run()
