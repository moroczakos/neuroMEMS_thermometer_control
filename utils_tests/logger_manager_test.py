import logging
from tkinter import messagebox

from utils.logger_manager import LoggerManager, safe_execute


def test_logger_manager_creates_log_file(tmp_path):
    # Arrange & Act
    log_file = tmp_path / "logs" / "test_app.log"
    manager = LoggerManager(log_file = str(log_file))
    logger = manager.get_logger()

    # Assert
    assert isinstance(logger, logging.Logger)
    assert log_file.parent.exists()


def test_logger_manager_close_removes_handler(tmp_path):
    # Arrange
    log_file = tmp_path / "close_test.log"
    manager = LoggerManager(log_file = str(log_file))
    logger = manager.get_logger()

    assert len(logger.handlers) > 0

    # Act
    manager.close()

    # Assert
    assert len(logger.handlers) == 0
    assert manager.file_handler._closed


def test_logger_manager_creates_unique_loggers(tmp_path):
    """Each LoggerManager instance should have its own logger."""
    # Arrange
    log1 = tmp_path / "a.log"
    log2 = tmp_path / "b.log"

    # Act
    manager1 = LoggerManager(str(log1))
    manager2 = LoggerManager(str(log2))

    # Assert
    assert manager1.get_logger() is not manager2.get_logger()
    assert id(manager1.get_logger()) != id(manager2.get_logger())

    manager1.close()
    manager2.close()


def test_safe_execute_success():
    """safe_execute should return normally if no exception occurs."""
    # Arrange
    called = False

    @safe_execute
    def foo():
        nonlocal called
        called = True
        return "OK"

    # Act
    result = foo()

    # Assert
    assert called
    assert result == "OK"


def test_safe_execute_handles_exception(monkeypatch):
    # Arrange
    logged_error = {}
    shown_error = {}

    # Monkeypatch logging.error and messagebox.showerror
    def fake_log_error(msg, *args, **kwargs):
        logged_error["msg"] = msg

    def fake_showerror(title, message):
        shown_error["title"] = title
        shown_error["message"] = message

    monkeypatch.setattr(logging, "error", fake_log_error)
    monkeypatch.setattr(messagebox, "showerror", fake_showerror)

    @safe_execute
    def faulty():
        raise ValueError("Boom!")

    # Act
    # Should not raise
    result = faulty()
    assert result is None

    # Assert
    assert "faulty" in logged_error["msg"]
    assert "Boom!" in shown_error["message"]
    assert "Unexpected Error" in shown_error["title"]
