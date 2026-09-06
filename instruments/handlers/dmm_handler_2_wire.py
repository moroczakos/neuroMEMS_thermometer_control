from instruments.handlers.dmm_handler import DMMHandler


class DMMHandler2Wire(DMMHandler):
    def reset(self):
        instr = self.instrument
        instr.write("*RST")
        instr.write("CONF:VOLT:DC 10")
        instr.write("SENS:VOLT:NPLC 1")

