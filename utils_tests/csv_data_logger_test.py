import pytest
import queue
from unittest.mock import MagicMock
from concurrent.futures import ThreadPoolExecutor

from utils.constants import Logger
from utils.csv_data_logger import CSVDataLogger
from utils.file_utils import CsvLogger


@pytest.fixture
def mock_logger():
    """Mock the logger callable used by CSVDataLogger."""
    return MagicMock()


@pytest.fixture
def csv_logger_mock(monkeypatch):
    """Replace CsvLogger with a mock so no real file I/O occurs."""
    mock_instance = MagicMock(spec = CsvLogger)
    monkeypatch.setattr("utils.csv_data_logger.CsvLogger", lambda: mock_instance)
    return mock_instance


def test_initialization_resets_state(mock_logger):
    # Arrange & Act
    logger = CSVDataLogger(mock_logger)

    # Assert
    assert isinstance(logger.data_queue, queue.Queue)
    assert logger.data == []
    assert not logger.running


def test_setters_work(mock_logger):
    # Arrange & Act
    logger = CSVDataLogger(mock_logger)
    logger.set_file_name("test.csv")
    logger.set_file_directory("/tmp")
    logger.set_first_row(["a", "b"])
    logger.set_max_queue_size(50)

    # Assert
    assert logger.filename == "test.csv"
    assert logger.file_directory == "/tmp"
    assert logger.first_row == ["a", "b"]
    assert logger.max_queue_size == 50


def test_start_initializes_csv_logger(csv_logger_mock, mock_logger, tmp_path):
    """Ensure CSV logger is configured and worker thread starts."""
    # Arrange & Act
    logger = CSVDataLogger(mock_logger)
    logger.set_file_name("file.csv")
    logger.set_file_directory(tmp_path)
    logger.set_first_row(["col1", "col2"])

    logger.start()

    # Assert
    csv_logger_mock.set_file_name.assert_called_once_with("file.csv")
    csv_logger_mock.set_file_directory.assert_called_once_with(tmp_path)
    csv_logger_mock.set_first_row.assert_called_once_with(["col1", "col2"])
    csv_logger_mock.create.assert_called_once()
    assert logger.running is True
    assert isinstance(logger.executor, ThreadPoolExecutor)

    # cleanup
    logger.stop()


def test_stop_logs_and_closes(csv_logger_mock, mock_logger, tmp_path):
    # Arrange
    logger = CSVDataLogger(mock_logger)
    logger.set_file_name("file.csv")
    logger.set_file_directory(tmp_path)
    logger.set_first_row(["x"])
    logger.start()

    # Act
    logger.stop()

    # Assert
    csv_logger_mock.close.assert_called_once()


def test_enqueue_adds_to_queue(mock_logger):
    # Arrange
    logger = CSVDataLogger(mock_logger)
    item = ("a", "b")

    # Act
    logger.enqueue(item)

    # Assert
    assert not logger.data_queue.empty()
    assert logger.data_queue.get() == item


def test_worker_loop_writes_data(csv_logger_mock, mock_logger):
    """Simulate a worker loop iteration writing a row."""
    # Arrange
    logger = CSVDataLogger(mock_logger)
    logger.running = True
    logger.csv_logger = csv_logger_mock

    logger.data_queue.put(("x", "y"))

    # stop after processing
    def stop_after_once(data):
        logger.running = False
        csv_logger_mock.write_row(data)

    logger._accumulate_and_write_csv_log = stop_after_once

    # Act
    logger._worker_loop()

    # Assert
    csv_logger_mock.write_row.assert_called_once_with(("x", "y"))


def test_accumulate_and_write_warns_on_backlog(csv_logger_mock, mock_logger):
    """If queue is over max size, should log a warning."""
    # Arrange
    logger = CSVDataLogger(mock_logger)
    logger.csv_logger = csv_logger_mock
    logger.max_queue_size = 1

    # Act
    # artificially enlarge queue
    logger.data_queue.put("A")
    logger.data_queue.put("B")

    logger._accumulate_and_write_csv_log(["test"])

    # Assert
    mock_logger.assert_any_call(Logger.WARNING, "Queue backlog detected during measurement logging!")
    csv_logger_mock.write_row.assert_called_once_with(["test"])


def test_accumulate_and_write_handles_exceptions(csv_logger_mock, mock_logger):
    """If writing fails, should log an error with traceback."""
    # Arrange
    logger = CSVDataLogger(mock_logger)
    logger.csv_logger = csv_logger_mock
    csv_logger_mock.write_row.side_effect = Exception("Write failed")

    # Act
    logger._accumulate_and_write_csv_log(["bad"])

    # Assert
    found = False
    for level, message in mock_logger.call_args:
        if (level == Logger.ERROR and message.startswith(
                "CSV file writing error: Write failed\nTraceback (most recent call last):"
        )):
            found = True
            break

    assert found, "Expected error log with correct message prefix not found"