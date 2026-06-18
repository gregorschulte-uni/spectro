"""Spectrometer abstraction layer for Ocean Optics Flame.

Wraps python-seabreeze for real hardware and provides a MockSpectrometer
fallback so the GUI can be developed/tested without a physical device.
"""
from __future__ import annotations

import numpy as np


class SpectrometerBase:
    """Common interface implemented by both real and mock spectrometers."""

    serial_number: str = "unknown"
    model: str = "unknown"

    def wavelengths(self) -> np.ndarray:
        raise NotImplementedError

    def intensities(self, correct_dark: bool = False,
                    correct_nonlinearity: bool = False) -> np.ndarray:
        raise NotImplementedError

    def set_integration_time_micros(self, micros: int) -> None:
        raise NotImplementedError

    @property
    def integration_time_micros_limits(self) -> tuple[int, int]:
        return (1000, 65_000_000)

    @property
    def max_intensity(self) -> float:
        return 65535.0

    def close(self) -> None:
        pass


class SeabreezeSpectrometer(SpectrometerBase):
    """Real device wrapper using python-seabreeze."""

    def __init__(self, device=None):
        from seabreeze.spectrometers import Spectrometer

        if device is None:
            self._spec = Spectrometer.from_first_available()
        else:
            self._spec = Spectrometer(device)

        self.serial_number = self._spec.serial_number
        self.model = self._spec.model

    def wavelengths(self) -> np.ndarray:
        return self._spec.wavelengths()

    def intensities(self, correct_dark: bool = False,
                    correct_nonlinearity: bool = False) -> np.ndarray:
        return self._spec.intensities(
            correct_dark_counts=correct_dark,
            correct_nonlinearity=correct_nonlinearity,
        )

    def set_integration_time_micros(self, micros: int) -> None:
        self._spec.integration_time_micros(int(micros))

    @property
    def integration_time_micros_limits(self) -> tuple[int, int]:
        return self._spec.integration_time_micros_limits

    @property
    def max_intensity(self) -> float:
        return self._spec.max_intensity

    def close(self) -> None:
        try:
            self._spec.close()
        except Exception:
            pass


class MockSpectrometer(SpectrometerBase):
    """Simulated spectrometer producing a noisy multi-peak spectrum."""

    def __init__(self, n_pixels: int = 2048,
                 wl_start: float = 340.0, wl_end: float = 1020.0):
        self.serial_number = "MOCK-0001"
        self.model = "Flame (simulated)"
        self._wl = np.linspace(wl_start, wl_end, n_pixels)
        self._integration_us = 100_000
        # Define some emission-like peaks: (center_nm, amplitude, width_nm)
        self._peaks = [
            (436.0, 30000, 3.0),
            (546.0, 45000, 4.0),
            (611.0, 20000, 5.0),
            (750.0, 15000, 8.0),
        ]

    def wavelengths(self) -> np.ndarray:
        return self._wl

    def intensities(self, correct_dark: bool = False,
                    correct_nonlinearity: bool = False) -> np.ndarray:
        # Baseline scales mildly with integration time.
        scale = self._integration_us / 100_000.0
        spectrum = np.full_like(self._wl, 800.0 * scale)
        for center, amp, width in self._peaks:
            spectrum += amp * scale * np.exp(-0.5 * ((self._wl - center) / width) ** 2)
        # Add shot-like noise.
        noise = np.random.normal(0.0, 50.0 * np.sqrt(scale), size=self._wl.shape)
        spectrum = np.clip(spectrum + noise, 0, self.max_intensity)
        if correct_dark:
            spectrum = np.clip(spectrum - 800.0 * scale, 0, self.max_intensity)
        return spectrum

    def set_integration_time_micros(self, micros: int) -> None:
        lo, hi = self.integration_time_micros_limits
        self._integration_us = int(np.clip(micros, lo, hi))

    @property
    def integration_time_micros_limits(self) -> tuple[int, int]:
        return (1000, 65_000_000)

    @property
    def max_intensity(self) -> float:
        return 65535.0


def open_spectrometer(force_mock: bool = False) -> SpectrometerBase:
    """Open the first available real spectrometer, else fall back to mock.

    Returns a tuple is not used; returns the spectrometer instance. Use
    ``isinstance(spec, MockSpectrometer)`` to detect simulation mode.
    """
    if force_mock:
        return MockSpectrometer()
    try:
        return SeabreezeSpectrometer()
    except Exception:
        # No device, missing backend, or driver issue -> simulate.
        return MockSpectrometer()
