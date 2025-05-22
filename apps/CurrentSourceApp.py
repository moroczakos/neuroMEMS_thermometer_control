import queue
import tkinter as tk
import traceback
from tkinter import ttk, messagebox
import threading
import time
from instruments.instrument_manager import InstrumentManager
from utils.file_utils import CsvLogger
from utils.measurement_profile import MeasurementProfile
from utils.plot_utils import update_plot, create_dual_axis_plot
import os
from utils.settings_utils import SettingManager
from utils.logger_manager import LoggerManager
from utils.ui_utils.logger_panel import LoggingPanel
from utils.other_utils import get_widget_value
from concurrent.futures import ThreadPoolExecutor


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
        self.current_high = tk.DoubleVar(value = self.setting_manager.load_setting("current_high"))
        self.current_low = tk.DoubleVar(value = self.setting_manager.load_setting("current_low"))
        self.duration_high = tk.IntVar(value = self.setting_manager.load_setting("duration_high"))
        self.duration_low = tk.IntVar(value = self.setting_manager.load_setting("duration_low"))
        self.cycles = tk.IntVar(value = self.setting_manager.load_setting("cycles"))
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting("interval"))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting("avg_count"))

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

    def setup_logger_panel(self):
        """Insert the reusable LoggingPanel into the GUI and link it to the logger."""
        self.logging_panel = LoggingPanel(self.root, logger = self.logger)
        self.logging_panel.pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        self.logger.info("Application started and UI initialized.")

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding = 10)
        frame.pack(fill = tk.X)

        # VISA selection
        ttk.Label(frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 2)

        self.refresh_button = ttk.Button(frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 3, padx = 5, pady = 10)

        # Current source and duration settings
        ttk.Label(frame, text = "----------Current source settings----------", justify = 'center').grid(row = 1,
                                                                                                        column = 0,
                                                                                                        columnspan = 6)

        ttk.Label(frame, text = "High Current (A):").grid(row = 2, column = 0)
        self.c_high_entry = ttk.Entry(frame, textvariable = self.current_high, width = 6, justify = 'center')
        self.c_high_entry.grid(row = 2, column = 1)
        self.current_high.trace("w", lambda *args: self.save_entry_value("current_high", self.current_high))

        ttk.Label(frame, text = "Low Current (A):").grid(row = 2, column = 2)
        self.c_low_entry = ttk.Entry(frame, textvariable = self.current_low, width = 6, justify = 'center')
        self.c_low_entry.grid(row = 2, column = 3)
        self.current_low.trace("w", lambda *args: self.save_entry_value("current_low", self.current_low))

        self.start_low_var = tk.BooleanVar(value = self.start_low)
        ttk.Label(frame, text = "Starts with low current:", ).grid(row = 2, column = 4)
        self.start_low_cbutton = ttk.Checkbutton(frame, variable = self.start_low_var, command = self.update_start_low)
        self.start_low_cbutton.grid(row = 2, column = 5)

        ttk.Label(frame, text = "High Duration (s):").grid(row = 3, column = 0)
        self.d_high_entry = ttk.Entry(frame, textvariable = self.duration_high, width = 6, justify = 'center')
        self.d_high_entry.grid(row = 3, column = 1)
        self.duration_high.trace("w", lambda *args: self.save_entry_value("duration_high", self.duration_high))

        ttk.Label(frame, text = "Low Duration (s):").grid(row = 3, column = 2)
        self.d_low_entry = ttk.Entry(frame, textvariable = self.duration_low, width = 6, justify = 'center')
        self.d_low_entry.grid(row = 3, column = 3)
        self.duration_low.trace("w", lambda *args: self.save_entry_value("duration_low", self.duration_low))

        ttk.Label(frame, text = "Cycles:").grid(row = 3, column = 4)
        self.cycles_entry = ttk.Entry(frame, textvariable = self.cycles, width = 6, justify = 'center')
        self.cycles_entry.grid(row = 3, column = 5, pady = 10)
        self.cycles.trace("w", lambda *args: self.save_entry_value("cycles", self.cycles))

        # Current measurement settings
        ttk.Label(frame, text = "--------Current measurement settings-------", justify = 'center').grid(row = 4,
                                                                                                        column = 0,
                                                                                                        columnspan = 6)

        ttk.Label(frame, text = "Interval (s):").grid(row = 5, column = 0)
        ttk.Entry(frame, textvariable = self.interval, width = 6, justify = 'center').grid(row = 5, column = 1)
        self.interval.trace("w", lambda *args: self.save_entry_value("interval", self.interval))

        ttk.Label(frame, text = "Average count:").grid(row = 5, column = 2)
        ttk.Entry(frame, textvariable = self.average_count, width = 6, justify = 'center').grid(row = 5, column = 3)
        self.average_count.trace("w", lambda *args: self.save_entry_value("avg_count", self.average_count))

        self.start_button = ttk.Button(frame, text = "Start", command = self.start_measurement)
        self.start_button.grid(row = 5, column = 4)

        self.stop_button = ttk.Button(frame, text = "Stop", command = self.stop_measurement, state = "disabled")
        self.stop_button.grid(row = 5, column = 5)

        ttk.Label(frame, text = "Live current (A):").grid(row = 6, column = 0, sticky = 'e')
        ttk.Label(frame, textvariable = self.current_y1, foreground = 'blue').grid(row = 6, column = 1,
                                                                                   sticky = 'w')

        ttk.Label(frame, text = "Live voltage (V):").grid(row = 6, column = 2, sticky = 'e')
        ttk.Label(frame, textvariable = self.voltage_y2, foreground = 'black').grid(row = 6, column = 3,
                                                                                    sticky = 'w')

    def load_visa_resources(self):
        resources = self.instrument_manager.list_resources(only_tcpip = False)
        if self.instrument_manager.allow_mock:
            resources = ("MOCK_6221", "MOCK_2611") + tuple(resources)
        self.visa_dropdown['values'] = resources
        self.visa_resource.set(resources[0] if resources else "No VISA resources found")
        self.logger.info(f"Loaded VISA resources: {resources}")

    def save_entry_value(self, name, value):
        try:
            v = get_widget_value(value)
            if v is not None:
                self.setting_manager.save_setting(name, v)
                self.logger.info(f"Saved setting '{name}': {v}")
        except Exception as e:
            self.logger.warning(f"Failed to save setting '{name}': {e}\n {traceback.format_exc()}")

    def setup_plot(self):
        _, ax1, ax2, line1, line2, self.canvas = create_dual_axis_plot(
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label, "blue",
            "black")
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]

    def perform_measurement(self):
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)
        y1, y2 = self.profile.measure_func(source_handler)
        y3 = self.profile.post_process_func(y1, y2) if self.profile.post_process_func else None
        self.current_y1.set(round(y1, 4))
        self.voltage_y2.set(round(y2, 2) if y2 is not None else float('nan'))
        return y1, y2, y3

    def start_measurement(self):
        if not self._connect():
            return

        self.running = True

        # Control widget accessibility
        self.start_button.config(state = "disabled")
        self.stop_button.config(state = "normal")
        self.c_high_entry.config(state = "disabled")
        self.c_low_entry.config(state = "disabled")
        self.start_low_cbutton.config(state = "disabled")
        self.d_high_entry.config(state = "disabled")
        self.d_low_entry.config(state = "disabled")
        self.cycles_entry.config(state = "disabled")

        # File setup
        self.csv_logger.create(f"log_{self.profile.name.replace('/', '_')}", self.profile.headers,
                               self.output_file_path)

        self.timestamps = []
        self.current_y1_data = []
        self.voltage_y2_data = []
        self.start_time = time.time()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        threading.Thread(target = self.cycle_loop, daemon = True).start()
        threading.Thread(target = self.data_worker_loop, daemon = True).start()
        self.logger.info("Started measurement.")

    def stop_measurement(self):
        if self.running:
            self.running = False

            # Control widget accessibility
            self.start_button.config(state = "normal")
            self.stop_button.config(state = "disabled")
            self.c_high_entry.config(state = "normal")
            self.c_low_entry.config(state = "normal")
            self.start_low_cbutton.config(state = "normal")
            self.d_high_entry.config(state = "normal")
            self.d_low_entry.config(state = "normal")
            self.cycles_entry.config(state = "normal")

            if self.instrument_manager.get_instrument(self.instrument_alias):
                self.instrument_manager.disconnect(self.instrument_alias)

            self.logger.info("Measurement stopped.")

            if hasattr(self, 'csv_logger'):
                self.logger.info(f"Data saved to {self.csv_logger.get_filename()}")
                self.csv_logger.close()

            if self.main_app:
                self.main_app.stop_apps()  # Stop main app

    def _connect(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return False
        try:
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
                self.logger.exception(
                    f"Not known model: {model}. Known models are 6221 and 2611\n {traceback.format_exc()}")
                messagebox.showerror("Not known model error",
                                     f"Not known model: {model}. Known models are 6221 and 2611")
                return

            self.instrument_manager.connect(self.instrument_alias, visa_address, role = self.instrument_alias)
            self.logger.info(f"Connected to VISA resource: {visa_address}")
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {e}\n {traceback.format_exc()}")
            messagebox.showerror("Connection Error", f"Could not open VISA resource:\n{e}")
            return False

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
        MAX_QUEUE_SIZE = 100
        while self.running or not self.data_queue.empty():
            try:
                if self.data_queue.qsize() > MAX_QUEUE_SIZE:
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
