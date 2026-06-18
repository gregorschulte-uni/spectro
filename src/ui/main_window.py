"""PyQt5 main window with live PyQtGraph plotting and controls."""
from __future__ import annotations

import os
import time
from datetime import datetime

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

from acquisition import AcquisitionWorker
from spectrometer import MockSpectrometer, SpectrometerBase, open_spectrometer


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, force_mock: bool = False):
        super().__init__()
        self.setWindowTitle("Ocean Optics Flame Spectrometer")
        self.resize(1100, 700)

        self._spec: SpectrometerBase | None = None
        self._thread: QtCore.QThread | None = None
        self._worker: AcquisitionWorker | None = None
        self._force_mock = force_mock

        self._last_wl: np.ndarray | None = None
        self._last_inten: np.ndarray | None = None

        self._build_ui()
        self.statusBar().showMessage("Not connected.")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        # ---- Plot ----
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.setLabel("bottom", "Wavelength", units="nm")
        self.plot_widget.setLabel("left", "Intensity", units="counts")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot_widget.plot(pen=pg.mkPen("#1f77b4", width=1))
        layout.addWidget(self.plot_widget, stretch=3)

        # ---- Control panel ----
        panel = QtWidgets.QWidget()
        panel.setMaximumWidth(320)
        form = QtWidgets.QVBoxLayout(panel)
        layout.addWidget(panel, stretch=1)

        # Connection
        conn_box = QtWidgets.QGroupBox("Device")
        conn_layout = QtWidgets.QVBoxLayout(conn_box)
        self.lbl_device = QtWidgets.QLabel("No device")
        self.btn_connect = QtWidgets.QPushButton("Connect")
        self.btn_connect.clicked.connect(self.toggle_connect)
        conn_layout.addWidget(self.lbl_device)
        conn_layout.addWidget(self.btn_connect)
        form.addWidget(conn_box)

        # Parameters
        param_box = QtWidgets.QGroupBox("Parameters")
        grid = QtWidgets.QFormLayout(param_box)

        self.spin_integration = QtWidgets.QDoubleSpinBox()
        self.spin_integration.setRange(0.001, 65000.0)
        self.spin_integration.setDecimals(3)
        self.spin_integration.setValue(100.0)
        self.spin_integration.setSuffix(" ms")
        self.spin_integration.valueChanged.connect(self.apply_integration_time)
        grid.addRow("Integration time:", self.spin_integration)

        self.spin_average = QtWidgets.QSpinBox()
        self.spin_average.setRange(1, 1000)
        self.spin_average.setValue(1)
        self.spin_average.valueChanged.connect(self.apply_averaging)
        grid.addRow("Scans to average:", self.spin_average)

        self.spin_boxcar = QtWidgets.QSpinBox()
        self.spin_boxcar.setRange(0, 50)
        self.spin_boxcar.setValue(0)
        self.spin_boxcar.valueChanged.connect(self.apply_boxcar)
        grid.addRow("Boxcar width:", self.spin_boxcar)

        self.chk_dark = QtWidgets.QCheckBox("Electric dark correction")
        self.chk_dark.stateChanged.connect(self.apply_corrections)
        grid.addRow(self.chk_dark)

        self.chk_nonlin = QtWidgets.QCheckBox("Nonlinearity correction")
        self.chk_nonlin.stateChanged.connect(self.apply_corrections)
        grid.addRow(self.chk_nonlin)

        form.addWidget(param_box)

        # Acquisition controls
        acq_box = QtWidgets.QGroupBox("Acquisition")
        acq_layout = QtWidgets.QVBoxLayout(acq_box)
        self.btn_start = QtWidgets.QPushButton("Start")
        self.btn_start.clicked.connect(self.start_acquisition)
        self.btn_start.setEnabled(False)
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop_acquisition)
        self.btn_stop.setEnabled(False)
        self.chk_autorange = QtWidgets.QCheckBox("Auto Y-range")
        self.chk_autorange.setChecked(True)
        acq_layout.addWidget(self.btn_start)
        acq_layout.addWidget(self.btn_stop)
        acq_layout.addWidget(self.chk_autorange)
        form.addWidget(acq_box)

        # Save
        save_box = QtWidgets.QGroupBox("Save")
        save_layout = QtWidgets.QVBoxLayout(save_box)
        self.btn_save = QtWidgets.QPushButton("Save spectrum as .txt")
        self.btn_save.clicked.connect(self.save_spectrum)
        self.btn_save.setEnabled(False)
        save_layout.addWidget(self.btn_save)
        form.addWidget(save_box)

        form.addStretch(1)

    # ----------------------------------------------------------- connection
    def toggle_connect(self) -> None:
        if self._spec is None:
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self) -> None:
        try:
            self._spec = open_spectrometer(force_mock=self._force_mock)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection error", str(exc))
            return

        is_mock = isinstance(self._spec, MockSpectrometer)
        self.apply_integration_time(self.spin_integration.value())
        self.lbl_device.setText(
            f"{self._spec.model}\nS/N: {self._spec.serial_number}"
            + ("\n[SIMULATION]" if is_mock else "")
        )
        self.btn_connect.setText("Disconnect")
        self.btn_start.setEnabled(True)
        self.btn_save.setEnabled(True)
        msg = "Connected (simulation mode)." if is_mock else "Connected."
        self.statusBar().showMessage(msg)

    def disconnect_device(self) -> None:
        self.stop_acquisition()
        if self._spec is not None:
            self._spec.close()
            self._spec = None
        self.lbl_device.setText("No device")
        self.btn_connect.setText("Connect")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.statusBar().showMessage("Disconnected.")

    # ------------------------------------------------------------ parameters
    def apply_integration_time(self, value_ms: float) -> None:
        if self._spec is None:
            return
        micros = int(round(value_ms * 1000.0))
        lo, hi = self._spec.integration_time_micros_limits
        micros = max(lo, min(hi, micros))
        try:
            self._spec.set_integration_time_micros(micros)
        except Exception as exc:
            self.statusBar().showMessage(f"Integration time error: {exc}")

    def apply_averaging(self, n: int) -> None:
        if self._worker is not None:
            self._worker.set_scans_to_average(n)

    def apply_boxcar(self, w: int) -> None:
        if self._worker is not None:
            self._worker.set_boxcar_width(w)

    def apply_corrections(self) -> None:
        if self._worker is not None:
            self._worker.set_corrections(
                self.chk_dark.isChecked(), self.chk_nonlin.isChecked()
            )

    # ----------------------------------------------------------- acquisition
    def start_acquisition(self) -> None:
        if self._spec is None or self._thread is not None:
            return

        self._worker = AcquisitionWorker(self._spec)
        self._worker.set_scans_to_average(self.spin_average.value())
        self._worker.set_boxcar_width(self.spin_boxcar.value())
        self._worker.set_corrections(
            self.chk_dark.isChecked(), self.chk_nonlin.isChecked()
        )

        self._thread = QtCore.QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.spectrum_ready.connect(self.update_plot)
        self._worker.error.connect(self.on_worker_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage("Acquiring...")

    def stop_acquisition(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self.btn_start.setEnabled(self._spec is not None)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage("Stopped.")

    def on_worker_error(self, message: str) -> None:
        self.statusBar().showMessage(f"Acquisition error: {message}")
        QtWidgets.QMessageBox.warning(self, "Acquisition error", message)
        self.stop_acquisition()

    # --------------------------------------------------------------- plotting
    def update_plot(self, wl: np.ndarray, inten: np.ndarray) -> None:
        self._last_wl = wl
        self._last_inten = inten
        self.curve.setData(wl, inten)
        if self.chk_autorange.isChecked():
            self.plot_widget.enableAutoRange(axis="y")

    # ------------------------------------------------------------------ save
    def save_spectrum(self) -> None:
        if self._last_wl is None or self._last_inten is None:
            QtWidgets.QMessageBox.information(
                self, "No data", "No spectrum has been acquired yet."
            )
            return

        default_name = datetime.now().strftime("spectrum_%Y%m%d_%H%M%S.txt")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save spectrum", default_name, "Text files (*.txt);;All files (*)"
        )
        if not path:
            return

        header = self._build_header()
        try:
            data = np.column_stack((self._last_wl, self._last_inten))
            np.savetxt(path, data, fmt="%.6f", delimiter="\t", header=header)
            self.statusBar().showMessage(f"Saved: {os.path.basename(path)}")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save error", str(exc))

    def _build_header(self) -> str:
        spec = self._spec
        lines = [
            "Ocean Optics Flame spectrum",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Model: {spec.model if spec else 'unknown'}",
            f"Serial: {spec.serial_number if spec else 'unknown'}",
            f"Integration time (ms): {self.spin_integration.value()}",
            f"Scans averaged: {self.spin_average.value()}",
            f"Boxcar width: {self.spin_boxcar.value()}",
            f"Dark correction: {self.chk_dark.isChecked()}",
            f"Nonlinearity correction: {self.chk_nonlin.isChecked()}",
            "",
            "Wavelength(nm)\tIntensity(counts)",
        ]
        return "\n".join(lines)

    # ----------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        self.stop_acquisition()
        if self._spec is not None:
            self._spec.close()
        event.accept()
