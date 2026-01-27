---
numbering:
  heading_2:
    start: 14
  figure:
    enumerator: 14.%s
  table:
    enumerator: 14.%s
  equation:
    enumerator: 14.%s
  code:
    enumerator: 14.%s
---
# Time History Generator

(sec:mimo_time)=
# Time History Generator

Rattlesnake's Time History Generator environment provides the ability to simply stream a user-created signal to an output device.  While this is a relatively simple environment, it can be used to create simple shocks or run open-loop excitation devices such as a centrifuge with voltage input being proportional to speed.  There is no system identification, and therefore no test predictions that are made for this environment.
    
## Signal Definition

The first step to defining a Time History Generator environment is to create the signal that will be output.  Rattlesnake accepts the signal in the form of a 2D array consisting of an output sample for each excitation signal for each time step.  Signals can be loaded from Numpy `*.npy` or `*.npz` files or Matlab `*.mat` files.  For `*.npy` files, the stored array defines the signal directly, and it is assumed that the signal uses the sample rate specified in Rattlesnake.  Note that if a hardware device over-samples the output (e.g. LAN-XI, see Section \ref{sec:rattlesnake_hardware_lanxi}), it is the over-sampled output sample rate that is used rather than the acquisition sample rate.  Matlab `*.mat` and Numpy `*.npz` files allow the users to specify a time vector as well as a signal, and should contain the following data members:

    \item[signal] A $n_o \times n_s$ array containing the signal for each exciter for each time step in `t`.
    \item[t] A $n_s$ array of times corresponding to the samples in the `signal` matrix.

where $n_o$ is the number of exciters and $n_s$ is the number of samples in the signal.  If the time vector specified by `t` does not match the sample rate specified in Rattlesnake, the `signal` data will be linearly interpolated to provide the correct sample rate.  If `t` is not provided in the `*.mat` or `*.npz` file, Rattlesnake will treat `signal` as if it were defined at the output sample rate of the controller.

The ordering of the signals in the signal file is the same as the ordering of the excitation devices in the channel table that are active in the current environment.  The first signal will be played to the first excitation device, and so on.

Note that the environment will play the signal as-is, so it is up to the user to implement graceful startup and shutdown at the start and end of the signal if the test configuration requires it.

## Defining the Time History Generator Environment in Rattlesnake
In addition to the signal that will be played to the excitation devices, there is only one parameter that needs to be defined in the Time History Generator.  Figure \ref{fig:timehistorygeneratorenvironmentdefinition} shows a Time History Generator sub-tab in the `Environment Definition` tab of Rattlesnake.

\begin{figure}
    \centering
    \includegraphics[width=\linewidth]{figures/time_history_generator_environment_definition}
    \caption{GUI defining the Time History Generation environment}
    \label{fig:timehistorygeneratorenvironmentdefinition}
\end{figure}

Pressing the `Load Signal` button brings up a file dialog from which the signal file can be loaded.  Once the file is loaded, it is displayed in the main plot window.  Signal statistics are also displayed in the adjacent table.  The checkbox in the `Show?` column of the table can be used to show or hide individual signals.  The signal name in the `Signal` column is constructed from the node number and direction in the channel table.  The `Max` and `RMS` value of the signal is also displayed.

At the bottom of the window, there are various computed parameters, and one user defined parameter.

    \item[Sample Rate]  The global sample rate of the data acquisition system.  This is set on the `Data Acquisition Setup` tab, and displayed here for convenience as a read-only value.
    \item[Output Sample Rate]  This is the output sample rate, which might be different than `Sample Rate` if the hardware over-samples the output device.  This is set on the `Data Acquisition Setup` tab, and displayed here for convenience as a read-only value.
    \item[Output Channels]  The number of excitation signals being used by this environment.  This is a computed quantity presented for convenience, so the user cannot modify it directly.
    \item[Signal Samples] The number of samples in the loaded signal.  This is a computed quantity presented for convenience, so the use cannot modify it directly.
    \item[Signal Time] The amount of time it will take to play the signal.  This is a computed quantity presented for convenience, so the user cannot modify it directly.
    \item[Cancel Rampdown Time] The amount of time the environment will take to ramp to zero if the environment is stopped prior to the signal being completely played.


## Running the Time History Generator Environment
The Time History Generator environment is then run on the `Run Test` tab of the controller.  With the data acquisition system armed, the GUI looks like Figure \ref{fig:timehistorygeneratorruntest}.

\begin{figure}
    \centering
    \includegraphics[width=\linewidth]{figures/time_history_generator_run_test}
    \caption{GUI for running the Time History Generator Environment}
    \label{fig:timehistorygeneratorruntest}
\end{figure}

Two parameters can be defined prior to starting the environment.

    \item[Signal Level] Allows the user to scale the signal prior to output by a number of dB.
    \item[Repeat Signal] Checking this checkbox makes the signal repeat once started until the environment is stopped manually.  Alternatively, the environment will stop automatically once the signal has been played.


Similar to other environments, there are `Start Environment` and `Stop Environment` buttons to control when the environment occurs.  If the `Stop Environment` button is clicked, the signal will continue to play for the specified `Cancel Rampdown Time` while the environment ramps the signal level to zero.

## Output NetCDF File Structure
When Rattlesnake saves data to a netCDF file, environment-specific parameters are stored in a netCDF group with the same name as the environment name.  Similar to the root netCDF structure described in Section \ref{sec:using_rattlesnake_output_files}, this group will have its own attributes, dimensions, and variables, which are described here.

### NetCDF Dimensions

    \item[output\_channels] The number of output signals used by the environment
    \item[signal\_samples] The number of samples in the output signals


### NetCDF Attributes

    \item[cancel\_rampdown\_time] The time to ramp to zero if the environment is stopped.


### NetCDF Variables

    \item[output\_signal] The signals that are played to the excitation devices  Type: 64-bit float; Dimensions: `output_channels` $\times$ `signal_samples`

