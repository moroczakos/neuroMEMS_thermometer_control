import pytest
from unittest.mock import Mock
from instruments.handlers.source_handler import SourceHandler
from instruments.handlers.source_handler_6221 import SourceHandler6221
from instruments.mock_Keithley6221 import MockKeithley6221


class TestSourceHandler6221:
    def test_connect_uses_mock_when_address_is_mock(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.use_mock = True
        handler.address = "MOCK_6221"
        rm = Mock()

        # Act
        instr = handler.connect(rm)

        # Assert
        rm.open_resource.assert_not_called()
        assert isinstance(handler.instrument, MockKeithley6221)
        assert instr is handler.instrument

    def test_connect_uses_resource_manager_when_not_mock(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.use_mock = False
        handler.address = "GPIB::3"
        rm = Mock()
        mock_instr = Mock(name = "REAL_INSTR")
        rm.open_resource = Mock(return_value = mock_instr)

        # Act
        instr = handler.connect(rm)

        # Assert
        rm.open_resource.assert_called_once_with("GPIB::3")
        assert handler.instrument == instr == mock_instr

    def test_reset_writes_expected_commands(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.instrument = Mock()

        # Act
        handler.reset()

        # Assert
        calls = [c.args[0] for c in handler.instrument.write.call_args_list]
        assert any("*RST" in s for s in calls)
        assert any("SOUR:CURR:RANG:AUTO ON" in s for s in calls)
        assert any("SOUR:CURR:COMP 10" in s for s in calls)
        assert any("OUTP ON" in s for s in calls)

    def test_measure_returns_current_value(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.current = 0.123

        # Act
        result = handler.measure()

        # Assert
        assert result["current"] == pytest.approx(0.123)

    def test_close_turns_output_off(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.instrument = Mock()

        # Act
        handler.close()

        # Assert
        handler.instrument.write.assert_called_with("OUTP OFF")

    def test_close_turns_output_off_and_swallows_errors(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        bad_instr = Mock()
        bad_instr.write.side_effect = Exception("write failed")
        handler.instrument = bad_instr

        # Act / Assert
        handler.close()

    def test_set_current_and_voltage_limit(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.instrument = Mock()

        # Act / Assert
        handler.set_current(0.05)
        handler.instrument.write.assert_called_with(":SOUR:CURR 0.05")
        handler.set_voltage_limit(5)
        handler.instrument.write.assert_called_with(":SOUR:CURR:COMP 5")

    def test_unimplemented_methods_do_nothing(self):
        # Arrange
        handler = SourceHandler6221(SourceHandler)
        handler.instrument = Mock()

        # Act & Asert
        handler.set_current_range(0.1)
        handler.set_digital_io_high()
        handler.set_digital_io_low()
        # none of the unimplemented methods should call write
        handler.instrument.write.assert_not_called()
