# ─── Standard Library ────────────────────────────────────────────────────────
import os
import sys
import tkinter as tk
from tkinter import messagebox

# ─── Local Modules ───────────────────────────────────────────────────────────
from apps.cycle_sequence_editor import CycleSequenceEditor
from controllers.current_cycle_controller import CurrentCycleController
from models.current_cycle_model import CurrentCycleModel
from base_classes.main_base import MainBase
from views.current_cycle_view import CurrentCycleView
from instruments.instrument_manager import InstrumentManager
from utils.measurement_profile import MeasurementProfile


class CurrentCycleMain(MainBase):
    def __init__(self, root):
        MainBase.__init__(self)

        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        self.setup_logger("current_source_app.log")
        self.output_file_path = os.path.join(self.output_base_file_path, "current_cycle")

        instrument_manager = InstrumentManager()
        profile = self._create_measurement_profile()

        model = CurrentCycleModel(
            instrument_manager,
            self.setting_manager,
            profile,
            self.output_file_path
        )

        self.view = CurrentCycleView(self.root, self.setting_manager, self.logger, profile)
        self.view.set_cycle_sequence_editor_app_opener(self._cycle_sequence_editor)

        self.controller = CurrentCycleController(model, self.view)

    def can_close_app(self):
        if self.controller.is_running():
            messagebox.showwarning("Closing", "Stop the running current measurement!\n"
                                              "Press Stop button in the Current source app to close the app!")
            return False

        return True

    def _create_measurement_profile(self):
        return MeasurementProfile(
            name = "Current/Voltage/Resistance",
            headers = ["Timestamp", "Current (A)", "Voltage (V)", "Resistance (Ohms)"],
            y1_label = "Current (A)",
            y2_label = "Voltage (V)",
            measure_func = lambda source: source.measure(),
            post_process_func = lambda a, v: v / a if v is not None else float('nan')
        )

    def _cycle_sequence_editor(self):
        CycleSequenceEditor(self.setting_manager, self.logger)

    def close_app(self):
        if self.can_close_app():
            self.root.destroy()
            return True

        return False


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Current Source")
    app = CurrentCycleMain(root)


    def on_close():
        if app.close_app():
            sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
