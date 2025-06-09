# ─── Standard Library ────────────────────────────────────────────────────────
import os
import queue
import threading
import time
import traceback

# ─── Third-Party Libraries ───────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ─── Local Modules ───────────────────────────────────────────────────────────
from concurrent.futures import ThreadPoolExecutor
from instruments.instrument_manager import InstrumentManager
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
from utils.settings_utils import SettingManager
from utils.ui_utils.logger_panel import LoggingPanel
from utils.constants import Keys, EntryConfig, States, Labels, UI, Other


class CurrentCycleApp:
    def __init__(self, root, main_app=None):
        self.main_app = main_app
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        # Settings
        self.input_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'input_files'))
        self.output_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_files'))
        self.setting_manager = SettingManager(os.path.join(self.input_file_path, 'settings.json'))
        self.start_low = True  # Square wave current starts with low value

        # Logger
        self.csv_logger = CsvLogger()
        self.logger = LoggerManager(log_file = "../logs/current_source_app.log").get_logger()

        # Instrument
        self.instrument_manager = InstrumentManager()
        self.instrument_alias = None

        # Control variables
        self.running = False
        self.visa_resource = tk.StringVar()
        self.current_high = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.CURRENT_HIGH))
        self.current_low = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.CURRENT_LOW))
        self.duration_high = tk.IntVar(value = self.setting_manager.load_setting(Keys.DURATION_HIGH))
        self.duration_low = tk.IntVar(value = self.setting_manager.load_setting(Keys.DURATION_LOW))
        self.cycles = tk.IntVar(value = self.setting_manager.load_setting(Keys.CYCLES))
        self.other_settings = tk.StringVar()
        self.other_settings_value = tk.DoubleVar()
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.INTERVAL))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting(Keys.AVG_COUNT))

        self.interval_curr = self.interval
        self.average_count_curr = self.average_count

        # Data
        self.timestamps = []
        self.current_y1_data = []
        self.voltage_y2_data = []
        self.data_queue = queue.Queue()
        self.current_y1 = tk.DoubleVar()
        self.voltage_y2 = tk.DoubleVar()
        self.executor = None

        # Define measurement profile
        self.profile = MeasurementProfile(
            name = "Current/Voltage/Resistance",
            headers = ["Timestamp", "Current (A)", "Voltage (V)", "Resistance (Ohms)"],
            y1_label = "Current (A)",
            y2_label = "Voltage (V)",
            measure_func = lambda source: source.measure(),
            post_process_func = lambda a, v: v / a if v is not None else float('nan')
        )

        self.create_widgets()
        self.setup_plot()
        self.setup_logger_panel()
        self.load_visa_resources()
        self.load_other_settings()

    def setup_logger_panel(self):
        """Insert the reusable LoggingPanel into the GUI and link it to the logger."""
        self.logging_panel = LoggingPanel(self.root, logger = self.logger)
        self.logging_panel.pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        self.logger.info("Application started and UI initialized.")

    def create_widgets(self):
        self.frame = ttk.Frame(self.root, padding = 10)
        self.frame.pack(fill = tk.X)

        self.create_visa_selector()
        self.create_current_settings_section()
        self.create_other_settings_section()
        self.create_measurement_settings_section()
        self.create_live_display_section()

    def create_visa_selector(self):
        ttk.Label(self.frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(self.frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3)

        self.refresh_button = ttk.Button(self.frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5, pady = 10)

    def create_current_settings_section(self):
        row = 1
        ttk.Label(self.frame, text = Labels.CURRENT_SOURCE_SETTINGS, justify = 'center') \
            .grid(row = row, column = 0, columnspan = 9)

        row += 1
        self.c_high_entry = self._entry_with_label(row, 0, "High Current (A):", self.current_high,
                                                   self.save_entry_value, Keys.CURRENT_HIGH)
        self.c_low_entry = self._entry_with_label(row, 2, "Low Current (A):", self.current_low, self.save_entry_value,
                                                  Keys.CURRENT_LOW)

        ttk.Label(self.frame, text = Labels.STARTS_WITH_LOW).grid(row = row, column = 4)
        self.start_low_var = tk.BooleanVar(value = self.start_low)
        self.start_low_cbutton = ttk.Checkbutton(self.frame, variable = self.start_low_var,
                                                 command = self.update_start_low)
        self.start_low_cbutton.grid(row = row, column = 5)

        self.cycles_entry = self._entry_with_label(row, 6, "Cycles:", self.cycles, self.save_entry_value, Keys.CYCLES)

        row += 1
        self.d_high_entry = self._entry_with_label(row, 0, "High Duration (s):", self.duration_high,
                                                   self.save_entry_value, Keys.DURATION_HIGH)
        self.d_low_entry = self._entry_with_label(row, 2, "Low Duration (s):", self.duration_low, self.save_entry_value,
                                                  Keys.DURATION_LOW)

    def create_other_settings_section(self):
        ttk.Label(self.frame, text = Labels.OTHER_SETTINGS).grid(row = 3, column = 4)

        self.other_settings_dropdown = ttk.Combobox(
            self.frame, textvariable = self.other_settings, width = 16, state = States.READONLY
        )
        self.other_settings_dropdown.grid(row = 3, column = 5, columnspan = 2)
        self.other_settings_dropdown.bind("<<ComboboxSelected>>", self.on_other_setting_selected)

        self.other_settings_entry = ttk.Entry(
            self.frame, textvariable = self.other_settings_value, width = EntryConfig.WIDTH,
            justify = EntryConfig.JUSTIFY
        )
        self.other_settings_entry.grid(row = 3, column = 7)

        self.save_other_button = ttk.Button(self.frame, text = Labels.SAVE, command = self.save_other_setting)
        self.save_other_button.grid(row = 3, column = 8, padx = 5)

    def create_measurement_settings_section(self):
        ttk.Label(self.frame, text = Labels.CURRENT_MEASUREMENT_SETTINGS, justify = 'center') \
            .grid(row = 4, column = 0, columnspan = 9)

        self._entry_with_label(5, 0, "Interval (s):", self.interval, self.save_entry_value, Keys.INTERVAL)
        self._entry_with_label(5, 2, "Average count:", self.average_count, self.save_entry_value, Keys.AVG_COUNT)

        self.start_button = ttk.Button(self.frame, text = "Start", command = self.start_measurement)
        self.start_button.grid(row = 5, column = 4)

        self.stop_button = ttk.Button(self.frame, text = "Stop", command = self.stop_measurement,
                                      state = States.DISABLED)
        self.stop_button.grid(row = 5, column = 5)

    def create_live_display_section(self):
        ttk.Label(self.frame, text = "Live current (A):").grid(row = 6, column = 0, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.current_y1, foreground = 'blue').grid(row = 6, column = 1,
                                                                                        sticky = 'w')

        ttk.Label(self.frame, text = "Live voltage (V):").grid(row = 6, column = 2, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.voltage_y2, foreground = 'black').grid(row = 6, column = 3,
                                                                                         sticky = 'w')

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
                                             mock_resources = ("MOCK_6221", "MOCK_2611"))
        self.visa_dropdown['values'] = resources
        self.visa_resource.set(resources[0] if resources else "No VISA resources found")
        self.logger.info(f"Loaded VISA resources: {resources}")

    def load_other_settings(self):
        try:
            # Save current selection
            current_key = self.other_settings.get()

            values = self.setting_manager.load_setting("device_settings")
            if not isinstance(values, dict):
                values = {}

            keys = list(values.keys())
            self.other_settings_dropdown['values'] = keys

            # Restore current selection if it still exists
            if current_key in keys:
                self.other_settings.set(current_key)
            elif keys:
                self.other_settings.set(keys[0])
            else:
                self.other_settings.set("")
                self.other_settings_value.set(0.0)

            self.on_other_setting_selected()

        except Exception as e:
            self.logger.warning(f"Failed to load device settings: {e}\n{traceback.format_exc()}")
            self.other_settings_dropdown['values'] = []

    def on_other_setting_selected(self, event=None):
        try:
            key = self.other_settings.get()
            settings_dict = self.setting_manager.load_setting("device_settings")
            if isinstance(settings_dict, dict) and key in settings_dict:
                self.other_settings_value.set(settings_dict[key])
                self.logger.info(f"Loaded device setting '{key}': {settings_dict[key]}")
            else:
                self.other_settings_value.set(0.0)
        except Exception as e:
            self.logger.warning(f"Failed to load selected device setting: {e}\n{traceback.format_exc()}")
            self.other_settings_value.set(0.0)

    def save_other_setting(self):
        try:
            key = self.other_settings.get()
            value = self.other_settings_value.get()
            if not key:
                messagebox.showwarning("Warning", "Setting name is empty.")
                return

            settings_dict = self.setting_manager.load_setting("device_settings")
            if not isinstance(settings_dict, dict):
                settings_dict = {}

            settings_dict[key] = value
            self.setting_manager.save_setting("device_settings", settings_dict)

            self.load_other_settings()
            self.other_settings.set(key)  # Keep focus on saved key
            self.logger.info(f"Saved device setting '{key}': {value}")
        except Exception as e:
            self.logger.error(f"Failed to save other setting: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to save setting: {e}")

    def save_entry_value(self, name, value):
        save_setting_from_widget(self.setting_manager, name, value, logger = self.logger)

    def setup_plot(self):
        _, ax1, ax2, line1, line2, self.canvas = create_dual_axis_plot(
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label, "blue",
            "black")
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]

    def perform_measurement(self):
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)
        meas_dict = self.profile.measure_func(source_handler)
        y1 = meas_dict["current"]
        if "voltage" in meas_dict:
            y2 = meas_dict["voltage"]
        else:
            y2 = None
        if "resistance" in meas_dict:
            y3 = meas_dict["resistance"]
        else:
            y3 = self.profile.post_process_func(y1, y2) if self.profile.post_process_func else None
        self.root.after(0, lambda: self.current_y1.set(round(y1, 4)))
        self.root.after(0, lambda: self.voltage_y2.set(round(y2, 2)) if y2 is not None else float('nan'))
        return y1, y2, y3

    def set_widget_states(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.start_button.config(state = state)
        self.stop_button.config(state = "normal" if not enabled else "disabled")

        widgets = [
            self.visa_dropdown,
            self.refresh_button,
            self.c_high_entry,
            self.c_low_entry,
            self.start_low_cbutton,
            self.d_high_entry,
            self.d_low_entry,
            self.cycles_entry,
            self.other_settings_dropdown,
            self.other_settings_entry,
            self.save_other_button,
        ]

        for widget in widgets:
            widget.config(state = state)

    @safe_execute
    def start_measurement(self):
        if not self._connect():
            return
        self.configure_device()

        self.running = True

        # Control widget accessibility
        self.set_widget_states(enabled = False)

        # File setup
        self.csv_logger.set_file_name(
            f"log_{self.profile.name.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.csv_logger.set_file_directory(self.output_file_path)
        self.csv_logger.set_first_row(self.profile.headers)
        self.csv_logger.create()

        self.timestamps = []
        self.current_y1_data = []
        self.voltage_y2_data = []
        self.start_time = time.time()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        threading.Thread(target = self.cycle_loop, daemon = True).start()
        threading.Thread(target = self.data_worker_loop, daemon = True).start()
        self.logger.info("Started measurement.")

    @safe_execute
    def stop_measurement(self):
        if self.running:
            self.running = False

            if self.executor:
                self.executor.shutdown(wait = False)

            # Control widget accessibility
            self.set_widget_states(enabled = True)

            if self.instrument_manager.get_instrument(self.instrument_alias):
                self.instrument_manager.disconnect(self.instrument_alias)

            self.logger.info("Measurement stopped.")

            if hasattr(self, 'csv_logger'):
                self.logger.info(f"Data saved to {self.csv_logger.get_full_filename()}")
                self.csv_logger.close()

            if self.main_app:
                self.main_app.stop_apps()  # Stop main app

    def _connect(self):
        visa_address = self.visa_resource.get()

        def connect_func():
            if "6221" in visa_address:
                model = "6221"
            elif "2611" in visa_address:
                model = "2611"
            else:
                model = self.instrument_manager.get_instrument_model(visa_address)

            if "6221" in model:
                self.instrument_alias = "source_6221"
            elif "2611" in model:
                self.instrument_alias = "source_2611"
            else:
                raise ValueError(f"Unknown model: {model}. Expected 6221 or 2611.")

            self.instrument_manager.connect(self.instrument_alias, visa_address, role = self.instrument_alias)

        return connect_with_popup(self.root, visa_address, self.logger, connect_func)

    def configure_device(self):
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)
        settings_dict = self.setting_manager.load_setting("device_settings")

        current_range = settings_dict.get(Keys.CURRENT_RANGE_KEY)
        voltage_limit = settings_dict.get(Keys.VOLTAGE_LIMIT_KEY)

        if current_range:
            source_handler.set_current_range(current_range)
        if voltage_limit:
            source_handler.set_voltage_limit(voltage_limit)

    @safe_execute
    def update_start_low(self):
        # Update self.start_low based on the checkbox state
        self.start_low = self.start_low_var.get()
        self.logger.info(f"The start with low current state changed to {self.start_low}")

    def cycle_loop(self):
        threading.Thread(target = self.measure_loop, daemon = True).start()
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)

        try:
            first_current, second_current = (
                self.current_low.get(), self.current_high.get()) if self.start_low else (
                self.current_high.get(), self.current_low.get())
            first_duration, second_duration = (
                self.duration_low.get(), self.duration_high.get()) if self.start_low else (
                self.duration_high.get(), self.duration_low.get())

            for cycle in range(self.cycles.get()):
                if not self.running: break
                self.logger.info(f"Cycle {cycle + 1}/{self.cycles.get()}: Setting current to {first_current}A")
                source_handler.set_current(first_current)
                time.sleep(first_duration)

                if not self.running: break
                self.logger.info(f"Cycle {cycle + 1}/{self.cycles.get()}: Setting current to {second_current}A")
                source_handler.set_current(second_current)
                time.sleep(second_duration)
        except Exception as e:
            self.logger.exception(f"Cycle Error {e}\n {traceback.format_exc()}")
            messagebox.showerror("Cycle Error", str(e))

        if self.running:
            self.stop_measurement()

    def measure_loop(self):
        self.data_counter = 0
        self.total_y1 = 0.0
        self.total_y2 = 0.0

        while self.running:
            try:
                y1, y2, y3 = self.perform_measurement()
                timestamp = time.time() - self.start_time
                self.data_queue.put(
                    (timestamp,
                     y1,
                     y2 if y2 is not None else float('nan'),
                     y3 if y3 is not None else float('nan')))

                interval = get_widget_value(self.interval)
                if interval is not None:
                    self.interval_curr = interval
                time.sleep(self.interval_curr)
            except Exception as e:
                self.running = False
                self.logger.error(f"Measurement error: {e}\n {traceback.format_exc()}")

                error = self.instrument_manager.get_error(self.instrument_alias)
                if error:
                    self.logger.error(error)
                break

    def data_worker_loop(self):
        while self.running or not self.data_queue.empty():
            try:
                if self.data_queue.qsize() > Other.MAX_QUEUE_SIZE:
                    self.logger.warning("⚠️ Queue backlog detected!")
                timestamp, y1, y2, y3 = self.data_queue.get(timeout = 0.5)
                if self.running:
                    self.executor.submit(self.safe_log, timestamp, y1, y2, y3)
                    self.executor.submit(self.safe_plot, timestamp, y1, y2)
            except queue.Empty:
                continue

    def safe_log(self, timestamp, y1, y2, y3):
        try:
            self.csv_logger.write_row([timestamp, y1, y2, y3])
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
                self.current_y1_data.append(self.total_y1 / self.average_count_curr)
                self.voltage_y2_data.append(self.total_y2 / self.average_count_curr)
                self.data_counter = 0
                self.total_y1 = 0.0
                self.total_y2 = 0.0
                self.update_plot()

            if len(self.timestamps) > UI.MAX_POINTS:
                self.timestamps = self.timestamps[-
                                                  UI.MAX_POINTS:]
                self.current_y1_data = self.current_y1_data[-UI.MAX_POINTS:]
                self.voltage_y2_data = self.voltage_y2_data[-UI.MAX_POINTS:]
        except Exception as e:
            self.logger.error(f"Plotting error: {e}\n {traceback.format_exc()}")

    def update_plot(self):
        line_data_pairs = [
            (self.lines[0], (self.timestamps, self.current_y1_data)),
            (self.lines[1], (self.timestamps, self.voltage_y2_data))
        ]
        update_plot(line_data_pairs, self.axes, self.canvas)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Current Source")
    app = CurrentCycleApp(root)
    root.mainloop()
