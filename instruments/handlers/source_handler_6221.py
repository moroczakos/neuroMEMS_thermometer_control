import time

from instruments.handlers.source_handler import SourceHandler
from instruments.mock_Keithley6221 import MockKeithley6221


class SourceHandler6221(SourceHandler):
    def _get_mock(self):
        return MockKeithley6221()

    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK_6221":
            self.instrument = self._get_mock()
            #time.sleep(11)
        else:
            self.instrument = resource_manager.open_resource(self.address)
        self.reset()
        return self.instrument

    def reset(self):
        instr = self.instrument
        instr.write("*RST")  # Restore 622x defaults.
        instr.write("SOUR:CURR:RANG:AUTO ON")  # Select auto source range.
        instr.write("SOUR:CURR:COMP 10")  # Set compliance to 10V.
        instr.write("OUTP ON")

    def measure(self):
        # No measurement
        return {"current": self.current}

    def close(self):
        if self.instrument:
            try:
                self.instrument.write("OUTP OFF")
            except:
                pass
        super().close()

    def set_current(self, value):
        super().set_current(value)
        self.instrument.write(f":SOUR:CURR {value}")

    def set_current_range(self, value):
        pass

    def set_voltage_limit(self, value):
        self.instrument.write(f":SOUR:CURR:COMP {value}")
