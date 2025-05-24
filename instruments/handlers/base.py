from abc import ABC, abstractmethod


class InstrumentHandler(ABC):
    def __init__(self, address, use_mock=False):
        self.address = address
        self.use_mock = use_mock
        self.instrument = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @abstractmethod
    def connect(self, resource_manager):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def measure(self):
        pass

    @abstractmethod
    def get_error(self):
        pass

    def close(self):
        if self.instrument:
            try:
                self.instrument.close()
            except Exception:
                pass
