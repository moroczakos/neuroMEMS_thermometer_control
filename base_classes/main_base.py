import os

from utils.logger_manager import LoggerManager
from utils.settings_utils import SettingManager
from utils.other_utils import find_project_root, add_current_date_to_folder_path


class MainBase:
    def __init__(self):
        self.project_root = ""  # find_project_root()
        self.setting_manager = self._load_settings()
        self.logger_manager = None
        self.logger = None

    def _load_settings(self):
        settings_path = os.path.join(self.project_root, 'input_files', 'settings.json')
        setting_manager = SettingManager(settings_path)

        self.input_file_path = os.path.join(
            self.project_root, setting_manager.load_setting("input_files")
        )

        selected_output_folder = setting_manager.load_setting("selected_output_folder")
        if os.path.isdir(selected_output_folder):
            self.output_base_file_path = selected_output_folder
        else:
            self.output_base_file_path = os.path.join(
                self.project_root, setting_manager.load_setting("output_files")
            )
        self.output_base_file_path = add_current_date_to_folder_path(self.output_base_file_path)

        self.log_file_path = add_current_date_to_folder_path(os.path.join(
            self.project_root, setting_manager.load_setting("log_files")
        ))

        return setting_manager

    def setup_logger(self, log_file_name):
        log_path = os.path.join(self.log_file_path, log_file_name)
        self.logger_manager = LoggerManager(log_file = log_path)
        self.logger = self.logger_manager.get_logger()
