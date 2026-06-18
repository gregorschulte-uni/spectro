"""Background acquisition worker that continuously reads spectra."""
from __future__ import annotations

import time
from collections import deque

import numpy as np
from PyQt5 import QtCore

from spectrometer import SpectrometerBase


class AcquisitionWorker(QtCore.QObject):
    """Runs in its own QThread and emits new spectra continuously."""

    # wavelengths, intensities
    spectrum_ready = QtCore.pyqtSignal(np.ndarray, np.ndarray)
    error = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, spectrometer: SpectrometerBase):
        super().__init__()
        self._spec = spectrometer
        self._running = False

        # Parameters (guarded by a mutex since the GUI thread updates them).
        self._mutex = QtCore.QMutex()
        self._scans_to_average = 1
        self._boxcar_width = 0
        self._correct_dark = False
        self._correct_nonlinearity = False

    # ----- parameter setters (called from GUI thread) -----
    def set_scans_to_average(self, n: int) -> None:
        with QtCore.QMutexLocker(self._mutex):
            self._scans_to_average = max(1, int(n))

    def set_boxcar_width(self, w: int) -> None:
        with QtCore.QMutexLocker(self._mutex):
            self._boxcar_width = max(0, int(w))

    def set_corrections(self, dark: bool, nonlinearity: bool) -> None:
        with QtCore.QMutexLocker(self._mutex):
            self._correct_dark = bool(dark)
            self._correct_nonlinearity = bool(nonlinearity)

    def stop(self) -> None:
        self._running = False

    # ----- acquisition loop -----
    @QtCore.pyqtSlot()
    def run(self) -> None:
        self._running = True
        wl = self._spec.wavelengths()
        try:
            while self._running:
                with QtCore.QMutexLocker(self._mutex):
                    n_avg = self._scans_to_average
                    boxcar = self._boxcar_width
                    dark = self._correct_dark
                    nonlin = self._correct_nonlinearity

                acc = None
                for _ in range(n_avg):
                    if not self._running:
                        break
                    data = self._spec.intensities(
                        correct_dark=dark, correct_nonlinearity=nonlin
                    )
                    acc = data if acc is None else acc + data
                if acc is None:
                    break
                inten = acc / float(n_avg)

                if boxcar > 0:
                    inten = self._boxcar_smooth(inten, boxcar)

                self.spectrum_ready.emit(wl, inten)
                # Yield briefly so the event loop stays responsive.
                time.sleep(0.001)
        except Exception as exc:  # pragma: no cover - hardware errors
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    @staticmethod
    def _boxcar_smooth(data: np.ndarray, half_width: int) -> np.ndarray:
        window = 2 * half_width + 1
        kernel = np.ones(window) / window
        return np.convolve(data, kernel, mode="same")
