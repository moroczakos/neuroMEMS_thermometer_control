import time
from instruments.handlers.base import InstrumentHandler
from instruments.mock_Keithley2100 import MockKeithley2100


class DMMHandler(InstrumentHandler):
    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK":
            self.instrument = MockKeithley2100()
            # time.sleep(11)
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
        resistance = float(instr.query("FETCH?").strip())

        return {"resistance": resistance}

    def get_error(self):
        instr = self.instrument
        error = instr.query("SYST:ERR?").strip()
        if error.startswith("+0") or "No error" in error:
            return None

        return error
