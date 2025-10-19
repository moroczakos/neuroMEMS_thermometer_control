import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from instruments.instrument_manager import InstrumentManager


class RMMock:
    def __init__(self, resources = None, idn = None, open_error = None, list_error = None):
        self._resources = resources or []
        self._idn = idn or "MAN,MODEL,SN,FW"
        self._open_error = open_error
        self._list_error = list_error

    def list_resources(self):
        if self._list_error:
            raise self._list_error
        return tuple(self._resources)

    def open_resource(self, resource):
        if self._open_error:
            raise self._open_error
        return SimpleNamespace(query = lambda q: self._idn)


class HandlerMock:
    def __init__(self, address, use_mock = False):
        self.address = address
        self.use_mock = use_mock
        self.closed = False
        self.instrument = None

    def connect(self, rm):
        # simulate storing an instrument object
        self.instrument = f"INST:{self.address}"
        return self.instrument

    def get_error(self):
        return "0,No error"

    def close(self):
        self.closed = True


class TestInstrumentManager:
    def test_list_resources_filters_tcpip_and_returns_all(self, monkeypatch):
        # Arrange
        rm_mock = RMMock(resources = ["TCPIP::1", "GPIB::2"])
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        mgr = InstrumentManager()

        # Act & Assert
        assert list(mgr.list_resources()) == ["TCPIP::1", "GPIB::2"]
        assert mgr.list_resources(only_tcpip = True) == ["TCPIP::1"]

    def test_list_resources_on_error_shows_message_and_returns_empty(self, monkeypatch):
        # Arrange
        rm_mock = RMMock(list_error = RuntimeError("boom"))
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        showerr = Mock()
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", showerr)

        mgr = InstrumentManager()

        # Act
        res = mgr.list_resources()

        # Assert
        showerr.assert_called_once()
        assert res == []

    def test_get_instrument_model_parses_idn(self, monkeypatch):
        # Arrange
        rm_mock = RMMock(idn = "ACME,MODEL123,1000,1.2")
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        mgr = InstrumentManager()

        # Act
        model = mgr.get_instrument_model("GPIB::1")

        # Assert
        assert model == "MODEL123"

    def test_get_instrument_model_on_error_shows_message_and_returns_none(self, monkeypatch):
        # Arrange
        rm_mock = RMMock(open_error = RuntimeError("open fail"))
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        showerr = Mock()
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", showerr)

        mgr = InstrumentManager()

        # Act
        model = mgr.get_instrument_model("GPIB::1")

        # Assert
        showerr.assert_called_once()
        assert model is None

    def test_connect_success_registers_handler_and_returns_instrument(self, monkeypatch):
        # Arrange
        rm_mock = RMMock()
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        # register fake handler under role 'fake'
        monkeypatch.setitem(InstrumentManager.handler_registry, "fake", HandlerMock)

        mgr = InstrumentManager()

        # Act
        instr = mgr.connect("alias1", "GPIB::5", "fake")

        # Assert
        assert instr == "INST:GPIB::5"
        assert mgr.get_instrument("alias1") == "INST:GPIB::5"
        handler = mgr.get_handler("alias1")
        assert isinstance(handler, HandlerMock)

    def test_connect_unsupported_role_raises(self, monkeypatch):
        # Arrange
        rm_mock = RMMock()
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        mgr = InstrumentManager()

        # Act & Assert
        with pytest.raises(ValueError):
            mgr.connect("a", "addr", "no_such_role")

    def test_connect_shows_error_and_returns_none_on_exception(self, monkeypatch):
        # Arrange
        rm_mock = RMMock()
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        showerr = Mock()
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", showerr)

        class BadHandlerMock(HandlerMock):
            def connect(self, rm):
                raise RuntimeError("conn fail")

        monkeypatch.setitem(InstrumentManager.handler_registry, "bad", BadHandlerMock)

        mgr = InstrumentManager()

        # Act
        instr = mgr.connect("alias2", "ADDR", "bad")

        # Assert
        showerr.assert_called_once()
        assert instr is None
        assert mgr.get_handler("alias2") is None

    def test_get_error_no_instrument_returns_message(self, monkeypatch):
        # Arrange
        rm_mock = RMMock()
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        mgr = InstrumentManager()

        # Act & Assert
        assert mgr.get_error("missing") == "No instrument found."

    def test_get_error_handles_handler_exceptions(self, monkeypatch):
        # Arrange
        rm_mock = RMMock()
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        class BrokenHandlerMock(HandlerMock):
            def get_error(self):
                raise RuntimeError("err")

        # register and attach handler instance manually
        monkeypatch.setitem(InstrumentManager.handler_registry, "broken", BrokenHandlerMock)
        mgr = InstrumentManager()
        # simulate a stored handler with an instrument
        h = BrokenHandlerMock("ADDR")
        h.instrument = "INST"
        mgr.handlers["x"] = h

        # Act & Assert
        assert mgr.get_error("x") == "Could not query error."

    def test_disconnect_and_disconnect_all_close_and_remove_handlers(self, monkeypatch):
        # Arrange
        rm_mock = RMMock()
        monkeypatch.setattr("instruments.instrument_manager.pyvisa.ResourceManager", lambda: rm_mock)
        monkeypatch.setattr("instruments.instrument_manager.messagebox.showerror", Mock())

        mgr = InstrumentManager()
        h1 = HandlerMock("A")
        h1.instrument = "I1"
        h2 = HandlerMock("B")
        h2.instrument = "I2"
        mgr.handlers["one"] = h1
        mgr.handlers["two"] = h2

        # Act & Assert
        mgr.disconnect("one")
        assert "one" not in mgr.handlers
        assert h1.closed is True

        mgr.disconnect_all()
        assert mgr.handlers == {}
        assert h2.closed is True
