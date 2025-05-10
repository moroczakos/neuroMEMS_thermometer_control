from instruments.handlers.base import InstrumentHandler



# from mock_Keithley2100 import MockKeithley2100


class SourceHandler(InstrumentHandler):
    def connect(self, resource_manager):
        # if self.use_mock or self.address == "MOCK":
        # self.instrument = MockKeithley2100()
        # else:
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
