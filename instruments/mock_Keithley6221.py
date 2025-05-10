import re
import time


class MockKeithley6211:
    def __init__(self):
        self.buffer = []
        self.query_delay = 0.05  # seconds
        self.current = None

    def write(self, command):
        # Just record commands for debugging, optional
        if "SOUR:CURR" in command:
            match = re.search(r"[-+]?\d*\.\d+|\d+", command)
            if match:
                self.current = match.group(0)

    def query(self, command):
        time.sleep(self.query_delay)

        if ":SOUR:CURR?" in command:
            return self.current
        elif ":MEAS:VOLT?" in command:
            return f"{1:.6f}"
        elif "SYST:ERR?" in command:
            return "No error"
        return "Not known command"

    def close(self):
        pass
