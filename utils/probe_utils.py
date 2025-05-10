import json
import os
import pandas as pd


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def load_probe_data(csv_path):
    try:
        df = pd.read_csv(csv_path)
        return df.set_index("Name").to_dict(orient = "index")
    except Exception as e:
        raise RuntimeError(f"Failed to load probes: {e}")


def load_last_probe(settings_file):
    try:
        with open(settings_file, "r") as f:
            settings = json.load(f)
            return settings.get("last_probe", "")
    except Exception as e:
        raise RuntimeError(f"Could not load settings: {e}")


def save_last_probe(probe_name, settings_file):
    try:
        with open(settings_file, "w") as f:
            json.dump({"last_probe": probe_name}, f)
    except Exception as e:
        print(f"Could not save settings: {e}")
