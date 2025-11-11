import time

import pytest
import logging
import tkinter as tk
from unittest.mock import MagicMock, patch

from utils.ui_utils.logger_panel import LoggingPanel


@pytest.fixture(scope = "function")
def root():
    """Fixture providing a hidden Tk root window."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def test_panel_initialization(root):
    """Verify text widget, scrollbar, and handler are initialized correctly."""
    # Arrange & Act
    panel = LoggingPanel(root)

    # Assert
    # Check widgets exist and are packed
    assert isinstance(panel.text_widget, tk.Text)
    assert isinstance(panel.scrollbar, tk.Scrollbar)
    assert panel.text_widget.cget("wrap") == "word"
    assert panel.text_widget.cget("yscrollcommand") is not None

    # Handler should be a logging.Handler subclass
    handler = panel.get_handler()
    assert isinstance(handler, logging.Handler)
    assert handler.formatter is not None


def test_handler_attached_to_logger(root):
    """Ensure handler is attached when logger is provided."""
    # Arrange
    test_logger = logging.getLogger("test_logger")
    original_handlers = len(test_logger.handlers)

    # Act
    panel = LoggingPanel(root, logger = test_logger)

    # Assert
    # Handler should be attached
    assert len(test_logger.handlers) == original_handlers + 1
    assert any(isinstance(h, LoggingPanel.TextHandler) for h in test_logger.handlers)

    # Clean up to avoid logger pollution across tests
    test_logger.handlers.clear()


def test_emit_calls_after_with_formatted_message(root):
    """Ensure emit() schedules _write with formatted log message."""
    # Arrange
    panel = LoggingPanel(root)
    handler = panel.get_handler()

    mock_record = logging.LogRecord(
        name = "test",
        level = logging.INFO,
        pathname = __file__,
        lineno = 10,
        msg = "Test message",
        args = (),
        exc_info = None,
    )

    formatted_msg = handler.format(mock_record)

    # Act & Assert
    # Patch .after() so we can verify the scheduling call instead of execution
    with patch.object(panel.text_widget, "after") as mock_after:
        handler.emit(mock_record)

        # Ensure after() was called once with correct arguments
        mock_after.assert_called_once_with(0, handler._write, formatted_msg)


def test_write_inserts_text_and_scrolls(root):
    """_write() should insert text and call see(END)."""
    # Arrange
    panel = LoggingPanel(root)
    handler = panel.get_handler()

    panel.text_widget.insert = MagicMock()
    panel.text_widget.see = MagicMock()

    message = "Hello log"

    # Act
    handler._write(message)

    # Assert
    panel.text_widget.insert.assert_called_once()
    args, _ = panel.text_widget.insert.call_args
    assert args[1].strip() == message

    panel.text_widget.see.assert_called_once()


def test_logging_panel_integration_writes_to_text(root):
    # Arrange
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)

    panel = LoggingPanel(root, logger)
    handler = panel.get_handler()

    # Act
    # Log a message
    logger.info("Integration message")

    # Assert
    # Allow Tkinter event loop to process 'after' callbacks
    root.update()
    time.sleep(0.05)  # allow after(0) to execute
    root.update()

    contents = panel.text_widget.get("1.0", "end-1c")
    assert "Integration message" in contents

    # Cleanup handler
    logger.removeHandler(handler)
