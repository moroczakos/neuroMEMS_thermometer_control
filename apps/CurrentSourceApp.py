import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from instruments.instrument_manager import InstrumentManager
from utils.file_utils import CsvLogger
from utils.plot_utils import create_single_axis_plot, update_plot
import os
from utils.settings_utils import SettingManager


class CurrentCycleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley 6221 Current Source")

        # Settings
        self.input_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'input_files'))
        self.output_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_files'))
        self.setting_manager = SettingManager(os.path.join(self.input_file_path, 'settings.json'))

        # Logger
        self.logger = CsvLogger()

        # VISA Setup
        self.instrument_manager = InstrumentManager()

        # Control variables
        self.running = False
        self.visa_resource = tk.StringVar()
        self.current_high = tk.DoubleVar(value = self.setting_manager.load_setting("current_high"))
        self.current_low = tk.DoubleVar(value = self.setting_manager.load_setting("current_low"))
        self.duration_high = tk.IntVar(value = self.setting_manager.load_setting("duration_high"))
        self.duration_low = tk.IntVar(value = self.setting_manager.load_setting("duration_low"))
        self.cycles = tk.IntVar(value = self.setting_manager.load_setting("cycles"))

        # Data
        self.timestamps = []
        self.currents = []
        self.current_current = tk.DoubleVar()

        self.create_widgets()
        self.setup_plot()
        self.load_visa_resources()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding = 10)
        frame.pack(fill = tk.X)

        # VISA selection
        ttk.Label(frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 2)

        self.refresh_button = ttk.Button(frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 3, padx = 5)

        # Current and duration settings
        ttk.Label(frame, text = "High Current (A):").grid(row = 1, column = 0)
        ttk.Entry(frame, textvariable = self.current_high, width = 6).grid(row = 1, column = 1)
        self.current_high.trace("w", lambda *args: self.save_entry_value("current_high", self.current_high))

        ttk.Label(frame, text = "Low Current (A):").grid(row = 1, column = 2)
        ttk.Entry(frame, textvariable = self.current_low, width = 6).grid(row = 1, column = 3)
        self.current_low.trace("w", lambda *args: self.save_entry_value("current_low", self.current_low))

        ttk.Label(frame, text = "High Duration (s):").grid(row = 2, column = 0)
        ttk.Entry(frame, textvariable = self.duration_high, width = 6).grid(row = 2, column = 1)
        self.duration_high.trace("w", lambda *args: self.save_entry_value("duration_high", self.duration_high))

        ttk.Label(frame, text = "Low Duration (s):").grid(row = 2, column = 2)
        ttk.Entry(frame, textvariable = self.duration_low, width = 6).grid(row = 2, column = 3)
        self.duration_low.trace("w", lambda *args: self.save_entry_value("duration_low", self.duration_low))

        ttk.Label(frame, text = "Cycles:").grid(row = 3, column = 0)
        ttk.Entry(frame, textvariable = self.cycles, width = 6).grid(row = 3, column = 1)
        self.cycles.trace("w", lambda *args: self.save_entry_value("cycles", self.cycles))

        self.start_button = ttk.Button(frame, text = "Start", command = self.start_measurement)
        self.start_button.grid(row = 3, column = 2)

        self.stop_button = ttk.Button(frame, text = "Stop", command = self.stop_measurement, state = "disabled")
        self.stop_button.grid(row = 3, column = 3)

    def load_visa_resources(self):
        resources = self.instrument_manager.list_resources(only_tcpip = True)
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
        _, self.ax, self.line, self.canvas = create_single_axis_plot(self.root,
                                                                     "Live Current Plot",
                                                                     "Time (s)",
                                                                     "Current (A)")

    def start_measurement(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return

        try:
            self.instrument_manager.connect("source", visa_address, role = "source")

            self.running = True
            self.start_button.config(state = "disabled")
            self.stop_button.config(state = "normal")

            # File setup
            self.logger.create("current_log_",
                               ['Timestamp', 'Current (A)', 'Voltage (V)'],
                               self.output_file_path)

            self.timestamps = []
            self.currents = []
            self.start_time = time.time()

            threading.Thread(target = self.cycle_loop, daemon = True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not open VISA resource:\n{e}")

    def stop_measurement(self):
        self.running = False
        self.start_button.config(state = "normal")
        self.stop_button.config(state = "disabled")

        if self.instrument_manager.get_instrument("source"):
            self.instrument_manager.disconnect("source")
        if hasattr(self, 'logger'):
            self.logger.close()
            print(f"Data saved to {self.logger.get_filename()}")

    def cycle_loop(self):
        threading.Thread(target = self.measure_loop, daemon = True).start()
        source_handler = self.instrument_manager.get_handler("source")

        try:
            for cycle in range(self.cycles.get()):
                if not self.running: break
                source_handler.set_current(self.current_high.get())
                time.sleep(self.duration_high.get())

                if not self.running: break
                source_handler.set_current(self.current_low.get())
                time.sleep(self.duration_low.get())
        except Exception as e:
            messagebox.showerror("Cycle Error", str(e))

        if self.running:
            self.stop_measurement()

    def measure_loop(self):
        source_handler = self.instrument_manager.get_handler("source")

        while self.running:
            try:
                voltage, current = source_handler.measure()
                timestamp = time.time() - self.start_time

                self.timestamps.append(timestamp)
                self.currents.append(current)

                self.current_current.set(round(current, 2))

                if self.running:
                    self.logger.write_row([timestamp, current, voltage])

                self.update_plot()
                time.sleep(0.01)

            except Exception as e:
                print("Measurement error:", e)
                self.running = False
                break

    def update_plot(self):
        curr_data = (self.timestamps, self.currents)

        line_data_pairs = [(self.line, curr_data)]

        update_plot(line_data_pairs, [self.ax], self.canvas)


if __name__ == "__main__":
    root = tk.Tk()
    app = CurrentCycleApp(root)
    root.mainloop()
