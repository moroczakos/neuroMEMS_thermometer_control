# python
from abc import ABC
from unittest.mock import Mock
import pytest

from instruments.handlers.source_handler import SourceHandler


class DummySourceHandler(SourceHandler, ABC):
    def __init__(self, address = "DUMMY", use_mock = False):
        super().__init__(address, use_mock)

    def connect(self, resource_manager):
        self.instrument = Mock()
        return self.instrument

    def reset(self):
        pass

    def set_current(self, value):
        super().set_current(value)

    def set_current_range(self, value):
        pass

    def set_voltage_limit(self, value):
        pass

    def measure(self):
        return {"current": self.current}

    def set_digital_io_high(self):
        pass

    def set_digital_io_low(self):
        pass


class TestSourceHandler:
    def test_set_current_updates_current(self):
        # Arrange
        handler = DummySourceHandler()

        # Act / Assert
        assert handler.current == pytest.approx(0.0)
        handler.set_current(0.25)
        assert handler.current == pytest.approx(0.25)

    def test_measure_reflects_current(self):
        # Arrange
        handler = DummySourceHandler()
        handler.set_current(0.75)

        # Act
        result = handler.measure()

        # Assert
        assert result["current"] == pytest.approx(0.75)

    def test_get_error_returns_none_for_ok_strings(self):
        # Arrange
        handler = DummySourceHandler()
        handler.instrument = Mock()

        # Act & Assert
        handler.instrument.query.return_value = "+0, \"No error\"\n"
        assert handler.get_error() is None
        handler.instrument.query.return_value = "Some No error message"
        assert handler.get_error() is None

    def test_get_error_returns_error_string_when_present(self):
        # Arrange
        handler = DummySourceHandler()
        handler.instrument = Mock()
        handler.instrument.query.return_value = "-100, \"Some error\"\n"

        # Act & Assert
        assert handler.get_error() == "-100, \"Some error\""
