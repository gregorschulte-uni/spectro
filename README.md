# spectro

A Python GUI application for **Ocean Optics / Ocean Insight Flame** spectrometers.
It continuously acquires and displays a live spectrum, lets you adjust the
spectrometer's parameters, and save spectra as `.txt` files.

Built with **PyQt5** + **PyQtGraph** for fast real-time plotting and
[**python-seabreeze**](https://python-seabreeze.readthedocs.io) for hardware
communication.

## Features

- Live continuous spectrum display (intensity vs. wavelength)
- Background acquisition thread keeps the UI responsive
- Adjustable parameters:
  - Integration time (ms)
  - Scans to average
  - Boxcar smoothing width
  - Electric dark correction
  - Nonlinearity correction
- Save the current spectrum to a tab-separated `.txt` file with a metadata header
- **Simulation mode** — if no device is found (or with `--mock`), a synthetic
  spectrum is generated so you can test the app without hardware

## Project layout

```
spectro/
├── requirements.txt
└── src/
    ├── main.py            # Entry point
    ├── spectrometer.py    # seabreeze wrapper + MockSpectrometer
    ├── acquisition.py     # Continuous acquisition QThread worker
    └── ui/
        └── main_window.py # PyQt window + PyQtGraph plot
```

## Quick start (easiest)

Use the included launcher scripts — they create the virtual environment,
install dependencies, and start the app automatically.

- **Windows:** double-click **`run.bat`** (or run `run.bat --mock` for simulation).
- **macOS / Linux:** in a terminal run:
  ```bash
  chmod +x run.sh   # first time only
  ./run.sh          # or ./run.sh --mock
  ```

The first launch takes a minute to set things up; later launches are fast.
Prefer to do it manually? See **Installation** below.

## Installation


```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Hardware setup (real device)

On Linux you need udev rules so the Flame is accessible without root:

```bash
seabreeze_os_setup
```

Then re-plug the device (or reboot). On Windows install the Ocean Optics
USB drivers. See the python-seabreeze docs for details.

> Note: USB devices are not accessible from cloud dev environments
> (e.g. GitHub Codespaces). Use `--mock` there to develop the UI.

## Usage

```bash
# Auto-detect a real device, fall back to simulation if none found
python src/main.py

# Force simulation mode
python src/main.py --mock
```

1. Click **Connect**.
2. Set your desired parameters.
3. Click **Start** to begin live acquisition.
4. Click **Save spectrum as .txt** to export the current spectrum.

## Testing in a GitHub Codespace (no hardware)

A Codespace has no USB access and no display, so use **mock mode**. Two options:

### Quick headless smoke test (no GUI visible)
Confirms the app boots and produces spectra:

```bash
sudo apt-get update
sudo apt-get install -y libgl1 libegl1 libxkbcommon0
pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen python scripts/smoke_test.py
```


A `SMOKE TEST PASSED` message means everything works.

### See and click the GUI in your browser (noVNC)
To actually interact with the window inside the Codespace:

```bash
sudo apt-get update
sudo apt-get install -y novnc x11vnc xvfb fluxbox \
    libgl1 libegl1 libxkbcommon0
pip install -r requirements.txt

# Start a virtual display + window manager
Xvfb :1 -screen 0 1280x800x24 &
export DISPLAY=:1
fluxbox &

# Expose the display over the browser on port 6080
x11vnc -display :1 -nopw -forever -shared &
websockify --web=/usr/share/novnc 6080 localhost:5900 &

# Launch the app
python src/main.py --mock
```

Then open the forwarded **port 6080** (VS Code "Ports" tab) and visit
`/vnc.html` to view and control the GUI in your browser.

> For real hardware, run on your local machine (Option A above) — USB devices
> cannot be reached from a cloud Codespace.

## Saved file format


Tab-separated, two columns (`Wavelength(nm)`, `Intensity(counts)`), preceded by a
commented header containing the timestamp, device model/serial, and acquisition
settings — readable by NumPy (`np.loadtxt`), Excel, Origin, etc.
