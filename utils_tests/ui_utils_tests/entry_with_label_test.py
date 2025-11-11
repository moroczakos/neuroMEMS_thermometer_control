import pytest
import tkinter as tk
from unittest.mock import MagicMock

from utils.ui_utils.entry_with_label import EntryWithLabel


@pytest.fixture
def root():
    """Creates a Tk root window for widget tests."""
    root = tk.Tk()
    yield root
    root.destroy()


def test_widget_initialization_basic(root):
    """Ensure widget initializes with correct label, entry, and layout."""
    # Arrange
    var = tk.StringVar(value = "default")

    # Act
    widget = EntryWithLabel(
        root,
        labeltext = "Test Label",
        entrytextvariable = var,
        entrywidth = 15,
        entryjustify = "center",
    )

    # Assert
    # Basic attribute checks
    assert widget.label_text == "Test Label"
    assert widget.entry_text_variable is var
    assert widget.entry_with == 15
    assert widget.entry_justify == "center"

    # The label and entry exist
    label, entry = widget.get_widgets()
    assert label["text"] == "Test Label"
    assert isinstance(entry, tk.Entry)

    # Layout grid is correctly populated
    assert label.grid_info()["column"] == 0
    assert entry.grid_info()["column"] == 1


def test_trace_callback_invoked_on_write(root):
    """Verify that both save and command callbacks are invoked on variable write."""
    # Arrange
    var = tk.StringVar(value = "init")

    mock_save = MagicMock()
    mock_cmd = MagicMock()

    widget = EntryWithLabel(
        root,
        labeltext = "Label",
        entrytextvariable = var,
        entrywidth = 10,
        entryjustify = "left",
        saveentrytextvariablecommand = mock_save,
        savecommandkey = "key",
        command = mock_cmd,
    )

    # Act
    # Trigger StringVar write trace
    var.set("new value")

    # Assert
    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert args[0] == "key" and args[1] == var

    mock_cmd.assert_called_once()


def test_trace_callback_not_added_without_required_args(root):
    """If no save_command_key or save_command, no trace should be added."""
    # Arrange
    var = tk.StringVar(value = "init")
    mock_save = MagicMock()

    # Missing save_command_key → trace should not be installed
    widget = EntryWithLabel(
        root,
        labeltext = "Label",
        entrytextvariable = var,
        entrywidth = 10,
        entryjustify = "left",
        saveentrytextvariablecommand = mock_save,
    )

    # Act
    # Changing variable should not trigger callback
    var.set("something else")

    # Assert
    mock_save.assert_not_called()


def test_getters_return_correct_widgets(root):
    """Ensure getter methods return expected ttk widgets."""
    # Arrange
    var = tk.StringVar(value = "abc")
    widget = EntryWithLabel(
        root,
        labeltext = "L",
        entrytextvariable = var,
        entrywidth = 5,
        entryjustify = "right",
    )

    # Act & Assert
    label = widget.get_label()
    entry = widget.get_entry()

    assert isinstance(label, type(widget.label_widget))
    assert isinstance(entry, type(widget.entry))

    all_widgets = widget.get_widgets()
    assert all_widgets == (label, entry)
