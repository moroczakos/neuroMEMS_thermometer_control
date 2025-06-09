import tkinter as tk
from tkinter import ttk
from refactor.thermometer_main import ThermometerMain
from refactor.current_cycle_main import CurrentCycleMain
from utils.constants import EntryConfig, States


class TemperatureMeasurementStationApp:
    def __init__(self, root):
        self.root = root

        # Create container frames
        self.left_frame = ttk.Frame(root, width = 400)
        self.left_frame.pack(side = 'left', fill = 'both', expand = True)

        self.right_frame = tk.Frame(root, width = 400)
        self.right_frame.pack(side = 'right', fill = 'both', expand = True)

        # Add labels at the top of each frame
        ttk.Label(self.left_frame, text = "Current source app", justify = EntryConfig.JUSTIFY,
                  font = ("Arial", 24)).pack()
        self.cycle_app = CurrentCycleMain(self.left_frame, self)

        ttk.Label(self.right_frame, text = "Thermometer app", justify = EntryConfig.JUSTIFY,
                  font = ("Arial", 24)).pack()
        self.thermometer_app = ThermometerMain(self.right_frame, self)

        # Create a frame for the buttons
        self.button_frame = ttk.Frame(root, relief = "solid", borderwidth = 2)
        self.button_frame.place(relx = 0.5, y = 200, anchor = "center")

        # Create the start/stop buttons inside the button frame
        ttk.Label(self.button_frame, text = "Control both apps", justify = EntryConfig.JUSTIFY,
                  font = ("Arial", 18)).pack()
        self.start_button = ttk.Button(self.button_frame, text = "Start", command = self.start_apps)
        self.start_button.pack(side = 'left', padx = 10)

        self.stop_button = ttk.Button(self.button_frame, text = "Stop", command = self.stop_apps)
        self.stop_button.pack(side = 'left', padx = 10)
        self.stop_button.config(state = "disabled")

    def start_apps(self):
        """Starts both applications."""
        self.cycle_app.controller.start_measurement()  # Call the start method of CurrentCycleApp
        self.thermometer_app.controller.start_measurement()  # Call the start method of ThermometerApp
        self.start_button.config(state = States.DISABLED)
        self.stop_button.config(state = States.NORMAL)

    def stop_apps(self):
        """Stops both applications."""
        self.cycle_app.controller.stop_measurement()  # Call the stop method of CurrentCycleApp
        self.thermometer_app.controller.stop_measurement()  # Call the stop method of ThermometerApp
        self.start_button.config(state = States.NORMAL)
        self.stop_button.config(state = States.DISABLED)

    def set_widget_states(self, enabled: bool):
        state = States.NORMAL if enabled else States.DISABLED
        self.start_button.config(state = state)
        self.stop_button.config(state = States.NORMAL if not enabled else States.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1600x900")
    root.title("Temperature measurement station app")
    app = TemperatureMeasurementStationApp(root)
    root.mainloop()
