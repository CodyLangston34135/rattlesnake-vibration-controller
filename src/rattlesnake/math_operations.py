import os
import numpy as np
import scipy.signal as sig
from scipy.interpolate import interp1d
from scipy.io import loadmat


def load_time_history(signal_path, sample_rate):
    """Loads a time history from a given file

    The signal can be loaded from numpy files (.npz, .npy) or matlab files (.mat).
    For .mat and .npz files, the time data can be included in the file in the
    't' field, or it can be excluded and the sample_rate input argument will
    be used.  If time data is specified, it will be linearly interpolated to the
    sample rate of the controller.
    For these file types, the signal should be stored in the 'signal'
    field.  For .npy files, only one array is stored, so it is treated as the
    signal, and the sample_rate input argument is used to construct the time
    data.

    Parameters
    ----------
    signal_path : str:
        Path to the file from which to load the time history

    sample_rate : str:
        The sample rate of the loaded signal.

    Returns
    -------
    signal : np.ndarray:
        A signal loaded from the file

    """
    _, extension = os.path.splitext(signal_path)
    if extension.lower() == ".npy":
        signal = np.load(signal_path)
    elif extension.lower() == ".npz":
        data = np.load(signal_path)
        signal = data["signal"]
        try:
            times = data["t"].squeeze()
            fn = interp1d(times, signal)
            abscissa = np.arange(0, max(times) + 1 / sample_rate - 1e-10, 1 / sample_rate)
            abscissa = abscissa[abscissa <= max(times)]
            signal = fn(abscissa)
        except KeyError:
            pass
    elif extension.lower() == ".mat":
        data = loadmat(signal_path)
        signal = data["signal"]
        try:
            times = data["t"].squeeze()
            fn = interp1d(times, signal)
            abscissa = np.arange(0, max(times) + 1 / sample_rate - 1e-10, 1 / sample_rate)
            abscissa = abscissa[abscissa <= max(times)]
            signal = fn(abscissa)
        except KeyError:
            pass
    else:
        raise ValueError(f"Could Not Determine the file type from the filename {signal_path}: {extension}")
    if signal.shape[-1] % 2 == 1:
        signal = signal[..., :-1]
    return signal


def align_signals(
    measurement_buffer,
    specification,
    correlation_threshold=0.9,
    perform_subsample=True,
    correlation_metric=None,
):
    """Computes the time shift between two signals in time

    Parameters
    ----------
    measurement_buffer : np.ndarray
        Signal coming from the measurement
    specification : np.ndarray
        Signal to align the measurement to
    correlation_threshold : float, optional
        Threshold for a "good" correlation, by default 0.9
    perform_subsample : bool, optional
        If True, computes a time shift that could be between samples using the phase of the FFT of
        the signals, by default True
    correlation_metric : function, optional
        An optional function to use to change the matching criterion, by default A simple
        correlation is used

    Returns
    -------
    spec_portion_aligned : np.ndarray
        The portion of the measurement that lines up with the specification
    delay : float
        The time difference between the measurement and specification
    mean_phase_slope : float
        The slope of the phase computed in the FFT from the subsample alignment.  Will be None
        if subsample matching is not used
    found_correlation : float
        The value of the correlation metric used to find the match
    """
    if correlation_metric is None:
        maximum_possible_correlation = np.sum(specification**2)
        correlation = sig.correlate(measurement_buffer, specification, mode="valid").squeeze() / maximum_possible_correlation
    else:
        correlation = correlation_metric(measurement_buffer, specification)
    delay = np.argmax(correlation)
    found_correlation = correlation[delay]
    print(f"Max Correlation: {found_correlation}")
    if found_correlation < correlation_threshold:
        return None, None, None, None
    # np.savez('alignment_debug.npz',measurement_buffer=measurement_buffer,
    #          specification = specification,
    #          correlation_threshold = correlation_threshold)
    specification_portion = measurement_buffer[:, delay : delay + specification.shape[-1]]

    if perform_subsample:
        # Compute ffts for subsample alignment
        spec_fft = np.fft.rfft(specification, axis=-1)
        spec_portion_fft = np.fft.rfft(specification_portion, axis=-1)

        # Compute phase angle differences for subpixel alignment
        phase_difference = np.angle(spec_portion_fft / spec_fft)
        phase_slope = phase_difference[..., 1:-1] / np.arange(phase_difference.shape[-1])[1:-1]
        mean_phase_slope = np.median(phase_slope)  # Use Median to discard outliers due to potentially noisy phase

        spec_portion_aligned_fft = spec_portion_fft * np.exp(-1j * mean_phase_slope * np.arange(spec_portion_fft.shape[-1]))
        spec_portion_aligned = np.fft.irfft(spec_portion_aligned_fft)
    else:
        spec_portion_aligned = specification_portion.copy()
        mean_phase_slope = None
    return spec_portion_aligned, delay, mean_phase_slope, found_correlation


