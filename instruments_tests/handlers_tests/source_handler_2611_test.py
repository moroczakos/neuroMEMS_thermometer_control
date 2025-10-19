import math
import pytest
from unittest.mock import Mock
from instruments.handlers.source_handler import SourceHandler
from instruments.handlers.source_handler_2611 import SourceHandler2611
from instruments.mock_Keithley2611 import MockKeithley2611


class TestSourceHandler2611:
    def test_connect_uses_mock_when_address_is_mock(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.use_mock = True
        handler.address = "MOCK_2611"
        rm = Mock()

        # Act
        instr = handler.connect(rm)

        # Assert
        rm.open_resource.assert_not_called()
        assert isinstance(handler.instrument, MockKeithley2611)
        assert instr is handler.instrument

    def test_connect_uses_resource_manager_when_not_mock(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.use_mock = False
        handler.address = "GPIB::5"
        rm = Mock()
        mock_instr = Mock(name = "REAL_INSTR")
        rm.open_resource = Mock(return_value = mock_instr)

        # Act
        instr = handler.connect(rm)

        # Assert
        rm.open_resource.assert_called_once_with("GPIB::5")
        assert handler.instrument == instr == mock_instr

    def test_reset_writes_expected_commands(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.instrument = Mock()

        # Act
        handler.reset()

        # Assert
        calls = [c.args[0] for c in handler.instrument.write.call_args_list]
        # Check presence of key commands
        assert any("smua.reset" in s for s in calls)
        assert any("smua.source.func" in s for s in calls)
        assert any("smua.source.rangei" in s for s in calls)
        assert any("smua.source.leveli" in s for s in calls)
        assert any("smua.source.limitv" in s for s in calls)
        assert any("smua.sense" in s for s in calls)
        assert any("smua.measure.autorangev" in s for s in calls)
        assert any("smua.source.output" in s for s in calls)

    def test_measure_parses_iv_and_calculates_resistance(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.instrument = Mock()
        handler.instrument.query.return_value = "0.5\t2.0\n"

        # Act
        result = handler.measure()

        # Assert
        assert result["current"] == pytest.approx(0.5)
        assert result["voltage"] == pytest.approx(2.0)
        assert result["resistance"] == pytest.approx(4.0)

    def test_measure_handles_zero_current_returns_inf(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.instrument = Mock()
        handler.instrument.query.return_value = "0.0\t1.23\n"

        # Act
        result = handler.measure()

        # Assert
        assert result["current"] == pytest.approx(0.0)
        assert result["voltage"] == pytest.approx(1.23)
        assert math.isinf(result["resistance"]) and result["resistance"] > 0

    def test_close_turns_output_off(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.instrument = Mock()

        # Act
        handler.close()

        # Assert
        handler.instrument.write.assert_called_with("smua.source.output = smua.OUTPUT_OFF")

    def test_close_turns_output_off_and_swallows_errors(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        bad_instr = Mock()
        bad_instr.write.side_effect = Exception("write failed")
        handler.instrument = bad_instr

        # Act / Assert
        handler.close()

    def test_set_range_and_limits_and_digital_io(self):
        # Arrange
        handler = SourceHandler2611(SourceHandler)
        handler.instrument = Mock()

        # Act & Assert
        handler.set_current_range(0.2)
        handler.instrument.write.assert_called_with("smua.source.rangei = 0.2")

        handler.set_voltage_limit(5)
        handler.instrument.write.assert_called_with("smua.source.limitv = 5")

        handler.set_digital_io_high()
        handler.instrument.write.assert_called_with("digio.writebit(1, 1)")

        handler.set_digital_io_low()
        handler.instrument.write.assert_called_with("digio.writebit(1, 0)")
