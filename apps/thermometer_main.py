# ─── Standard Library ────────────────────────────────────────────────────────
import os
import sys
import tkinter as tk

# ─── Local Modules ───────────────────────────────────────────────────────────
from controllers.thermometer_controller import ThermometerController
from models.thermometer_model import ThermometerModel
from views.thermometer_view import ThermometerView
from instruments.instrument_manager import InstrumentManager
from utils.other_utils import find_project_root
from utils.settings_utils import SettingManager
from utils.logger_manager import LoggerManager
from utils.measurement_profile import MeasurementProfile


class ThermometerMain:
    def __init__(self, root):
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        self.project_root = ".."  # find_project_root()
        self.setting_manager = self._load_settings()
        self.logger = self._setup_logger()

        instrument_manager = InstrumentManager()
        profile = self._create_measurement_profile()

        model = ThermometerModel(
            instrument_manager,
            self.setting_manager,
            profile,
            self.input_file_path,
            self.output_file_path
        )

        view = ThermometerView(self.root, self.probe_path, self.setting_manager, self.logger, profile)
        self.controller = ThermometerController(model, view)

    def _load_settings(self):
        settings_path = os.path.join(self.project_root, 'input_files', 'settings.json')
        setting_manager = SettingManager(settings_path)

        self.input_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("input_files")
        )
        self.output_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("output_files"), "thermometer"
        )
        self.log_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("log_files")
        )
        self.probe_path = os.path.join(self.input_file_path, "thermoprobes.csv")

        return setting_manager

    def _setup_logger(self):
        log_path = os.path.join(self.log_file_path, "thermometer_app.log")
        self.logger_manager = LoggerManager(log_file = log_path)
        return self.logger_manager.get_logger()

    def _create_measurement_profile(self):
        return MeasurementProfile(
            name = "Resistance/Temperature",
            headers = ["Timestamp", "Resistance (Ohms)", "Temperature (Celsius)"],
            y1_label = "Resistance (Ohms)",
            y2_label = "Temperature (°C)",
            measure_func = lambda dmm: dmm.measure(),
            post_process_func = lambda r, R0, TCR: (r / R0 - 1) / TCR if R0 > 0 and TCR > 0 else float('nan')
        )

    def close_app(self):
        self.logger_manager.close()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Thermometer")
    app = ThermometerMain(root)


    def on_close():
        app.close_app()
        root.destroy()
        sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
