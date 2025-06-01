# ─── Standard Library ────────────────────────────────────────────────────────
import os
import queue
import threading
import time
import traceback

# ─── Local Modules ───────────────────────────────────────────────────────────
from concurrent.futures import ThreadPoolExecutor
from utils.constants import Keys, Logger, Other
from utils.file_utils import CsvLogger


class MeasurementModel:
    def __init__(self, instrument_manager, setting_manager, profile, input_file_path, output_file_path):
        # Settings
        self.setting_manager = setting_manager
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.start_low = True  # Square wave current starts with low value
        self.current_high = None
        self.current_low = None
        self.duration_high = None
        self.duration_low = None
        self.cycles = None
        self.interval = None
        self.average_count = None

        # Define measurement profile
        self.profile = profile

        # Logger
        self.csv_logger = CsvLogger()

        # Instrument
        self.instrument_manager = instrument_manager
        self.instrument_alias = None

        # Data
        self.start_time = None
        self.timestamp = None
        self.current = None
        self.voltage = None
        self.resistance = None
        self.data_queue = queue.Queue()
        self.executor = None

        self.running = False
        self.observers = []

    def set_start_low(self, start_low):
        self.start_low = start_low

    def attach(self, observer):
        self.observers.append(observer)

    def notify_observers(self):
        for observer in self.observers:
            observer.update(self.running, self.timestamp, self.current, self.voltage, self.resistance)

    def notify_logger(self, message_type, message):
        for observer in self.observers:
            observer.log(message_type, message)

    def load_settings(self):
        self.current_high = self.setting_manager.load_setting(Keys.CURRENT_HIGH)
        self.current_low = self.setting_manager.load_setting(Keys.CURRENT_LOW)
        self.duration_high = self.setting_manager.load_setting(Keys.DURATION_HIGH)
        self.duration_low = self.setting_manager.load_setting(Keys.DURATION_LOW)
        self.cycles = self.setting_manager.load_setting(Keys.CYCLES)
        self.interval = self.setting_manager.load_setting(Keys.INTERVAL)
        self.average_count = self.setting_manager.load_setting(Keys.AVG_COUNT)

    def connect_instrument(self, visa_address):
        if "6221" in visa_address:
            model = "6221"
        elif "2611" in visa_address:
            model = "2611"
        else:
            model = self.instrument_manager.get_instrument_model(visa_address)

        if "6221" in model:
            self.instrument_alias = "source_6221"
        elif "2611" in model:
            self.instrument_alias = "source_2611"
        else:
            raise ValueError(f"Unknown model: {model}. Expected 6221 or 2611.")

        self.instrument_manager.connect(self.instrument_alias, visa_address, role = self.instrument_alias)

        return True

    def configure_device(self):
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)
        settings_dict = self.setting_manager.load_setting("device_settings")

        current_range = settings_dict.get(Keys.CURRENT_RANGE_KEY)
        voltage_limit = settings_dict.get(Keys.VOLTAGE_LIMIT_KEY)

        if current_range:
            source_handler.set_current_range(current_range)
        if voltage_limit:
            source_handler.set_voltage_limit(voltage_limit)

    def start_data_collection(self):
        self.running = True

        self.csv_logger.create(f"log_{self.profile.name.replace('/', '_')}", self.profile.headers,
                               self.output_file_path)

        self.start_time = time.time()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        threading.Thread(target = self.cycle_loop, daemon = True).start()
        threading.Thread(target = self.data_worker_loop, daemon = True).start()
        self.notify_logger(Logger.INFO, "Started measurement.")

    def stop_data_collection(self):
        if self.running:
            self.running = False
            self.notify_observers()

            if self.executor:
                self.executor.shutdown(wait = False)

            if self.instrument_manager.get_instrument(self.instrument_alias):
                self.instrument_manager.disconnect(self.instrument_alias)

            self.notify_logger(Logger.INFO, "Measurement stopped.")

            if hasattr(self, 'csv_logger'):
                self.notify_logger(Logger.INFO, f"Data saved to {self.csv_logger.get_filename()}")
                self.csv_logger.close()

    def cycle_loop(self):
        threading.Thread(target = self.measure_loop, daemon = True).start()
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)

        try:
            first_current, second_current = (
                self.current_low, self.current_high) if self.start_low else (
                self.current_high, self.current_low)
            first_duration, second_duration = (
                self.duration_low, self.duration_high) if self.start_low else (
                self.duration_high, self.duration_low)

            for cycle in range(self.cycles):
                if not self.running: break
                self.notify_logger(Logger.INFO, f"Cycle {cycle + 1}/{self.cycles}: Setting current to {first_current}A")
                source_handler.set_current(first_current)
                time.sleep(first_duration)

                if not self.running: break
                self.notify_logger(Logger.INFO,
                                   f"Cycle {cycle + 1}/{self.cycles}: Setting current to {second_current}A")
                source_handler.set_current(second_current)
                time.sleep(second_duration)
        except Exception as e:
            self.notify_logger(Logger.ERROR, f"Cycle Error {e}\n {traceback.format_exc()}")

        if self.running:
            self.stop_data_collection()

    def measure_loop(self):
        while self.running:
            try:
                self.timestamp, self.current, self.voltage, resistance = self.perform_measurement()
                self.notify_observers()

                self.data_queue.put(
                    (self.timestamp,
                     self.current,
                     self.voltage if self.voltage is not None else float('nan'),
                     resistance if resistance is not None else float('nan')))

                time.sleep(self.interval)
            except Exception as e:
                self.running = False
                self.notify_logger(Logger.ERROR, f"Measurement error: {e}\n {traceback.format_exc()}")

                error = self.instrument_manager.get_error(self.instrument_alias)
                if error:
                    self.notify_logger(Logger.ERROR, error)
                break

    def perform_measurement(self):
        source_handler = self.instrument_manager.get_handler(self.instrument_alias)
        timestamp = time.time() - self.start_time
        meas_dict = self.profile.measure_func(source_handler)
        current = meas_dict["current"]
        if "voltage" in meas_dict:
            voltage = meas_dict["voltage"]
        else:
            voltage = None
        if "resistance" in meas_dict:
            resistance = meas_dict["resistance"]
        else:
            resistance = self.profile.post_process_func(current, voltage) if self.profile.post_process_func else None

        return timestamp, current, voltage, resistance

    def data_worker_loop(self):
        while self.running or not self.data_queue.empty():
            try:
                if self.data_queue.qsize() + 2 > Other.MAX_QUEUE_SIZE:
                    self.notify_logger(Logger.WARNING, "Queue backlog detected during measurement logging!")
                timestamp, current, voltage, resistance = self.data_queue.get(timeout = 0.5)
                if self.running:
                    self.executor.submit(self.safe_log, timestamp, current, voltage, resistance)
            except queue.Empty:
                continue

    def safe_log(self, timestamp, current, voltage, resistance):
        try:
            self.csv_logger.write_row([timestamp, current, voltage, resistance])
        except Exception as e:
            self.notify_logger(Logger.ERROR, f"Logging error: {e}\n {traceback.format_exc()}")
