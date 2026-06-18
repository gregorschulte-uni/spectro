"""Headless smoke test: boot the app in mock mode, render one frame, exit.

Useful for verifying the GUI launches without a physical spectrometer or a
real display. Run under a virtual framebuffer in a Codespace:

    xvfb-run -a python scripts/smoke_test.py

Exit code 0 means the window built and produced at least one spectrum frame.
"""
from __future__ import annotations

import os
import sys

# Make the src/ package importable.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5 import QtCore, QtWidgets  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(force_mock=True)
    window.show()

    state = {"frames": 0}

    # Connect to the device and start acquisition programmatically.
    window.connect_device()
    window.start_acquisition()

    def on_frame(_wl, _inten):
        state["frames"] += 1

    if window._worker is not None:
        window._worker.spectrum_ready.connect(on_frame)

    # Stop after a short while and quit the event loop.
    def finish():
        window.stop_acquisition()
        app.quit()

    QtCore.QTimer.singleShot(1500, finish)
    app.exec_()

    if state["frames"] > 0:
        print(f"SMOKE TEST PASSED: received {state['frames']} spectrum frames.")
        return 0
    print("SMOKE TEST FAILED: no spectrum frames received.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
