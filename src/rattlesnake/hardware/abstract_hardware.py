from .hardware_utilities import Channel, HardwareType
from abc import ABC, abstractmethod
from typing import List
import numpy as np


class HardwareMetadata(ABC):
    def __init__(self):
        self.hardware_type = HardwareType.SELECT
        self.channel_list = []
        self.sample_rate = 1000
        self.time_per_read = 0.25
        self.time_per_write = 0.25
        self.output_oversample = 1

    @property
    def samples_per_read(self):
        return round(self.sample_rate * self.time_per_read)

    @property
    def samples_per_write(self):
        return round(self.sample_rate * self.time_per_write * self.output_oversample)

    @abstractmethod
    def validate(self):
        """ "
        Check if the hardware exists and is reconizable. Return True if everything
        checks out

        Please throw detailed errors while validating. Makes it easier for user to debug
        """


class HardwareAcquisition(ABC):
    """Abstract class defining the interface between the controller and acquisition

    This class defines the interfaces between the controller and the
    data acquisition portion of the hardware.  It is run by the Acquisition
    process, and must define how to get data from the test hardware into the
    controller."""

    @abstractmethod
    def set_up_data_output_parameters_and_channels(self, metadata: HardwareMetadata):
        """
        Initialize the hardware and set up channels and sampling properties

        The function must create channels on the hardware corresponding to
        the channels in the test.  It must also set the sampling rates.

        Parameters
        ----------
        test_data : DataAcquisitionParameters :
            A container containing the data acquisition parameters for the
            controller set by the user.
        channel_data : List[Channel] :
            A list of ``Channel`` objects defining the channels in the test

        Returns
        -------
        None.

        """

    @abstractmethod
    def start(self):
        """Method to start acquiring data from the hardware"""

    @abstractmethod
    def read(self) -> np.ndarray:
        """Method to read a frame of data from the hardware that returns
        an appropriately sized np.ndarray"""

    @abstractmethod
    def read_remaining(self) -> np.ndarray:
        """Method to read the rest of the data on the acquisition from the hardware
        that returns an appropriately sized np.ndarray"""

    @abstractmethod
    def stop(self):
        """Method to stop the acquisition"""

    @abstractmethod
    def close(self):
        """Method to close down the hardware"""

    @abstractmethod
    def get_acquisition_delay(self) -> int:
        """Get the number of samples between output and acquisition

        This function is designed to handle buffering done in the output
        hardware, ensuring that all data written to the output is read by the
        acquisition.  If a output hardware has a buffer, there may be a non-
        negligable delay between when output is written to the device and
        actually played out from the device."""


class HardwareOutput(ABC):
    """Abstract class defining the interface between the controller and output

    This class defines the interfaces between the controller and the
    output or source portion of the hardware.  It is run by the Output
    process, and must define how to get write data to the hardware from the
    control system"""

    @abstractmethod
    def set_up_data_output_parameters_and_channels(self, metadata: HardwareMetadata):
        """
        Initialize the hardware and set up sources and sampling properties

        The function must create channels on the hardware corresponding to
        the sources in the test.  It must also set the sampling rates.

        Parameters
        ----------
        test_data : DataAcquisitionParameters :
            A container containing the data acquisition parameters for the
            controller set by the user.
        channel_data : List[Channel] :
            A list of ``Channel`` objects defining the channels in the test

        Returns
        -------
        None.

        """
        pass

    @abstractmethod
    def start(self):
        """Method to start outputting data to the hardware"""
        pass

    @abstractmethod
    def write(self, data):
        """Method to write a np.ndarray with a frame of data to the hardware"""
        pass

    @abstractmethod
    def stop(self):
        """Method to stop the output"""
        pass

    @abstractmethod
    def close(self):
        """Method to close down the hardware"""
        pass

    @abstractmethod
    def ready_for_new_output(self) -> bool:
        """Method that returns true if the hardware should accept a new signal"""
        pass
