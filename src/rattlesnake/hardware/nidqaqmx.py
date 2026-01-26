from .abstract_hardware import HardwareMetadata, HardwareAcquisition, HardwareOutput
from .hardware_utilities import Channel, HardwareType
import nidaqmx as ni
import nidaqmx.constants as nic
import nidaqmx.stream_readers as ni_read
import nidaqmx.stream_writers as ni_write
import numpy as np
from enum import Enum
from typing import List
import time

BUFFER_SIZE_FACTOR = 3


class TaskTrigger(Enum):
    INTERNAL = 0
    EXTERNAL = 1
    TRIGGERTASK = 2
    NONE = 3


class NIDAQmxMetadata:
    def __init__(self):
        super().__init__()
        self.hardware_type = HardwareType.NI_DAQmx
        self.task_trigger = TaskTrigger.INTERNAL
        self.output_trigger_generator = 0

    def validate(self):
        if len(self.channel_list) != len(set(self.channel_list)):
            raise ValueError("Duplicate channels found in channel_list")

        return True


class NIDAQmxAcquisition(HardwareAcquisition):
    """Class defining the interface between the controller and NI hardware

    This class defines the interfaces between the controller and National
    Instruments Hardware that runs the NI-DAQmx library.  It is run by the
    Acquisition process, and must define how to get data from the test
    hardware into the controller."""

    def __init__(self):
        """
        Constructs the NIDAQmx Acquisition class and specifies values to null.
        """
        self.tasks = None
        self.channel_task_map = None
        self.read_datas = None
        self.read_data = None
        self.readers = None
        self.acquisition_delay = None
        self.read_triggers = None
        self.task_trigger = None
        self.output_trigger_generator = None
        self.has_printed_read_statement = False
        self.trigger_output_task = None
        self.metadata = None

    def set_up_data_acquisition_parameters_and_channels(self, metadata: NIDAQmxMetadata):
        """
        Initialize the hardware and set up channels and sampling properties

        The function must create channels on the hardware corresponding to
        the channels in the test.  It must also set the sampling rates.

        Parameters
        ----------
        metadata : NIDAQmxMetadata :
            A container containing the data acquisition parameters for the
            controller set by the user.
        channel_data : List[Channel] :
            A list of ``Channel`` objects defining the channels in the test

        Returns
        -------
        None.

        """
        self.create_response_channels(metadata.channel_list)
        self.set_parameters(metadata)
        self.metadata = metadata

    def create_response_channels(self, channel_data: List[Channel]):
        """Method to set up response channels

        This function takes channels from the supplied list of channels and
        creates analog inputs on the hardware.

        Parameters
        ----------
        channel_data : List[Channel] :
            A list of ``Channel`` objects defining the channels in the test

        """
        physical_devices = list(set(channel.physical_device for channel in channel_data))
        device_tasks = {}
        extra_task_index = 1
        task_names = set([])
        for device in physical_devices:
            if self.task_trigger == 0:
                chassis_number = "all"
            else:
                d = ni.system.device.Device(device)
                try:
                    chassis_number = f"P{d.pxi_chassis_num}"
                except ni.DaqError:
                    try:
                        chassis_number = f"C{d.compact_daq_chassis_device.name}"
                    except ni.DaqError:
                        chassis_number = f"E{extra_task_index}"
                        extra_task_index += 1
            device_tasks[device] = chassis_number
            task_names.add(chassis_number)
        task_names = list(task_names)
        print(f"Input Tasks: {task_names}")
        print("  P: PXI, C: CDAQ, E: Other,  All: All devices on one task")
        self.tasks = [ni.Task() for name in task_names]
        self.read_triggers = [None for name in task_names]
        self.channel_task_map = [[] for name in task_names]
        index = 0
        for channel in channel_data:
            task_name = device_tasks[channel.physical_device]
            task_index = task_names.index(task_name)
            self.channel_task_map[task_index].append(index)
            if self.task_trigger != 0:
                if self.read_triggers[task_index] is None:
                    try:
                        chassis_device = ni.system.device.Device(channel.physical_device).compact_daq_chassis_device
                        pfi_terminals = [trigger for trigger in chassis_device.terminals if "/PFI0" in trigger]
                        print(f"PFI Terminals on CDAQ Device:\n{pfi_terminals}")
                        self.read_triggers[task_index] = pfi_terminals[0]
                    except ni.DaqError:
                        self.read_triggers[task_index] = "/" + channel.physical_device.strip() + "/PFI0"
            index += 1
            self._create_channel(channel, task_index)
        print(f"Input Mapping: {self.channel_task_map}")

    def set_parameters(self, metadata: NIDAQmxMetadata):
        """Method to set up sampling rate and other test parameters

        This function sets the clock configuration on the NIDAQmx hardware.

        Parameters
        ----------
        metadata : NIDAQmxMetadata :
            A container containing the data acquisition parameters for the
            controller set by the user.

        """
        self.task_trigger = metadata.task_trigger
        self.output_trigger_generator = metadata.output_trigger_generator
        self.readers = []
        self.read_datas = []
        self.acquisition_delay = BUFFER_SIZE_FACTOR * metadata.samples_per_write
        self.read_data = np.zeros((len(metadata.channel_list), metadata.samples_per_read))
        for i, (task, trigger) in enumerate(zip(self.tasks, self.read_triggers)):
            task.timing.cfg_samp_clk_timing(
                metadata.sample_rate,
                sample_mode=nic.AcquisitionType.CONTINUOUS,
                samps_per_chan=metadata.samples_per_read,
            )
            task.in_stream.wait_mode = nic.WaitMode.POLL
            if trigger is not None:
                task.triggers.start_trigger.dig_edge_src = trigger
                task.triggers.start_trigger.dig_edge_edge = ni.constants.Edge.RISING
                task.triggers.start_trigger.trig_type = ni.constants.TriggerType.DIGITAL_EDGE
                print(f"Acquisition Task {i} Trigger {trigger}")
            self.readers.append(ni_read.AnalogMultiChannelReader(task.in_stream))
            self.read_datas.append(np.zeros((len(task.ai_channels), metadata.samples_per_read)))

            print(f"Acquisition Task {i} Actual Sample Rate: {task.timing.samp_clk_rate}")

    def start(self):
        """Start acquiring data"""
        for task in self.tasks:
            task.start()
        if self.task_trigger != 0:
            print("Input is Running, waiting for PFI Trigger")
        self.has_printed_read_statement = False
        # Now we're going to output the signal
        if self.task_trigger == 2:
            print("Creating Triggering Task")
            self.trigger_output_task = ni.Task()
            self.trigger_output_task.ao_channels.add_ao_voltage_chan(self.output_trigger_generator, min_val=-3.5, max_val=3.5)
            self.trigger_output_task.timing.cfg_samp_clk_timing(
                self.metadata.sample_rate,
                sample_mode=nic.AcquisitionType.CONTINUOUS,
                samps_per_chan=self.metadata.samples_per_write,
            )
            self.trigger_output_task.out_stream.regen_mode = nic.RegenerationMode.ALLOW_REGENERATION
            writer = ni_write.AnalogMultiChannelWriter(self.trigger_output_task.out_stream, auto_start=False)
            writer.write_many_sample(3 * np.ones((1, 100)))
            print("Starting Triggering Task")
            self.trigger_output_task.start()
            writer.write_many_sample(np.zeros((1, 100)))

    def get_acquisition_delay(self) -> int:
        """
        Get the number of samples between output and acquisition.

        This function returns the number of samples that need to be read to
        ensure that the last output is read by the acquisition.  If there is
        buffering in the output, this delay should be adjusted accordingly.

        Returns
        -------
        int
            Number of samples between when a dataset is written to the output
            and when it has finished playing.

        """
        return self.acquisition_delay

    def read(self):
        """Method to read a frame of data from the controller

        Returns
        -------
        read_data :
            2D Data read from the controller with shape ``n_channels`` x
            ``n_samples``
        """
        for reader, read_data, channel_mapping in zip(self.readers, self.read_datas, self.channel_task_map):
            reader.read_many_sample(
                read_data,
                number_of_samples_per_channel=read_data.shape[-1],
                timeout=nic.WAIT_INFINITELY,
            )
            self.read_data[channel_mapping] = read_data
        if not self.has_printed_read_statement:
            print("Input Read Data")
            self.has_printed_read_statement = True
        return self.read_data

    def read_remaining(self):
        """Method to read the rest of the data on the acquisition

        Returns
        -------
        read_data :
            2D Data read from the controller with shape ``n_channels`` x
            ``n_samples``
        """
        remaining_data = []
        for task, reader, channel_mapping in zip(self.tasks, self.readers, self.channel_task_map):
            read_data = np.zeros((len(task.ai_channels), task.in_stream.avail_samp_per_chan))
            reader.read_many_sample(
                read_data,
                number_of_samples_per_channel=read_data.shape[-1],
                timeout=nic.WAIT_INFINITELY,
            )
            remaining_data.append(read_data)
        max_samples = max([data.shape[-1] for data in remaining_data])
        read_data = np.zeros((self.read_data.shape[0], max_samples))
        for data, channel_mapping in zip(remaining_data, self.channel_task_map):
            read_data[channel_mapping, : data.shape[-1]] = data
        if not self.has_printed_read_statement:
            print("Input Read Data")
            self.has_printed_read_statement = True
        return read_data

    def stop(self):
        """Method to stop the acquisition"""
        print("Stopping Input Tasks")
        for task in self.tasks:
            task.stop()
        print("Input Tasks Stopped")
        if self.task_trigger == 2:
            print("Stopping Triggering Task")
            self.trigger_output_task.stop()
            print("Closing Triggering Task")
            self.trigger_output_task.close()

    def close(self):
        """Method to close down the hardware"""
        print("Closing Input Tasks")
        if self.tasks is not None:
            for task in self.tasks:
                task.close()
        print("Input Tasks Closed")

    def _create_channel(self, channel_data: Channel, task_index: int):
        """Helper function to construct a channel on the hardware.

        Parameters
        ----------
        channel_data: Channel :
            Channel object specifying the channel parameters.
        task_index: int :
            Index of the task to which the channel should be created

        Returns
        -------
            channel :
                A reference to the NIDAQmx channel created by the function
        """
        physical_channel = channel_data.physical_device + "/" + channel_data.physical_channel
        # Parse the channel structure to make sure datatypes are correct
        # Sensitivity
        try:
            sensitivity = float(channel_data.sensitivity)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{channel_data.sensitivity} not a valid sensitivity") from e
        # Minimum Value
        try:
            minimum_value = float(channel_data.minimum_value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{channel_data.minimum_value} not a valid minimum value") from e
        # Maximum Value
        try:
            maximum_value = float(channel_data.maximum_value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{channel_data.maximum_value} not a valid maximum value") from e
        # Channel Type and Units
        if channel_data.channel_type.lower() in [
            "accelerometer",
            "acceleration",
            "accel",
        ]:
            channel_type = nic.UsageTypeAI.ACCELERATION_ACCELEROMETER_CURRENT_INPUT
            if channel_data.unit.lower() in ["g", "gs"]:
                unit = nic.AccelUnits.G
            else:
                raise ValueError(f"Accelerometer units must be in G, not {channel_data.unit}")
        elif channel_data.channel_type.lower() == "force":
            channel_type = nic.UsageTypeAI.FORCE_IEPE_SENSOR
            if channel_data.unit.lower() in [
                "lb",
                "pound",
                "pounds",
                "lbf",
                "lbs",
                "lbfs",
            ]:
                unit = nic.ForceUnits.POUNDS
            elif channel_data.unit.lower() in ["n", "newton", "newtons", "ns"]:
                unit = nic.ForceUnits.NEWTONS
            else:
                raise ValueError(f"Unrecognized Force Unit {channel_data.unit}")
        elif channel_data.channel_type.lower() in ["voltage", "volt"]:
            channel_type = nic.UsageTypeAI.VOLTAGE
            unit = None
        else:
            raise ValueError(
                f"{channel_type} not a valid channel type.  " 'Must be one of ["acceleration","accelerometer","accel","force","voltage","volt"]'
            )
        # Excitation Source
        if channel_data.excitation_source.lower() == "internal":
            excitation_source = nic.ExcitationSource.INTERNAL
            try:
                excitation = float(channel_data.excitation)
            except (TypeError, ValueError) as e:
                raise ValueError(f"{channel_data.excitation} not a valid excitation") from e
        elif channel_data.excitation_source.lower() == "none":
            excitation_source = nic.ExcitationSource.NONE
            excitation = 0
        else:
            raise ValueError(f"{channel_data.excitation_source} not a valid excitation source.  " 'Must be one of ["internal","none"]')
        # Now go and create the channel
        if channel_type != nic.UsageTypeAI.VOLTAGE:
            min_val = minimum_value * 1000 / sensitivity
            max_val = maximum_value * 1000 / sensitivity
        else:
            min_val = minimum_value
            max_val = maximum_value
        if channel_type == nic.UsageTypeAI.ACCELERATION_ACCELEROMETER_CURRENT_INPUT:
            try:
                channel = self.tasks[task_index].ai_channels.add_ai_accel_chan(
                    physical_channel,
                    min_val=min_val,
                    max_val=max_val,
                    units=unit,
                    sensitivity=sensitivity,
                    sensitivity_units=nic.AccelSensitivityUnits.M_VOLTS_PER_G,
                    current_excit_source=excitation_source,
                    current_excit_val=excitation,
                )
            except AttributeError:
                channel = self.tasks[task_index].ai_channels.add_ai_accel_chan(
                    physical_channel,
                    min_val=min_val,
                    max_val=max_val,
                    units=unit,
                    sensitivity=sensitivity,
                    sensitivity_units=nic.AccelSensitivityUnits.MILLIVOLTS_PER_G,
                    current_excit_source=excitation_source,
                    current_excit_val=excitation,
                )
        elif channel_type == nic.UsageTypeAI.FORCE_IEPE_SENSOR:
            try:
                channel = self.tasks[task_index].ai_channels.add_ai_force_iepe_chan(
                    physical_channel,
                    min_val=min_val,
                    max_val=max_val,
                    units=unit,
                    sensitivity=sensitivity,
                    sensitivity_units=(
                        nic.ForceIEPESensorSensitivityUnits.M_VOLTS_PER_NEWTON
                        if unit == nic.ForceUnits.NEWTONS
                        else nic.ForceIEPESensorSensitivityUnits.M_VOLTS_PER_POUND
                    ),
                    current_excit_source=excitation_source,
                    current_excit_val=excitation,
                )
            except AttributeError:
                channel = self.tasks[task_index].ai_channels.add_ai_force_iepe_chan(
                    physical_channel,
                    min_val=min_val,
                    max_val=max_val,
                    units=unit,
                    sensitivity=sensitivity,
                    sensitivity_units=(
                        nic.ForceIEPESensorSensitivityUnits.MILLIVOLTS_PER_NEWTON
                        if unit == nic.ForceUnits.NEWTONS
                        else nic.ForceIEPESensorSensitivityUnits.MILLIVOLTS_PER_POUND
                    ),
                    current_excit_source=excitation_source,
                    current_excit_val=excitation,
                )
        elif channel_type == nic.UsageTypeAI.VOLTAGE:
            channel = self.tasks[task_index].ai_channels.add_ai_voltage_chan(
                physical_channel,
                min_val=min_val,
                max_val=max_val,
                units=nic.VoltageUnits.VOLTS,
            )
        else:
            raise ValueError(f"Channel Type Not Implemented: {channel_type}")
        return channel


class NIDAQmxOutput(HardwareOutput):
    """Class defining the interface between the controller and NI hardware

    This class defines the interfaces between the controller and National
    Instruments Hardware that runs the NI-DAQmx library.  It is run by the
    Output process, and must define how to get data from the controller to the
    output hardware."""

    def __init__(self):
        """
        Constructs the NIDAQmx Output class and initializes values to null.
        """
        self.tasks = None
        self.channel_task_map = None
        self.writers = None
        self.write_trigger = None
        self.signal_samples = None
        self.sample_rate = None
        self.buffer_size_factor = BUFFER_SIZE_FACTOR

    def set_up_data_output_parameters_and_channels(self, metadata: HardwareMetadata):
        """
        Initialize the hardware and set up sources and sampling properties

        The function must create channels on the hardware corresponding to
        the sources in the test.  It must also set the sampling rates.

        Parameters
        ----------
        test_data : DataAcquisitionParameters :
            A container containing the data acquisition parameters for the
            controller set by the user.
        channel_data : List[Channel] :
            A list of ``Channel`` objects defining the channels in the test

        Returns
        -------
        None.

        """
        self.create_sources(metadata.channel_list)
        self.set_parameters(metadata)

    def create_sources(self, channel_data: List[Channel]):
        """Method to set up excitation sources

        This function takes channels from the supplied list of channels and
        creates analog outputs on the hardware.

        Parameters
        ----------
        channel_data : List[Channel] :
            A list of ``Channel`` objects defining the channels in the test
        """
        # Get the physical devices
        physical_devices = list(
            set(
                [
                    ni.system.device.Device(channel.feedback_device).product_type
                    for channel in channel_data
                    if not (channel.feedback_device is None) and not (channel.feedback_device.strip() == "")
                ]
            )
        )
        # Check if it's a CDAQ device
        try:
            devices = [
                ni.system.device.Device(channel.feedback_device)
                for channel in channel_data
                if not (channel.feedback_device is None) and not (channel.feedback_device.strip() == "")
            ]
            if len(devices) == 0:
                self.write_trigger = None  # No output device
            else:
                chassis_device = devices[0].compact_daq_chassis_device
                self.write_trigger = [trigger for trigger in chassis_device.terminals if "ai/StartTrigger" in trigger][0]
        except ni.DaqError:
            self.write_trigger = "/" + channel_data[0].physical_device + "/ai/StartTrigger"
        print("Output Devices: {:}".format(physical_devices))
        self.tasks = [ni.Task() for device in physical_devices]
        index = 0
        self.channel_task_map = [[] for device in physical_devices]
        for channel in channel_data:
            if not (channel.feedback_device is None) and not (channel.feedback_device.strip() == ""):
                device_index = physical_devices.index(ni.system.device.Device(channel.feedback_device).product_type)
                self.channel_task_map[device_index].append(index)
                index += 1
                self._create_channel(channel, device_index)
        print("Output Mapping: {:}".format(self.channel_task_map))

    def set_parameters(self, metadata: HardwareMetadata):
        """Method to set up sampling rate and other test parameters

        This function sets the clock configuration on the NIDAQmx hardware.

        Parameters
        ----------
        test_data : DataAcquisitionParameters :
            A container containing the data acquisition parameters for the
            controller set by the user.
        """
        self.signal_samples = metadata.samples_per_write
        self.sample_rate = metadata.sample_rate
        self.writers = []
        for task in self.tasks:
            task.timing.cfg_samp_clk_timing(
                metadata.sample_rate, sample_mode=nic.AcquisitionType.CONTINUOUS, samps_per_chan=metadata.samples_per_write
            )
            task.out_stream.regen_mode = nic.RegenerationMode.DONT_ALLOW_REGENERATION
            # task.out_stream.relative_to = nic.WriteRelativeTo.CURRENT_WRITE_POSITION
            task.triggers.start_trigger.dig_edge_src = self.write_trigger
            task.triggers.start_trigger.dig_edge_edge = ni.constants.Edge.RISING
            task.triggers.start_trigger.trig_type = ni.constants.TriggerType.DIGITAL_EDGE
            task.out_stream.output_buf_size = self.buffer_size_factor * metadata.samples_per_write
            self.writers.append(ni_write.AnalogMultiChannelWriter(task.out_stream, auto_start=False))
            print("Actual Output Sample Rate: {:}".format(task.timing.samp_clk_rate))

    def start(self):
        """Method to start acquiring data"""
        for task in self.tasks:
            task.start()

    def write(self, data):
        """Method to write a frame of data

        Parameters
        ----------
        data : np.ndarray
            2D Data to be written to the controller with shape ``n_sources`` x
            ``n_samples``

        """
        for i, writer in enumerate(self.writers):
            writer.write_many_sample(data[self.channel_task_map[i]])

    def stop(self):
        """Method to stop the output"""
        # Need to output everything in the buffer and then some zeros and we'll
        # shut down during the zeros portion
        for i, writer in enumerate(self.writers):
            writer.write_many_sample(np.zeros((len(self.channel_task_map[i]), self.signal_samples)))
        # Now figure out how many samples are remaining
        samples_remaining = (
            self.tasks[0].out_stream.curr_write_pos - self.tasks[0].out_stream.total_samp_per_chan_generated - self.signal_samples
        )  # Subtract off the zeros
        time_remaining = samples_remaining / self.sample_rate
        time.sleep(time_remaining)
        for task in self.tasks:
            task.stop()

    def close(self):
        """Method to close down the hardware"""
        if not self.tasks is None:
            for task in self.tasks:
                task.close()

    def ready_for_new_output(self):
        """Returns true if the system is ready for new outputs

        Returns
        -------
        bool :
            True if the hardware is accepting the next data to write."""
        return (
            self.tasks[0].out_stream.curr_write_pos - self.tasks[0].out_stream.total_samp_per_chan_generated
            < (self.buffer_size_factor - 1) * self.signal_samples
        )

    def _create_channel(self, channel_data: Channel, device_index):
        """
        Helper function to construct a channel on the hardware.

        Parameters
        ----------
        channel_data: Channel :
            Channel object specifying the channel parameters.

        Returns
        -------
            channel :
                A reference to the NIDAQmx channel created by the function
        """
        # Minimum Value
        try:
            minimum_value = float(channel_data.minimum_value)
        except (TypeError, ValueError):
            raise ValueError("{:} not a valid minimum value".format(channel_data.minimum_value))
        # Maximum Value
        try:
            maximum_value = float(channel_data.maximum_value)
        except (TypeError, ValueError):
            raise ValueError("{:} not a valid maximum value".format(channel_data.maximum_value))
        physical_channel = channel_data.feedback_device + "/" + channel_data.feedback_channel
        channel = self.tasks[device_index].ao_channels.add_ao_voltage_chan(physical_channel, min_val=minimum_value, max_val=maximum_value)
        return channel
