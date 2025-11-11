import csv
import os
from pathlib import Path

from utils.file_utils import CsvLogger


def test_set_file_name_and_directory(tmp_path):
    # Arrange
    logger = CsvLogger()

    test_dir = tmp_path / "logs"
    test_name = "test.csv"

    # Act
    logger.set_file_name(test_name)
    logger.set_file_directory(test_dir)

    # Assert
    normalized_expected = os.path.normpath(str(test_dir))
    normalized_actual = os.path.normpath(logger.file_directory)

    assert logger.filename == test_name
    assert normalized_actual == normalized_expected
    assert os.path.exists(normalized_expected)


def test_create_and_write_row(tmp_path):
    """CsvLogger should create a CSV file and write header  data rows."""
    # Arrange
    logger = CsvLogger()

    test_dir = tmp_path / "data"
    logger.set_file_directory(test_dir)
    logger.set_file_name("output.csv")
    logger.set_first_row(["Time", "Value"])

    full_path, csvfile, _ = logger.create()

    assert Path(full_path).exists()
    assert csvfile.writable()

    # Act
    logger.write_row(["12:00", "100"])
    logger.write_row(["12:01", "200"])
    logger.close()

    # Assert
    with open(full_path, newline = '') as f:
        rows = list(csv.reader(f))

    assert rows == [
        ["Time", "Value"],
        ["12:00", "100"],
        ["12:01", "200"],
    ]


def test_get_full_filename_returns_expected(tmp_path):
    """CsvLogger.get_full_filename() should return the correct full path."""
    # Arrange
    logger = CsvLogger()
    logger.set_file_directory(tmp_path)
    logger.set_file_name("log.csv")
    logger.set_first_row(["Header"])
    full_path, *_ = logger.create()

    # Act & Assert
    assert logger.get_full_filename() == full_path


def test_close_without_create_raises_no_error(monkeypatch):
    """CsvLogger.close() should safely handle being called before create()."""
    # Arrange
    logger = CsvLogger()

    # Patch time.sleep to avoid delay
    called = {}
    monkeypatch.setattr("time.sleep", lambda s: called.setdefault("slept", s))

    # Act
    logger.close()  # Should not raise or crash

    # Assert
    assert "slept" not in called


def test_close_after_create_logger_closed(monkeypatch, tmp_path):
    """CsvLogger.close() should close the file and call time.sleep()."""
    # Arrange
    logger = CsvLogger()
    logger.set_file_directory(tmp_path)
    logger.set_file_name("delayed.csv")
    logger.set_first_row(["Header"])

    full_path, csvfile, writer = logger.create()

    slept = {}
    monkeypatch.setattr("time.sleep", lambda s: slept.setdefault("slept", s))

    # Act
    logger.close()

    # Assert
    assert slept["slept"] == 0.5
    assert csvfile.closed


def test_write_row_flushes(monkeypatch, tmp_path):
    """write_row() should call flush() after writing."""
    # Arrange
    logger = CsvLogger()
    logger.set_file_directory(tmp_path)
    logger.set_file_name("flush.csv")
    logger.set_first_row(["Col"])
    _, csvfile, _ = logger.create()

    flushed = {}

    def fake_flush():
        flushed["ok"] = True

    monkeypatch.setattr(csvfile, "flush", fake_flush)

    # Act
    logger.write_row(["123"])

    # Assert
    assert flushed["ok"]