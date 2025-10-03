from instruments.handlers.source_handler import SourceHandler
from instruments.mock_Keithley2611 import MockKeithley2611


class SourceHandler2611(SourceHandler):
    def _get_mock(self):
        return MockKeithley2611()

    def connect(self, resource_manager):
        if self.use_mock or self.address == "MOCK_2611":
            self.instrument = self._get_mock()
            # time.sleep(11)
        else:
            self.instrument = resource_manager.open_resource(self.address)
        self.reset()
        return self.instrument

    def reset(self):
        instr = self.instrument
        instr.write("smua.reset() ")  # Restore Series 2600B defaults.
        instr.write("smua.source.func = smua.OUTPUT_DCAMPS")  # Select current source function.
        instr.write("smua.source.rangei = 0.6")  # Set source range to 0.6 A.
        instr.write("smua.source.leveli = 0")  # Set current source to 0 A.
        instr.write("smua.source.limitv = 10")  # Set voltage limit to 10 V.
        instr.write("smua.sense = smua.SENSE_REMOTE")  # Enable 4-wire ohms.
        instr.write("smua.measure.autorangev = smua.AUTORANGE_ON")  # Set voltage range to auto.
        instr.write("smua.source.output = smua.OUTPUT_ON")  # Turn on output.

    def measure(self):
        instr = self.instrument
        # current = float(instr.query("print(smua.measure.i())"))
        # voltage = float(instr.query("print(smua.measure.v())"))
        # resistance = float(instr.query("print(smua.measure.r())"))

        iv = instr.query("print(smua.measure.iv())").strip()
        current, voltage = map(float, iv.split('\t'))
        resistance = float(voltage) / float(current) if float(current) != 0 else float('inf')

        return {"current": current, "voltage": voltage, "resistance": resistance}

    def close(self):
        if self.instrument:
            try:
                self.instrument.write("smua.source.output = smua.OUTPUT_OFF")
            except:
                pass
        super().close()

    def set_current(self, value):
        super().set_current(value)
        self.instrument.write(f"smua.source.leveli = {value}")

    def set_current_range(self, value):
        self.instrument.write(f"smua.source.rangei = {value}")

    def set_voltage_limit(self, value):
        self.instrument.write(f"smua.source.limitv = {value}")

    def set_digital_io_high(self):
        self.instrument.write(f"digio.writebit(1, 1)")

    def set_digital_io_low(self):
        self.instrument.write(f"digio.writebit(1, 0)")
