import os
import tkinter as tk
from tkinter import messagebox

from utils.other_utils import find_project_root
from utils.settings_utils import load_tooltip_data
from utils.ui_utils.logger_panel import LoggingPanel
from utils.constants import Logger, UI


class ViewBase:
    def __init__(self, root, setting_manager, logger):
        self.root = tk.Frame(root)
        self.root.pack(fill = 'both', expand = True)

        self.logger = logger
        self.setting_manager = setting_manager
        self.project_root = ""  # find_project_root()
        self.input_file_path = os.path.join(self.project_root, self.setting_manager.load_setting("input_files"))
        self.tooltips = load_tooltip_data(
            os.path.join(self.input_file_path, self.setting_manager.load_setting(UI.TOOLTIPS)))

    def setup_logger_panel(self):
        """Insert the reusable LoggingPanel into the GUI and link it to the logger."""
        LoggingPanel(self.root, logger = self.logger).pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        self.log(Logger.INFO, "Application started and UI initialized.")

    def log(self, message_type, message):
        if message_type == Logger.INFO:
            self.root.after(0, lambda: self.logger.info(message))
        elif message_type == Logger.WARNING:
            self.root.after(0, lambda: self.logger.warning(message))
        else:
            self.root.after(0, lambda: self.logger.error(message))
            messagebox.showerror("Error", message)
