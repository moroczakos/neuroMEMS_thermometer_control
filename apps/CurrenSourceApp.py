import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
from datetime import datetime
import pyvisa
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class CurrentCycleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley 6221 Current Source")

        # VISA & Instrument
        self.rm = pyvisa.ResourceManager()
        self.instrument = None
        self.visa_resource = tk.StringVar()

        # Control variables
        self.current_high = tk.DoubleVar(value=0.375)
        self.current_low = tk.DoubleVar(value=0.0)
        self.duration_high = tk.IntVar(value=120)
        self.duration_low = tk.IntVar(value=240)
        self.cycles = tk.IntVar(value=10)

        self.running = False
        self.timestamps = []
        self.currents = []

        self.create_widgets()
        self.setup_plot()
        self.load_visa_resources()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.X)

        # VISA selection
        ttk.Label(frame, text="VISA Resource:").grid(row=0, column=0)
        self.visa_dropdown = ttk.Combobox(frame, textvariable=self.visa_resource, width=40)
        self.visa_dropdown.grid(row=0, column=1, columnspan=2)

        self.refresh_button = ttk.Button(frame, text = "Refresh", command = self.load_visa_resources)
        self.refresh_button.grid(row = 0, column = 3, padx = 5)

        # Current and duration settings
        ttk.Label(frame, text="High Current (A):").grid(row=1, column=0)
        ttk.Entry(frame, textvariable=self.current_high, width=6).grid(row=1, column=1)

        ttk.Label(frame, text="Low Current (A):").grid(row=1, column=2)
        ttk.Entry(frame, textvariable=self.current_low, width=6).grid(row=1, column=3)

        ttk.Label(frame, text="High Duration (s):").grid(row=2, column=0)
        ttk.Entry(frame, textvariable=self.duration_high, width=6).grid(row=2, column=1)

        ttk.Label(frame, text="Low Duration (s):").grid(row=2, column=2)
        ttk.Entry(frame, textvariable=self.duration_low, width=6).grid(row=2, column=3)

        ttk.Label(frame, text="Cycles:").grid(row=3, column=0)
        ttk.Entry(frame, textvariable=self.cycles, width=6).grid(row=3, column=1)

        self.start_button = ttk.Button(frame, text="Start", command=self.start_measurement)
        self.start_button.grid(row=3, column=2)

        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_measurement, state="disabled")
        self.stop_button.grid(row=3, column=3)

    def load_visa_resources(self):
        try:
            resources = self.rm.list_resources()
            # Filter to only show TCPIP (Ethernet) connections
            ethernet_resources = [r for r in resources if r.startswith("TCPIP")]
            if not ethernet_resources:
                self.visa_dropdown['values'] = ["No Ethernet instruments found"]
                self.visa_resource.set("No Ethernet instruments found")
            else:
                self.visa_dropdown['values'] = ethernet_resources
                self.visa_resource.set(ethernet_resources[0])
        except Exception as e:
            messagebox.showerror("VISA Error", f"Could not list VISA resources:\n{e}")

    def setup_plot(self):
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], label="Current (A)")
        self.ax.set_title("Live Current Plot")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Current (A)")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def start_measurement(self):
        visa_address = self.visa_resource.get()
        if "No VISA" in visa_address or not visa_address.strip():
            messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
            return

        try:
            self.instrument = self.rm.open_resource(visa_address)
            self.instrument.write("*RST")
            self.instrument.write("SOUR:FUNC CURR")  # Set to current source
            self.instrument.write("SOUR:CURR:RANG:AUTO ON")  # Auto range
            self.instrument.write("SOUR:CURR:MODE FIXED")  # Use fixed DC mode
            self.instrument.write("OUTP ON")

            self.running = True
            self.timestamps = []
            self.currents = []

            self.start_time = time.time()
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")

            # File setup
            self.filename = f"current_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.csvfile = open(self.filename, 'w', newline='')
            self.writer = csv.writer(self.csvfile)
            self.writer.writerow(['Timestamp', 'Current (A)', 'Voltage (V)'])

            threading.Thread(target=self.cycle_loop, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Instrument Error", str(e))

    def stop_measurement(self):
        self.running = False
        if self.instrument:
            self.instrument.write(":OUTP OFF")
            self.instrument.close()
        if hasattr(self, 'csvfile'):
            self.csvfile.close()
            print(f"Data saved to {self.filename}")

        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def cycle_loop(self):
        try:
            for cycle in range(self.cycles.get()):
                if not self.running: break

                self.set_current(self.current_high.get())
                self.log_data(self.duration_high.get())

                if not self.running: break

                self.set_current(self.current_low.get())
                self.log_data(self.duration_low.get())

        except Exception as e:
            messagebox.showerror("Cycle Error", str(e))
        finally:
            self.stop_measurement()

    def set_current(self, value):
        self.instrument.write(f":SOUR:CURR {value}")

    def log_data(self, duration):
        for _ in range(duration):
            if not self.running: break
            try:
                current = float(self.instrument.query(":SOUR:CURR?"))
                voltage = float(self.instrument.query(":MEAS:VOLT?"))
                timestamp = time.time() - self.start_time

                self.timestamps.append(timestamp)
                self.currents.append(current)
                self.writer.writerow([timestamp, current, voltage])
                self.csvfile.flush()

                self.update_plot()
                time.sleep(1)
            except Exception as e:
                print("Measurement error:", e)
                break

    def update_plot(self):
        self.line.set_data(self.timestamps, self.currents)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = CurrentCycleApp(root)
    root.mainloop()
