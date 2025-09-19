## 3. Using Rattlesnake

This chapter will describe how to use Rattlesnake through its graphical user interface (GUI).  Rattlesnake is capable of running several different types of control, therefore the GUI may look different for different tests.  In general, the GUI consists of a tabbed interface across the top of the main window, and users must complete each tab before proceeding to the next.  The tabs that exist in a given test will depend on which control type is being run.  For example, in a combined environments test (TODO: see Section \ref{sec:rattlesnake_environments_combining_environments}) such as the one shown in Figure 3-1, there is a `Test Profile` tab that allows the user to define a testing timeline.  Additionally, environments such as the MIMO Random Vibration environment (TODO: see Section \ref{sec:rattlesnake_environments_mimo_random}) require a system identification phase where the controller identifies relationships between the output signals and the control degrees of freedom.  Therefore, tests using the MIMO Random Vibration environment will also have a `System Identification` and `Test Predictions` tab.  Figure 3-2, on the other hand, shows the GUI for a test that only utilizes the Time History environment (TODO: see Section \ref{sec:rattlesnake_environments_time_generator}) so these optional tabs are not displayed.

![Rattlesnake_Main_GUI_Combined_Environments](figures/Rattlesnake_Main_GUI_Combined_Environments.png)

**Figure 3-1. Rattlesnake GUI tabs when running a combined environments test with an environment that requires a system identification.**

Users of Rattlesnake must be aware that depending on their test configuration, their GUI may not appear identical to images shown in this User's Manual.  Additionally, users should be aware that the GUI library used by this software will inherit stylistic features from the operating system.  There may therefore be cosmetic differences between the images of the GUI shown in this document and the GUI seen by the user.  All images in this document were created using Microsoft Windows 10 or Windows 11 operating systems, so users with Mac or Linux operating systems will note a difference in GUI appearance.

Note that the Rattlesnake enforces an order to operations when defining a particular test by enabling and disabling tabs in the GUI.  Initially, only the first tab will be enabled.  As the users complete each tab, the next tab will become available.  In Figures 3-1 and 3-2, it can be seen that only the initial tab is enabled, and subsequent tabs are disabled.

![Rattlesnake_Main_GUI_Time_Generation](figures/Rattlesnake_Main_GUI_Time_Generation.png)

**Figure 3-2. Rattlesnake GUI tabs when running a single environment with no system identification phase.**

### Environment Selection

When Rattlesnake is opened, the first GUI window that the user will see allows the user to select the environment that they will run (Figure 3-3.).  Users can select a single environment, or alternatively select a combined environments test (TODO: see Section \ref{sec:rattlesnake_environments_combining_environments}).  The selection made in this dialog box will determine which tabs are set up in the main GUI.

![environment_selection](figures/environment_selection.png)

**Figure 3-3. Initial Rattlesnake dialog to select the type of control that will be run.**

### Global Data Acquisition Settings

The `Data Acquisition Setup` tab of the Rattlesnake GUI specifies the global test parameters that the controller will use.  Parameters are determined to be global when they affect all environments or the controller itself.  The three main sections of this portion of the interface are the Channel Table, Environment Table, and Global Data Acquisition Parameters.  Figure 3-4. shows this.

![data_acquisition_setup](figures/data_acquisition_setup.png)

**Figure 3-4. Data Acqisition Setup tab in the Rattlesnake Controller where the Channel Table, Environment Table, and Data Acquisition Parameters are specified.**

#### Channel Table

The channel table specifies how the instrument channels in a given test are connected to the data acquisition hardware, as well as how the data read from those channels are used by the software.

In general, for a given test there will be a set of excitation devices that use the output signals from Rattlesnake as well as instrumentation to record the test article's responses to those exciters.  Rattlesnake requires each instrument (or each channel on each instrument for multi-axial instruments) as well as each excitation device to have a row in the channel table.  This is perhaps contrary to other control software where only the response channels need to be set up in the channel table.  However, to maintain the flexibility to run multiple types of hardware devices, some of which having limitations to their triggering capabilities, Rattlesnake must read in the signal from its output directly in order to be able to synchronize its outputs and the responses to those outputs.  Therefore, for all Rattlesnake test setups, the output signal should be split using a tee to the exciter and the corresponding input channel.  Because of this requirement, one should keep in mind that the number of acquisition channels required on the hardware device for a given test is actually the number of responses plus the number of outputs.  Figure 3-5 shows a schematic of a four acquisition channel, two output channel LAN-XI module set up for use with Rattlesnake.

![lanxi_source_tee_labelled](figures/lanxi_source_tee_labelled.png)

