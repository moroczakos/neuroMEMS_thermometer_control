import random
import time


class MockKeithley2100:
    def __init__(self):
        self.buffer = []
        self.query_delay = 0.05  # seconds

    def write(self, command):
        # Just record commands for debugging, optional
        pass

    def query(self, command):
        time.sleep(self.query_delay)
        if "FETCH?" in command:
            resistance = random.uniform(320, 430)  # Simulated range
            return f"{resistance:.6f}"
        elif "SYST:ERR?" in command:
            return "No error"
        return "Not known command"

    def close(self):
        pass
