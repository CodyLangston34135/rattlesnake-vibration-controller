import numpy as np
import scipy.signal as sig


def align_signals(measurement_buffer, specification, correlation_threshold=0.9, perform_subsample=True):
    maximum_possible_correlation = np.sum(specification**2)
    correlation = sig.correlate(measurement_buffer, specification, mode="valid").squeeze()
    delay = np.argmax(correlation)
    print("Max Correlation: {:}".format(np.max(correlation) / maximum_possible_correlation))
    if correlation[delay] < correlation_threshold * maximum_possible_correlation:
        return None, None, None
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
    return spec_portion_aligned, delay, mean_phase_slope


def shift_signal(signal, samples_to_keep, sample_delay, phase_slope):
    # np.savez('shift_debug.npz',signal=signal,
    #          samples_to_keep = samples_to_keep,
    #          sample_delay = sample_delay,
    #          phase_slope=phase_slope)
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
