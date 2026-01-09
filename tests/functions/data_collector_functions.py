import multiprocessing as mp
import unittest.mock as mock
import pytest


def create_acquire_log_calls(last_data):
    log_calls = [mock.call('Acquired Data with shape (1, 2, 100) and Last Data {:}'.format(last_data)),
                 mock.call('Data Average RMS: 0.0000'),
                 mock.call('Putting Data to Buffer'),
                 mock.call('Measurement Frames Received (1)'),
                 mock.call('Received output from framebuffer with RMS: \n  [0.]'),
                 mock.call('Sending data'),
                 mock.call('Sent Data')]
    return log_calls