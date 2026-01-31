from rattlesnake.environment.abstract_environment import EnvironmentMetadata, EnvironmentInstructions, EnvironmentProcess
from rattlesnake.environment.environment_utilities import ControlTypes
from .mock_utilities import mock_channel_list
from unittest import mock
from enum import Enum

UNIMPLEMENTED_ENVIRONMENT = {
    ControlTypes.MODAL,
    ControlTypes.RANDOM,
    ControlTypes.READ,
    ControlTypes.SINE,
    ControlTypes.TRANSIENT,
}


# region: MockEnvironmentType
class MockEnvironmentType(Enum):
    ENVIRONMENT = 0


# region: MockEnvironmentMetadata
class MockEnvironmentMetadata(EnvironmentMetadata):
    def __init__(self):
        super().__init__(MockEnvironmentType.ENVIRONMENT, "Mock Environment")
        self.queue_name = "Environment 0"
        self.channel_list = mock_channel_list()

    def validate(self):
        super().validate()
        return True

    def store_to_netcdf(self, netcdf_group_handle):
        super().store_to_netcdf(netcdf_group_handle)
        return None


# region: MockEnvironmentInstructions
class MockEnvironmentInstructions(EnvironmentInstructions):
    def __init__(self):
        super().__init__(MockEnvironmentType.ENVIRONMENT, "Environment 0")


# region: MockEnvironmentProcess
class MockEnvironmentProcess(EnvironmentProcess):
    def __init__(
        self,
        environment_name,
        queue_name,
        command_queue,
        gui_update_queue,
        controller_communication_queue,
        log_file_queue,
        data_in_queue,
        data_out_queue,
        acquisition_active,
        output_active,
        ready_event,
    ):
        super().__init__(
            environment_name,
            queue_name,
            command_queue,
            gui_update_queue,
            controller_communication_queue,
            log_file_queue,
            data_in_queue,
            data_out_queue,
            acquisition_active,
            output_active,
            ready_event,
        )

    def initialize_hardware(self, hardware_metadata):
        super().initialize_hardware(hardware_metadata)
        return None

    def initialize_environment(self, environment_metadata):
        super().initialize_environment(environment_metadata)
        return None

    def stop_environment(self, data):
        super().stop_environment(data)
        return None
