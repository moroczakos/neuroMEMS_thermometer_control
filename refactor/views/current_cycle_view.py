# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import traceback

# ─── Third-Party Libraries ───────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox

# ─── Local Modules ───────────────────────────────────────────────────────────
from instruments.instrument_manager import InstrumentManager
from utils.ui_utils.live_plotter import LiveDataPlotter
from utils.logger_manager import safe_execute
from utils.other_utils import (
    connect_with_popup,
    get_widget_value,
    load_visa_resources_util,
    save_setting_from_widget,
)
from utils.plot_utils import create_dual_axis_plot
from utils.ui_utils.logger_panel import LoggingPanel
from utils.constants import Keys, EntryConfig, States, Labels, Logger


class CurrentCycleView:
    def __init__(self, root, setting_manager, logger, profile, parent_app=None):
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)
        self.parent_app = parent_app
        self.controller = None
        self.live_data_plotter = None

        # Settings
        self.setting_manager = setting_manager
        self.start_low = True  # Square wave current starts with low value
        self.profile = profile

        # Logger
        self.logger = logger

        # Instrument
        self.instrument_manager = InstrumentManager()
        self.instrument_alias = None

        # Control variables
        self.running = False
        self.visa_resource = tk.StringVar()
        self.current_high = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.CURRENT_HIGH))
        self.current_low = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.CURRENT_LOW))
        self.duration_high = tk.IntVar(value = self.setting_manager.load_setting(Keys.DURATION_HIGH))
        self.duration_low = tk.IntVar(value = self.setting_manager.load_setting(Keys.DURATION_LOW))
        self.cycles = tk.IntVar(value = self.setting_manager.load_setting(Keys.CYCLES))
        self.other_settings = tk.StringVar()
        self.other_settings_value = tk.DoubleVar()
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.INTERVAL))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting(Keys.AVG_COUNT))

        # Data
        self.timestamps = []
        self.current_y1_data = []
        self.voltage_y2_data = []
        self.data_queue = queue.Queue()
        self.current_y1 = tk.DoubleVar()
        self.voltage_y2 = tk.DoubleVar()

        self._create_widgets()
        self._setup_plot()
        self._setup_logger_panel()
        self._load_visa_resources()
        self._load_other_settings()

        self.live_data_plotter = LiveDataPlotter(self.canvas, self.axes, self.lines, self.average_count.get(), self.log)

    def get_visa_resource(self):
        return self.visa_resource.get()

    def get_start_low(self):
        return self.start_low_var.get()

    def set_start_button_command(self, command):
        self.start_button.config(command = command)

    def set_stop_button_command(self, command):
        self.stop_button.config(command = command)

    def _setup_logger_panel(self):
        """Insert the reusable LoggingPanel into the GUI and link it to the logger."""
        self.logging_panel = LoggingPanel(self.root, logger = self.logger)
        self.logging_panel.pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        self.log(Logger.INFO, "Application started and UI initialized.")

    def _create_widgets(self):
        self.frame = ttk.Frame(self.root, padding = 10)
        self.frame.pack(fill = tk.X)

        self._create_visa_selector()
        self._create_current_settings_section()
        self._create_other_settings_section()
        self._create_measurement_settings_section()
        self._create_live_display_section()

    def _create_visa_selector(self):
        ttk.Label(self.frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(self.frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3)

        self.refresh_button = ttk.Button(self.frame, text = "Refresh", command = self._load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5, pady = 10)

    def _create_current_settings_section(self):
        row = 1
        ttk.Label(self.frame, text = Labels.CURRENT_SOURCE_SETTINGS, justify = 'center') \
            .grid(row = row, column = 0, columnspan = 9)

        row += 1
        self.c_high_entry = self._entry_with_label(row, 0, "High Current (A):", self.current_high,
                                                   self._save_entry_value, Keys.CURRENT_HIGH)
        self.c_low_entry = self._entry_with_label(row, 2, "Low Current (A):", self.current_low,
                                                  self._save_entry_value,
                                                  Keys.CURRENT_LOW)

        ttk.Label(self.frame, text = Labels.STARTS_WITH_LOW).grid(row = row, column = 4)
        self.start_low_var = tk.BooleanVar(value = self.start_low)
        self.start_low_cbutton = ttk.Checkbutton(self.frame, variable = self.start_low_var,
                                                 command = self._update_start_low)
        self.start_low_cbutton.grid(row = row, column = 5)

        self.cycles_entry = self._entry_with_label(row, 6, "Cycles:", self.cycles, self._save_entry_value,
                                                   Keys.CYCLES)

        row += 1
        self.d_high_entry = self._entry_with_label(row, 0, "High Duration (s):", self.duration_high,
                                                   self._save_entry_value, Keys.DURATION_HIGH)
        self.d_low_entry = self._entry_with_label(row, 2, "Low Duration (s):", self.duration_low,
                                                  self._save_entry_value,
                                                  Keys.DURATION_LOW)

    def _create_other_settings_section(self):
        ttk.Label(self.frame, text = Labels.OTHER_SETTINGS).grid(row = 3, column = 4)

        self.other_settings_dropdown = ttk.Combobox(
            self.frame, textvariable = self.other_settings, width = 16, state = States.READONLY
        )
        self.other_settings_dropdown.grid(row = 3, column = 5, columnspan = 2)
        self.other_settings_dropdown.bind("<<ComboboxSelected>>", self._on_other_setting_selected)

        self.other_settings_entry = ttk.Entry(
            self.frame, textvariable = self.other_settings_value, width = EntryConfig.WIDTH,
            justify = EntryConfig.JUSTIFY
        )
        self.other_settings_entry.grid(row = 3, column = 7)

        self.save_other_button = ttk.Button(self.frame, text = Labels.SAVE, command = self._save_other_setting)
        self.save_other_button.grid(row = 3, column = 8, padx = 5)

    def _create_measurement_settings_section(self):
        ttk.Label(self.frame, text = Labels.CURRENT_MEASUREMENT_SETTINGS, justify = 'center') \
            .grid(row = 4, column = 0, columnspan = 9)

        self._entry_with_label(5, 0, "Interval (s):", self.interval, self._save_entry_value, Keys.INTERVAL)
        self._entry_with_label(5, 2, "Average count:", self.average_count, self._save_entry_value, Keys.AVG_COUNT,
                               self._update_average_count)

        self.start_button = ttk.Button(self.frame, text = "Start")
        self.start_button.grid(row = 5, column = 4)

        self.stop_button = ttk.Button(self.frame, text = "Stop", state = States.DISABLED)
        self.stop_button.grid(row = 5, column = 5)

    def _create_live_display_section(self):
        ttk.Label(self.frame, text = "Live current (A):").grid(row = 6, column = 0, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.current_y1, foreground = 'blue').grid(row = 6, column = 1,
                                                                                        sticky = 'w')

        ttk.Label(self.frame, text = "Live voltage (V):").grid(row = 6, column = 2, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.voltage_y2, foreground = 'black').grid(row = 6, column = 3,
                                                                                         sticky = 'w')

    def _entry_with_label(self, row, col, label, variable, trace_callback=None, key=None, command=None):
        ttk.Label(self.frame, text = label).grid(row = row, column = col)
        entry = ttk.Entry(self.frame, textvariable = variable, width = EntryConfig.WIDTH,
                          justify = EntryConfig.JUSTIFY)

        def all_trace_callback(k, v):
            trace_callback(k, v)

            if command:
                command()

        entry.grid(row = row, column = col + 1)
        if trace_callback and key:
            variable.trace_add("write", lambda *args: all_trace_callback(key, variable))
        return entry

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

    def _on_other_setting_selected(self, event=None):
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

    def _save_entry_value(self, name, value):
        save_setting_from_widget(self.setting_manager, name, value, logger = self.logger)

    def _setup_plot(self):
        _, ax1, ax2, line1, line2, self.canvas = create_dual_axis_plot(
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label,
            "blue",
            "black")
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]

    def loading_connection(self, connect_func):
        return connect_with_popup(self.root, self.visa_resource.get(), self.logger, connect_func)

    @safe_execute
    def _update_start_low(self):
        # Update self.start_low based on the checkbox state
        self.start_low = self.start_low_var.get()
        self.log(Logger.INFO, f"The start with low current state changed to {self.start_low}")

    @safe_execute
    def _update_average_count(self):
        if self.live_data_plotter and self.average_count:
            self.live_data_plotter.set_average_count(get_widget_value(self.average_count))

    def _set_widget_states(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.start_button.config(state = state)
        self.stop_button.config(state = "normal" if not enabled else "disabled")

        widgets = [
            self.visa_dropdown,
            self.refresh_button,
            self.c_high_entry,
            self.c_low_entry,
            self.start_low_cbutton,
            self.d_high_entry,
            self.d_low_entry,
            self.cycles_entry,
            self.other_settings_dropdown,
            self.other_settings_entry,
            self.save_other_button,
        ]

        for widget in widgets:
            widget.config(state = state)

    def disable_controls(self):
        self._set_widget_states(enabled = False)

    def enable_controls(self):
        self._set_widget_states(enabled = True)

    def start_live_display(self):
        self.live_data_plotter.reset()
        self.live_data_plotter.start()
        self.running = True

        self.log(Logger.INFO, "Live display started.")

    def show_measurement_stopped(self):
        if self.running:
            self.running = False

            self.live_data_plotter.stop()

            # Control widget accessibility
            self._set_widget_states(enabled = True)

            self.log(Logger.INFO, "Live display stopped.")

            if self.parent_app:
                self.parent_app.stop_apps()

    def update(self, running, timestamp, current, voltage, _):
        if not running:
            self.show_measurement_stopped()

        self.root.after(0, lambda: self.current_y1.set(round(current, 4)))
        self.root.after(0, lambda: self.voltage_y2.set(round(voltage, 2)) if voltage is not None else float('nan'))

        self.live_data_plotter.enqueue(
            timestamp,
            current,
            voltage if voltage is not None else float('nan')
        )

    def log(self, message_type, message):
        if message_type == Logger.INFO:
            self.root.after(0, lambda: self.logger.info(message))
        elif message_type == Logger.WARNING:
            self.root.after(0, lambda: self.logger.warning(message))
        else:
            self.root.after(0, lambda: self.logger.error(message))
            messagebox.showerror("Error", message)
