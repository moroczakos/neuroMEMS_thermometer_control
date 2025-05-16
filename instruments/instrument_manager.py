import pyvisa
from tkinter import messagebox
from instruments.handlers.dmm_handler import DMMHandler
from instruments.handlers.source_handler import SourceHandler6221, SourceHandler2635


class InstrumentManager:
    handler_registry = {
        "dmm": DMMHandler,
        "source_6221": SourceHandler6221,
        "source_2635": SourceHandler2635
    }

    def __init__(self, allow_mock=True):
        self.rm = pyvisa.ResourceManager()
        self.allow_mock = allow_mock
        self.handlers = {}

    def list_resources(self, only_tcpip=False):
        try:
            resources = self.rm.list_resources()
            if only_tcpip:
                resources = [r for r in resources if r.startswith("TCPIP")]
            return resources
        except Exception as e:
            messagebox.showerror("VISA Error", f"Could not list VISA resources:\n{e}")
            return []

    def get_instrument_model(self, resource):
        try:
            instrument = self.rm.open_resource(resource)
            idn = instrument.query("*IDN?")
            self.rm.close()
            manufacturer, model, serial, firmware = idn.split(',')
            return model
        except Exception as e:
            messagebox.showerror("Model number error", f"Could not check the model number of the instrument:\n{e}")
            return None

    def connect(self, alias, address, role):
        if role not in self.handler_registry:
            raise ValueError(f"Unsupported role: {role}")

        try:
            handler_cls = self.handler_registry[role]
            handler = handler_cls(address, use_mock = ("MOCK" in address))
            instr = handler.connect(self.rm)
            self.handlers[alias] = handler
            return instr
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect {alias} ({role}) at {address}:\n{e}")
            return None

    def get_instrument(self, alias):
        handler = self.handlers.get(alias)
        return handler.instrument if handler else None

    def get_handler(self, alias):
        handler = self.handlers.get(alias)
        return handler if handler else None

    def get_error(self, alias):
        instr = self.get_instrument(alias)
        if not instr:
            return "No instrument found."

        try:
            handler = self.handlers.get(alias)
            return handler.get_error()
        except:
            return "Could not query error."

    def disconnect(self, alias):
        handler = self.handlers.get(alias)
        if handler:
            handler.close()
            del self.handlers[alias]

    def disconnect_all(self):
        for alias in list(self.handlers.keys()):
            self.disconnect(alias)

    @classmethod
    def register_handler(cls, role, handler_cls):
        cls.handler_registry[role] = handler_cls
