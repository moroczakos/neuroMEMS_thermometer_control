import os
import sys
import tkinter as tk
from tkinter import Tk, ttk, filedialog
from utils.logger_manager import LoggerManager
from utils.ui_utils.logger_panel import LoggingPanel
from utils.settings_utils import load_probe_data, SettingManager
import csv
import traceback


class TemperatureByRecalibratedProbeDataApp:
    def __init__(self, root):
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        # File paths and settings
        self.file_path = None  # To store the file path selected by user
        self.project_root = ".."  # find_project_root()
        self.setting_manager = self._load_settings()
        self.logger = self._setup_logger()

        # Probes
        self.probes = load_probe_data(self.probe_path)
        self.selected_probe = tk.StringVar(value = self.setting_manager.load_setting("probe"))
        self.R0 = tk.DoubleVar()
        self.TCR = tk.DoubleVar()
        self.update_probe_values()

        self.setup_ui()
        self.setup_logger_panel()

    def _load_settings(self):
        settings_path = os.path.join(self.project_root, 'input_files', 'settings.json')
        setting_manager = SettingManager(settings_path)

        self.input_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("input_files")
        )
        self.output_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("output_files")
        )
        self.log_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("log_files")
        )
        self.probe_path = os.path.join(self.input_file_path, "thermoprobes.csv")

        return setting_manager

    def _setup_logger(self):
        log_path = os.path.join(self.log_file_path, "thermometer_calibration_app.log")
        self.logger_manager = LoggerManager(log_file = log_path)
        return self.logger_manager.get_logger()

    def setup_logger_panel(self):
        """Insert the reusable LoggingPanel into the GUI and link it to the logger."""
        self.logging_panel = LoggingPanel(self.root, logger = self.logger)
        self.logging_panel.pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        self.logger.info("Application started and UI initialized.")

    def setup_ui(self):
        """Set up the main user interface components."""
        frame = ttk.Frame(self.root, padding = 10)
        frame.pack(fill = tk.X)

        self.file_label = ttk.Label(frame, text = "No file selected.", width = 50)
        self.file_label.grid(row = 0, column = 0, columnspan = 4)

        ttk.Button(frame, text = "Select File", command = self.select_file).grid(row = 0, column = 5)

        ttk.Label(frame, text = "Thermoprobe:").grid(row = 1, column = 0)
        self.probe_dropdown = ttk.Combobox(frame, textvariable = self.selected_probe, values = list(self.probes.keys()),
                                           width = 11)
        self.probe_dropdown.grid(row = 1, column = 1)
        self.probe_dropdown.bind("<<ComboboxSelected>>", self.update_probe_values)

        ttk.Label(frame, text = "R₀:").grid(row = 1, column = 2)
        ttk.Entry(frame, textvariable = self.R0, width = 10, state = "readonly").grid(row = 1, column = 3)

        ttk.Label(frame, text = "TCR:").grid(row = 1, column = 4)
        ttk.Entry(frame, textvariable = self.TCR, width = 10, state = "readonly").grid(row = 1, column = 5)

        self.calibrate_button = ttk.Button(frame, text = "Save calibrated data",
                                           command = self.convert_resistance_to_temperature)
        self.calibrate_button.grid(row = 2, column = 0)
        self.calibrate_button.config(state = "disabled")

    def select_file(self):
        """Allow user to select a CSV file and plot the data."""
        self.file_path = filedialog.askopenfilename(
            title = "Select CSV File",
            filetypes = [("CSV Files", "*.csv")]
        )

        if self.file_path:
            self.file_label.config(text = f"Selected File: {os.path.basename(self.file_path)}")
            self.calibrate_button.config(state = "normal")
            self.logger.info(f"Selected File: {os.path.basename(self.file_path)}")
        else:
            self.file_label.config(text = "No file selected.")
            self.calibrate_button.config(state = "disabled")
            self.logger.warning("No file was selected.")

    def update_probe_values(self, event=None):
        probe = self.selected_probe.get()
        if probe in self.probes:
            self.R0.set(self.probes[probe]["R0"])
            self.TCR.set(self.probes[probe]["TCR"])
            self.setting_manager.save_setting("probe", probe)
            self.logger.info(f"Probe selected: {probe}, R0={self.R0.get()}, TCR={self.TCR.get()}")

    def convert_resistance_to_temperature(self):
        """Converts resistance data to temperature and writes it to a new CSV file."""
        output_csv = self.add_probe_to_filename()

        try:
            with open(self.file_path, mode = 'r') as infile, open(output_csv, mode = 'w', newline = '') as outfile:
                reader = csv.DictReader(infile)

                # Ensure 'Temperature (°C)' is not duplicated
                fieldnames = reader.fieldnames.copy()
                if 'Temperature (Celsius)' not in fieldnames:
                    fieldnames.append('Temperature (Celsius)')

                writer = csv.DictWriter(outfile, fieldnames = fieldnames)

                writer.writeheader()
                for row in reader:
                    resistance = float(row['Resistance (Ohms)'])
                    temperature = (resistance / self.R0.get() - 1) / self.TCR.get()
                    row['Temperature (Celsius)'] = temperature
                    writer.writerow(row)

            self.logger.info(f"Recalibrated data saved to: {output_csv}")
        except Exception as e:
            self.logger.error(f"Resistance to temperature conversion error: {e}\n {traceback.format_exc()}")

    def add_probe_to_filename(self):
        """
        Inserts 'probe' into a filename after 'log_'.

        Example:
        'log_Resistance_20250518_173912.csv' → 'log_probe_Resistance_Temperature_20250518_173912.csv'
        """
        directory, filename = os.path.split(self.file_path)
        base, ext = os.path.splitext(filename)

        # Split by underscores
        parts = base.split("_")

        if len(parts) >= 4 and parts[0] == "log":
            # Insert 'probe' after 'log'
            parts.insert(1, self.selected_probe.get())
            # Insert 'Temperature' before the timestamp (at index -2)
            parts.insert(-2, "Temperature")

            new_base = "_".join(parts)
        else:
            # Fallback if the format doesn't match the expected one
            new_base = f"{self.selected_probe.get()}_{base}"

        new_filename = f"{new_base}{ext}"
        return os.path.join(directory, new_filename)

    def close_app(self):
        self.logger_manager.close()


if __name__ == "__main__":
    # Create and run the Tkinter application
    root = Tk()
    root.title("Temperature by recalibrated probe data app")
    app = TemperatureByRecalibratedProbeDataApp(root)


    def on_close():
        app.close_app()
        root.destroy()
        sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
