import threading
from datetime import datetime
import tkinter as tk
from unittest.mock import Mock

from utils import other_utils


def test_get_widget_value_success():
    # Arrange
    class Var:
        def get(self):
            return "value"

    # Act & Assert
    assert other_utils.get_widget_value(Var()) == "value"


def test_get_widget_value_handles_tcl_error_and_value_error():
    # Arrange
    class VarTcl:
        def get(self):
            raise tk.TclError("tcl error")

    class VarVal:
        def get(self):
            raise ValueError("val error")

    # Act & Assert
    assert other_utils.get_widget_value(VarTcl()) is None
    assert other_utils.get_widget_value(VarVal()) is None


def test_save_setting_from_widget_saves_and_logs(monkeypatch):
    # Arrange
    saved = {}

    class SM:
        def save_setting(self, name, value):
            saved[name] = value

    logger = Mock()

    class Widget:
        def get(self):
            return 123

    # Act
    other_utils.save_setting_from_widget(SM(), "k", Widget(), logger = logger)

    # Assert
    assert saved["k"] == 123
    logger.info.assert_called_once()
    assert "Saved setting 'k'" in logger.info.call_args[0][0]


def test_save_setting_from_widget_no_value(monkeypatch):
    # Arrange
    saved = {}

    class SM:
        def save_setting(self, name, value):
            saved[name] = value

    logger = Mock()

    class Widget:
        def get(self):
            return None

    # Act
    other_utils.save_setting_from_widget(SM(), "k", Widget(), logger = logger)

    # Assert
    assert saved == {}
    logger.info.assert_not_called()


def test_save_setting_from_widget_handles_exception(monkeypatch):
    # Arrange
    class SM:
        def save_setting(self, name, value):
            raise RuntimeError("fail")

    logger = Mock()

    class Widget:
        def get(self):
            return "v"

    # Act
    other_utils.save_setting_from_widget(SM(), "k", Widget(), logger = logger)

    # Assert
    logger.warning.assert_called_once()
    assert "Failed to save setting 'k'" in logger.warning.call_args[0][0]


def test_load_visa_resources_util_combines_mock(monkeypatch):
    # Arrange
    class IM:
        def __init__(self):
            self.allow_mock = True

        def list_resources(self, only_tcpip = False):
            return ("GPIB0",)

    # Act
    resources = other_utils.load_visa_resources_util(IM(), only_tcpip = False, include_mock = True,
                                                     mock_resources = ("MOCK1",))

    # Assert
    assert resources == ("MOCK1",) + ("GPIB0",)


def test_load_visa_resources_util_only_tcpip_and_no_allow_mock(monkeypatch):
    # Arrange
    class IM:
        def list_resources(self, only_tcpip = False):
            return ("TCPIP::1::INSTR",)

    # Act
    # instrument manager has no allow_mock attribute, only_tcpip=True -> allow_mock resolves to True
    resources = other_utils.load_visa_resources_util(IM(), only_tcpip = True, include_mock = True,
                                                     mock_resources = ("MOCKX",))

    # Assert
    assert resources == ("MOCKX",) + ("TCPIP::1::INSTR",)


def test_connect_with_popup_invalid_address(monkeypatch):
    # Arrange
    showerror = Mock()
    monkeypatch.setattr(other_utils.messagebox, "showerror", showerror)
    logger = Mock()

    # Act
    res = other_utils.connect_with_popup(root = None, visa_address = "No VISA here", logger = logger,
                                         connect_func = lambda: None)

    # Assert
    assert res is False
    showerror.assert_called_once()


def test_connect_with_popup_success(monkeypatch):
    # Arrange
    # stub LoadingPopup so it doesn't create any GUI
    class StubLoading:
        def __init__(self, root):
            self.closed = False

        def close(self):
            self.closed = True

    monkeypatch.setattr(other_utils, "LoadingPopup", StubLoading)
    showerror = Mock()
    monkeypatch.setattr(other_utils.messagebox, "showerror", showerror)
    logger = Mock()

    def connect_func():
        # quick successful connect
        return

    # Act
    res = other_utils.connect_with_popup(root = None, visa_address = "TCPIP::1", logger = logger,
                                         connect_func = connect_func, timeout = 1)

    # Assert
    assert res is True
    logger.info.assert_called_with(f"Connected to VISA resource: TCPIP::1")
    showerror.assert_not_called()


def test_connect_with_popup_timeout(monkeypatch):
    # Arrange
    class StubLoading:
        def __init__(self, root):
            self.closed = False

        def close(self):
            self.closed = True

    monkeypatch.setattr(other_utils, "LoadingPopup", StubLoading)
    showerror = Mock()
    monkeypatch.setattr(other_utils.messagebox, "showerror", showerror)
    logger = Mock()

    stop_event = threading.Event()

    def blocking_connect():
        # will block until event set; join with timeout will expire
        stop_event.wait()

    # Act
    res = other_utils.connect_with_popup(root = None, visa_address = "TCPIP::2", logger = logger,
                                         connect_func = blocking_connect, timeout = 0.5)

    # Assert
    assert res is False
    # timeout path should call logger.error and showerror for timeout
    logger.error.assert_called()
    showerror.assert_called()
    # ensure we don't leave the event set (cleanup)
    stop_event.set()


def test_connect_with_popup_exception(monkeypatch):
    # Arrange
    class StubLoading:
        def __init__(self, root):
            pass

        def close(self):
            pass

    monkeypatch.setattr(other_utils, "LoadingPopup", StubLoading)
    showerror = Mock()
    monkeypatch.setattr(other_utils.messagebox, "showerror", showerror)
    logger = Mock()

    def raising_connect():
        raise RuntimeError("boom")

    # Act
    res = other_utils.connect_with_popup(root = None, visa_address = "TCPIP::3", logger = logger,
                                         connect_func = raising_connect, timeout = 1)

    # Assert
    assert res is False
    logger.error.assert_called()
    showerror.assert_called_once()


def test_find_project_root_finds_marker(tmp_path, monkeypatch):
    # Arrange
    # create a fake project tree and set other_utils.__file__ inside it
    proj = tmp_path / "proj"
    nested = proj / "src" / "pkg"
    nested.mkdir(parents = True)
    (proj / "README.md").write_text("project readme")
    fake_file = nested / "module.py"
    fake_file.write_text("# dummy")
    monkeypatch.setattr(other_utils, "__file__", str(fake_file))

    # Act
    root = other_utils.find_project_root(marker = "README.md")

    # Assert
    assert root == proj


def test_find_project_root_fallback(tmp_path, monkeypatch):
    # Arrange
    # no marker present -> should return parent of the module path
    base = tmp_path / "base"
    base.mkdir()
    file = base / "m.py"
    file.write_text("")
    monkeypatch.setattr(other_utils, "__file__", str(file))

    # Act
    root = other_utils.find_project_root(marker = "NON_EXISTENT_MARKER")

    # Assert
    assert root == base


def test_add_current_date_to_folder_path_returns_appended_date(tmp_path):
    # Arrange
    folder = str(tmp_path / "out")

    # Act
    res = other_utils.add_current_date_to_folder_path(folder)

    # Assert
    today = datetime.now().strftime("%Y-%m-%d")
    assert res.endswith(today)
    assert res.startswith(folder)
