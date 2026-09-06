from instruments.handlers.dmm_handler import DMMHandler


class DMMHandler4Wire(DMMHandler):
    def reset(self):
        instr = self.instrument
        instr.write("*RST")
        instr.write("CONF:FRES 1000")
        instr.write("SENS:FRES:NPLC 1")
