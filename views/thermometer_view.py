# ─── Standard Library ────────────────────────────────────────────────────────
import queue

# ─── Third-Party Libraries ───────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox

# ─── Local Modules ───────────────────────────────────────────────────────────
from instruments.instrument_manager import InstrumentManager
from utils.ui_utils.live_plotter import LiveDataPlotter
from utils.logger_manager import safe_execute
from utils.settings_utils import load_probe_data
from utils.other_utils import (
    connect_with_popup,
    get_widget_value,
    load_visa_resources_util,
    save_setting_from_widget,
)
from utils.plot_utils import create_dual_axis_plot
from utils.ui_utils.logger_panel import LoggingPanel
from utils.constants import Keys, EntryConfig, States, Logger


class ThermometerView:
    def __init__(self, root, probe_path, setting_manager, logger, profile, parent_app=None):
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)
        self.parent_app = parent_app
        self.controller = None
        self.live_data_plotter = None

        # Settings
        self.probe_path = probe_path
        self.setting_manager = setting_manager
        self.profile = profile

        # Logger
        self.logger = logger

        # Instrument
        self.instrument_manager = InstrumentManager()

        # Control variables
        self.running = False
        self.preview_running = False
        self.visa_resource = tk.StringVar()
        self.probes = load_probe_data(self.probe_path)
        self.selected_probe = tk.StringVar(value = self.setting_manager.load_setting("probe"))
        self.R0 = tk.DoubleVar()
        self.TCR = tk.DoubleVar()
        self.interval = tk.DoubleVar(value = self.setting_manager.load_setting(Keys.INTERVAL))
        self.average_count = tk.IntVar(value = self.setting_manager.load_setting(Keys.AVG_COUNT))

        # Data
        self.timestamps = []
        self.resistance_y1_data = []
        self.temperature_y2_data = []
        self.data_queue = queue.Queue()
        self.resistance_y1 = tk.DoubleVar()
        self.temperature_y2 = tk.DoubleVar()

        self._create_widgets()
        self._setup_plot()
        self._setup_logger_panel()
        self._load_visa_resources()
        self._update_probe_values()

        # Placeholder
        ttk.Label(self.frame, text = "").grid(row = 4, column = 0, pady = 19)

        self.live_data_plotter = LiveDataPlotter(self.canvas, self.axes, self.lines, self.average_count.get(), self.log)

    def get_visa_resource(self):
        return self.visa_resource.get()

    def get_R0_TCR(self):
        return self.R0.get(), self.TCR.get()

    def get_probe_name(self):
        return self.selected_probe.get()

    def set_start_preview_button_command(self, command):
        self.preview_start_button.config(command = command)

    def set_stop_preview_button_command(self, command):
        self.preview_stop_button.config(command = command)

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
        self._create_thermoprobe_selector()
        self._create_measurement_settings_section()
        self._create_preview_section()
        self._create_live_display_section()

    def _create_visa_selector(self):
        ttk.Label(self.frame, text = "VISA Resource:").grid(row = 0, column = 0)
        self.visa_dropdown = ttk.Combobox(self.frame, textvariable = self.visa_resource, width = 40)
        self.visa_dropdown.grid(row = 0, column = 1, columnspan = 3)

        self.refresh_button = ttk.Button(self.frame, text = "Refresh", command = self._load_visa_resources)
        self.refresh_button.grid(row = 0, column = 4, padx = 5, pady = 10)

    def _create_thermoprobe_selector(self):
        ttk.Label(self.frame, text = "Thermoprobe:").grid(row = 1, column = 0)
        self.probe_dropdown = ttk.Combobox(self.frame, textvariable = self.selected_probe,
                                           values = list(self.probes.keys()),
                                           width = 11)
        self.probe_dropdown.grid(row = 1, column = 1)
        self.probe_dropdown.bind("<<ComboboxSelected>>", self._update_probe_values)

        ttk.Label(self.frame, text = "R₀:").grid(row = 1, column = 2)
        ttk.Entry(self.frame, textvariable = self.R0, width = 10, state = States.READONLY).grid(row = 1, column = 3)

        ttk.Label(self.frame, text = "TCR:").grid(row = 1, column = 4)
        ttk.Entry(self.frame, textvariable = self.TCR, width = 10, state = States.READONLY).grid(row = 1, column = 5)

    def _create_measurement_settings_section(self):
        self._entry_with_label(2, 0, "Interval (s):", self.interval, self._save_entry_value, Keys.INTERVAL)
        self._entry_with_label(2, 2, "Average count:", self.average_count, self._save_entry_value, Keys.AVG_COUNT,
                               self._update_average_count)

        self.start_button = ttk.Button(self.frame, text = "Start")
        self.start_button.grid(row = 2, column = 4)

        self.stop_button = ttk.Button(self.frame, text = "Stop", state = States.DISABLED)
        self.stop_button.grid(row = 2, column = 5)

    def _create_live_display_section(self):
        ttk.Label(self.frame, text = f"Live {self.profile.y1_label}:").grid(row = 3, column = 0, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.resistance_y1).grid(row = 3, column = 1, sticky = 'w')
        ttk.Label(self.frame, text = f"Live {self.profile.y2_label}:").grid(row = 3, column = 2, sticky = 'e')
        ttk.Label(self.frame, textvariable = self.temperature_y2, foreground = 'red').grid(row = 3, column = 3,
                                                                                           sticky = 'w')

    def _create_preview_section(self):
        self.preview_start_button = ttk.Button(self.frame, text = "Start Preview")
        self.preview_start_button.grid(row = 3, column = 4)
        self.preview_stop_button = ttk.Button(self.frame, text = "Stop Preview",
                                              state = States.DISABLED)
        self.preview_stop_button.grid(row = 3, column = 5)

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
                                             mock_resources = ("MOCK",))
        self.visa_dropdown['values'] = resources
        self.visa_resource.set(resources[0] if resources else "No VISA resources found")
        self.logger.info(f"Loaded VISA resources: {resources}")

    def _save_entry_value(self, name, value):
        save_setting_from_widget(self.setting_manager, name, value, logger = self.logger)

    def _setup_plot(self):
        _, ax1, ax2, line1, line2, self.canvas = create_dual_axis_plot(
            self.root, f"Live {self.profile.name}", "Time (s)", self.profile.y1_label, self.profile.y2_label)
        self.lines = [line1, line2]
        self.axes = [ax1, ax2]

    def loading_connection(self, connect_func):
        return connect_with_popup(self.root, self.visa_resource.get(), self.logger, connect_func)

    @safe_execute
    def _update_average_count(self):
        if self.live_data_plotter and self.average_count:
            self.live_data_plotter.set_average_count(get_widget_value(self.average_count))

    @safe_execute
    def _update_probe_values(self, event=None):
        probe = self.selected_probe.get()
        if probe in self.probes:
            self.R0.set(self.probes[probe]["R0"])
            self.TCR.set(self.probes[probe]["TCR"])
            self.setting_manager.save_setting("probe", probe)
            self.logger.info(f"Probe selected: {probe}, R0={self.R0.get()}, TCR={self.TCR.get()}")

    def _set_widget_states(self, enabled: bool, preview: bool):
        # Enabled: allow to start measurement
        # Preview: allow to start preview
        state = States.NORMAL if enabled and preview else States.DISABLED

        if enabled and preview:
            self.start_button.config(state = States.NORMAL)
            self.stop_button.config(state = States.DISABLED)
            self.preview_start_button.config(state = States.NORMAL)
            self.preview_stop_button.config(state = States.DISABLED)

        if not enabled and preview:
            self.start_button.config(state = States.DISABLED)
            self.stop_button.config(state = States.NORMAL)
            self.preview_start_button.config(state = States.DISABLED)
            self.preview_stop_button.config(state = States.DISABLED)

        if not preview and enabled:
            self.start_button.config(state = States.DISABLED)
            self.stop_button.config(state = States.DISABLED)
            self.preview_start_button.config(state = States.DISABLED)
            self.preview_stop_button.config(state = States.NORMAL)

        widgets = [
            self.visa_dropdown,
            self.refresh_button,
            self.probe_dropdown
        ]

        for widget in widgets:
            widget.config(state = state)

    def set_started_measurement_controls(self):
        self._set_widget_states(enabled = False, preview = True)

    def set_started_preview_controls(self):
        self._set_widget_states(enabled = True, preview = False)

    def enable_controls(self):
        self._set_widget_states(enabled = True, preview = True)

    def start_live_display(self):
        self.live_data_plotter.reset()
        self.live_data_plotter.start()
        self.running = True
        self._set_widget_states(enabled = False, preview = True)

        if self.parent_app:
            self.parent_app.set_widget_states(False)

        self.log(Logger.INFO, "Live display started.")

    def show_measurement_stopped(self):
        if self.running:
            self.running = False

            self.live_data_plotter.stop()

            # Control widget accessibility
            self._set_widget_states(enabled = True, preview = True)

            self.log(Logger.INFO, "Live display stopped.")

            if self.parent_app:
                self.parent_app.stop_apps()

    def start_preview(self):
        self.preview_running = True
        self._set_widget_states(enabled = True, preview = False)

        if self.parent_app:
            self.parent_app.set_widget_states(False)

    def stop_preview(self):
        self.preview_running = False
        self._set_widget_states(enabled = True, preview = True)

    def update(self, running, preview, timestamp, resistance, temperature):
        if not running and not preview:
            self.show_measurement_stopped()
            self.stop_preview()
        else:
            self.root.after(0, lambda: self.resistance_y1.set(round(resistance, 2)))
            self.root.after(0, lambda: self.temperature_y2.set(round(temperature, 2)))

            if not preview:
                self.live_data_plotter.enqueue(
                    timestamp,
                    resistance,
                    temperature
                )

    def log(self, message_type, message):
        if message_type == Logger.INFO:
            self.root.after(0, lambda: self.logger.info(message))
        elif message_type == Logger.WARNING:
            self.root.after(0, lambda: self.logger.warning(message))
        else:
            self.root.after(0, lambda: self.logger.error(message))
            messagebox.showerror("Error", message)
