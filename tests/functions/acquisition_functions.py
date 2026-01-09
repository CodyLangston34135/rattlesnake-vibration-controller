import unittest.mock as mock


def create_acquire_log_calls():
    log_calls = [mock.call('Waiting for Output to Start'),
                 mock.call('Listening for first data for environment Modal'),
                 mock.call('Detected Output Started'),
                 mock.call('Starting Hardware Acquisition'),
                 mock.call("Acquiring Data for ['Modal'] environments"),
                 mock.call('Correlation check for environment Modal took 10.00 seconds'),
                 mock.call('Found First Data for Environment Modal'),
                 mock.call('Sending (2, 98) data to Modal environment')]
    
    return log_calls