from instruments.handlers.base import InstrumentHandler
from instruments.mock_Keithley6221 import MockKeithley6221
from instruments.mock_Keithley2635 import MockKeithley2635


class SourceHandler6221(InstrumentHandler):
    def __init__(self, address, use_mock=False):
        super().__init__(address, use_mock)
        self.current = 0.0

    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK_6221":
            self.instrument = MockKeithley6221()
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
        return self.current, None

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
        self.current = value
        self.instrument.write(f":SOUR:CURR {value}")


class SourceHandler2635(InstrumentHandler):
    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK_2635":
            self.instrument = MockKeithley2635()
        else:
            self.instrument = resource_manager.open_resource(self.address)
        self.reset()
        return self.instrument

    def reset(self):
        instr = self.instrument
        instr.write("smua.reset() ")  # Restore Series 2600B defaults.
        instr.write("smua.source.func = smua.OUTPUT_DCAMPS")  # Select current source function.
        instr.write("smua.source.rangei = 10e-3")  # Set source range to 10 mA.
        instr.write("smua.source.leveli = 0")  # Set current source to 0 A.
        instr.write("smua.source.limitv = 10")  # Set voltage limit to 10 V.
        instr.write("smua.sense = smua.SENSE_REMOTE")  # Enable 4-wire ohms.
        instr.write("smua.measure.autorangev = smua.AUTORANGE_ON")  # Set voltage range to auto.
        instr.write("smua.source.output = smua.OUTPUT_ON")  # Turn on output.

    def measure(self):
        instr = self.instrument
        current = float(instr.query("smua.measure.i()"))
        voltage = float(instr.query("smua.measure.v()"))
        resistance = float(instr.query("smua.measure.r()"))

        return current, voltage#, resistance

    def close(self):
        if self.instrument:
            try:
                self.instrument.write("smua.source.output = smua.OUTPUT_OFF")
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
        self.instrument.write(f":smua.source.rangei = {value}")
        self.instrument.write(f":smua.source.leveli = {value}")
