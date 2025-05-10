from instruments.handlers.base import InstrumentHandler
from mock_Keithley2100 import MockKeithley2100


class DMMHandler(InstrumentHandler):
    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK":
            self.instrument = MockKeithley2100()
        else:
            self.instrument = resource_manager.open_resource(self.address)
        self.reset()
        return self.instrument

    def reset(self):
        instr = self.instrument
        instr.write("*RST")
        instr.write("CONF:FRES 1000")
        instr.write("SENS:FRES:NPLC 1")

    def measure(self):
        instr = self.instrument
        instr.write("INIT")

        return float(instr.query("FETCH?").strip())
