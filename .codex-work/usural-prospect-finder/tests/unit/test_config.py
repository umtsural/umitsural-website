from pathlib import Path

import pytest

from usural_prospect_finder.config import (
    PROJECT_ROOT,
    Settings,
    load_category_config,
    load_scoring_config,
    load_yaml,
)


def test_settings_load_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPF_GLOBAL_CONCURRENCY", "7")
    monkeypatch.setenv("UPF_DATABASE_PATH", "custom.db")
    settings = Settings.from_env()
    assert settings.global_concurrency == 7
    assert settings.database_path == PROJECT_ROOT / "custom.db"


def test_yaml_loading(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("version: 1\n", encoding="utf-8")
    assert load_yaml(path) == {"version": 1}


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("UPF_GLOBAL_CONCURRENCY", "0", "concurrency"),
        ("UPF_REQUEST_TIMEOUT", "0", "timeout"),
        ("UPF_LOG_LEVEL", "LOUD", "log level"),
    ],
)
def test_invalid_environment_fails_early(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str, message: str
) -> None:
    monkeypatch.setenv(variable, value)
    with pytest.raises(ValueError, match=message):
        Settings.from_env()


def test_project_configs_are_valid_and_uncalibrated() -> None:
    scoring = load_scoring_config()
    categories = load_category_config()
    assert scoring["status"] == "initial_defaults_not_calibrated"
    assert categories["architects"]["canonical_key"] == "architects"
    assert "es" in categories["architects"]["labels"]


def test_invalid_yaml_identifies_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("value: [\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"broken\.yaml"):
        load_yaml(path)
