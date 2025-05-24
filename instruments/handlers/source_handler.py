from abc import ABC, abstractmethod
from instruments.handlers.base import InstrumentHandler


class SourceHandler(InstrumentHandler, ABC):
    def __init__(self, address, use_mock=False):
        super().__init__(address, use_mock)
        self.current = 0.0

    @abstractmethod
    def set_current(self, value):
        self.current = value

    @abstractmethod
    def set_current_range(self, value):
        pass

    @abstractmethod
    def set_voltage_limit(self, value):
        pass

    @abstractmethod
    def measure(self):
        pass

    def get_error(self):
        instr = self.instrument
        error = instr.query("SYST:ERR?").strip()
        return None if error.startswith("+0") or "No error" in error else error
