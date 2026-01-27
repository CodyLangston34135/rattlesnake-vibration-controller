from .abstract_message_process import AbstractMessageProcess
from ..utilities import QueueContainer, GlobalCommands


TASK_NAME = "Controller"


class Controller(AbstractMessageProcess):
    """Class defining behavior during the ACQUISITION_START/OUTPUT_START states of Rattlesnake

    This class mainly recieves commands from controller_communication_queue and sends those
    commands to the correct processes that need them. This basically handles profile events
    so that the main controller can be used to oversee the processes while data is being collected

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
            queue_container.streaming_command_queue,
            queue_container.gui_update_queue,
        )
        self.queue_container = queue_container
        self.map_command(GlobalCommands.RUN_HARDWARE, self.run_hardware)
        self.map_command(GlobalCommands.STOP_HARDWARE, self.stop_hardware)
        self.map_command(GlobalCommands.START_ENVIRONMENT, self.start_environment)
        self.map_command(GlobalCommands.STOP_ENVIRONMENT, self.stop_environment)
        self.map_command(GlobalCommands.START_STREAMING, self.start_streaming)
        self.map_command(GlobalCommands.STOP_STREAMING, self.stop_streaming)

    def run_hardware(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, data))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.RUN_HARDWARE, data))

    def stop_hardware(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, data))
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.STOP_HARDWARE, data))

    def start_environment(self, data):
        self.queue_container.output_command_queue.put(TASK_NAME, (GlobalCommands.START_ENVIRONMENT, data))

    def stop_environment(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_ENVIRONMENT, data))

    def start_streaming(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.START_STREAMING, None))

    def stop_streaming(self, data):
        self.queue_container.acquisition_command_queue.put(TASK_NAME, (GlobalCommands.STOP_STREAMING, None))


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
