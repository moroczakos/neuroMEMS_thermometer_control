class InstrumentHandler:
    def __init__(self, address, use_mock=False):
        self.address = address
        self.use_mock = use_mock
        self.instrument = None

    def connect(self, resource_manager):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def measure(self):
        raise NotImplementedError

    def close(self):
        if self.instrument:
            try:
                self.instrument.close()
            except Exception:
                pass
