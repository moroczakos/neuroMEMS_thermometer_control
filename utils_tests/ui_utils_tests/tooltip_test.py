import pytest
import tkinter as tk
from unittest.mock import patch, MagicMock

from utils.ui_utils.tooltip import ToolTip


@pytest.fixture
def root():
    """Provides a hidden Tk root window."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def widget(root):
    """Provides a simple widget to attach tooltip to."""
    btn = tk.Button(root, text="Hover me")
    btn.pack()
    return btn


def test_tooltip_initialization(widget):
    """Ensure tooltip binds all expected events and sets initial state."""
    # Arrange & Act
    tooltip = ToolTip(widget, "Sample text")

    # Assert
    # Verify event bindings
    events = widget.bind()
    assert "<Enter>" in events
    assert "<Leave>" in events
    assert "<Motion>" in events

    # Verify initial attributes
    assert tooltip.text == "Sample text"
    assert tooltip.tip_window is None
    assert tooltip.after_id is None
    assert tooltip.delay == 500
    assert tooltip.wraplength == 200


def test_on_enter_calls_after(widget):
    """Verify that entering schedules tooltip show via after()."""
    # Arrange
    tooltip = ToolTip(widget, "Hello")

    # Act
    with patch.object(widget, "after", return_value="after123") as mock_after:
        tooltip._on_enter()

        # Assert
        mock_after.assert_called_once_with(tooltip.delay, tooltip._show_tip)
        assert tooltip.after_id == "after123"


def test_on_leave_hides_and_cancels(widget):
    """Verify _on_leave hides tooltip and cancels after."""
    # Arrange
    tooltip = ToolTip(widget, "Bye")
    tooltip.after_id = "after999"

    mock_after_cancel = MagicMock()
    widget.after_cancel = mock_after_cancel

    # Act
    with patch.object(tooltip, "_hide_tip") as mock_hide:
        tooltip._on_leave()

        # Assert
        mock_hide.assert_called_once()
        mock_after_cancel.assert_called_once_with("after999")
        assert tooltip.after_id is None


def test_show_tip_creates_window(widget):
    """_show_tip should create a Toplevel with a Label and correct geometry."""
    # Arrange
    tooltip = ToolTip(widget, "Tooltip text")

    # Patch geometry dependencies
    widget.winfo_rootx = lambda: 100
    widget.winfo_rooty = lambda: 200

    # Act
    with patch("tkinter.Toplevel") as MockTop:
        mock_toplevel = MockTop.return_value
        mock_label = MagicMock()
        with patch("tkinter.Label", return_value=mock_label):
            tooltip._show_tip()

        # Assert
        MockTop.assert_called_once_with(widget)
        mock_toplevel.wm_overrideredirect.assert_called_once_with(True)
        mock_toplevel.geometry.assert_called_once_with("+120+220")
        mock_label.pack.assert_called_once()
        assert tooltip.tip_window == mock_toplevel


def test_show_tip_respects_disabled_flag(widget):
    """If global show_tooltip is False, _show_tip does nothing."""
    tooltip = ToolTip(widget, "No show")
    ToolTip.show_tooltip = False
    tooltip._show_tip()
    assert tooltip.tip_window is None
    ToolTip.show_tooltip = True  # restore


def test_show_tip_does_nothing_when_text_missing(widget):
    """If no text is given, tooltip should not display."""
    tooltip = ToolTip(widget, "")
    tooltip._show_tip()
    assert tooltip.tip_window is None


def test_hide_tip_destroys_existing(widget):
    """If tip_window exists, it should be destroyed and set to None."""
    tooltip = ToolTip(widget, "Hide me")
    mock_window = MagicMock()
    tooltip.tip_window = mock_window
    tooltip._hide_tip()
    mock_window.destroy.assert_called_once()
    assert tooltip.tip_window is None


def test_on_motion_updates_position(widget):
    """_on_motion moves the tooltip window based on cursor position."""
    tooltip = ToolTip(widget, "Move me")
    tooltip.tip_window = MagicMock()

    event = MagicMock()
    event.x_root = 50
    event.y_root = 60

    tooltip._on_motion(event)
    tooltip.tip_window.geometry.assert_called_once_with("+60+70")


def test_on_motion_does_nothing_without_tip(widget):
    """If no tip_window, _on_motion should not crash."""
    tooltip = ToolTip(widget, "No move")
    event = MagicMock(x_root=10, y_root=10)
    tooltip._on_motion(event)  # should not raise
