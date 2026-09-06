# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ─── Local Modules ───────────────────────────────────────────────────────────
from utils.csv_data_logger import CSVDataLogger
from utils.constants import Keys, Logger, UI


class ThermometerModel:
    def __init__(self, instrument_manager, setting_manager, profile, input_file_path, output_file_path, current_source_app = None, current_source = None):
        self.name = "thermometer_model"

        # Settings
        self.setting_manager = setting_manager
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.R0 = None
        self.TCR = None
        self.interval = None
        self.average_count = None
        self.probe_name = None

        # Define measurement profile
        self.profile = profile
        self.c_app = current_source_app
        self.c_source = current_source

        # Instrument
        self.instrument_manager = instrument_manager
        self.instrument_alias = "dmm4wire"

        # Data
        self.start_time = None
        self.timestamp = None
        self.resistance = None
        self.temperature = None
        self.data_queue = queue.Queue()
        self.executor = None

        self.running = False
        self.preview_running = False
        self.observers = []
        self.csv_data_logger = CSVDataLogger(self._notify_logger)
        self.csv_raw_data_logger = CSVDataLogger(self._notify_logger)

        self.csv_data_logger.set_max_queue_size(self.setting_manager.load_setting(UI.MAX_QUEUE_SIZE))
        self.csv_raw_data_logger.set_max_queue_size(self.setting_manager.load_setting(UI.MAX_QUEUE_SIZE))

    def set_R0_TCR(self, data):
        self.R0 = data[0]
        self.TCR = data[1]

    def set_probe_name(self, probe_name):
        self.probe_name = probe_name

    def set_instrument_alias(self, alias):
        self.instrument_alias = alias

    def attach(self, observer):
        self.observers.append(observer)

    def _notify_observers_about_update(self):
        for observer in self.observers:
            observer.update(self.running, self.preview_running, self.timestamp, self.resistance, self.temperature)

    def _notify_observers_about_running(self):
        for observer in self.observers:
            if hasattr(observer, 'is_running'):
                observer.is_running(self.name, self.running or self.preview_running)

    def _notify_logger(self, message_type, message):
        for observer in self.observers:
            observer.log(message_type, message)

    def load_settings(self):
        self.interval = self.setting_manager.load_setting(Keys.INTERVAL)
        self.average_count = self.setting_manager.load_setting(Keys.AVG_COUNT)

    def connect_instrument(self, visa_address):
        self.instrument_manager.connect(self.instrument_alias, visa_address, role = self.instrument_alias)
        return True

    def start_data_preview(self):
        self.preview_running = True
        self._notify_observers_about_running()
        self.start_time = time.time()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        self.executor.submit(self._preview_loop)

        self._notify_logger(Logger.INFO, "Started preview.")

    def stop_data_preview(self):
        if self.preview_running:
            self.preview_running = False
            self._notify_observers_about_update()
            self._notify_observers_about_running()

            if self.executor:
                self.executor.shutdown(wait = False)

            if self.instrument_manager.get_instrument(self.instrument_alias):
                self.instrument_manager.disconnect(self.instrument_alias)

            self._notify_logger(Logger.INFO, "Preview stopped.")

    def start_data_collection(self):
        self.running = True
        self._notify_observers_about_running()
        self.start_time = time.time()

        # Initialize current source if the instrument alias is "dmm2wire" as in case of 2-wire measurement the
        # dmm measures resistance with a known input current provided by the mock current source (dmm measures voltage
        # and calculates resistance using Ohm's law). In 4-wire measurement, the dmm measures resistance directly
        # without needing a current source.
        self.c_source = None
        if self.instrument_alias == "dmm2wire":
            self.c_source = CurrentSourceMock(self.setting_manager)
            #self.c_app.controller.set_current_and_start(0.001)

        self.executor = ThreadPoolExecutor(max_workers = 4)
        self.executor.submit(self._measure_loop)

        start_time = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.csv_data_logger.reset()
        self.csv_data_logger.set_file_name(
            f"log_{self.profile.name.replace('/', '_')}_{self.probe_name}_{start_time}.csv")
        self.csv_data_logger.set_file_directory(self.output_file_path)
        self.csv_data_logger.set_first_row(self.profile.headers)
        self.csv_data_logger.start()

        self.csv_raw_data_logger.reset()
        self.csv_raw_data_logger.set_file_name(
            f"log_Resistance_{start_time}.csv")
        self.csv_raw_data_logger.set_file_directory(self.output_file_path)
        self.csv_raw_data_logger.set_first_row(self.profile.headers[0:2])
        self.csv_raw_data_logger.start()

        self._notify_logger(Logger.INFO, "Started measurement.")

    def stop_data_collection(self):
        if self.running:
            self.running = False
            self._notify_observers_about_update()
            self._notify_observers_about_running()

            if self.executor:
                self.executor.shutdown(wait = False)

            if self.instrument_manager.get_instrument(self.instrument_alias):
                self.instrument_manager.disconnect(self.instrument_alias)

            self._notify_logger(Logger.INFO, "Measurement stopped.")
            self.csv_data_logger.stop()
            self.csv_raw_data_logger.stop()

            #if self.instrument_alias == "dmm2wire":
            #    self.c_app.controller.stop_current()

    def _preview_loop(self):
        while self.preview_running:
            try:
                self.timestamp, self.resistance, self.temperature = self._perform_measurement()
                self._notify_observers_about_update()

                time.sleep(self.interval)
            except Exception as e:
                self.running = False
                self._notify_observers_about_running()
                self._notify_logger(Logger.ERROR, f"Preview error: {e}\n {traceback.format_exc()}")

                error = self.instrument_manager.get_error(self.instrument_alias)
                if error:
                    self._notify_logger(Logger.ERROR, error)
                break

    def _measure_loop(self):
        while self.running:
            try:
                self.timestamp, self.resistance, self.temperature = self._perform_measurement()
                self._notify_observers_about_update()

                self.csv_data_logger.enqueue(
                    (self.timestamp,
                     self.resistance if self.resistance is not None else float('nan'),
                     self.temperature if self.temperature is not None else float('nan')))

                self.csv_raw_data_logger.enqueue(
                    (self.timestamp,
                     self.resistance if self.resistance is not None else float('nan')))

                time.sleep(self.interval)
            except Exception as e:
                self.running = False
                self._notify_observers_about_running()
                self._notify_logger(Logger.ERROR, f"Measurement error: {e}\n {traceback.format_exc()}")

                error = self.instrument_manager.get_error(self.instrument_alias)
                if error:
                    self._notify_logger(Logger.ERROR, error)
                break

    def _perform_measurement(self):
        dmm_handler = self.instrument_manager.get_handler(self.instrument_alias)
        timestamp = time.time() - self.start_time
        meas_dict = self.profile.measure_func(dmm_handler, self.c_source)
        resistance = meas_dict["resistance"]
        temperature = self.profile.post_process_func(resistance, self.R0,
                                                     self.TCR) if self.profile.post_process_func else None

        return timestamp, resistance, temperature


class CurrentSourceMock:
    def __init__(self, setting_manager):
        self.cycles = setting_manager.load_setting(Keys.CYCLES)
        self.cycle_sequence = setting_manager.load_setting(Keys.CYCLE_SEQUENCE)
        self.offset = self.cycle_sequence.pop(0)
        self.start_time = None

    def get_schedule(self):
        schedule = [{"end_time_step": self.offset["duration"], "current": self.offset["current"]}]

        for i in range(0, self.cycles):
            for step_index, step in enumerate(self.cycle_sequence):
                last_end_time = schedule[-1]["end_time_step"]
                schedule.append({"end_time_step": last_end_time + step["duration"], "current": step["current"]})

        return schedule

    def set_start_time(self, start_time):
        self.start_time = start_time

    def measure(self):
        if self.start_time is None:
            self.start_time = time.time()

        elapsed_time = time.time() - self.start_time
        schedule = self.get_schedule()

        for step in schedule:
            if elapsed_time <= step["end_time_step"]:
                return step["current"]

        return 1.0
