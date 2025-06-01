# ─── Standard Library ────────────────────────────────────────────────────────
import os
import tkinter as tk

# ─── Local Modules ───────────────────────────────────────────────────────────
from refactor.controllers.current_cycle_controller import CurrentCycleController
from refactor.models.measurement_model import MeasurementModel
from refactor.views.current_cycle_view import CurrentCycleView
from instruments.instrument_manager import InstrumentManager
from utils.other_utils import find_project_root
from utils.settings_utils import SettingManager
from utils.logger_manager import LoggerManager
from utils.measurement_profile import MeasurementProfile

if __name__ == "__main__":
    root = tk.Tk()

    # Settings
    project_root = find_project_root()
    setting_manager = SettingManager(os.path.join(project_root, 'input_files', 'settings.json'))
    input_file_path = os.path.join(project_root, setting_manager.load_setting("input_files"))
    output_file_path = os.path.join(project_root, setting_manager.load_setting('output_files'))
    log_file_path = os.path.join(project_root, setting_manager.load_setting('log_files'))

    logger = LoggerManager(log_file = os.path.join(log_file_path, "current_source_app.log")).get_logger()
    instrument_manager = InstrumentManager()
    profile = MeasurementProfile(
        name = "Current/Voltage/Resistance",
        headers = ["Timestamp", "Current (A)", "Voltage (V)", "Resistance (Ohms)"],
        y1_label = "Current (A)",
        y2_label = "Voltage (V)",
        measure_func = lambda source: source.measure(),
        post_process_func = lambda a, v: v / a if v is not None else float('nan')
    )

    model = MeasurementModel(instrument_manager, setting_manager, profile, input_file_path, output_file_path)
    view = CurrentCycleView(root, setting_manager, logger, profile)
    controller = CurrentCycleController(model, view)

    root.mainloop()
