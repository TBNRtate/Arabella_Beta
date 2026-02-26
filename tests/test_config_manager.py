import os

import pytest
import yaml

from core_framework.config.manager import ConfigManager


def test_load_from_file(tmp_path):
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({"debug": False, "logging": {"level": "WARNING"}}))
    cfg = ConfigManager(tmp_path).load()
    assert cfg.logging.level == "WARNING"


def test_env_override(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({"debug": False}))
    monkeypatch.setenv("CF_DEBUG", "true")
    cfg = ConfigManager(tmp_path).load()
    assert cfg.debug is True


def test_profile_selection(tmp_path):
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({"debug": False}))
    (tmp_path / "config.dev.yaml").write_text(yaml.safe_dump({"debug": True}))
    cfg = ConfigManager(tmp_path, profile="dev").load()
    assert cfg.debug is True


def test_missing_file_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("CF_DEBUG", raising=False)
    cfg = ConfigManager(tmp_path).load()
    assert cfg.profile == "default"
    assert cfg.offline_mode is True
