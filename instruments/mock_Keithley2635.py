import re
import time


class MockKeithley2635:
    def __init__(self):
        self.buffer = []
        self.query_delay = 0.05  # seconds
        self.current = None

    def write(self, command):
        # Just record commands for debugging, optional
        if "smua.source.leveli =" in command:
            match = re.search(r"[-+]?\d*\.\d+|\d+", command)
            if match:
                self.current = match.group(0)

    def query(self, command):
        time.sleep(self.query_delay)
        if "smua.measure.i()" in command:
            return self.current
        if "smua.measure.v()" in command:
            return 1.0
        if "smua.measure.r()" in command:
            return 1.0
        if "*IDN?" in command:
            return "Keithley Instruments Inc., 2635, 123456, 1.2.3"
        elif "SYST:ERR?" in command:
            return "No error"
        return "Not known command"

    def close(self):
        pass
