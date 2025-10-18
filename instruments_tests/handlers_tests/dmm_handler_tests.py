import pytest
from unittest.mock import Mock

from instruments.handlers.base import InstrumentHandler
from instruments.handlers.dmm_handler import DMMHandler
from instruments.mock_Keithley2100 import MockKeithley2100


class TestDMMHandler:
    def test_connect_uses_mock_when_address_is_mock(self):
        # Arrange
        handler = DMMHandler(InstrumentHandler)
        handler.use_mock = True
        handler.address = "MOCK"
        rm = Mock()

        # Act
        instr = handler.connect(rm)

        # Assert
        rm.open_resource.assert_not_called()
        assert isinstance(handler.instrument, MockKeithley2100)
        assert instr is handler.instrument

    def test_connect_uses_resource_manager_when_not_mock(self):
        # Arrange
        handler = DMMHandler(InstrumentHandler)
        handler.use_mock = False
        handler.address = "GPIB::1"
        rm = Mock()
        mock_instr = Mock(name = "REAL_INSTR")
        rm.open_resource = Mock(return_value = mock_instr)

        # Act
        instr = handler.connect(rm)

        # Assert
        rm.open_resource.assert_called_once_with("GPIB::1")
        assert handler.instrument == instr == mock_instr

    def test_reset_writes_expected_commands(self):
        # Arrange
        handler = DMMHandler(InstrumentHandler)
        handler.instrument = Mock()

        # Act
        handler.reset()

        # Assert
        calls = [c.args[0] for c in handler.instrument.write.call_args_list]
        assert any("*RST" in s for s in calls)
        assert any("CONF:FRES 1000" in s for s in calls)
        assert any("SENS:FRES:NPLC 1" in s for s in calls)

    def test_measure_writes_init_and_queries_fetch(self):
        # Arrange
        handler = DMMHandler(InstrumentHandler)
        handler.instrument = Mock()
        handler.instrument.query.return_value = "123.45\n"

        # Act
        result = handler.measure()

        # Assert
        handler.instrument.write.assert_called_with("INIT")
        handler.instrument.query.assert_called_with("FETCH?")
        assert result["resistance"] == pytest.approx(123.45)

    def test_get_error_returns_none_for_ok_strings(self):
        # Arrange
        handler = DMMHandler(InstrumentHandler)
        handler.instrument = Mock()

        # Act & Assert
        handler.instrument.query.return_value = "+0, \"No error\"\n"
        assert handler.get_error() is None
        handler.instrument.query.return_value = "Some No error message"
        assert handler.get_error() is None

    def test_get_error_returns_error_string_when_present(self):
        # Arrange
        handler = DMMHandler(InstrumentHandler)
        handler.instrument = Mock()
        handler.instrument.query.return_value = "-123, \"OverRange\"\n"

        # Act & Assert
        assert handler.get_error() == "-123, \"OverRange\""
