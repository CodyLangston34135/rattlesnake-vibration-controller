import numpy as np

# Parameters
num_rows = 3
num_samples = 10000
sample_rate = 1000  # Hz
frequency = 5  # Hz sine wave

# Create time vector
t = np.arange(num_samples) / sample_rate

# Create signal array
signal = np.zeros((num_rows, num_samples))
signal[0, :] = np.sin(2 * np.pi * frequency * t)  # sine wave in first row

# Save to .npy file
np.save("test_signal.npy", signal)

print("Signal saved to 'test_signal.npy'")
print("Shape:", signal.shape)
