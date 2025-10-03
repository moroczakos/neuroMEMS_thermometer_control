# ─── Standard Library ────────────────────────────────────────────────────────
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog

# ─── Local Modules ───────────────────────────────────────────────────────────
from base_classes.main_base import MainBase
from utils.constants import UI
from utils.other_utils import add_current_date_to_folder_path


class SettingsApp(MainBase):
    def __init__(self, root):
        super().__init__()

        self.root = tk.Frame(root)
        self.root.pack(fill = "both", expand = True)

        # Setup
        self.setup_logger("settings_app.log")
        self.int_validate_cmd = (root.register(self.validate_int), "%P")
        self.orig_output_base_file_path = add_current_date_to_folder_path(os.path.join(
            self.project_root, self.setting_manager.load_setting("output_files")
        ))

        self.tooltip_state = tk.IntVar(
            value = 0 if self.setting_manager.load_setting(UI.SHOW_TOOLTIP) == "False" else 1
        )

        self.digital_io_state = tk.IntVar(
            value = 0 if self.setting_manager.load_setting(UI.ENABLE_DIGITAL_IO) == "False" else 1
        )

        self._build_ui()

        # Save baseline settings for change detection
        self._original_settings = self._collect_settings()
        self._update_save_button()

    # ─── UI Builders ─────────────────────────────────────────────────────────
    def _build_ui(self):
        """Main entry point for UI setup."""
        frame = ttk.Frame(self.root, padding = 10)
        frame.pack(fill = tk.X)

        row = 0
        row = self._build_file_info_section(frame, row)
        row = self._build_tooltip_section(frame, row)
        row = self._build_digital_io_section(frame, row)
        self._build_entry_section(frame, row)
        self._build_save_section()

    def _build_file_info_section(self, frame, row):
        row = self._add_path_row(frame, row, "Input file path:", self.input_file_path)
        row = self._add_path_row(frame, row, "Log file path:", self.log_file_path)

        # Output folder
        ttk.Label(frame, text = "Output file path:").grid(row = row, column = 0, sticky = "w")
        self._output_file_lbl = self.create_copiable_label(
            frame, text = os.path.abspath(self.output_base_file_path)
        )
        self._output_file_lbl.grid(row = row, column = 1, sticky = "w")
        ttk.Button(frame, text = "Select folder", command = self._select_output_folder).grid(
            row = row, column = 2, sticky = "w"
        )
        ttk.Button(frame, text = "Default", command = self._default_output_folder).grid(
            row = row, column = 3, sticky = "w"
        )

        return row + 1

    def _build_tooltip_section(self, frame, row):
        ttk.Label(frame, text = "Show tooltip").grid(row = row, column = 0, sticky = "w")
        ttk.Checkbutton(frame, variable = self.tooltip_state).grid(
            row = row, column = 1, sticky = "w"
        )
        ttk.Button(frame, text = "Default", command = lambda: self.tooltip_state.set(1)).grid(
            row = row, column = 3, sticky = "w"
        )
        self.tooltip_state.trace_add("write", lambda *_: self._check_changes())

        return row + 1

    def _build_digital_io_section(self, frame, row):
        ttk.Label(frame, text = "Enable digital IO").grid(row = row, column = 0, sticky = "w")
        ttk.Checkbutton(frame, variable = self.digital_io_state).grid(
            row = row, column = 1, sticky = "w"
        )
        ttk.Button(frame, text = "Default", command = lambda: self.digital_io_state.set(1)).grid(
            row = row, column = 3, sticky = "w"
        )
        self.digital_io_state.trace_add("write", lambda *_: self._check_changes())

        return row + 1

    def _build_entry_section(self, frame, row):
        """Build integer entry fields with validation and defaults."""
        self._max_point_entry = self._add_validated_entry(
            frame,
            row = row,
            label = "Max points to plot (live plotting)",
            default_val = self.setting_manager.load_setting("max_points_to_plot"),
            default_btn_text = "Default",
            default_btn_cmd = self._default_max_points_to_plot,
            focus_out_cmd = self.on_focus_out,
        )

        row = row + 1

        self._max_queue_entry = self._add_validated_entry(
            frame,
            row = row,
            label = "Max queue size (live plotting)",
            default_val = self.setting_manager.load_setting("max_queue_size"),
            default_btn_text = "Default",
            default_btn_cmd = self._default_max_queue_size,
            focus_out_cmd = self.on_focus_out_queue,
        )

        return row + 1

    def _build_save_section(self):
        self._save_btn = ttk.Button(
            self.root, text = "Save settings", command = self._save_settings
        )
        self._save_btn.pack()
        self._save_btn.bind("<FocusOut>", self.on_button_focus_out)

        self._info_lbl = ttk.Label(
            self.root, text = "", foreground = "red", font = ("Arial", 12, "bold")
        )
        self._info_lbl.pack()

    # ─── UI Helper Methods ───────────────────────────────────────────────────
    def _add_path_row(self, frame, row, label, path):
        ttk.Label(frame, text = label).grid(row = row, column = 0, sticky = "w")
        self.create_copiable_label(frame, text = os.path.abspath(path)).grid(row = row, column = 1, sticky = "w")
        return row + 1

    def _add_validated_entry(
            self, frame, row, label, default_val, default_btn_text, default_btn_cmd, focus_out_cmd
    ):
        ttk.Label(frame, text = label).grid(row = row, column = 0, sticky = "w")
        entry = ttk.Entry(frame, validate = "key", validatecommand = self.int_validate_cmd)
        entry.grid(row = row, column = 1, sticky = "w")
        entry.insert(0, default_val)
        entry.bind("<KeyRelease>", self._check_changes)
        entry.bind("<FocusOut>", focus_out_cmd)

        ttk.Button(frame, text = default_btn_text, command = default_btn_cmd).grid(
            row = row, column = 3, sticky = "w"
        )
        return entry

    def create_copiable_label(self, parent, text):
        width = max(10, len(text) + 3)

        entry = tk.Entry(
            parent,
            state = "readonly",
            borderwidth = 0,
            relief = "flat",
            width = width,
            takefocus = False,
        )
        entry.grid(sticky = "w")  # caller can override grid later
        entry.config(state = "normal")
        entry.insert(0, text)
        entry.config(state = "readonly")
        return entry

    def update_copiable_label(self, entry, text):
        entry.config(state = "normal")
        entry.delete(0, tk.END)
        entry.insert(0, text)
        entry.config(state = "readonly")

    # ─── Settings Lifecycle ──────────────────────────────────────────────────
    def _collect_settings(self):
        return {
            "selected_output_folder": os.path.dirname(self.output_base_file_path),
            "show_tooltip": "False" if self.tooltip_state.get() == 0 else "True",
            "enable_digital_io": "False" if self.digital_io_state.get() == 0 else "True",
            "max_points_to_plot": int(self._max_point_entry.get()),
            "max_queue_size": int(self._max_queue_entry.get()),
        }

    def _check_changes(self, event = None):
        changed = self._collect_settings() != self._original_settings
        self._save_btn.config(state = "normal" if changed else "disabled")

    def _update_save_button(self):
        self._save_btn.config(state = "disabled")

    def _save_settings(self):
        current = self._collect_settings()
        for key, val in current.items():
            self.setting_manager.save_setting(key, val)

        self._original_settings = current
        self._update_save_button()
        self._info_lbl.config(text = "Restart the app to apply the new settings!")

    # ─── UI Event Handlers ───────────────────────────────────────────────────
    def _select_output_folder(self):
        folder = filedialog.askdirectory(title = "Select base folder for the output files!")
        if folder:
            self.output_base_file_path = folder
            self.update_copiable_label(self._output_file_lbl, os.path.abspath(self.output_base_file_path))
            self._check_changes()

    def _default_output_folder(self):
        self.output_base_file_path = self.orig_output_base_file_path
        self.update_copiable_label(self._output_file_lbl, os.path.abspath(self.output_base_file_path))
        self._check_changes()

    def _default_max_points_to_plot(self):
        self._set_entry_value(self._max_point_entry, "500")

    def _default_max_queue_size(self):
        self._set_entry_value(self._max_queue_entry, "100")

    def _set_entry_value(self, entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, value)
        self._check_changes()

    def validate_int(self, value):
        return value == "" or value.isdigit()

    def on_focus_out(self, event):
        self._enforce_min_value(self._max_point_entry, 100)

    def on_focus_out_queue(self, event):
        self._enforce_min_value(self._max_queue_entry, 100)

    def _enforce_min_value(self, entry, minimum):
        value = entry.get()
        if value and int(value) < minimum:
            self._set_entry_value(entry, str(minimum))
        self._check_changes()

    def on_button_focus_out(self, event):
        self._info_lbl.config(text = "")

    def close_app(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Settings app")
    app = SettingsApp(root)


    def on_close():
        app.close_app()
        sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
