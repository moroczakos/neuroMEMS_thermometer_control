# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import traceback

# ─── Local Modules ───────────────────────────────────────────────────────────
from concurrent.futures import ThreadPoolExecutor
from utils.plot_utils import update_plot
from utils.constants import Logger


class LiveDataPlotter:
    def __init__(self, canvas, axes, lines, scrollbar, average_count, logger):
        self.data_queue = None
        self.data_counter = 0
        self.total_y1 = 0.0
        self.total_y2 = 0.0
        self.timestamps = []
        self.y1_data = []
        self.y2_data = []
        self.full_timestamps = []
        self.full_y1_data = []
        self.full_y2_data = []
        self.view_offset = 0  # 0 means most recent, positive = scroll to past
        self.running = False
        self.logger = logger
        self.average_count_var = average_count
        self.max_offset = 0
        self.max_points_to_plot = 100

        self.canvas = canvas
        self.axes = axes
        self.lines = lines
        self.scrollbar = scrollbar

        self.executor = None

        self.reset()

    def get_max_offset(self):
        return self.max_offset

    def get_view_offset(self):
        return self.view_offset

    def set_max_points_to_plot(self, value):
        self.max_points_to_plot = value

    def set_average_count(self, average_count):
        self.average_count_var = average_count

    def set_view_offset(self, view_offset):
        self.view_offset = view_offset

    def reset(self):
        if self.executor:
            self.executor.shutdown(wait = False)

        self.data_queue = queue.Queue()
        self.data_counter = 0
        self.total_y1 = 0.0
        self.total_y2 = 0.0
        self.timestamps = []
        self.y1_data = []
        self.y2_data = []
        self.full_timestamps = []
        self.full_y1_data = []
        self.full_y2_data = []
        self.view_offset = 0
        self.max_offset = 0
        self.running = False

    def start(self):
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers = 4)
        self.executor.submit(self._worker_loop)

    def stop(self):
        self.running = False
        if self.executor:
            self.executor.shutdown(wait = False)

    def enqueue(self, timestamp, y1, y2):
        self.data_queue.put((timestamp, y1, y2))

    def update_plot(self):
        # Calculate window range
        end = len(self.full_timestamps) - self.view_offset
        start = max(0, end - self.max_points_to_plot)

        self.timestamps = self.full_timestamps[start:end]
        self.y1_data = self.full_y1_data[start:end]
        self.y2_data = self.full_y2_data[start:end]

        total_points = len(self.full_timestamps)
        max_points = self.max_points_to_plot
        self.max_offset = max(total_points - max_points, 0)

        if total_points == 0:
            self.scrollbar.set(1.0, 1.0)
        else:
            lo = 1.0 - (self.view_offset + max_points) / total_points
            hi = 1.0 - self.view_offset / total_points
            self.scrollbar.set(lo, hi)

        update_plot(
            [(self.lines[0], (self.timestamps, self.y1_data)), (self.lines[1], (self.timestamps, self.y2_data))],
            self.axes,
            self.canvas)

    def _worker_loop(self):
        while self.running or not self.data_queue.empty():
            try:
                timestamp, y1, y2 = self.data_queue.get(timeout = 0.5)
                self._accumulate_and_plot(timestamp, y1, y2)
            except queue.Empty:
                continue

    def _accumulate_and_plot(self, timestamp, y1, y2):
        try:
            avg_count = self.average_count_var or 1
            self.data_counter += 1
            self.total_y1 += y1
            self.total_y2 += y2

            if self.data_counter >= avg_count:
                if self.data_counter == avg_count:
                    self.full_timestamps.append(timestamp)
                    self.full_y1_data.append(self.total_y1 / avg_count)
                    self.full_y2_data.append(self.total_y2 / avg_count)

                self.total_y1 = 0.0
                self.total_y2 = 0.0
                self.data_counter = 0

                self.update_plot()

        except Exception as e:
            self.logger(Logger.ERROR, f"Plotting error: {e}\n{traceback.format_exc()}")
