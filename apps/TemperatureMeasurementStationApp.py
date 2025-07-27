import os
import sys
import tkinter as tk
from tkinter import ttk
from apps.thermometer_main import ThermometerMain
from apps.current_cycle_main import CurrentCycleMain
from base_classes.main_base import MainBase
from utils.constants import EntryConfig, States, UI
from utils.settings_utils import load_tooltip_data
from utils.ui_utils.tooltip import ToolTip


class TemperatureMeasurementStationApp(MainBase):
    def __init__(self, root):
        MainBase.__init__(self)

        self.root = root
        self.is_current_cycle_app_running = False
        self.is_thermometer_app_running = False
        self.is_combined = False

        self.tooltips = load_tooltip_data(
            os.path.join(self.input_file_path, self.setting_manager.load_setting(UI.TOOLTIPS)))
        if self.setting_manager.load_setting(UI.SHOW_TOOLTIP) == "False":
            ToolTip.show_tooltip = False

        # Create container frames
        self.left_frame = ttk.Frame(root, width = 400)
        self.left_frame.pack(side = 'left', fill = 'both', expand = True)

        self.right_frame = tk.Frame(root, width = 400)
        self.right_frame.pack(side = 'right', fill = 'both', expand = True)

        # Add labels at the top of each frame
        ttk.Label(self.left_frame, text = "Current source app", justify = EntryConfig.JUSTIFY,
                  font = ("Arial", 24)).pack()
        self.cycle_app = CurrentCycleMain(self.left_frame)

        ttk.Label(self.right_frame, text = "Thermometer app", justify = EntryConfig.JUSTIFY,
                  font = ("Arial", 24)).pack()
        self.thermometer_app = ThermometerMain(self.right_frame)

        # Create a frame for the buttons
        self.button_frame = ttk.Frame(root, relief = "solid", borderwidth = 2)
        self.button_frame.place(relx = 0.5, y = 250, anchor = "center")

        # Create the start/stop buttons inside the button frame
        ttk.Label(self.button_frame, text = "Control both apps", justify = EntryConfig.JUSTIFY,
                  font = ("Arial", 18)).pack()
        self.start_button = ttk.Button(self.button_frame, text = "Ⓘ Start", command = self.start_apps)
        self.start_button.pack(side = 'left', padx = 10)
        ToolTip(self.start_button, self.tooltips.get("station_start_button", ""))

        self.stop_button = ttk.Button(self.button_frame, text = "Ⓘ Stop", command = self.stop_apps)
        self.stop_button.pack(side = 'left', padx = 10)
        self.stop_button.config(state = "disabled")
        ToolTip(self.stop_button, self.tooltips.get("station_stop_button", ""))

        self.cycle_app.controller.attach_to_model(self)
        self.thermometer_app.controller.attach_to_model(self)

    def start_apps(self):
        """Starts both applications."""
        self.cycle_app.controller.start_measurement()  # Call the start method of CurrentCycleApp
        self.thermometer_app.controller.start_measurement()  # Call the start method of ThermometerApp

        self.cycle_app.controller.disable_controls()
        self.thermometer_app.controller.disable_controls()

        self._set_widget_states(False)
        self.is_combined = True

    def stop_apps(self):
        """Stops both applications."""
        self.cycle_app.controller.stop_measurement()  # Call the stop method of CurrentCycleApp
        self.thermometer_app.controller.stop_measurement()  # Call the stop method of ThermometerApp

        self.cycle_app.controller.enable_controls()
        self.thermometer_app.controller.enable_controls()

        self._set_widget_states(True)
        self.is_combined = False

    def _set_widget_states(self, enabled: bool):
        state = States.NORMAL if enabled else States.DISABLED
        self.start_button.config(state = state)
        self.stop_button.config(state = States.NORMAL if not enabled else States.DISABLED)

    def _disable_controls(self):
        self._set_widget_states(False)
        self.stop_button.config(state = States.DISABLED)

    def is_running(self, name, running):
        if name == "current_cycle_model":
            self.is_current_cycle_app_running = running
        elif name == "thermometer_model":
            self.is_thermometer_app_running = running

        if not self.is_current_cycle_app_running and self.is_combined:
            self.stop_apps()
        elif self.is_current_cycle_app_running or self.is_thermometer_app_running:
            self._disable_controls()
        else:
            self._set_widget_states(True)

    def update(self, *args):
        pass

    def log(self, *args):
        pass

    def close_app(self):
        if self.thermometer_app.can_close_app() and self.cycle_app.can_close_app():
            self.thermometer_app.close_app()
            self.cycle_app.close_app()
            self.root.destroy()
            return True

        return False


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1600x900")
    root.title("Temperature measurement station app")
    app = TemperatureMeasurementStationApp(root)


    def on_close():
        if app.close_app():
            sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
