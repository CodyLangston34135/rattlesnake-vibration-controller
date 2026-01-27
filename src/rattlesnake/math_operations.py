import os
import numpy as np
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
