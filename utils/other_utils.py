import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox
from utils.ui_utils.loading_popup import LoadingPopup


def get_widget_value(variable):
    try:
        return variable.get()
    except (tk.TclError, ValueError):
        return None


def save_setting_from_widget(setting_manager, name, widget, logger=None):
    try:
        value = get_widget_value(widget)
        if value is not None:
            setting_manager.save_setting(name, value)
            if logger:
                logger.info(f"Saved setting '{name}': {value}")
    except Exception as e:
        if logger:
            logger.warning(f"Failed to save setting '{name}': {e}\n{traceback.format_exc()}")


def load_visa_resources_util(instrument_manager, only_tcpip=False, logger=None, include_mock=True, mock_resources=None):
    resources = instrument_manager.list_resources(only_tcpip = only_tcpip)
    if include_mock and getattr(instrument_manager, 'allow_mock', only_tcpip):
        resources = mock_resources + tuple(resources)
    if logger:
        logger.info(f"Loaded VISA resources: {resources}")
    return resources


def connect_with_popup(root, visa_address, logger, connect_func, timeout=10, loading_message="Connecting..."):
    if "No VISA" in visa_address or not visa_address.strip():
        messagebox.showerror("Connection Error", "Please select a valid VISA resource.")
        return False

    loading = LoadingPopup(root)
    success = False
    exception = None

    def attempt():
        nonlocal success, exception
        try:
            connect_func()
            success = True
        except Exception as e:
            exception = e

    thread = threading.Thread(target = attempt, daemon = True)
    thread.start()
    thread.join(timeout = timeout)

    loading.close()

    if not success:
        if exception is None:
            logger.error("VISA resource connection timeout")
            messagebox.showerror("Connection timeout", "Could not connect to VISA resource:\nConnection timeout")
        else:
            logger.error(f"Connection error: {exception}\n{traceback.format_exc()}")
            messagebox.showerror("Connection Error", f"Could not connect to VISA resource:\n{exception}")
        return False

    logger.info(f"Connected to VISA resource: {visa_address}")
    return True


def find_project_root(marker="README.md"):
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / marker).exists():
            return parent
    return path.parent  # fallback
