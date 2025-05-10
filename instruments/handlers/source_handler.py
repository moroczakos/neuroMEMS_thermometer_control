from instruments.handlers.base import InstrumentHandler
from instruments.mock_Keithley6221 import MockKeithley6211


class SourceHandler(InstrumentHandler):
    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK":
            self.instrument = MockKeithley6211()
        else:
            self.instrument = resource_manager.open_resource(self.address)
        self.reset()
        return self.instrument

    def reset(self):
        instr = self.instrument
        instr.write("*RST")
        instr.write("SOUR:FUNC CURR")
        instr.write("SOUR:CURR:RANG:AUTO ON")
        instr.write("SOUR:CURR:MODE FIXED")
        instr.write("OUTP ON")

    def measure(self):
        instr = self.instrument
        current = float(instr.query(":SOUR:CURR?"))
        voltage = float(instr.query(":MEAS:VOLT?"))

        return voltage, current

    def close(self):
        if self.instrument:
            try:
                self.instrument.write("OUTP OFF")
            except:
                pass
        super().close()

    def get_error(self):
        instr = self.instrument
        error = instr.query("SYST:ERR?").strip()
        if error.startswith("+0") or "No error" in error:
            return None

        return error

    def set_current(self, value):
        self.instrument.write(f":SOUR:CURR {value}")
