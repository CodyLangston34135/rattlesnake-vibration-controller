from rattlesnake.user_interface.ui_utilities import modal_mdi_ui_path, error_message_qt
import numpy as np
import pyqtgraph
from qtpy import QtWidgets, uic


class ModalMDISubWindow(QtWidgets.QWidget):
    """A window that shows modal data"""

    def __init__(self, parent):
        super().__init__(parent)
        uic.loadUi(modal_mdi_ui_path, self)

        self.parent = parent
        self.channel_names = self.parent.channel_names
        self.reference_names = np.array([self.parent.channel_names[i] for i in self.parent.reference_channel_indices])
        self.response_names = np.array([self.parent.channel_names[i] for i in self.parent.response_channel_indices])
        self.reciprocal_responses = self.parent.reciprocal_responses

        self.signal_selector.currentIndexChanged.connect(self.update_ui)
        self.data_type_selector.currentIndexChanged.connect(self.update_ui_no_clear)
        self.response_coordinate_selector.currentIndexChanged.connect(self.update_data)
        self.reference_coordinate_selector.currentIndexChanged.connect(self.update_data)

        self.primary_plotitem = self.primary_plot.getPlotItem()
        self.secondary_plotitem = self.secondary_plot.getPlotItem()
        self.primary_viewbox = self.primary_plotitem.getViewBox()
        self.secondary_viewbox = self.secondary_plotitem.getViewBox()
        self.primary_axis = self.primary_plotitem.getAxis("left")
        self.secondary_axis = self.secondary_plotitem.getAxis("left")

        self.secondary_plotitem.setXLink(self.primary_plotitem)

        self.primary_plotdataitem = pyqtgraph.PlotDataItem(np.arange(2), np.zeros(2), pen={"color": "r", "width": 1})
        self.secondary_plotdataitem = pyqtgraph.PlotDataItem(np.arange(2), np.zeros(2), pen={"color": "r", "width": 1})

        self.primary_viewbox.addItem(self.primary_plotdataitem)
        self.secondary_viewbox.addItem(self.secondary_plotdataitem)

        self.twinx_viewbox = None
        self.twinx_axis = None
        self.twinx_original_plotitem = None
        self.twinx_plotdataitem = None

        self.is_comparing = False
        self.primary_plotdataitem_compare = pyqtgraph.PlotDataItem(np.arange(2), np.zeros(2), pen={"color": "b", "width": 1})
        self.secondary_plotdataitem_compare = pyqtgraph.PlotDataItem(np.arange(2), np.zeros(2), pen={"color": "b", "width": 1})

        self.update_ui()

    def remove_twinx(self):
        """Removes the overlaid plot"""
        if self.twinx_viewbox is None:
            return
        self.twinx_original_plotitem.layout.removeItem(self.twinx_axis)
        self.twinx_original_plotitem.scene().removeItem(self.twinx_viewbox)
        self.twinx_original_plotitem.scene().removeItem(self.twinx_axis)
        self.twinx_viewbox = None
        self.twinx_axis = None
        self.twinx_original_plotitem = None

    def add_twinx(self, existing_plot_item: pyqtgraph.PlotItem):
        """Adds an overlaid plot"""
        # Create a viewbox
        self.twinx_original_plotitem = existing_plot_item
        self.twinx_viewbox = pyqtgraph.ViewBox()
        self.twinx_original_plotitem.scene().addItem(self.twinx_viewbox)
        self.twinx_axis = pyqtgraph.AxisItem("right")
        self.twinx_axis.setLogMode(False)
        self.twinx_axis.linkToView(self.twinx_viewbox)
        self.twinx_original_plotitem.layout.addItem(self.twinx_axis, 2, 3)
        self.updateTwinXViews()
        self.twinx_viewbox.setXLink(self.twinx_original_plotitem)
        self.twinx_original_plotitem.vb.sigResized.connect(self.updateTwinXViews)
        self.twinx_plotdataitem = pyqtgraph.PlotDataItem(np.arange(2), np.zeros(2), pen={"color": "b", "width": 1})
        self.twinx_viewbox.addItem(self.twinx_plotdataitem)

    def add_compare(self):
        """Adds a second function for comparison for reciprocal plots"""
        self.is_comparing = True
        self.primary_viewbox.addItem(self.primary_plotdataitem_compare)
        self.secondary_viewbox.addItem(self.secondary_plotdataitem_compare)

    def remove_compare(self):
        """Removes the second function that was used for comparison"""
        if self.is_comparing:
            self.primary_viewbox.removeItem(self.primary_plotdataitem_compare)
            self.secondary_viewbox.removeItem(self.secondary_plotdataitem_compare)
            self.is_comparing = False

    def updateTwinXViews(self):  # pylint: disable=invalid-name
        """Updates the second view box based on the view from the first box"""
        if self.twinx_viewbox is None:
            return
        self.twinx_viewbox.setGeometry(self.twinx_original_plotitem.vb.sceneBoundingRect())
        # self.twinx_viewbox.linkedViewChanged(
        #     self.twinx_original_plotitem.vb, self.twinx_viewbox.XAxis)

    def update_ui_no_clear(self):
        """Updates the UI without clearing the data"""
        self.update_ui(False)

    def update_ui(self, clear_channels=True):
        """Updates the UI based on which function type is selected"""
        self.response_coordinate_selector.blockSignals(True)
        self.reference_coordinate_selector.blockSignals(True)
        self.remove_twinx()
        self.remove_compare()
        if self.signal_selector.currentIndex() in [
            0,
            1,
            2,
            3,
        ]:  # Time or Windowed Time or Spectrum or Autospectrum
            self.reference_coordinate_selector.hide()
            self.data_type_selector.hide()
            self.secondary_plot.hide()
            if clear_channels:
                self.response_coordinate_selector.clear()
                self.reference_coordinate_selector.clear()
                for channel_name in self.channel_names:
                    self.response_coordinate_selector.addItem(channel_name)
            if self.signal_selector.currentIndex() in [0, 1]:
                self.primary_axis.setLogMode(False)
                self.primary_plotdataitem.setLogMode(False, False)
            else:
                self.primary_axis.setLogMode(True)
                self.primary_plotdataitem.setLogMode(False, True)
        elif self.signal_selector.currentIndex() in [
            4,
            6,
            7,
        ]:  # FRF or FRF Coherence or Reciprocity
            self.reference_coordinate_selector.show()
            self.data_type_selector.show()
            if self.data_type_selector.currentIndex() in [1, 4]:
                self.secondary_plot.show()
                if self.signal_selector.currentIndex() == 6:
                    self.add_twinx(self.secondary_plotitem)
            else:
                self.secondary_plot.hide()
                if self.signal_selector.currentIndex() == 6:
                    self.add_twinx(self.primary_plotitem)
            if self.signal_selector.currentIndex() == 7:
                if any([val is None for val in self.reciprocal_responses]):
                    error_message_qt(
                        "Invalid Reciprocal Channels",
                        "Could not deterimine reciprocal channels for this test",
                    )
                    self.signal_selector.setCurrentIndex(4)
                    return
                self.add_compare()
            if clear_channels:
                self.response_coordinate_selector.clear()
                self.reference_coordinate_selector.clear()
                if self.signal_selector.currentIndex() == 7:
                    for channel_name in self.response_names[self.reciprocal_responses]:
                        self.response_coordinate_selector.addItem(channel_name)
                else:
                    for channel_name in self.response_names:
                        self.response_coordinate_selector.addItem(channel_name)
                for channel_name in self.reference_names:
                    self.reference_coordinate_selector.addItem(channel_name)
            if self.data_type_selector.currentIndex() == 0:
                self.primary_axis.setLogMode(True)
                self.primary_plotdataitem.setLogMode(False, True)
                self.primary_plotdataitem_compare.setLogMode(False, True)
            elif self.data_type_selector.currentIndex() == 1:
                self.primary_axis.setLogMode(False)
                self.primary_plotdataitem.setLogMode(False, False)
                self.primary_plotdataitem_compare.setLogMode(False, False)
                self.secondary_axis.setLogMode(True)
                self.secondary_plotdataitem.setLogMode(False, True)
                self.secondary_plotdataitem_compare.setLogMode(False, True)
            elif self.data_type_selector.currentIndex() in [2, 3]:
                self.primary_axis.setLogMode(False)
                self.primary_plotdataitem.setLogMode(False, False)
                self.primary_plotdataitem_compare.setLogMode(False, False)
            elif self.data_type_selector.currentIndex() == 4:
                self.primary_axis.setLogMode(False)
                self.primary_plotdataitem.setLogMode(False, False)
                self.primary_plotdataitem_compare.setLogMode(False, False)
                self.secondary_axis.setLogMode(False)
                self.secondary_plotdataitem.setLogMode(False, False)
                self.secondary_plotdataitem_compare.setLogMode(False, False)
            if self.signal_selector.currentIndex() == 6:
                self.twinx_axis.setLogMode(False)
                self.twinx_plotdataitem.setLogMode(False, False)
        elif self.signal_selector.currentIndex() in [5]:  # Coherence
            self.reference_coordinate_selector.hide()
            self.data_type_selector.hide()
            self.secondary_plot.hide()
            if clear_channels:
                self.response_coordinate_selector.clear()
                self.reference_coordinate_selector.clear()
                for channel_name in self.response_names:
                    self.response_coordinate_selector.addItem(channel_name)
            self.primary_axis.setLogMode(False)
            self.primary_plotdataitem.setLogMode(False, False)
        self.update_data()
        self.response_coordinate_selector.blockSignals(False)
        self.reference_coordinate_selector.blockSignals(False)

    def set_window_title(self):
        """Sets the window title"""
        signal_name = self.signal_selector.itemText(self.signal_selector.currentIndex())
        response_name = self.response_coordinate_selector.itemText(self.response_coordinate_selector.currentIndex())
        reference_name = (
            self.reference_coordinate_selector.itemText(self.reference_coordinate_selector.currentIndex())
            if self.signal_selector.currentIndex() == 4
            else ""
        )
        self.setWindowTitle(f"{signal_name} {response_name} {reference_name}")

    def update_data(self):
        """Updates the data in the plot"""
        self.set_window_title()
        current_index = self.signal_selector.currentIndex()
        if current_index in [0, 1]:  # Time history
            if self.parent.last_frame is None:
                return
            data = self.parent.last_frame[self.response_coordinate_selector.currentIndex()]
            if current_index == 1:
                data = data * self.parent.window_function
            self.primary_plotdataitem.setData(self.parent.time_abscissa, data)
        elif current_index == 2:  # Spectrum
            if self.parent.last_spectrum is None:
                return
            data = self.parent.last_spectrum[self.response_coordinate_selector.currentIndex()]
            self.primary_plotdataitem.setData(self.parent.frequency_abscissa, data)
        elif current_index == 3:  # Autospectrum
            if self.parent.last_autospectrum is None:
                return
            data = self.parent.last_autospectrum[self.response_coordinate_selector.currentIndex()]
            self.primary_plotdataitem.setData(self.parent.frequency_abscissa, data)
        elif current_index == 4 or current_index == 6:  # FRF or FRF Coherence
            if self.parent.last_frf is None:
                return
            data = self.parent.last_frf[
                :,
                self.response_coordinate_selector.currentIndex(),
                self.reference_coordinate_selector.currentIndex(),
            ]
            if self.data_type_selector.currentIndex() == 0:  # Magnitude
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.abs(data))
            elif self.data_type_selector.currentIndex() == 1:  # Magnitude/Phase
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.angle(data))
                self.secondary_plotdataitem.setData(self.parent.frequency_abscissa, np.abs(data))
            elif self.data_type_selector.currentIndex() == 2:  # Real
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.real(data))
            elif self.data_type_selector.currentIndex() == 3:  # Imag
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.imag(data))
            elif self.data_type_selector.currentIndex() == 4:  # Real/Imag
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.real(data))
                self.secondary_plotdataitem.setData(self.parent.frequency_abscissa, np.imag(data))
            if current_index == 6:
                data = self.parent.last_coh[self.response_coordinate_selector.currentIndex()]
                self.twinx_plotdataitem.setData(self.parent.frequency_abscissa, data)
        elif current_index == 5:  # Coherence
            if self.parent.last_coh is None:
                return
            data = self.parent.last_coh[self.response_coordinate_selector.currentIndex()]
            self.primary_plotdataitem.setData(self.parent.frequency_abscissa, data)
        elif current_index == 7:  # FRF or FRF Coherence
            if self.parent.last_frf is None:
                return
            resp_ind = self.response_coordinate_selector.currentIndex()
            ref_ind = self.reference_coordinate_selector.currentIndex()
            data = self.parent.last_frf[:, self.reciprocal_responses[resp_ind], ref_ind]
            compare_data = self.parent.last_frf[:, self.reciprocal_responses[ref_ind], resp_ind]
            if self.data_type_selector.currentIndex() == 0:  # Magnitude
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.abs(data))
                self.primary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.abs(compare_data))
            elif self.data_type_selector.currentIndex() == 1:  # Magnitude/Phase
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.angle(data))
                self.secondary_plotdataitem.setData(self.parent.frequency_abscissa, np.abs(data))
                self.primary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.angle(compare_data))
                self.secondary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.abs(compare_data))
            elif self.data_type_selector.currentIndex() == 2:  # Real
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.real(data))
                self.primary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.real(compare_data))
            elif self.data_type_selector.currentIndex() == 3:  # Imag
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.imag(data))
                self.primary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.imag(compare_data))
            elif self.data_type_selector.currentIndex() == 4:  # Real/Imag
                self.primary_plotdataitem.setData(self.parent.frequency_abscissa, np.real(data))
                self.secondary_plotdataitem.setData(self.parent.frequency_abscissa, np.imag(data))
                self.primary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.real(compare_data))
                self.secondary_plotdataitem_compare.setData(self.parent.frequency_abscissa, np.imag(compare_data))

    def increment_channel(self, increment=1):
        """Increments the channel number by the specified amount"""
        if not self.lock_response_checkbox.isChecked():
            num_channels = self.response_coordinate_selector.count()
            current_index = self.response_coordinate_selector.currentIndex()
            new_index = (current_index + increment) % num_channels
            self.response_coordinate_selector.setCurrentIndex(new_index)
