# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import traceback

# ─── Local Modules ───────────────────────────────────────────────────────────
from concurrent.futures import ThreadPoolExecutor
from utils.file_utils import CsvLogger
from utils.constants import Logger, Other


class CSVDataLogger:
    def __init__(self, output_file_path, profile, logger):
        self.data_queue = None
        self.output_file_path = output_file_path
        self.profile = profile
        self.data = []
        self.running = False
        self.logger = logger
        self.csv_logger = CsvLogger()

        self.executor = None

        self.reset()

    def reset(self):
        self.data_queue = queue.Queue()
        self.data = []
        self.running = False

    def start(self):
        self.running = True
        self.csv_logger.create(f"log_{self.profile.name.replace('/', '_')}", self.profile.headers,
                               self.output_file_path)

        self.executor = ThreadPoolExecutor(max_workers = 4)
        self.executor.submit(self._worker_loop)

    def stop(self):
        self.running = False
        if self.executor:
            self.executor.shutdown(wait = False)

        self.logger(Logger.INFO, f"Data saved to {self.csv_logger.get_filename()}")

    def enqueue(self, data):
        self.data_queue.put(data)

    def _worker_loop(self):
        while self.running or not self.data_queue.empty():
            try:
                data = self.data_queue.get(timeout = 0.5)
                self._accumulate_and_write_csv_log(data)
            except queue.Empty:
                continue

    def _accumulate_and_write_csv_log(self, data):
        try:
            if self.data_queue.qsize() > Other.MAX_QUEUE_SIZE:
                self.logger(Logger.WARNING, "Queue backlog detected during measurement logging!")

            self.csv_logger.write_row(list(data))
        except Exception as e:
            self.logger(Logger.ERROR, f"CSV file writing error: {e}\n{traceback.format_exc()}")
