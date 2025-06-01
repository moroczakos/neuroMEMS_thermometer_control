# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import traceback

# ─── Third-Party Libraries ───────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox

# ─── Local Modules ───────────────────────────────────────────────────────────
from concurrent.futures import ThreadPoolExecutor
from instruments.instrument_manager import InstrumentManager
from utils.logger_manager import safe_execute
from utils.other_utils import (
    connect_with_popup,
    get_widget_value,
    load_visa_resources_util,
    save_setting_from_widget,
)
from utils.plot_utils import create_dual_axis_plot, update_plot
from utils.ui_utils.logger_panel import LoggingPanel
from utils.constants import Keys, EntryConfig, States, Labels, UI, Other, Logger

class LiveDataPlotter:
    def __init__(self, canvas, axes, lines, average_count, logger):
        self.timestamps = []
        self.y1_data = []
        self.y2_data = []
        self.logger = logger
        self.average_count_var = average_count

        self.canvas = canvas
        self.axes = axes
        self.lines = lines

        self.reset()

    def reset(self):
        self.data_queue = queue.Queue()
        self.data_counter = 0
        self.total_y1 = 0.0
        self.total_y2 = 0.0
        self.running = False

    def start(self):
        self.running = True
        ThreadPoolExecutor(max_workers=4).submit(self._worker_loop)

    def stop(self):
        self.running = False

    def enqueue(self, timestamp, y1, y2):
        self.data_queue.put((timestamp, y1, y2))

    def _worker_loop(self):
        while self.running or not self.data_queue.empty():
            try:
                timestamp, y1, y2 = self.data_queue.get(timeout=0.5)
                self._accumulate_and_plot(timestamp, y1, y2)
            except queue.Empty:
                continue

    def _accumulate_and_plot(self, timestamp, y1, y2):
        try:
            avg_count = get_widget_value(self.average_count_var) or 1
            self.data_counter += 1
            self.total_y1 += y1
            self.total_y2 += y2

            if self.data_counter >= avg_count:
                self.timestamps.append(timestamp)
                self.y1_data.append(self.total_y1 / avg_count)
                self.y2_data.append(self.total_y2 / avg_count)

                self.total_y1 = 0.0
                self.total_y2 = 0.0
                self.data_counter = 0

                if len(self.timestamps) > UI.MAX_POINTS:
                    self.timestamps = self.timestamps[-UI.MAX_POINTS:]
                    self.y1_data = self.y1_data[-UI.MAX_POINTS:]
                    self.y2_data = self.y2_data[-UI.MAX_POINTS:]

                update_plot(
                    [(self.lines[0], (self.timestamps, self.y1_data)),
                     (self.lines[1], (self.timestamps, self.y2_data))],
                    self.axes, self.canvas)

        except Exception as e:
            self.logger.error(f"Plotting error: {e}\n{traceback.format_exc()}")
