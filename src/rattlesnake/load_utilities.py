from rattlesnake.hardware.hardware_utilities import Channel
import os
import netCDF4
import openpyxl
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


def load_channel_list_from_netcdf(filepath):
    dataset = netCDF4.Dataset(filepath)
    channel_table = dataset["channels"]
    channel_list = []
    num_channels = dataset.dimensions["response_channels"].size
    channel_attr_list = Channel().channel_attr_list
    for row_idx in range(num_channels):
        channel = Channel()
        for attr in channel_attr_list:
            value = channel_table[attr][row_idx]
            value = None if isinstance(value, str) and not value.strip() else value
            setattr(channel, attr, value)

        if not channel.is_empty:  # optional safety check
            channel_list.append(channel)

    return channel_list


def load_channel_list_from_worksheet(filepath):
    workbook = openpyxl.load_workbook(filepath, read_only=True)
    sheets = workbook.sheetnames

    if len(sheets) > 1:
        sheets = [sheet for sheet in sheets if "channel" in sheet.lower()]
    if len(sheets) > 1:
        raise ValueError("Multiple channel table sheets located in Excel Spreadsheet")
    if len(sheets) == 0:
        raise ValueError("Excel Spreadsheet does not contain a channel table sheet")

    worksheet = workbook[sheets[0]]

    channel_list = []
    channel_attr_list = Channel().channel_attr_list
    for row in worksheet.iter_rows(min_row=3, min_col=2, max_col=23):
        channel = Channel()
        for col, cell in enumerate(row):
            value = cell.value
            value = None if isinstance(value, str) and not value.strip() else value
            setattr(channel, channel_attr_list[col], cell.value)
        if channel.is_empty:
            break
        channel_list.append(channel)
    workbook.close()

    return channel_list
