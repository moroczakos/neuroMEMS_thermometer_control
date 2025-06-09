# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import traceback

# ─── Local Modules ───────────────────────────────────────────────────────────
from concurrent.futures import ThreadPoolExecutor
from utils.file_utils import CsvLogger
from utils.constants import Logger, Other


class CSVDataLogger:
    def __init__(self, logger):
        self.data_queue = None
        self.filename = None
        self.file_directory = None
        self.first_row = None
        self.data = []
        self.running = False
        self.logger = logger
        self.csv_logger = CsvLogger()
        self.executor = None

        self.reset()

    def set_file_name(self, file_name):
        self.filename = file_name

    def set_file_directory(self, directory):
        self.file_directory = directory

    def set_first_row(self, first_row):
        self.first_row = first_row

    def reset(self):
        self.data_queue = queue.Queue()
        self.data = []
        self.running = False

    def start(self):
        self.running = True

        self.csv_logger.set_file_name(self.filename)
        self.csv_logger.set_file_directory(self.file_directory)
        self.csv_logger.set_first_row(self.first_row)
        self.csv_logger.create()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        self.executor.submit(self._worker_loop)

    def stop(self):
        self.running = False
        if self.executor:
            self.executor.shutdown(wait = False)

        self.logger(Logger.INFO, f"Data saved to {self.csv_logger.get_full_filename()}")

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
