import tkinter as tk
import traceback
from tkinter import ttk, messagebox
import threading
import time
import os
import queue
from concurrent.futures import ThreadPoolExecutor
from instruments.instrument_manager import InstrumentManager
from utils.file_utils import CsvLogger
from utils.plot_utils import create_dual_axis_plot, update_plot
from utils.settings_utils import load_probe_data, SettingManager
from utils.logger_manager import LoggerManager
from utils.ui_utils.logger_panel import LoggingPanel
from utils.other_utils import get_widget_value
from utils.measurement_profile import MeasurementProfile


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
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting("interval"))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting("avg_count"))

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
        frame = ttk.Frame(self.root, padding = 10)
        frame.pack(fill = tk.X)

        ttk.Label(frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3)

        self.refresh_button = ttk.Button(frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5, pady = 10)

        ttk.Label(frame, text = "Thermoprobe:").grid(row = 1, column = 0)
        self.probe_dropdown = ttk.Combobox(frame, textvariable = self.selected_probe, values = list(self.probes.keys()),
                                           width = 11)
        self.probe_dropdown.grid(row = 1, column = 1)
        self.probe_dropdown.bind("<<ComboboxSelected>>", self.update_probe_values)

        ttk.Label(frame, text = "R₀:").grid(row = 1, column = 2)
        ttk.Entry(frame, textvariable = self.R0, width = 10, state = "readonly").grid(row = 1, column = 3)

        ttk.Label(frame, text = "TCR:").grid(row = 1, column = 4)
        ttk.Entry(frame, textvariable = self.TCR, width = 10, state = "readonly").grid(row = 1, column = 5)

        ttk.Label(frame, text = "Interval (s):").grid(row = 2, column = 0)
        ttk.Entry(frame, textvariable = self.interval, width = 6).grid(row = 2, column = 1)
        self.interval.trace("w", lambda *args: self.save_entry_value("interval", self.interval))

        ttk.Label(frame, text = "Average count:").grid(row = 2, column = 2)
        ttk.Entry(frame, textvariable = self.average_count, width = 6).grid(row = 2, column = 3)
        self.average_count.trace("w", lambda *args: self.save_entry_value("avg_count", self.average_count))

        self.start_button = ttk.Button(frame, text = "Start", command = self.start_measurement)
        self.start_button.grid(row = 2, column = 4)
        self.stop_button = ttk.Button(frame, text = "Stop", command = self.stop_measurement, state = "disabled")
        self.stop_button.grid(row = 2, column = 5)

        ttk.Label(frame, text = f"Live {self.profile.y1_label}:").grid(row = 3, column = 0, sticky = 'e')
        ttk.Label(frame, textvariable = self.resistance_y1).grid(row = 3, column = 1, sticky = 'w')
        ttk.Label(frame, text = f"Live {self.profile.y2_label}:").grid(row = 3, column = 2, sticky = 'e')
        ttk.Label(frame, textvariable = self.temperature_y2, foreground = 'red').grid(row = 3, column = 3, sticky = 'w')

        self.preview_start_button = ttk.Button(frame, text = "Start Preview", command = self.start_preview)
        self.preview_start_button.grid(row = 3, column = 4)
        self.preview_stop_button = ttk.Button(frame, text = "Stop Preview", command = self.stop_preview,
                                              state = "disabled")
        self.preview_stop_button.grid(row = 3, column = 5)

        # Placeholder to match height (6 rows)
        ttk.Label(frame, text = "").grid(row = 4, column = 0, pady = 8)
        ttk.Label(frame, text = "").grid(row = 5, column = 0)
        ttk.Label(frame, text = "").grid(row = 6, column = 0)

    def load_visa_resources(self):
        resources = self.instrument_manager.list_resources()
        if self.instrument_manager.allow_mock:
            resources = ("MOCK",) + tuple(resources)
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
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label)
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]

    def perform_measurement(self):
        dmm_handler = self.instrument_manager.get_handler("dmm")
        y1 = self.profile.measure_func(dmm_handler)
        y2 = self.profile.post_process_func(y1, self.R0.get(), self.TCR.get()) if self.profile.post_process_func else y1
        self.resistance_y1.set(round(y1, 4))
        self.temperature_y2.set(round(y2, 2))
        return y1, y2

    def update_probe_values(self, event=None):
        probe = self.selected_probe.get()
        if probe in self.probes:
            self.R0.set(self.probes[probe]["R0"])
            self.TCR.set(self.probes[probe]["TCR"])
            self.setting_manager.save_setting("probe", probe)
            self.logger.info(f"Probe selected: {probe}, R0={self.R0.get()}, TCR={self.TCR.get()}")

    def start_preview(self):
        if not self._connect():
            return
        self.preview_running = True
        self.preview_start_button.config(state = "disabled")
        self.preview_stop_button.config(state = "normal")
        self.start_button.config(state = "disabled")
        threading.Thread(target = self.preview_loop, daemon = True).start()
        self.logger.info("Started preview mode.")

    def stop_preview(self):
        self.preview_running = False
        self.preview_start_button.config(state = "normal")
        self.preview_stop_button.config(state = "disabled")
        self.start_button.config(state = "normal")

        self.instrument_manager.disconnect("dmm")
        self.logger.info("Stopped preview mode.")

    def enable_preview(self):
        self.preview_start_button.config(state = "normal")
        self.preview_stop_button.config(state = "disabled")

    def disable_preview(self):
        self.preview_start_button.config(state = "disabled")
        self.preview_stop_button.config(state = "disabled")

    def preview_loop(self):
        while self.preview_running:
            try:
                self.perform_measurement()
                time.sleep(self.interval.get())
            except Exception as e:
                self.logger.error(f"Preview error: {e}\n {traceback.format_exc()}")
                break

    def start_measurement(self):
        if not self._connect():
            return

        self.running = True
        self.start_button.config(state = "disabled")
        self.stop_button.config(state = "normal")
        self.disable_preview()

        self.csv_logger.create(f"log_{self.selected_probe.get()}_{self.profile.name.replace('/', '_')}",
                               self.profile.headers,
                               self.output_file_path)
        self.raw_csv_logger.create(f"log_Resistance", self.profile.headers[0:2],
                                   self.output_file_path)
        self.timestamps.clear()
        self.resistance_y1_data.clear()
        self.temperature_y2_data.clear()
        self.start_time = time.time()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        threading.Thread(target = self.measure_loop, daemon = True).start()
        threading.Thread(target = self.data_worker_loop, daemon = True).start()
        self.logger.info("Started measurement.")

    def stop_measurement(self):
        if self.running:
            self.running = False
            self.start_button.config(state = "normal")
            self.stop_button.config(state = "disabled")
            self.enable_preview()

            self.instrument_manager.disconnect("dmm")
            if self.executor:
                self.executor.shutdown(wait = False)
            self.csv_logger.close()
            self.raw_csv_logger.close()
            self.logger.info(
                f"Measurement stopped. Data saved to {self.csv_logger.get_filename()} and {self.raw_csv_logger.get_filename()}")

            if self.main_app:
                self.main_app.stop_apps()  # Stop main app

    def show_loading_popup(self, message="Connecting..."):
        self.loading_popup = tk.Toplevel(self.root)
        self.loading_popup.title("Please wait")
        self.loading_popup.geometry("200x100")
        self.loading_popup.resizable(False, False)
        ttk.Label(self.loading_popup, text = message).pack(pady = 20)
        self.loading_popup.grab_set()
        self.loading_popup.update()

    def close_loading_popup(self):
        if hasattr(self, 'loading_popup') and self.loading_popup.winfo_exists():
            self.loading_popup.destroy()

    def _connect(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return False

        self.show_loading_popup()

        success = False
        exception = None

        def connect_attempt():
            nonlocal success, exception
            try:
                self.instrument_manager.connect("dmm", visa_address, role = "dmm")
                success = True
            except Exception as e:
                exception = e

        # Run connection attempt in a thread with timeout
        thread = threading.Thread(target = connect_attempt, daemon = True)
        thread.start()
        thread.join(timeout = 10)  # 10 seconds timeout

        self.close_loading_popup()

        if not success:
            if exception is None:
                self.logger.error(f"Connection timeout")
                messagebox.showerror("Connection timeout", f"Could not connect to VISA resource:\nConnection timeout")
            else:
                self.logger.error(f"Connection error: {exception}\n{traceback.format_exc()}")
                messagebox.showerror("Connection Error", f"Could not connect to VISA resource:\n{exception}")
            return False

        self.logger.info(f"Connected to VISA resource: {visa_address}")

        return True

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