def shift_signal(signal, samples_to_keep, sample_delay, phase_slope):
    """Applies a time shift to a signal by modifying the phase of the FFT

    Parameters
    ----------
    signal : np.ndarray
        The signal to shift
    samples_to_keep : int
        The number of samples to keep in the shifted signal
    sample_delay : int
        The number of samples to delay
    phase_slope : float
        The slope of the phase if subsample shift is used

    Returns
    -------
    np.ndarray
        The shifted signal
    """
    signal_sample_aligned = signal[..., sample_delay : sample_delay + samples_to_keep]
    sample_aligned_fft = np.fft.rfft(signal_sample_aligned, axis=-1)
    subsample_aligned_fft = sample_aligned_fft * np.exp(-1j * phase_slope * np.arange(sample_aligned_fft.shape[-1]))
    return np.fft.irfft(subsample_aligned_fft)


def correlation_norm_signal_spec_ratio(signal, specification):
    """Computes correlation weighted by the ratio of the norms of the signals

    Parameters
    ----------
    signal : np.ndarray
        The signal to compute the correlation on
    specification : np.ndarray
        The signal to compute the correlation against

    Returns
    -------
    np.ndarray
        The weighted correlation signal
    """
    correlation = sig.correlate(signal, specification, mode="valid").squeeze()
    norm_specification = np.linalg.norm(specification)
    norm_signal = np.sqrt(np.sum(moving_sum(signal**2, specification.shape[-1]), axis=0))
    norm_signal_divide = norm_signal.copy()
    norm_signal_divide[norm_signal_divide == 0] = 1e14
    return correlation / norm_specification / norm_signal_divide - abs(1 - (norm_signal / norm_specification) ** 2)


def moving_sum(signal, n):
    """Computes a moving sum of the specified number of items

    Parameters
    ----------
    signal : np.ndarray
        The signal(s) to compute the moving sum on
    n : int
        The number of items to use in the moving sum

    Returns
    -------
    np.array
        The moving sum computed at each time step in the signal
    """
    return_value = np.cumsum(signal, axis=-1)
    return_value[..., n:] = return_value[..., n:] - return_value[..., :-n]
    return return_value[..., n - 1 :]


def rms_time(signal, axis=None, keepdims=False):
    """Computes RMS over a time signal

    Parameters
    ----------
    signal : np.ndarray :
        Signal over which to compute the root-mean-square value
    axis : int :
        The dimension over which the mean is performed (Default value = None)
    keepdims : bool :
        Whether to keep the dimension over which mean is computed (Default value = False)

    Returns
    -------
    rms : numpy scalar or numpy.ndarray
        The root-mean-square value of signal

    """
    return np.sqrt(np.mean(signal**2, axis=axis, keepdims=keepdims))


def db2scale(decibel):
    """Converts a decibel value to a scale factor

    Parameters
    ----------
    decibel : float :
        Value in decibels


    Returns
    -------
    scale : float :
        Value in linear

    """
    return 10 ** (decibel / 20)
