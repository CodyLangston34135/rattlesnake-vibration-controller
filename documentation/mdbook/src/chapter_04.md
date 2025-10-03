# Part II. Rattlesnake Hardware Devices

Designed for flexibility, Rattlesnake can be used with multiple hardware devices and even perform virtual control using a synthetic data acquisition system.  This Part will cover the hardware-specific implementation details that must be considered when running Rattlesnake with each hardware device.

Rattlesnake is designed so there is minimal differences in software workflow when using different hardware devices.  Nonetheless, there are some slight differences in how channels and devices must be specified, and these differences are primarily found on the `Data Acquisition Setup` tab in the Rattlesnake software.

The Chapters in this Part document the hardware devices that are able to be used by Rattlesnake, as well as the virtual devices that can be used to simulate control.  [Chapter 4](./chapter_04.md) describes the implementation and utilization of NI-DAQmx devices.  [Chapter 5](./chapter_05.md) describes the HBK LAN-XI hardware.  [Chapter 6](./chapter_06.md) and [Chapter 7](./chapter_07.md) describe the Data Physics Quattro and 900-series hardware devices, respectively.  [Chapter 8](./chapter_08.md), [Chapter 9](./chapter_09.md), and [Chapter 10](./chapter_10.md) describe virtual or synthetic hardware devices that are defined using state space matrices, eigensolution results stored in an exodus file, or a SDynPy System object, respectively.

If a user is interested in implementing a new hardware device, [Chapter 11](./chapter_11.md) describes some of the things to be aware of.  Implementation of new hardware devices will require a good amount of knowledge of the Rattlesnake architecture.

## Chapter 4. NI-DAQmx Devices

