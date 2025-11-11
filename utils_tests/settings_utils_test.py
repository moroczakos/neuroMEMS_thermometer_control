import json
import pytest
from utils.settings_utils import (
    load_probe_data,
    load_tooltip_data,
    SettingManager,
)


def test_load_probe_data_success(tmp_path):
    # Arrange
    p = tmp_path / "probes.csv"
    p.write_text("Name,Val1,Val2\nA,1,2\nB,3,4\n")

    # Act
    result = load_probe_data(str(p))

    # Assert
    assert set(result.keys()) == {"A", "B"}
    assert int(result["A"]["Val1"]) == 1
    assert int(result["A"]["Val2"]) == 2
    assert int(result["B"]["Val1"]) == 3
    assert int(result["B"]["Val2"]) == 4


def test_load_probe_data_file_not_found(tmp_path):
    # Arrange & Act
    p = tmp_path / "missing.csv"
    with pytest.raises(RuntimeError) as exc:
        load_probe_data(str(p))

    # Assert
    assert "Failed to load probes" in str(exc.value)


def test_load_probe_data_invalid_csv(tmp_path):
    # Arrange & Act
    p = tmp_path / "bad.csv"
    p.write_text("not,a,valid,csv\n:::")
    with pytest.raises(RuntimeError) as exc:
        load_probe_data(str(p))

    # Assert
    assert "Failed to load probes" in str(exc.value)


def test_load_tooltip_data_success(tmp_path):
    # Arrange
    data = {"hint1": "Do this", "hint2": "Do that"}
    p = tmp_path / "tooltips.json"
    p.write_text(json.dumps(data))

    # Act
    result = load_tooltip_data(str(p))

    # Assert
    assert result == data


def test_load_tooltip_data_file_not_found(tmp_path):
    # Arrange & Act
    p = tmp_path / "missing_tooltips.json"
    with pytest.raises(RuntimeError) as exc:
        load_tooltip_data(str(p))

    # Assert
    assert "Failed to load tooltip texts" in str(exc.value)


def test_load_tooltip_data_invalid_json(tmp_path):
    # Arrange & Act
    p = tmp_path / "bad_tooltips.json"
    p.write_text("not valid json")
    with pytest.raises(RuntimeError) as exc:
        load_tooltip_data(str(p))

    # Assert
    assert "Failed to load tooltip texts" in str(exc.value)


def test_setting_manager_load_and_save(tmp_path):
    # Arrange
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"alpha": "one", "keep": 42}))
    mgr = SettingManager(str(settings_file))
    assert mgr.load_setting("alpha") == "one"

    # Act
    mgr.save_setting("beta", {"x": 1})
    loaded = json.loads(settings_file.read_text())

    # Assert
    assert loaded["alpha"] == "one"
    assert loaded["keep"] == 42
    assert loaded["beta"] == {"x": 1}


def test_setting_manager_load_missing_file_raises(tmp_path):
    # Arrange & Act
    settings_file = tmp_path / "does_not_exist.json"
    mgr = SettingManager(str(settings_file))
    with pytest.raises(RuntimeError) as exc:
        mgr.load_setting("any")

    # Assert
    assert "Could not load settings: [Errno 2] No such file or directory:" in str(exc.value)


def test_setting_manager_save_creates_file_when_missing(tmp_path):
    # Arrange
    settings_file = tmp_path / "new_settings.json"
    mgr = SettingManager(str(settings_file))

    # Act
    mgr.save_setting("newkey", "newvalue")

    # Assert
    assert settings_file.exists()
    content = json.loads(settings_file.read_text())
    assert content == {"newkey": "newvalue"}


def test_setting_manager_save_handles_invalid_json_by_overwriting(tmp_path):
    # Arrange
    settings_file = tmp_path / "broken.json"
    settings_file.write_text("not json")
    mgr = SettingManager(str(settings_file))

    # Act
    mgr.save_setting("k", "v")

    # Assert
    content = json.loads(settings_file.read_text())
    assert content == {"k": "v"}