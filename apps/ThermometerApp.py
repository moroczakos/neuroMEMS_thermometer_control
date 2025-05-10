import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from instruments.instrument_manager import InstrumentManager
from utils.file_utils import CsvLogger
from utils.plot_utils import create_dual_axis_plot, update_plot
from utils.settings_utils import load_probe_data, SettingManager
import os


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
        self.current_resistance = tk.DoubleVar()
        self.current_temperature = tk.DoubleVar()

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
        ttk.Entry(frame, textvariable = self.R0, width = 10, state = "readonly").grid(row = 1, column = 3)

        ttk.Label(frame, text = "TCR:").grid(row = 1, column = 4)
        ttk.Entry(frame, textvariable = self.TCR, width = 10, state = "readonly").grid(row = 1, column = 5)

        ttk.Label(frame, text = "Interval (s):").grid(row = 2, column = 0)
        ttk.Entry(frame, textvariable = self.interval, width = 6).grid(row = 2, column = 1)
        self.interval.trace("w", lambda *args: self.save_entry_value("interval", self.interval))

        ttk.Label(frame, text = "Average Count:").grid(row = 2, column = 2)
        ttk.Entry(frame, textvariable = self.average_count, width = 6).grid(row = 2, column = 3)
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

            # File setup
            self.logger.create("resistance_log",
                               ['Timestamp', 'Resistance (Ohms)', 'Temperature (°C)'],
                               self.output_file_path)

            self.timestamps = []
            self.resistances = []
            self.temperatures = []
            self.start_time = time.time()

            threading.Thread(target = self.measure_loop, daemon = True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not open VISA resource:\n{e}")

    def stop_measurement(self):
        self.running = False
        self.start_button.config(state = "normal")
        self.stop_button.config(state = "disabled")

        if self.instrument_manager.get_instrument("dmm"):
            self.instrument_manager.disconnect("dmm")
        if hasattr(self, 'logger'):
            self.logger.close()
            print(f"Data saved to {self.logger.get_filename()}")

    def measure_loop(self):
        dmm = self.instrument_manager.get_handler("dmm")

        while self.running:
            error = self.instrument_manager.get_error("dmm")
            if error:
                print(error)

            try:
                # Resistance computation
                total = 0.0
                for _ in range(self.average_count.get()):
                    reading = dmm.measure()
                    total += reading
                    time.sleep(0.01)
                resistance = total / self.average_count.get()
                timestamp = time.time() - self.start_time

                # Compute temperature from resistance according to the Callendar-Van Dusen equation
                R0 = self.R0.get()
                TCR = self.TCR.get()
                if R0 > 0 and TCR > 0:
                    temperature = (resistance / R0 - 1) / TCR
                else:
                    temperature = float('nan')

                self.timestamps.append(timestamp)
                self.resistances.append(resistance)
                self.temperatures.append(temperature)

                self.current_resistance.set(round(resistance, 4))
                self.current_temperature.set(round(temperature, 2))

                if self.running:
                    self.logger.write_row([timestamp, resistance, temperature])

                self.update_plot()
                time.sleep(self.interval.get())

            except Exception as e:
                print("Measurement error:", e)
                self.running = False
                break

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