Rattlesnake is able to run National Instruments devices that utilize the NI-DAQmx programming interface.  See the [NI-DAQmx Documentation](https://www.ni.com/pdf/manuals/374768ae.html#MXSupport) for a list of supported devices for this programming interface.  Note that users must have the proper drivers installed in order to communicate with their devices, though users need not have LabView or other NI software installed.  See the instruction manual or online documentation for the specific device in use.

Drivers can be found [here](https://www.ni.com/en-us/support/downloads/drivers.html).

[Appendix B](./appendix_b.md) shows a complete example problem using a NI data acquisition system.

### Setting up the Channel Table for NI-DAQmx Device <!--Section 4.1-->

This section lists the channel table requirements specific to NI-DAQmx.

NI-DAQmx channels are identified by a device name and a channel name.  Device names vary depending on the type of device used.  For example, USB devices may simply be called `Dev#`, where `#` is a device number.  cDAQ devices might be called `cDAQ#Mod#` where the first `#` denotes the data acquisition system number and the second represents the module within the data acquisition system.  PXI/PXIe chassis devices will be similarly named `PXI#Slot#` where the first `#` is the chassis number and the second is the card number on the chassis.  In general, the names of NI-DAQmx devices that are attached to a given computer can be found using the National Instruments Measurement Automation Explorer (NI MAX).
        
Channel names for NI-DAQmx devices generally are called `ai` for analog input and `ao` for analog output.  A four acquisition channel, one output device might have acquisition channels `ai0`, `ai1`, `ai2`, and `ai3` and output channel `ao0`.  Again, see the Measurement Automation Explorer to determine the channels that exist on each device.
    
The channel type of a given channel determines what parameters are used and required for that channel.  Valid channel types are `Acceleration`, `Force`, or `Voltage`.
    
`Acceleration` channel types must have a sensitivity specified in mV/G in the channel table, as the only valid Engineering Unit for an acceleration channel is `G`.
    
`Force` channel types must also have a sensitivity specified.  Valid units for a force channel are pounds (specified by `lb`, `pound`, `pounds`, `lbf`, `lbs`, or `lbfs`, case insensitive) or newtons (specified by `n`, `newton`, `newtons`, or `ns`, case insensitive).
    
`Voltage` channel types need not have a sensitivity or unit specified, as they will always be reported in volts.  A best practice is to fill out these columns anyways with the correct values `V` for engineering unit and sensitivity of 1000 mV/V.  **Note that specifying a different sensitivity for a voltage channel WILL NOT result in the voltage being scaled.  The NI-DAQmx implementation does not have the ability to scale voltage channels.  Users should specify 1000 mV/V as the sensitivity**.  Note that if a sensitivity is not specified, the Warning and Abort limits may not be correctly computed, as they rely on sensitivity information to convert between a measured raw voltage and the correct sensitivity unit.
    
The `Physical Device` and `Physical Channel` (as well as `Feedback Device` and `Feedback Channel` for output channels) should correspond to the device and channel names in the Measurement Automation Explorer.  For example, channel `ai3` on device `PXI1Slot4` would have `Physical Device` set to `PXI1Slot4` and `Physical Channel` set to `ai3`.
   
Maximum and Minimum Values should be specified based on the levels expected for the given test, taking into account that they are not outside the range acceptable for the device.
    
The Coupling column in the channel table is not currently used by the NI-DAQmx system, rather the coupling is specified automatically by the channel type (Acceleration and Force are AC coupled, Voltage is DC coupled).
    
Excitation Source should be set to either `Internal` or `None`.  If set to `Internal`, the device will generate the ICP/CCLD/IEPE signal conditioning required by the sensor.  If set to `None`, no signal conditioning will be provided by the hardware device.
    
Current Excitation should typically be set to 0.004 A (4 mA) unless the sensor requires a different current to be provided.  The Current Excitation value is only used if the Excitation Source is set to `Internal`.  If set to `None`, no current is generated.

### Hardward Parameters <!--Section 4.2-->

Besides the sample rate, no additional hardware-specific parameters must be specified for NI hardware.  Figure 4.1 shows the parameters for NI-DAQmx hardware devices.
    
**WARNING:** Some NI-DAQmx devices have discrete allowable sample rates, while others can have any sample rate that is desired up to some maximum value.  Please refer to the documentation of your device to determine which sample rates are allowable for your device.  The NI-DAQmx drivers, when provided an incompatible sample rate, often simply select the closest available rate or the next highest rate, which can result in data being acquired at a rate that is not equivalent to the rate selected in the software.  Additionally, further issues can occur when the sample rate of an output device is not compatible with the sample rate of an acquisition device, meaning the output is being delivered at a different rate than it is being measured, resulting in inconsistent data.  **Currently Rattlesnake does not do very rigorous checks to determine if the specified sample rate is allowable, so it falls on the user to ensure that it is!**
    
![nidaqmx_data_acquisition_parameters](figures/nidaqmx_data_acquisition_parameters.png)

**Figure 4-1. NI-DAQmx Data Acquisition Parameters**

### Implmentation Details <!--Section 4.3-->
    
This section contains details on the NI-DAQmx implementation in Rattlesnake, which may be helpful for users when diagnosing issues that arise in the controller.
    
#### NI-DAQmx Tasks <!--Subsection 4.3.1-->

NI-DAQmx hardware interfaces are defined within Tasks.  The acquisition exists within one task.  The output exists within one or more more separate tasks with one task per type of output card.  This multi-task output enables, for example, two different types of output cards to be used in the same chassis.  
    
#### Sampling Parameters <!--Subsection 4.3.2-->

Both acquisition and output operate in continuous mode.  This means that if the controller cannot output signals fast enough and the hardware runs out of samples to generate, the controller will throw an error and stop abruptly.  A buffer size of three times the number of samples per write is specified in the source code which gives a cushion against the controller falling behind.  The output will accept a set of samples into the output buffer whenever there is less than two writes worth of samples remaining in the buffer.  The buffer size is computed by subtracting the total samples generated by the output task from the current write position in the output tasks buffer.

#### Starting the Hardware <!--Subsection 4.3.3-->

When a measurement is started, the output is set up and started first.  The output task uses a start trigger from an analog input task (`/<physical_device_name>/ai/StartTrigger`) as its trigger, so once it starts, it effectively waits for the acquisition to be set up and started.  To determine which start trigger is used, it checks if the device is a cDAQ device.  If the device is a cDAQ device, it uses the start trigger from the cDAQ chassis.  If it is not a cDAQ device, it utilizes the start trigger from the first analog input channel.  This configuration has been tested with both cDAQ and PXI devices.  When the acquisition is started, its start trigger will trigger the output to start outputting signals simultaneously.  Because the system tries to use the analog input start trigger for all outputs, users may have trouble daisy-chaining multiple chassis together if the trigger signal is not able to be passed between all of the chassis.
