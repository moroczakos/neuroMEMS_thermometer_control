# ─── Standard Library ────────────────────────────────────────────────────────
import json
import os
import queue
import traceback

# ─── Third-Party Libraries ───────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ─── Local Modules ───────────────────────────────────────────────────────────
from base_classes.view_base import ViewBase
from instruments.instrument_manager import InstrumentManager
from utils.ui_utils.entry_with_label import EntryWithLabel
from utils.ui_utils.live_plotter import LiveDataPlotter
from utils.logger_manager import safe_execute
from utils.other_utils import (
    connect_with_popup,
    get_widget_value,
    load_visa_resources_util,
    save_setting_from_widget,
)
from utils.plot_utils import create_dual_axis_plot
from utils.constants import Keys, EntryConfig, States, Labels, Logger, UI
from utils.ui_utils.tooltip import ToolTip


class CurrentCycleView(ViewBase):
    def __init__(self, root, setting_manager, logger, profile):
        ViewBase.__init__(self, root, setting_manager, logger)

        self.controller = None
        self.live_data_plotter = None
        self.open_editor = None

        # Settings
        self.start_low = True  # Square wave current starts with low value
        self.profile = profile

        # Instrument
        self.instrument_manager = InstrumentManager()
        self.instrument_alias = None

        # Control variables
        self.running = False
        self.visa_resource = tk.StringVar()
        self.cycles = tk.IntVar(value = self.setting_manager.load_setting(Keys.CYCLES))
        self.other_settings = tk.StringVar()
        self.other_settings_value = tk.DoubleVar()
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.INTERVAL))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting(Keys.AVG_COUNT))
        self.max_points_to_plot = self.setting_manager.load_setting(UI.MAX_POINTS_TO_PLOT)

        # Data
        self.timestamps = []
        self.current_y1_data = []
        self.voltage_y2_data = []
        self.data_queue = queue.Queue()
        self.current_y1 = tk.DoubleVar()
        self.voltage_y2 = tk.DoubleVar()
        self.cycle_sequence_waveform_label = tk.StringVar(
            value = f"Selected cycle waveform: {self.setting_manager.load_setting(Keys.CYCLE_SEQUENCE_FILE)} (click to enlarge)")

        self._create_widgets()
        self._setup_plot()
        self.setup_logger_panel()
        self._load_visa_resources()
        self._load_other_settings()

        self.live_data_plotter = LiveDataPlotter(self.canvas, self.axes, self.lines, self.scrollbar,
                                                 self.average_count.get(), self.log)
        self.live_data_plotter.set_max_points_to_plot(self.max_points_to_plot)

    def get_visa_resource(self):
        return self.visa_resource.get()

    def set_start_button_command(self, command):
        self.start_button.config(command = command)

    def set_stop_button_command(self, command):
        self.stop_button.config(command = command)

    def set_cycle_sequence_editor_app_opener(self, opener):
        self.open_editor = opener

    def _create_widgets(self):
        self.frame = ttk.Frame(self.root, padding = 10)
        self.frame.pack(fill = tk.X)

        self._create_visa_selector()
        self._create_current_settings_section()
        self._create_cycle_sequence_plotter()
        self._create_other_settings_section()
        self._create_measurement_settings_section()
        self._create_live_display_section()

    def _create_visa_selector(self):
        ttk.Label(self.frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(self.frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3)

        self.refresh_button = ttk.Button(self.frame, text = "Ⓘ Refresh", command = self._load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5, pady = 10)
        ToolTip(self.refresh_button, self.tooltips.get("refresh_button", ""))

    def _create_current_settings_section(self):
        row = 1
        ttk.Label(self.frame, text = Labels.CURRENT_SOURCE_SETTINGS, justify = 'center') \
            .grid(row = row, column = 0, columnspan = 9)

        row += 1
        self.edit_cycle_button = ttk.Button(self.frame, text = "Ⓘ Cycle waveform editor",
                                            command = self._edit_cycle_setting)
        self.edit_cycle_button.grid(row = row, column = 0, columnspan = 2)
        ToolTip(self.edit_cycle_button, self.tooltips.get("edit_cycle_button", ""))

        ttk.Label(self.frame, textvariable = self.cycle_sequence_waveform_label, foreground = 'black',
                  justify = 'center').grid(row = row, column = 2, columnspan = 4)

        row += 1
        self.change_cycle_setting_button = ttk.Button(self.frame, text = "Ⓘ Change cycle waveform file",
                                                      command = self._change_cycle_setting_file)
        self.change_cycle_setting_button.grid(row = row, column = 0, columnspan = 2)
        ToolTip(self.change_cycle_setting_button, self.tooltips.get("change_cycle_setting_button", ""))

        row += 2

        self.cycle_ewl = EntryWithLabel(self.frame,
                                        labeltext = "Ⓘ Cycles:",
                                        entrytextvariable = self.cycles,
                                        entrywidth = EntryConfig.WIDTH,
                                        entryjustify = EntryConfig.JUSTIFY,
                                        savecommandkey = Keys.CYCLES,
                                        saveentrytextvariablecommand = self._save_entry_value,
                                        command = self._plot_waveform)
        self.cycle_ewl.grid(row = row, column = 0, columnspan = 2)
        ToolTip(self.cycle_ewl.get_label(), self.tooltips.get("cycle_label", ""))

    def _create_cycle_sequence_plotter(self):
        row = 3

        self.preview_fig, self.preview_ax = plt.subplots(figsize = (3.5, 0.8))
        self.preview_canvas = FigureCanvasTkAgg(self.preview_fig, master = self.frame)
        self.preview_canvas_widget = self.preview_canvas.get_tk_widget()
        self.preview_canvas_widget.grid(row = row, column = 2, columnspan = 4, rowspan = 3, sticky = "w", padx = 5,
                                        pady = 5)
        self.preview_canvas_widget.bind("<Button-1>", self._show_full_plot_popup)
        ToolTip(self.preview_canvas_widget, self.tooltips.get("preview_canvas_widget", ""))

        self.preview_ax.tick_params(
            axis = 'both',  # apply to both x and y axes
            which = 'both',  # apply to both major and minor ticks
            bottom = False,  # remove bottom ticks
            top = False,  # remove top ticks
            left = False,  # remove left ticks
            right = False,  # remove right ticks
            labelbottom = False,  # remove x tick labels
            labelleft = False  # remove y tick labels
        )
        self.preview_ax.grid(True)
        self._plot_waveform()

    def _create_other_settings_section(self):
        row = 2
        ttk.Label(self.frame, text = Labels.OTHER_SETTINGS).grid(row = row, column = 6, columnspan = 3)

        self.other_settings_dropdown = ttk.Combobox(
            self.frame, textvariable = self.other_settings, width = 16, state = States.READONLY
        )

        row += 1
        self.other_settings_dropdown.grid(row = row, column = 6, columnspan = 2)
        self.other_settings_dropdown.bind("<<ComboboxSelected>>", self._on_other_setting_selected)

        self.other_settings_entry = ttk.Entry(
            self.frame, textvariable = self.other_settings_value, width = EntryConfig.WIDTH,
            justify = EntryConfig.JUSTIFY
        )
        self.other_settings_entry.grid(row = row, column = 8)

        row += 1
        self.save_other_button = ttk.Button(self.frame, text = "Save other settings",
                                            command = self._save_other_setting)
        self.save_other_button.grid(row = row, column = 6, columnspan = 3, padx = 5)

    def _create_measurement_settings_section(self):
        row = 6
        ttk.Label(self.frame, text = Labels.CURRENT_MEASUREMENT_SETTINGS, justify = 'center') \
            .grid(row = row, column = 0, columnspan = 9)

        row += 1

        self.interval_ewl = EntryWithLabel(self.frame,
                                           labeltext = "Ⓘ Interval (s):",
                                           entrytextvariable = self.interval,
                                           entrywidth = EntryConfig.WIDTH,
                                           entryjustify = EntryConfig.JUSTIFY,
                                           savecommandkey = Keys.INTERVAL,
                                           saveentrytextvariablecommand = self._save_entry_value)
        self.interval_ewl.grid(row = row, column = 0, columnspan = 2)
        ToolTip(self.interval_ewl.get_label(), self.tooltips.get("interval_label", ""))

        average_ewl = EntryWithLabel(self.frame,
                                     labeltext = "Ⓘ Average count:",
                                     entrytextvariable = self.average_count,
                                     entrywidth = EntryConfig.WIDTH,
                                     entryjustify = EntryConfig.JUSTIFY,
                                     savecommandkey = Keys.AVG_COUNT,
                                     saveentrytextvariablecommand = self._save_entry_value,
                                     command = self._update_average_count)
        average_ewl.grid(row = row, column = 2, columnspan = 2)
        ToolTip(average_ewl.get_label(), self.tooltips.get("average_label", ""))

        self.start_button = ttk.Button(self.frame, text = "Ⓘ Start")
        self.start_button.grid(row = row, column = 4)
        ToolTip(self.start_button, self.tooltips.get("current_start_btn", ""))

        self.stop_button = ttk.Button(self.frame, text = "Ⓘ Stop", state = States.DISABLED)
        self.stop_button.grid(row = row, column = 5)
        ToolTip(self.stop_button, self.tooltips.get("current_stop_btn", ""))

    def _create_live_display_section(self):
        row = 8
        ttk.Label(self.frame, text = "Live current (A):").grid(row = row, column = 0, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.current_y1, foreground = 'blue').grid(row = row, column = 1,
                                                                                        sticky = 'w')

        ttk.Label(self.frame, text = "Live voltage (V):").grid(row = row, column = 2, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.voltage_y2, foreground = 'black').grid(row = row, column = 3,
                                                                                         sticky = 'w')

    def _generate_waveform(self, sequence, n_cycles):
        def append_step(time_points, current_points, current_time, step):
            time_points.extend([current_time, current_time + step["duration"]])
            current_points.extend([step["current"], step["current"]])
            return current_time + step["duration"]

        time_points = []
        current_points = []
        current_time = 0

        if sequence and all(k in sequence[0] for k in ("current", "duration")):
            current_time = append_step(time_points, current_points, current_time, sequence.pop(0))

        for _ in range(n_cycles):
            for step in sequence:
                current_time = append_step(time_points, current_points, current_time, step)

        return time_points, current_points

    def _plot_waveform(self):
        sequence = self.setting_manager.load_setting(Keys.CYCLE_SEQUENCE)

        n_cycles = get_widget_value(self.cycles)

        if n_cycles:
            time_data, current_data = self._generate_waveform(sequence, n_cycles)

            self.preview_ax.clear()
            self.preview_ax.step(time_data, current_data, where = "post", linewidth = 2)
            self.preview_canvas.draw()

    def _show_full_plot_popup(self, event = None):
        popup = tk.Toplevel(self.root)
        popup.title("Cycle Waveform")
        popup.geometry("700x400")

        # Close when focus is lost
        popup.bind("<FocusOut>", lambda e: popup.destroy())

        fig, ax = plt.subplots(figsize = (6.5, 3))
        canvas = FigureCanvasTkAgg(fig, master = popup)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill = tk.BOTH, expand = True)

        sequence = self.setting_manager.load_setting(Keys.CYCLE_SEQUENCE)

        n_cycles = get_widget_value(self.cycles)

        if n_cycles:
            time_data, current_data = self._generate_waveform(sequence, n_cycles)

            ax.step(time_data, current_data, where = "post", linewidth = 2)
            ax.set_title("Current Cycle Waveform")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Current (A)")
            ax.grid(True)
            canvas.draw()

    @safe_execute
    def _load_visa_resources(self):
        resources = load_visa_resources_util(self.instrument_manager,
                                             only_tcpip = False,
                                             logger = self.logger,
                                             include_mock = True,
                                             mock_resources = ("MOCK_6221", "MOCK_2611"))
        self.visa_dropdown['values'] = resources
        self.visa_resource.set(resources[0] if resources else "No VISA resources found")
        self.log(Logger.INFO, f"Loaded VISA resources: {resources}")

    def _load_other_settings(self):
        try:
            # Save current selection
            current_key = self.other_settings.get()

            values = self.setting_manager.load_setting("device_settings")
            if not isinstance(values, dict):
                values = {}

            keys = list(values.keys())
            self.other_settings_dropdown['values'] = keys

            # Restore current selection if it still exists
            if current_key in keys:
                self.other_settings.set(current_key)
            elif keys:
                self.other_settings.set(keys[0])
            else:
                self.other_settings.set("")
                self.other_settings_value.set(0.0)

            self._on_other_setting_selected()

        except Exception as e:
            self.log(Logger.WARNING, f"Failed to load device settings: {e}\n{traceback.format_exc()}")
            self.other_settings_dropdown['values'] = []

    def _on_other_setting_selected(self, event = None):
        try:
            key = self.other_settings.get()
            settings_dict = self.setting_manager.load_setting("device_settings")
            if isinstance(settings_dict, dict) and key in settings_dict:
                self.other_settings_value.set(settings_dict[key])
                self.log(Logger.INFO, f"Loaded device setting '{key}': {settings_dict[key]}")
            else:
                self.other_settings_value.set(0.0)
        except Exception as e:
            self.log(Logger.WARNING, f"Failed to load selected device setting: {e}\n{traceback.format_exc()}")
            self.other_settings_value.set(0.0)

    def _save_other_setting(self):
        try:
            key = self.other_settings.get()
            value = self.other_settings_value.get()
            if not key:
                messagebox.showwarning("Warning", "Setting name is empty.")
                return

            settings_dict = self.setting_manager.load_setting("device_settings")
            if not isinstance(settings_dict, dict):
                settings_dict = {}

            settings_dict[key] = value
            self.setting_manager.save_setting("device_settings", settings_dict)

            self._load_other_settings()
            self.other_settings.set(key)  # Keep focus on saved key
            self.log(Logger.INFO, f"Saved device setting '{key}': {value}")
        except Exception as e:
            self.log(Logger.ERROR, f"Failed to save other setting: {e}\n{traceback.format_exc()}")

    def _change_cycle_setting_file(self):
        file_path = filedialog.askopenfilename(
            title = "Import Cycle Sequence from JSON",
            filetypes = [("JSON files", "*.json")],
            initialdir = self.input_file_path
        )
        if not file_path:
            self.logger.info("Import canceled by user.")
            return

        try:
            with open(file_path, "r") as f:
                sequence = json.load(f)

            if not isinstance(sequence, list):
                raise ValueError("JSON root should be a list.")

            file_name = os.path.basename(file_path)
            self.setting_manager.save_setting(Keys.CYCLE_SEQUENCE_FILE, file_name)
            self.setting_manager.save_setting(Keys.CYCLE_SEQUENCE, sequence)
            self.logger.info(f"Saved cycle sequence settings from {file_path}")

            self.root.after(0, lambda: self.cycle_sequence_waveform_label.set(
                f"Selected cycle waveform: {file_name} (click to enlarge)"))
            self._plot_waveform()

        except Exception as e:
            self.logger.error(f"Saving cycle sequence settings failed: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Saving Error", f"Saving cycle sequence settings failed: {e}")

    def _edit_cycle_setting(self):
        self.open_editor()

    def _save_entry_value(self, name, value):
        save_setting_from_widget(self.setting_manager, name, value, logger = self.logger)

    def _setup_plot(self):
        _, ax1, ax2, line1, line2, self.canvas, self.scrollbar = create_dual_axis_plot(
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label,
            "blue",
            "black")
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]
        self.scrollbar.config(command = self._on_scroll)

    def _on_scroll(self, *args):
        try:
            max_offset = self.live_data_plotter.get_max_offset()
            view_offset = self.live_data_plotter.get_view_offset()

            if args[0] == 'scroll':
                delta = int(args[1]) * self.max_points_to_plot
                self.live_data_plotter.set_view_offset(min(max_offset, max(view_offset - delta, 0)))
            elif args[0] == 'moveto':
                # Slider drag
                fraction = float(args[1])
                view_offset = int((1 - fraction) * (max_offset + self.max_points_to_plot))
                self.live_data_plotter.set_view_offset(max(0, min(view_offset - self.max_points_to_plot, max_offset)))

            if not self.running:
                self.live_data_plotter.update_plot()

        except Exception as e:
            self.logger.error(f"Scroll error: {e}\n{traceback.format_exc()}")

    def loading_connection(self, connect_func):
        return connect_with_popup(self.root, self.visa_resource.get(), self.logger, connect_func)

    @safe_execute
    def _update_average_count(self):
        if self.live_data_plotter and self.average_count:
            self.live_data_plotter.set_average_count(get_widget_value(self.average_count))

    def _set_widget_states(self, enabled: bool):
        state = States.NORMAL if enabled else States.DISABLED
        self.start_button.config(state = state)
        self.stop_button.config(state = States.NORMAL if not enabled else States.DISABLED)

        widgets = [
            self.visa_dropdown,
            self.refresh_button,
            self.change_cycle_setting_button,
            self.cycle_ewl.get_entry(),
            self.other_settings_dropdown,
            self.other_settings_entry,
            self.save_other_button,
            self.interval_ewl.get_entry()
        ]

        for widget in widgets:
            widget.config(state = state)

    def set_started_current_cycle_controls(self):
        self._set_widget_states(enabled = False)

    def enable_controls(self):
        self._set_widget_states(enabled = True)

    def disable_controls(self):
        self._set_widget_states(enabled = False)
        self.stop_button.config(state = States.DISABLED)

    def start_live_display(self):
        self.live_data_plotter.reset()
        self.live_data_plotter.start()
        self.running = True
        self._set_widget_states(enabled = False)

        self.log(Logger.INFO, "Live display started.")

    def show_measurement_stopped(self):
        if self.running:
            self.running = False

            self.live_data_plotter.stop()

            # Control widget accessibility
            self._set_widget_states(enabled = True)

            self.log(Logger.INFO, "Live display stopped.")

    def update(self, running, timestamp, current, voltage, _):
        if not running:
            self.show_measurement_stopped()
        else:
            self.root.after(0, lambda: self.current_y1.set(round(current, 4)))
            self.root.after(0, lambda: self.voltage_y2.set(round(voltage, 2)) if voltage is not None else float('nan'))

            self.live_data_plotter.enqueue(
                timestamp,
                current,
                voltage if voltage is not None else float('nan')
            )
