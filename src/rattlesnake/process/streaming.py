# -*- coding: utf-8 -*-
"""
Controller subsystem that handles streaming data and metadata to NetCDF4 files
on the disk.

Rattlesnake Vibration Control Software
Copyright (C) 2021  National Technology & Engineering Solutions of Sandia, LLC
(NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S.
Government retains certain rights in this software.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from .abstract_message_process import AbstractMessageProcess
from ..utilities import GlobalCommands, QueueContainer
from ..hardware.abstract_hardware import HardwareMetadata
from ..environment.abstract_environment import EnvironmentMetadata
from typing import List
import netCDF4 as nc
import numpy as np


class StreamingProcess(AbstractMessageProcess):
    """Class containing the functionality to stream data to disk.

    This class will handle receiving data from the acquisition and saving it
    to a netCDF file."""

    def __init__(self, process_name: str, queue_container: QueueContainer):
        """Constructor for the StreamingProcess class

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
        self.map_command(GlobalCommands.INITIALIZE_STREAMING, self.initialize)
        self.map_command(GlobalCommands.STREAMING_DATA, self.write_data)
        self.map_command(GlobalCommands.FINALIZE_STREAMING, self.finalize)
        self.map_command(GlobalCommands.CREATE_NEW_STREAM, self.create_new_stream)
        self.netcdf_handle = None
        # Track the variable we are streaming data to
        self.stream_variable = "time_data"
        self.stream_dimension = "time_samples"
        self.stream_index = 0

    def initialize(self, data):
        """Creates a file with all metadata from the controller

        Creates a netCDF4 dataset and stores all the global data acquisition
        parameters as well as the parameters from each environment.

        Parameters
        ----------
        data : tuple
            Tuple containing a string filename, global DataAcquisitionParameters
            defining the controller settings, and a dictionary containing the
            environment names as keys and the environment metadata (inheriting
            from AbstractMetadata) as values for each environment.

        """
        filename: str
        hardware_metadata: HardwareMetadata
        environment_metadata_list: List[EnvironmentMetadata]
        filename, hardware_metadata, environment_metadata_list = data
        self.stream_variable = "time_data"
        self.stream_dimension = "time_samples"
        self.stream_index = 0
        self.netcdf_handle = nc.Dataset(filename, "w", format="NETCDF4", clobber=True)  # pylint: disable=no-member
        # Create dimensions
        self.netcdf_handle.createDimension("response_channels", len(hardware_metadata.channel_list))
        self.netcdf_handle.createDimension(
            "output_channels",
            len([channel for channel in hardware_metadata.channel_list if channel.feedback_device is not None]),
        )
        self.netcdf_handle.createDimension(self.stream_dimension, None)
        self.netcdf_handle.createDimension("num_environments", len(environment_metadata_list))
        # Create attributes
        self.netcdf_handle.file_version = "3.0.0"
        self.netcdf_handle.sample_rate = hardware_metadata.sample_rate
        self.netcdf_handle.time_per_write = hardware_metadata.samples_per_write / hardware_metadata.output_sample_rate
        self.netcdf_handle.time_per_read = hardware_metadata.samples_per_read / hardware_metadata.sample_rate
        self.netcdf_handle.hardware = hardware_metadata.hardware_type.value
        self.netcdf_handle.output_oversample = hardware_metadata.output_oversample
        for attr_name in hardware_metadata.extra_attr_list():
            value = getattr(hardware_metadata, attr_name)
            setattr(self.netcdf_handle, attr_name, value)
        # Create Variables
        self.netcdf_handle.createVariable(self.stream_variable, "f8", ("response_channels", self.stream_dimension))
        var = self.netcdf_handle.createVariable("environment_names", str, ("num_environments",))
        environment_booleans = []
        for i, metadata in enumerate(environment_metadata_list):
            var[i] = metadata.environment_name
            environment_booleans.append(metadata.map_channel_bools(hardware_metadata.channel_list))
        var = self.netcdf_handle.createVariable(
            "environment_active_channels",
            "i1",
            ("response_channels", "num_environments"),
        )
        var[...] = environment_booleans.astype("int8")
        # Create channel table variables
        labels = [
            ["node_number", str],
            ["node_direction", str],
            ["comment", str],
            ["serial_number", str],
            ["triax_dof", str],
            ["sensitivity", str],
            ["unit", str],
            ["make", str],
            ["model", str],
            ["expiration", str],
            ["physical_device", str],
            ["physical_channel", str],
            ["channel_type", str],
            ["minimum_value", str],
            ["maximum_value", str],
            ["coupling", str],
            ["excitation_source", str],
            ["excitation", str],
            ["feedback_device", str],
            ["feedback_channel", str],
            ["warning_level", str],
            ["abort_level", str],
        ]
        for label, netcdf_datatype in labels:
            var = self.netcdf_handle.createVariable("/channels/" + label, netcdf_datatype, ("response_channels",))
            channel_data = [getattr(channel, label) for channel in hardware_metadata.channel_list]
            if netcdf_datatype == "i1":
                channel_data = np.array([1 if val else 0 for val in channel_data])
            else:
                channel_data = ["" if val is None else val for val in channel_data]
            for i, cd in enumerate(channel_data):
                var[i] = cd
        # Now write all the environment data to the netCDF file
        for environment_metadata in environment_metadata_list:
            group_handle = self.netcdf_handle.createGroup(environment_metadata.environment_name)
            environment_metadata.store_to_netcdf(group_handle)

    def write_data(self, data):
        """Writes data to an initialized netCDF file

        Parameters
        ----------
        data : np.ndarray
            Data to be written to the netCDF file


        """
        if self.netcdf_handle is None:
            return
        test_data = data
        timesteps = slice(self.netcdf_handle.dimensions[self.stream_dimension].size, None, None)
        self.netcdf_handle.variables[self.stream_variable][:, timesteps] = test_data

    def create_new_stream(self, data):  # pylint: disable=unused-argument
        """Creates a new stream in the streaming file"""
        if self.netcdf_handle is None:
            return
        self.stream_index += 1
        self.stream_variable = f"time_data_{self.stream_index}"
        self.stream_dimension = f"time_samples_{self.stream_index}"
        self.netcdf_handle.createDimension(self.stream_dimension, None)
        self.netcdf_handle.createVariable(self.stream_variable, "f8", ("response_channels", self.stream_dimension))

    def finalize(self, data):  # pylint: disable=unused-argument
        """Closes the netCDF file when data writing is complete

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``
        """
        if self.netcdf_handle is not None:
            self.netcdf_handle.close()
            self.netcdf_handle = None

    def quit(self, data):
        """Stops the process.

        Parameters
        ----------
        data : Ignored
            This parameter is not used by the function but must be present
            due to the calling signature of functions called through the
            ``command_map``
        """
        self.finalize(None)
        return True


def streaming_process(queue_container: QueueContainer):
    """Function passed to multiprocessing as the streaming process

    This process creates the ``StreamingProcess`` object and calls the ``run``
    command.

    Parameters
    ----------
    queue_container : QueueContainer
        A container containing the queues used to communicate between
        controller processes

    """

    streaming_instance = StreamingProcess("Streaming", queue_container)

    streaming_instance.run()
