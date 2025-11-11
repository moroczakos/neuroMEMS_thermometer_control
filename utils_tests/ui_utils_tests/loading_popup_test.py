import pytest
import tkinter as tk
from unittest.mock import patch

from utils.ui_utils.loading_popup import LoadingPopup


@pytest.fixture
def root():
    """Fixture to provide a Tk root window and destroy it after tests."""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    yield root
    root.destroy()


def test_popup_creation(root):
    """Verify popup window and label are correctly initialized."""
    # Arrange & Act
    popup = LoadingPopup(root, message = "Testing...")

    # Assert
    # Check window properties
    assert popup.popup.winfo_exists()
    assert popup.popup.title() == "Please wait"
    assert popup.popup.winfo_geometry().startswith("200x100")

    # Check label text
    label = popup.popup.winfo_children()[0]
    assert isinstance(label, tk.Widget)
    assert label.cget("text") == "Testing..."

    popup.close()


def test_close_destroys_popup(root):
    """Ensure close() properly destroys the popup window."""
    # Arrange
    popup = LoadingPopup(root)
    assert popup.popup.winfo_exists()

    # Act
    popup.close()

    # Assert
    # After destroy, window should not exist
    assert not popup.popup.winfo_exists()


def test_close_handles_missing_popup(root):
    """If popup already destroyed, close() should not raise errors."""
    # Arrange
    popup = LoadingPopup(root)
    popup.popup.destroy()  # manually remove

    # Act & Assert
    try:
        popup.close()  # should not raise
    except Exception as e:
        pytest.fail(f"close() raised unexpectedly: {e}")


def test_popup_methods_called(root):
    """Verify geometry, grab_set, and update are invoked properly."""
    # Arrange & Act
    with patch("tkinter.Toplevel") as MockTop:
        mock_popup = MockTop.return_value
        LoadingPopup(root, message = "Connecting...")

        # Assert
        MockTop.assert_called_once_with(root)
        mock_popup.title.assert_called_once_with("Please wait")
        mock_popup.geometry.assert_called_once_with("200x100")
        mock_popup.resizable.assert_called_once_with(False, False)
        mock_popup.grab_set.assert_called_once()
        mock_popup.update.assert_called_once()
