from hardware_utilities import Channel
from abc import ABC, abstractmethod
from typing import List
import numpy as np


class HardwareMetadata(ABC):
    def __init__(self):
        self.channel_list = []


class HardwareAcquisition(ABC):
    """Abstract class defining the interface between the controller and acquisition

    This class defines the interfaces between the controller and the
    data acquisition portion of the hardware.  It is run by the Acquisition
    process, and must define how to get data from the test hardware into the
    controller."""

    @abstractmethod
    def set_up_harware(self, test_data: HardwareMetadata, channel_data: List[Channel]):
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
