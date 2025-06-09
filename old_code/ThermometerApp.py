# ─── Standard Library ────────────────────────────────────────────────────────
import os
import queue
import threading
import time
import traceback
from datetime import datetime

# ─── Third-Party Libraries ───────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor

# ─── Local Modules ───────────────────────────────────────────────────────────
from instruments.instrument_manager import InstrumentManager
from utils.constants import Keys, States, EntryConfig
from utils.file_utils import CsvLogger
from utils.logger_manager import LoggerManager, safe_execute
from utils.measurement_profile import MeasurementProfile
from utils.other_utils import (
    connect_with_popup,
    get_widget_value,
    load_visa_resources_util,
    save_setting_from_widget,
)
from utils.plot_utils import create_dual_axis_plot, update_plot
from utils.settings_utils import SettingManager, load_probe_data
from utils.ui_utils.logger_panel import LoggingPanel


class ThermometerApp:
    def __init__(self, root, main_app=None):
        self.main_app = main_app
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        # File paths and settings
        self.input_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'input_files'))
        self.output_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_files'))
        self.setting_manager = SettingManager(os.path.join(self.input_file_path, 'settings.json'))

        # Logger
        self.csv_logger = CsvLogger()  # Save timestamps, resistance, temperature
        self.raw_csv_logger = CsvLogger()  # Save timestamps, resistance,
        self.logger = LoggerManager(log_file = "../logs/thermometer_app.log").get_logger()

        # Instrument
        self.instrument_manager = InstrumentManager()

        # Control Variables
        self.running = False
        self.preview_running = False
        self.visa_resource = tk.StringVar()
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.INTERVAL))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting(Keys.AVG_COUNT))

        self.interval_curr = self.interval
        self.average_count_curr = self.average_count

        # Probes
        self.probes = load_probe_data(os.path.join(self.input_file_path, 'thermoprobes.csv'))
        self.selected_probe = tk.StringVar(value = self.setting_manager.load_setting("probe"))
        self.R0 = tk.DoubleVar()
        self.TCR = tk.DoubleVar()
        self.update_probe_values()

        # Data containers
        self.timestamps = []
        self.resistance_y1_data = []
        self.temperature_y2_data = []
        self.data_queue = queue.Queue()
        self.resistance_y1 = tk.DoubleVar()
        self.temperature_y2 = tk.DoubleVar()
        self.executor = None

        # Define measurement profile
        self.profile = MeasurementProfile(
            name = "Resistance/Temperature",
            headers = ["Timestamp", "Resistance (Ohms)", "Temperature (Celsius)"],
            y1_label = "Resistance (Ohms)",
            y2_label = "Temperature (°C)",
            measure_func = lambda dmm: dmm.measure(),
            post_process_func = lambda r, R0, TCR: (r / R0 - 1) / TCR if R0 > 0 and TCR > 0 else float('nan')
        )

        self.create_widgets()
        self.setup_plot()
        self.setup_logger_panel()
        self.load_visa_resources()

    def setup_logger_panel(self):
        """Insert the reusable LoggingPanel into the GUI and link it to the logger."""
        self.logging_panel = LoggingPanel(self.root, logger = self.logger)
        self.logging_panel.pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        self.logger.info("Application started and UI initialized.")

    def create_widgets(self):
        self.frame = ttk.Frame(self.root, padding = 10)
        self.frame.pack(fill = tk.X)

        self.create_visa_selector()
        self.create_thermoprobe_selector()
        self.create_measurement_settings_section()
        self.create_live_display_section()
        self.create_preview_section()

        # Placeholder to match height (6 rows)
        ttk.Label(self.frame, text = "").grid(row = 4, column = 0, pady = 9.5)
        ttk.Label(self.frame, text = "").grid(row = 5, column = 0)

    def create_visa_selector(self):
        ttk.Label(self.frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(self.frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3)

        self.refresh_button = ttk.Button(self.frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5, pady = 10)

    def create_thermoprobe_selector(self):
        ttk.Label(self.frame, text = "Thermoprobe:").grid(row = 1, column = 0)
        self.probe_dropdown = ttk.Combobox(self.frame, textvariable = self.selected_probe,
                                           values = list(self.probes.keys()),
                                           width = 11)
        self.probe_dropdown.grid(row = 1, column = 1)
        self.probe_dropdown.bind("<<ComboboxSelected>>", self.update_probe_values)

        ttk.Label(self.frame, text = "R₀:").grid(row = 1, column = 2)
        ttk.Entry(self.frame, textvariable = self.R0, width = 10, state = States.READONLY).grid(row = 1, column = 3)

        ttk.Label(self.frame, text = "TCR:").grid(row = 1, column = 4)
        ttk.Entry(self.frame, textvariable = self.TCR, width = 10, state = States.READONLY).grid(row = 1, column = 5)

    def create_measurement_settings_section(self):
        self._entry_with_label(2, 0, "Interval (s):", self.interval, self.save_entry_value, Keys.INTERVAL)
        self._entry_with_label(2, 2, "Average count:", self.average_count, self.save_entry_value, Keys.AVG_COUNT)

        self.start_button = ttk.Button(self.frame, text = "Start", command = self.start_measurement)
        self.start_button.grid(row = 2, column = 4)

        self.stop_button = ttk.Button(self.frame, text = "Stop", command = self.stop_measurement,
                                      state = States.DISABLED)
        self.stop_button.grid(row = 2, column = 5)

    def create_live_display_section(self):
        ttk.Label(self.frame, text = f"Live {self.profile.y1_label}:").grid(row = 3, column = 0, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.resistance_y1).grid(row = 3, column = 1, sticky = 'w')
        ttk.Label(self.frame, text = f"Live {self.profile.y2_label}:").grid(row = 3, column = 2, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.temperature_y2, foreground = 'red').grid(row = 3, column = 3,
                                                                                           sticky = 'w')

    def create_preview_section(self):
        self.preview_start_button = ttk.Button(self.frame, text = "Start Preview", command = self.start_preview)
        self.preview_start_button.grid(row = 3, column = 4)
        self.preview_stop_button = ttk.Button(self.frame, text = "Stop Preview", command = self.stop_preview,
                                              state = States.DISABLED)
        self.preview_stop_button.grid(row = 3, column = 5)

    def _entry_with_label(self, row, col, label, variable, trace_callback=None, key=None):
        ttk.Label(self.frame, text = label).grid(row = row, column = col)
        entry = ttk.Entry(self.frame, textvariable = variable, width = EntryConfig.WIDTH, justify = EntryConfig.JUSTIFY)
        entry.grid(row = row, column = col + 1)
        if trace_callback and key:
            variable.trace_add("write", lambda *args: trace_callback(key, variable))
        return entry

    @safe_execute
    def load_visa_resources(self):
        resources = load_visa_resources_util(self.instrument_manager,
                                             only_tcpip = False,
                                             logger = self.logger,
                                             include_mock = True,
                                             mock_resources = ("MOCK",))
        self.visa_dropdown['values'] = resources
        self.visa_resource.set(resources[0] if resources else "No VISA resources found")
        self.logger.info(f"Loaded VISA resources: {resources}")

    def save_entry_value(self, name, value):
        save_setting_from_widget(self.setting_manager, name, value, logger = self.logger)

    def setup_plot(self):
        _, ax1, ax2, line1, line2, self.canvas = create_dual_axis_plot(
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label)
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]

    def perform_measurement(self):
        dmm_handler = self.instrument_manager.get_handler("dmm")
        y1 = self.profile.measure_func(dmm_handler)["resistance"]
        y2 = self.profile.post_process_func(y1, self.R0.get(), self.TCR.get()) if self.profile.post_process_func else y1
        self.resistance_y1.set(round(y1, 4))
        self.temperature_y2.set(round(y2, 2))
        return y1, y2

    @safe_execute
    def update_probe_values(self, event=None):
        probe = self.selected_probe.get()
        if probe in self.probes:
            self.R0.set(self.probes[probe]["R0"])
            self.TCR.set(self.probes[probe]["TCR"])
            self.setting_manager.save_setting("probe", probe)
            self.logger.info(f"Probe selected: {probe}, R0={self.R0.get()}, TCR={self.TCR.get()}")

    @safe_execute
    def start_preview(self):
        if not self._connect():
            return
        self.preview_running = True
        self.preview_start_button.config(state = States.DISABLED)
        self.preview_stop_button.config(state = States.NORMAL)
        self.start_button.config(state = States.DISABLED)
        threading.Thread(target = self.preview_loop, daemon = True).start()
        self.logger.info("Started preview mode.")

    @safe_execute
    def stop_preview(self):
        self.preview_running = False
        self.preview_start_button.config(state = States.NORMAL)
        self.preview_stop_button.config(state = States.DISABLED)
        self.start_button.config(state = States.NORMAL)

        self.instrument_manager.disconnect("dmm")
        self.logger.info("Stopped preview mode.")

    @safe_execute
    def enable_preview(self):
        self.preview_start_button.config(state = States.NORMAL)
        self.preview_stop_button.config(state = States.DISABLED)

    @safe_execute
    def disable_preview(self):
        self.preview_start_button.config(state = States.DISABLED)
        self.preview_stop_button.config(state = States.DISABLED)

    def preview_loop(self):
        while self.preview_running:
            try:
                self.perform_measurement()
                time.sleep(self.interval.get())
            except Exception as e:
                self.logger.error(f"Preview error: {e}\n {traceback.format_exc()}")
                break

    @safe_execute
    def start_measurement(self):
        if not self._connect():
            return

        self.running = True
        self.start_button.config(state = States.DISABLED)
        self.stop_button.config(state = States.NORMAL)
        self.disable_preview()

        start_time = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.csv_logger.set_file_name(
            f"log_{self.profile.name.replace('/', '_')}_{self.selected_probe.get()}_{start_time}.csv")
        self.csv_logger.set_file_directory(self.output_file_path)
        self.csv_logger.set_first_row(self.profile.headers)
        self.csv_logger.create()

        self.raw_csv_logger.set_file_name(
            f"log_Resistance_{start_time}.csv")
        self.raw_csv_logger.set_file_directory(self.output_file_path)
        self.raw_csv_logger.set_first_row(self.profile.headers[0:2])
        self.raw_csv_logger.create()

        self.timestamps.clear()
        self.resistance_y1_data.clear()
        self.temperature_y2_data.clear()
        self.start_time = time.time()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        threading.Thread(target = self.measure_loop, daemon = True).start()
        threading.Thread(target = self.data_worker_loop, daemon = True).start()
        self.logger.info("Started measurement.")

    @safe_execute
    def stop_measurement(self):
        if self.running:
            self.running = False
            self.start_button.config(state = States.NORMAL)
            self.stop_button.config(state = States.DISABLED)
            self.enable_preview()

            self.instrument_manager.disconnect("dmm")
            if self.executor:
                self.executor.shutdown(wait = False)
            self.csv_logger.close()
            self.raw_csv_logger.close()
            self.logger.info(
                f"Measurement stopped. Data saved to {self.csv_logger.get_full_filename()} and {self.raw_csv_logger.get_full_filename()}")

            if self.main_app:
                self.main_app.stop_apps()  # Stop main app

    def _connect(self):
        visa_address = self.visa_resource.get()

        def connect_func():
            self.instrument_manager.connect("dmm", visa_address, role = "dmm")

        return connect_with_popup(self.root, visa_address, self.logger, connect_func)

    def measure_loop(self):
        self.data_counter = 0
        self.total_y1 = 0.0
        self.total_y2 = 0.0

        while self.running:
            try:
                y1, y2 = self.perform_measurement()
                timestamp = time.time() - self.start_time
                self.data_queue.put((timestamp, y1, y2))

                interval = get_widget_value(self.interval)
                if interval is not None:
                    self.interval_curr = interval
                time.sleep(self.interval_curr)
            except Exception as e:
                self.running = False
                self.logger.error(f"Measurement error: {e}\n {traceback.format_exc()}")

                error = self.instrument_manager.get_error("dmm")
                if error:
                    self.logger.error(error)
                break

    def data_worker_loop(self):
        MAX_QUEUE_SIZE = 100
        while self.running or not self.data_queue.empty():
            try:
                if self.data_queue.qsize() > MAX_QUEUE_SIZE:
                    self.logger.warning("⚠️ Queue backlog detected!")
                timestamp, y1, y2 = self.data_queue.get(timeout = 0.5)
                if self.running:
                    self.executor.submit(self.safe_log, timestamp, y1, y2)
                    self.executor.submit(self.safe_plot, timestamp, y1, y2)
            except queue.Empty:
                continue

    def safe_log(self, timestamp, y1, y2):
        try:
            self.csv_logger.write_row([timestamp, y1, y2])
            self.raw_csv_logger.write_row([timestamp, y1])
        except Exception as e:
            self.logger.error(f"Logging error: {e}\n {traceback.format_exc()}")

    def safe_plot(self, timestamp, y1, y2):
        try:
            avg_count = get_widget_value(self.average_count)
            if avg_count is not None:
                self.average_count_curr = avg_count

            self.data_counter += 1
            self.total_y1 += y1
            self.total_y2 += y2
            if self.data_counter >= self.average_count_curr:
                self.timestamps.append(timestamp)
                self.resistance_y1_data.append(self.total_y1 / self.average_count_curr)
                self.temperature_y2_data.append(self.total_y2 / self.average_count_curr)
                self.data_counter = 0
                self.total_y1 = 0.0
                self.total_y2 = 0.0
                self.update_plot()
        except Exception as e:
            self.logger.error(f"Plotting error: {e}\n {traceback.format_exc()}")

    def update_plot(self):
        line_data_pairs = [
            (self.lines[0], (self.timestamps, self.resistance_y1_data)),
            (self.lines[1], (self.timestamps, self.temperature_y2_data))
        ]
        update_plot(line_data_pairs, self.axes, self.canvas)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Keithley 2100 4-Wire Resistance Logger")
    app = ThermometerApp(root)
    root.mainloop()
