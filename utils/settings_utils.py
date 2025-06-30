import json
import os.path
from datetime import datetime

import pandas as pd


def load_probe_data(csv_path):
    try:
        df = pd.read_csv(csv_path)
        return df.set_index("Name").to_dict(orient = "index")
    except Exception as e:
        raise RuntimeError(f"Failed to load probes: {e}")


class SettingManager:
    def __init__(self, settings_file):
        self.settings_file = settings_file

    def load_setting(self, setting_name):
        try:
            with open(self.settings_file, "r") as f:
                settings = json.load(f)

                setting = settings.get(f"{setting_name}", "")

                if setting_name == "log_files" or setting_name == "output_files":
                    return os.path.join(setting, f"{datetime.now().strftime('%Y-%m-%d')}")

                return setting

        except Exception as e:
            raise RuntimeError(f"Could not load settings: {e}")

    def save_setting(self, setting_name, setting_value):
        try:
            # Try to load the existing settings from the file
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # If the file doesn't exist or is empty, initialize an empty dictionary
                settings = {}

            # Update the setting with the new value
            settings[setting_name] = setting_value

            # Save the updated settings back to the file
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent = 4)

        except Exception as e:
            print(f"Could not save settings: {e}")