**Figure 3-5. Output channels teed to acquisition channels so they can be read by the controller.**

The required data input into the channel table varies with the physical or virtual hardware used for the test.  For device-specific channel table requirements, see the appropriate section of [Part II](./chapter_04.md).  In general, the entries to the channel table are as follows:

* **Node Number** Determines the instrumentation position on the test article.  While not used directly by the controller except to label plots, it is important for book-keeping and test documentation.  The node number will generally correspond to a node in a test geometry or FEM.
* **Node Direction** Determines the instrumentation direction on the test article at the position specified by the Node Number.  Again, this is not used directly by the controller except to label plots, but it is important for book-keeping.  The Node Direction will generally correspond to the node's local coordinate system if one exists in the test geometry.
* **Comment** Provides space for additional information about a channel that may not be captured by the Node Number and Node Direction.
* **Serial Number** The serial number of the instrument used for the given channel.  This field is not used by the controller but will be stored with the test data and is important for data traceability to know which instruments were used to measure which channels.
* **Triax DoF** The degree of freedom on a given instrument corresponding to the given channel.  This is primarily used to distinguish between the three axes of a triaxial accelerometer, but has the potential to be used for other multi-axis instrumentation types such as strain gauge rosettes.
* **Sensitivity** The sensitivity of the instrument in millivolts per Engineering Unit.  This is used to transform the acquired data from a raw voltage to a engineering quantity such as acceleration or force.
* **Engineering Unit** The unit in which the measured signal for the given instrument will be reported.  Certain hardware will limit the units that can be specified: see [Part II](./chapter_04.md) for more information.
* **Make** The name of the instrument's manufacturer, used for data traceability.
* **Model** The product name or model number of the instrument, used for data traceability.
* **Expiration** The expiration date of the instrument's calibration certificate.  Note that this is only for data traceability; no checking of this date with the current data to ensure a valid calibration is performed by the software.
* **Physical Device** The reference to a physical device attached to the computer.  The entries in this field will be specific to the acquisition hardware being used for a given test.  For virtual control, this column must be filled to specify that a given channel is active.  See [Part II](./chapter_04.md) for more information.
* **Physical Channel** The reference to a channel on a physical device attached to the computer.  The entries in this column will be specific to the acquisition hardware being used for a given test.  See [Part II](./chapter_04.md) for more information.
* **Channel Type** The type of the channel being used for a given test, such as Acceleration, Force, or Voltage.  The allowable entries in this column will be specific to the acquisition hardware being used for a given test.  See [Part II](./chapter_04.md) for more information.
* **Minimum Value (V)** The minimum voltage that the data acquisition system can handle during a test.  This is used to set the range on the data acquisition system.  For hardware devices with symmetric ranges (e.g. $\pm$10V), this column can be left blank.
* **Maximum Value (V)]**  The maximum voltage that the data acquisition system can handle during a test.  This is used to set the range on the data acquisition system.  For hardware devices with symmetric ranges (e.g. $\pm$10V), this column is used to set the maximum and minimum voltage values.
* **Coupling** The coupling used by the data acquisition system.  This may include filtering in addition to AC/DC coupling, which is dependent on the hardware being used for a given test.  See [Part II](./chapter_04.md) for more information.
* **Excitation Source** Used to specify the signal conditioning that is required by the instrument.  This column is generally where the constant current line drive (CCLD)/integrated electronics piezoelectric (IEPE)/integrated circuit piezoelectric (ICP) is specified for a given hardware device.  See [Part II](./chapter_04.md) for more information.
* **Current Excitation (A)** Used to specify the excitation current sent to the device for signal conditioning.  Depending on whether the device has a fixed or variable excitation current, this field may be left empty.  This can also be left empty if no signal conditioning is provided by the data acquisition system.  See [Part II](./chapter_04.md) for more information.
* **Feedback Device** For output channels, this is the reference to the output or excitation device that is being fed back into the current channel's Physical device.  If the current channel is not an output channel, it should be left empty.  A populated Feedback Device column tells the controller that the given channel is an output channel.
* **Feedback Channel** For output channels, this is the reference to the output channel on the output or excitation device that is being fed back into the current channel's Physical Device.  As an example using generic device and channel names, if `Channel 2` on `Generator 1` is teed off to `Channel 3` on `Acquisition Card 2`, the corresponding row in the channel table would have `Acquisition Card 2` specified as the Physical Device, `Channel 3` specified as the Physical Channel, `Generator 1` specified as the `Feedback Device` and `Channel 2` specified as the feedback channel.
* **Warning Level** A warning level can be implemented for each channel.  The warning level is specified in the same units as the Engineering Unit column.  When a channel hits the warning limit, it will be flagged as Yellow in the Channel Monitor (TODO: see Section \ref{sec:channel_monitor}).  The warning level can be left blank if no warning is desired.
* **Abort Level** An abort level can be implemented for each channel.  The abort level is specified in the same units as the Engineering Unit column.  When a channel hits the abort limit, it will be flagged as Red in the Channel Monitor (TODO: see Section \ref{sec:channel_monitor}).  The controller will also shut down if an abort level is reached.  The abort level can be left blank if no abort is desired.

