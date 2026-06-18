"""Entry point for the Ocean Optics Flame spectrometer application."""
from __future__ import annotations

import argparse
import os
import sys

# Ensure local modules are importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5 import QtWidgets

from ui.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Ocean Optics Flame spectrometer GUI")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force simulation mode (do not attempt to open real hardware).",
    )
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(force_mock=args.mock)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
