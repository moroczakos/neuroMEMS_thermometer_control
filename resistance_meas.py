import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyvisa
import pandas as pd
import json
import os
from instruments.mock_Keithley2100 import MockKeithley2100


class ResistanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley 2100 4-Wire Resistance Logger")

        self.settings_file = "input_files/settings.json"

        # Control Variables
        self.running = False
        self.interval = tk.DoubleVar(value = 0.1)
        self.average_count = tk.IntVar(value = 5)
        self.visa_resource = tk.StringVar()

        # VISA Setup
        self.rm = pyvisa.ResourceManager()
        self.dmm = None

        # Probe
        self.probes = self.load_probe_data()
        self.last_probe = self.load_last_probe()
        self.selected_probe = tk.StringVar(value = self.last_probe)
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

        ttk.Label(frame, text = "Average Count:").grid(row = 2, column = 2)
        ttk.Entry(frame, textvariable = self.average_count, width = 6).grid(row = 2, column = 3)

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
        try:
            resources = self.rm.list_resources()
            resources = ("MOCK",) + resources  # Add mock option at top
            self.visa_dropdown['values'] = resources
            if resources:
                self.visa_resource.set(resources[0])
            else:
                self.visa_resource.set("No VISA resources found")
        except Exception as e:
            messagebox.showerror("VISA Error", f"Could not list VISA resources:\n{e}")

    def load_probe_data(self):
        try:
            df = pd.read_csv("input_files/thermoprobes.csv")
            return df.set_index("Name").to_dict(orient = "index")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load probe data:\n{e}")
            return {}

    def setup_plot(self):
        self.fig, self.ax = plt.subplots()
        self.ax2 = self.ax.twinx()  # secondary Y axis for temperature
        self.line_R, = self.ax.plot([], [], label = "Resistance (Ohms)", color = 'black')
        self.line_T, = self.ax2.plot([], [], label = "Temperature (°C)", color = 'red')
        self.ax.set_title("Live Resistance and Temperature Measurement")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Resistance (Ohms)", color = 'black')
        self.ax2.set_ylabel("Temperature (°C)", color = 'red')
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master = self.root)
        self.canvas.get_tk_widget().pack(fill = tk.BOTH, expand = True)

    def start_measurement(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return

        try:
            if visa_address == "MOCK":
                self.dmm = MockKeithley2100()
            else:
                self.dmm = self.rm.open_resource(visa_address)
            self.dmm.write("*RST")
            time.sleep(1)
            self.dmm.write("CONF:FRES 1000")
            # self.dmm.write("SENS:FRES:RANG:AUTO ON")
            self.dmm.write("SENS:FRES:NPLC 1")
            # self.dmm.write("TRIG:COUNT 1")

            self.running = True
            self.start_button.config(state = "disabled")
            self.stop_button.config(state = "normal")

            # File setup
            self.filename = f"resistance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.csvfile = open(self.filename, 'w', newline = '')
            self.writer = csv.writer(self.csvfile)
            self.writer.writerow(['Timestamp', 'Resistance (Ohms)', 'Temperature (°C)'])

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
        if self.dmm:
            self.dmm.close()
        if hasattr(self, 'csvfile'):
            self.csvfile.close()
            print(f"Data saved to {self.filename}")

    def measure_loop(self):
        while self.running:

            error = self.dmm.query('SYST:ERR?').strip()
            print(error)

            try:
                # Resistance computation
                total = 0.0
                for _ in range(self.average_count.get()):
                    self.dmm.write("INIT")
                    reading = float(self.dmm.query("FETCH?").strip())
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

                self.writer.writerow([timestamp, resistance, temperature])
                self.csvfile.flush()

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
            self.save_last_probe(probe)

    def save_last_probe(self, probe_name):
        try:
            with open(self.settings_file, "w") as f:
                json.dump({"last_probe": probe_name}, f)
        except Exception as e:
            print(f"Could not save settings: {e}")

    def load_last_probe(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                    return settings.get_instrument("last_probe", "")
            except Exception as e:
                print(f"Could not load settings: {e}")
        return ""

    def update_plot(self):
        self.line_R.set_data(self.timestamps, self.resistances)
        self.line_T.set_data(self.timestamps, self.temperatures)

        self.ax.relim()
        self.ax.autoscale_view()
        self.ax2.relim()
        self.ax2.autoscale_view()

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = ResistanceApp(root)
    root.mainloop()