To limit the tediousness of inputting channel table information into the GUI by hand, the channel table can be loaded from an Excel spreadsheet or Comma-separated-value file.  A channel table can be loaded by clicking the `Load Channel Table` button under the channel table, which will bring up a file selection dialog, enabling the user to select a file to load.  For convenience, a template Excel spreadsheet is attached to this PDF: (TODO) \attachfile{attachments/channel_table_template.xlsx}.  A template Excel file can also be generated by creating a test in Rattlesnake and saving the empty channel table by clicking the `Save Channel Table` button under the channel table.  If a channel table is filled out in Rattlesnake's GUI, its contents will be saved to the file as well.

A complete test can be loaded by clicking the `Load Test from File` button.  See Section (TODO) \ref{sec:load_rattlesnake_test} for more details.

#### Environment Table

For combined environments tests, an environment table is also provided to the right of the standard Channel Table.  This table specifies which channels are used by which environments.  A channel can be used for multiple environments, a single environment, or no environments.  Channels used by no environments will still be measured and streamed to disk, but will not be sent to any environment for use in the respective control approaches.  The environment table is also used to specify which excitation devices are used by which environment.

For single environment tests, the environment table is not visible, and the software assumes that all channels in the channel table are used by the single environment.

If importing a channel table from an Excel spreadsheet for a combined environments test, the Environment Table can be specified as the columns after the main Channel Table information (starting in Column X with one column for each environment) with the environment name specified in row 2 and an entry (e.g. an `X` or some other mark) in the row corresponding to a given channel if that channel is used for the given environment.

#### Data Acquisition Paramters

The final portion of `Data Acquisition Setup` tab specifies data acquisition parameters.  These parameters may change depending on the hardware selected.

* **Hardware Selector** The physical or virtual hardware used for the test.  See [Part II](./chapter_04.md) for hardware specific details of the controller.  For some devices, a file selector window will appear will appear when the device is selected, as that device needs more information to operate.  This is primarily the case for virtual hardware where some model of the test article must be loaded.  This is also used when a specific hardware device needs to access external functionality in a library such as a `dll` file.
* **Sample Rate** The sample rate of all hardware devices used for the test.  Some devices will have arbitrary sample rates, and some devices have fixed sample rates, so the options available will depend on the acquisition hardware being used.
* **Time per Read** The amount of data that the acquisition system will acquire with each read from the hardware.  By reading data in chunks, hardware input/output operations with relatively large overhead can be limited, and the buffer gives the controller time to catch up if e.g. the operating system decides to start a computationally intensive task in the background of the computer.  Note that specifying large numbers for this quantity (e.g. 10) will reduce the responsiveness of the controller, because the controller will potentially not receive the acquired data until 10 seconds after it was acquired.  Note also that this does not need to correspond to the Samples per Analysis Frame or any other signal processing parameter used by an environment.  Each environment should be buffered such that it creates appropriately sized analysis windows from the differently sized acquisition chunks.
* **Time per Write** The amount of data that the output system will write with each write to the hardware.  By writing data in chunks, hardware input/output operations with relatively large overhead can be limited, and the buffer gives the control time to catch up if e.g. the operating system decides to start a computationally intensive task in the background of the computer.   Note that this output is also buffered, so it does not need to be equal to the size of the data that will be created during each control loop of the controller.
* **Maximum Acquisition Processes** For specific hardware devices with large channel count tests, it can be difficult to pull down large quantities of data fast enough for the controller to keep up using a single process.  This option allows the user to specify how many processes can be given to the acquisition system to be used to stream data off the hardware.  Note that too many processes will bog down the computer, and too few will result in the controller falling behind.  Generally about 20-40 channels per processor is sufficient, but this will depend on the sample rate.  For higher sample rates, more processors may be needed.
* **Integration Oversample** For synthetic hardware devices that integrate equations of motion, an integration oversample factor can be specified.  This factor will be applied to the sample rate to determine the time step for the integration.  Generally a factor of 10 is sufficient for reasonably accurate data without significant computational expense.

WIP: subsection: Initialize Data Acquisition