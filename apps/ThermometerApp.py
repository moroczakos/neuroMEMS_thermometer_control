import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from instruments.instrument_manager import InstrumentManager
from utils.file_utils import CsvLogger
from utils.plot_utils import create_dual_axis_plot, update_plot
from utils.settings_utils import load_probe_data, SettingManager
import os
import queue
from concurrent.futures import ThreadPoolExecutor


class ThermometerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley 2100 4-Wire Resistance Logger")

        # Settings
        self.input_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'input_files'))
        self.output_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_files'))
        self.setting_manager = SettingManager(os.path.join(self.input_file_path, 'settings.json'))

        # Logger
        self.logger = CsvLogger()

        # VISA Setup
        self.instrument_manager = InstrumentManager()

        # Control Variables
        self.running = False
        self.preview_running = False
        self.visa_resource = tk.StringVar()
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting("interval"))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting("avg_count"))

        # Probe
        self.probes = load_probe_data(os.path.join(self.input_file_path, 'thermoprobes.csv'))
        self.selected_probe = tk.StringVar(value = self.setting_manager.load_setting("probe"))
        self.R0 = tk.DoubleVar()
        self.TCR = tk.DoubleVar()
        self.update_probe_values()

        # Data
        self.timestamps = []
        self.resistances = []
        self.temperatures = []
        self.data_queue = queue.Queue()
        self.current_resistance = tk.DoubleVar()
        self.current_temperature = tk.DoubleVar()

        self.executor = None

        self.create_widgets()
        self.setup_plot()
        self.load_visa_resources()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding = 10)
        frame.pack(fill = tk.X)

        ttk.Label(frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3, padx = 5, pady = 5)

        self.refresh_button = ttk.Button(frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5)

        ttk.Label(frame, text = "Thermoprobe:").grid(row = 1, column = 0)
        self.probe_dropdown = ttk.Combobox(frame, textvariable = self.selected_probe, values = list(self.probes.keys()),
                                           width = 11)
        self.probe_dropdown.grid(row = 1, column = 1)
        self.probe_dropdown.bind("<<ComboboxSelected>>", self.update_probe_values)

        ttk.Label(frame, text = "R₀:").grid(row = 1, column = 2)
        ttk.Entry(frame, textvariable = self.R0, width = 10, state = "readonly", justify = 'center').grid(row = 1,
                                                                                                          column = 3)

        ttk.Label(frame, text = "TCR:").grid(row = 1, column = 4)
        ttk.Entry(frame, textvariable = self.TCR, width = 10, state = "readonly", justify = 'center').grid(row = 1,
                                                                                                           column = 5)

        ttk.Label(frame, text = "Interval (s):").grid(row = 2, column = 0)
        ttk.Entry(frame, textvariable = self.interval, width = 6, justify = 'center').grid(row = 2, column = 1)
        self.interval.trace("w", lambda *args: self.save_entry_value("interval", self.interval))

        ttk.Label(frame, text = "Average count:").grid(row = 2, column = 2)
        ttk.Entry(frame, textvariable = self.average_count, width = 6, justify = 'center').grid(row = 2, column = 3)
        self.average_count.trace("w", lambda *args: self.save_entry_value("avg_count", self.average_count))

        self.start_button = ttk.Button(frame, text = "Start", command = self.start_measurement)
        self.start_button.grid(row = 2, column = 4, padx = 10)

        self.stop_button = ttk.Button(frame, text = "Stop", command = self.stop_measurement, state = "disabled")
        self.stop_button.grid(row = 2, column = 5)

        ttk.Label(frame, text = "Live Resistance (Ω):").grid(row = 3, column = 0, sticky = 'e')
        ttk.Label(frame, textvariable = self.current_resistance, foreground = 'black').grid(row = 3, column = 1,
                                                                                            sticky = 'w')

        ttk.Label(frame, text = "Live Temperature (°C):").grid(row = 3, column = 2, sticky = 'e')
        ttk.Label(frame, textvariable = self.current_temperature, foreground = 'red').grid(row = 3, column = 3,
                                                                                           sticky = 'w')

        self.preview_start_button = ttk.Button(frame, text = "Start Preview", command = self.start_preview)
        self.preview_start_button.grid(row = 3, column = 4, pady = 5)

        self.preview_stop_button = ttk.Button(frame, text = "Stop Preview", command = self.stop_preview,
                                              state = "disabled")
        self.preview_stop_button.grid(row = 3, column = 5, pady = 5)

    def load_visa_resources(self):
        resources = self.instrument_manager.list_resources()
        self.visa_dropdown['values'] = resources
        if resources:
            self.visa_resource.set(resources[0])
        else:
            self.visa_resource.set("No VISA resources found")

    def save_entry_value(self, name, value):
        try:
            self.setting_manager.save_setting(name, value.get())
        except Exception:
            pass

    def setup_plot(self):
        _, ax1, ax2, line_R, line_T, self.canvas = create_dual_axis_plot(self.root,
                                                                         "Live Resistance and Temperature Measurement",
                                                                         "Time (s)",
                                                                         "Resistance (Ohms)",
                                                                         "Temperature (°C)")
        self.lines = [line_R, line_T]
        self.axes = [ax1, ax2]

    def start_preview(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return

        try:
            self.instrument_manager.connect("dmm", visa_address, role = "dmm")
            self.preview_running = True
            self.preview_start_button.config(state = "disabled")
            self.preview_stop_button.config(state = "normal")
            self.start_button.config(state = "disabled")
            threading.Thread(target = self.preview_loop, daemon = True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not open VISA resource:\n{e}")

    def stop_preview(self):
        self.preview_running = False
        self.preview_start_button.config(state = "normal")
        self.preview_stop_button.config(state = "disabled")
        self.start_button.config(state = "normal")
        self.instrument_manager.disconnect("dmm")

    def preview_loop(self):
        self.instrument_manager.get_handler("dmm")  # ensure connected
        while self.preview_running:
            try:
                self.perform_measurement()
                time.sleep(self.interval.get())
            except Exception as e:
                print("Preview error:", e)
                self.preview_running = False
                break

    def start_measurement(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return

        try:
            self.instrument_manager.connect("dmm", visa_address, role = "dmm")

            self.running = True
            self.start_button.config(state = "disabled")
            self.stop_button.config(state = "normal")
            self.preview_start_button.config(state = "disabled")

            # File setup
            self.logger.create(f"resistance_log_{self.selected_probe.get()}",
                               ['Timestamp', 'Resistance (Ohms)', 'Temperature (°C)'],
                               self.output_file_path)

            self.timestamps = []
            self.resistances = []
            self.temperatures = []
            self.start_time = time.time()

            self.executor = ThreadPoolExecutor(max_workers = 6)
            threading.Thread(target = self.measure_loop, daemon = True).start()
            threading.Thread(target = self.data_worker_loop, daemon = True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not open VISA resource:\n{e}")

    def stop_measurement(self):
        self.running = False
        self.start_button.config(state = "normal")
        self.stop_button.config(state = "disabled")
        self.preview_start_button.config(state = "normal")

        if self.instrument_manager.get_instrument("dmm"):
            self.instrument_manager.disconnect("dmm")
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait = False)
        if hasattr(self, 'logger'):
            self.logger.close()
            print(f"Data saved to {self.logger.get_filename()}")

    def perform_measurement(self):
        """Performs a single averaged resistance reading, calculates temperature, updates UI."""
        dmm_handler = self.instrument_manager.get_handler("dmm")
        resistance = dmm_handler.measure()

        # Resistance computation
        R0 = self.R0.get()
        TCR = self.TCR.get()

        # Compute temperature from resistance according to the Callendar-Van Dusen equation
        temperature = (resistance / R0 - 1) / TCR if R0 > 0 and TCR > 0 else float('nan')

        self.current_resistance.set(round(resistance, 4))
        self.current_temperature.set(round(temperature, 2))

        return resistance, temperature

    def measure_loop(self):
        self.data_counter = 0
        self.total_resistance = 0.0
        self.total_temperature = 0.0

        while self.running:
            try:
                # Resistance computation
                resistance, temperature = self.perform_measurement()
                timestamp = time.time() - self.start_time

                # Enqueue data for logger and plotting
                self.data_queue.put((timestamp, resistance, temperature))
                time.sleep(self.interval.get())

            except Exception as e:
                print("Measurement error:", e)
                self.running = False

                error = self.instrument_manager.get_error("dmm")
                if error:
                    print(error)
                break

    def data_worker_loop(self):
        MAX_QUEUE_SIZE = 100

        while self.running or not self.data_queue.empty():
            # Warn if queue is growing too large
            if self.data_queue.qsize() > MAX_QUEUE_SIZE:
                print("⚠️ Queue backlog detected! Plotting/logging is slower than measurements.")

            try:
                timestamp, resistance, temperature = self.data_queue.get(timeout = 0.5)

                if self.running:
                    # Submit logging and plotting as async tasks
                    self.executor.submit(self.safe_log, timestamp, resistance, temperature)
                    self.executor.submit(self.safe_plot, timestamp, resistance, temperature)

            except queue.Empty:
                continue
            except Exception as e:
                print("Data processing error:", e)

    def safe_log(self, timestamp, resistance, temperature):
        try:
            self.logger.write_row([timestamp, resistance, temperature])
        except Exception as e:
            print(f"Logging error: {e}")

    def safe_plot(self, timestamp, resistance, temperature):
        try:
            # Average calculation
            avg_count = self.average_count.get()
            self.data_counter += 1
            self.total_resistance += resistance
            self.total_temperature += temperature
            if self.data_counter >= avg_count:
                self.timestamps.append(timestamp)
                self.resistances.append(self.total_resistance / avg_count)
                self.temperatures.append(self.total_temperature / avg_count)

                self.data_counter = 0
                self.total_resistance = 0.0
                self.total_temperature = 0.0

                self.update_plot()
        except Exception as e:
            print(f"Plotting error: {e}")

    def update_probe_values(self, event=None):
        probe = self.selected_probe.get()
        if probe in self.probes:
            self.R0.set(self.probes[probe]["R0"])
            self.TCR.set(self.probes[probe]["TCR"])
            self.setting_manager.save_setting("probe", probe)

    def update_plot(self):
        temp_data = (self.timestamps, self.resistances)
        res_data = (self.timestamps, self.temperatures)

        line_data_pairs = [(self.lines[0], temp_data),
                           (self.lines[1], res_data)]

        update_plot(line_data_pairs, self.axes, self.canvas)


if __name__ == "__main__":
    root = tk.Tk()
    app = ThermometerApp(root)
    root.mainloop()
