# ─── Standard Library ────────────────────────────────────────────────────────
import os
import sys
import tkinter as tk
from tkinter import messagebox

# ─── Local Modules ───────────────────────────────────────────────────────────
from controllers.thermometer_controller import ThermometerController
from models.thermometer_model import ThermometerModel
from base_classes.main_base import MainBase
from views.thermometer_view import ThermometerView
from instruments.instrument_manager import InstrumentManager
from utils.measurement_profile import MeasurementProfile


class ThermometerMain(MainBase):
    def __init__(self, root, cycle_app = None):
        MainBase.__init__(self)

        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        self.current_source = None
        self.current_source_app = cycle_app

        self.setup_logger("thermometer_app.log")
        self.probe_path = os.path.join(self.input_file_path, "thermoprobes.csv")
        self.output_file_path = os.path.join(self.output_base_file_path, "thermometer")

        instrument_manager = InstrumentManager()
        self.profile = self._create_measurement_profile()
        profile = self.profile

        model = ThermometerModel(
            instrument_manager,
            self.setting_manager,
            profile,
            self.input_file_path,
            self.output_file_path,
            self.current_source_app,
            self.current_source
        )

        view = ThermometerView(self.root, self.probe_path, self.setting_manager, self.logger, profile)
        self.controller = ThermometerController(model, view)

    def can_close_app(self):
        if self.controller.is_running():
            messagebox.showwarning("Closing",
                                   "Stop the running thermometer measurement/preview!\n"
                                   "Press Stop/Stop preview button in the Thermometer app to close the app!")
            return False

        return True

    def _create_measurement_profile(self):
        return MeasurementProfile(
            name = "Resistance/Temperature",
            headers = ["Timestamp", "Resistance (Ohms)", "Temperature (Celsius)"],
            y1_label = "Resistance (Ohms)",
            y2_label = "Temperature (°C)",
            measure_func = lambda dmm, c_source = None: (
                dmm.measure()
                if c_source is None
                else (
                    (lambda i: {"resistance": 0.001} if i is None or i == 0 else {
                        "resistance": dmm.measure()["resistance"] / i})(
                        c_source.get_current()
                    )
                )
            ),
            post_process_func = lambda r, R0, TCR: (r / R0 - 1) / TCR if R0 > 0 and TCR > 0 else float('nan')
        )

    def close_app(self):
        if self.can_close_app():
            self.root.destroy()
            return True

        return False


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Thermometer")
    app = ThermometerMain(root)


    def on_close():
        if app.close_app():
            sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
