# ─── Standard Library ────────────────────────────────────────────────────────
import queue
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Event

# ─── Local Modules ───────────────────────────────────────────────────────────
from utils.csv_data_logger import CSVDataLogger
from utils.constants import Keys, Logger, UI


class CurrentCycleModel:
    def __init__(self, instrument_manager, setting_manager, profile, output_file_path):
        self.name = "current_cycle_model"

        # Settings
        self.setting_manager = setting_manager
        self.output_file_path = output_file_path
        self.cycles = None
        self.interval = None
        self.average_count = None
        self.cycle_sequence = None

        # Define measurement profile
        self.profile = profile

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
        self.stop_event = Event()
        self.observers = []
        self.csv_data_logger = CSVDataLogger(self._notify_logger)

        self.csv_data_logger.set_max_queue_size(self.setting_manager.load_setting(UI.MAX_QUEUE_SIZE))

    def attach(self, observer):
        self.observers.append(observer)

    def _notify_observers_about_update(self):
        for observer in self.observers:
            observer.update(self.running, self.timestamp, self.current, self.voltage, self.resistance)

    def _notify_observers_about_running(self):
        for observer in self.observers:
            if hasattr(observer, 'is_running'):
                observer.is_running(self.name, self.running)

    def _notify_logger(self, message_type, message):
        for observer in self.observers:
            observer.log(message_type, message)

    def load_settings(self):
        self.cycles = self.setting_manager.load_setting(Keys.CYCLES)
        self.interval = self.setting_manager.load_setting(Keys.INTERVAL)
        self.average_count = self.setting_manager.load_setting(Keys.AVG_COUNT)
        self.cycle_sequence = self.setting_manager.load_setting(Keys.CYCLE_SEQUENCE)

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
        self._notify_observers_about_running()
        self.start_time = time.time()
        self.stop_event = Event()

        self.executor = ThreadPoolExecutor(max_workers = 4)
        self.executor.submit(self._cycle_sequence_loop)
        self.executor.submit(self._measure_loop)

        start_time = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.csv_data_logger.reset()
        self.csv_data_logger.set_file_name(
            f"log_{self.profile.name.replace('/', '_')}_{start_time}.csv")
        self.csv_data_logger.set_file_directory(self.output_file_path)
        self.csv_data_logger.set_first_row(self.profile.headers)
        self.csv_data_logger.start()

        self._notify_logger(Logger.INFO, "Started measurement.")

    def stop_data_collection(self):
        if self.running:
            self.running = False
            self._notify_observers_about_update()
            self._notify_observers_about_running()
            self.stop_event.set()

            if self.executor:
                self.executor.shutdown(wait = False)

            if self.instrument_manager.get_instrument(self.instrument_alias):
                self.instrument_manager.disconnect(self.instrument_alias)

            self._notify_logger(Logger.INFO, "Measurement stopped.")
            self.csv_data_logger.stop()

    def _cycle_sequence_loop(self):
        try:
            source_handler = self.instrument_manager.get_handler(self.instrument_alias)
            start_time = time.time()

            self._notify_logger(Logger.INFO, "Starting offset")
            offset = self.cycle_sequence.pop(0)
            if not self._wait_and_set_current(source_handler, offset, start_time):
                return  # Stop event triggered during offset wait

            for cycle_index in range(self.cycles):
                if self.stop_event.is_set():
                    break

                self._notify_logger(Logger.INFO, f"Starting cycle {cycle_index + 1}/{self.cycles}")
                if not self._handle_cycle(source_handler, start_time, offset["duration"], cycle_index):
                    break  # Stop event triggered during cycle

            # Wait for the duration of the last step if no stop was triggered
            if not self.stop_event.is_set() and self.cycle_sequence:
                last_duration = self.cycle_sequence[-1]["duration"]
                if self.stop_event.wait(last_duration):
                    return

        except Exception as e:
            self._notify_logger(Logger.ERROR, f"Cycle sequence error {e}\n{traceback.format_exc()}")

        if self.running:
            self.stop_data_collection()

    def _wait_and_set_current(self, source_handler, step, start_time):
        scheduled_time = start_time + step["duration"]

        if not self._wait_until(scheduled_time):
            return False

        self._set_current(source_handler, step["current"], step["duration"])

        return True

    def _handle_cycle(self, source_handler, start_time, offset_duration, cycle_index):
        total_cycle_duration = sum(step["duration"] for step in self.cycle_sequence)

        for step_index, step in enumerate(self.cycle_sequence):
            if self.stop_event.is_set():
                break

            scheduled_time = (
                    start_time +
                    offset_duration +
                    sum(s["duration"] for s in self.cycle_sequence[:step_index]) +
                    cycle_index * total_cycle_duration
            )

            if not self._wait_until(scheduled_time):
                return False

            self._set_current(source_handler, step["current"], step["duration"])

        return True

    def _wait_until(self, scheduled_time):
        wait_time = scheduled_time - time.time()
        if wait_time > 0:
            return not self.stop_event.wait(wait_time)
        return True

    def _set_current(self, source_handler, current, duration):
        self._notify_logger(Logger.INFO, f"Setting current to {current} A for {duration} s")
        source_handler.set_current(current)

    def _measure_loop(self):
        while self.running:
            try:
                self.timestamp, self.current, self.voltage, resistance = self._perform_measurement()
                self._notify_observers_about_update()

                self.csv_data_logger.enqueue(
                    (self.timestamp,
                     self.current,
                     self.voltage if self.voltage is not None else float('nan'),
                     resistance if resistance is not None else float('nan')))

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
