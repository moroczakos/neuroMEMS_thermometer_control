# Thermometer Control App

A small Python GUI application for controlling a current source and a multimeter to measure temperature and visualize results. The app launches a tabbed interface of sub-apps (see `apps/CombinedApp.py`) and is intended as a desktop controller and plotter for experiment workflows.

## Why This Project Is Useful

This project provides a single, tabbed GUI for running multiple related tools used in temperature measurement workflows.

It helps you:

- Control measurement instruments from one interface.
- Plot recorded temperature data.
- Recalculate temperature from resistance values.
- Manage application-wide settings.
- Launch, monitor, and close related utilities from one desktop window.

The application is lightweight and desktop-friendly, using Tkinter.

## Features

- Tabbed GUI launcher combining multiple sub-apps via `apps/CombinedApp.py`
- **Temperature measurement station tab** for controlling:
  - Keithley \(2611\) and \(6211\) current sources.
  - Keithley \(2100\) digital multimeter.
  - Parallel and separate instrument control for thermoprobe-based temperature measurements.
- **Temperature plotter tab** for plotting recorded temperature from measured resistance and temperature data.
- **Temperature recalculation tab** for recalculating temperature from a selected thermoprobe and measured resistance values.
- **Settings tab** for general application settings.
- Window icon support through `icon.png`.
- Graceful shutdown handling.
- Extendable structure for device control, plotting, and data logging modules.

## Tech Stack

- Python
- Tkinter
- `pip` for dependency management

## Installation

1. Install Python \(3.8+ recommended\).
2. Clone the repository:

   ```bash
   git clone https://github.com/moroczakos/neuroMEMS_thermometer_control.git
   cd neuroMEMS_thermometer_control
```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Install any additional packages if they are required by submodules or indicated by runtime errors.

## Configuration

* Place or update `icon.png` in the repository root to change the application icon.
* Review `apps/CombinedApp.py` to configure which sub-apps are included in the tabbed interface.
* The `input_files` folder contains settings and input data files, for example:

  * `settings.json`
  * `thermoprobes.csv`

## Usage

Run the main GUI with:

```bash
python main.py
```

On Windows, run this from Command Prompt or PowerShell in the project root.

The application opens a (1600 \times 900) window with tabs for each included sub-app.

To close the application, use the window close button. The app calls `app.close_app()` before exiting to allow graceful cleanup.

## Example

Launch the application using:

```bash
python main.py
```

The repository includes `apps/CombinedApp.py`, which defines the tab layout. Open that file to see which sub-apps are available and how the interface is assembled.

## Project Structure

```text
.
├── main.py                  # Application entry point
├── apps/                    # GUI sub-apps and CombinedApp container
│   └── CombinedApp.py
├── input_files/             # Settings and input data files
├── icon.png                 # Optional application icon
└── requirements.txt         # Python dependencies
```

## Common Commands

* Run the GUI:

  ```bash
  python main.py
  ```

* Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

* Run tests: see the Testing section below.

## Testing

Automated tests are not currently included by default.

If testing is added in the future, create a `tests/` folder and run tests with the appropriate runner, such as:

```bash
pytest
```

Check the repository for specific test instructions if tests are available.

## Documentation and Help

* Use GitHub Issues for questions or bug reports:
  [GitHub Issues](https://github.com/moroczakos/neuroMEMS_thermometer_control/issues)
* Inspect module docstrings, tooltip descriptions, and files in `apps/` for implementation details and extension points.

## Maintainer

Repository owner: [moroczakos](https://github.com/moroczakos)

## Future Improvements

* Add unit and integration tests for critical components.
* Extend support for more measurement devices and probes.
* Improve data logging capabilities for real-time logging and historical analysis.
* Enhance the plotting capabilities with interactive features like zoom and annotation.
* Include support for remote control of the measurement instruments over a network.

## Screenshots

Here are a few screenshots of the app's interface:

1. **Temperature Measurement Station**:
   <img width="1602" height="939" alt="temp_meas_station" src="https://github.com/user-attachments/assets/e913b334-f27c-4614-883e-c8680a189092" />
   
2. **Temperature Plotter**:
   <img width="1602" height="939" alt="temp_plotter" src="https://github.com/user-attachments/assets/730613c9-3c0d-4306-a85e-64cd07c960f5" />
   
3. **Temperature Recalculation**:
   <img width="1602" height="939" alt="temp_recalc" src="https://github.com/user-attachments/assets/c0686dec-d5ac-406d-b891-e7d00945a2e6" />

4. **Settings**:
   <img width="1602" height="939" alt="settings" src="https://github.com/user-attachments/assets/613d9203-283f-4d7b-8557-4d0bc238fb3e" />




