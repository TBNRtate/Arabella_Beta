from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from core_framework.config.defaults import get_defaults
from core_framework.config.schema import CoreConfig
from core_framework.constants import DEFAULT_CONFIG_FILENAME
from core_framework.exceptions import ConfigValidationError, ConfigurationError

logger = structlog.get_logger(__name__)


class _EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CF_", env_nested_delimiter="__", extra="allow")


class ConfigManager:
    def __init__(self, config_dir: Path, profile: str = "default", overrides: dict | None = None):
        self.config_dir = Path(config_dir)
        self.profile = profile
        self.overrides = overrides or {}
        self._config: CoreConfig | None = None

    def _load_yaml_file(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.info("config.source", source=str(path), status="skipped", reason="not_found")
            return {}
        logger.info("config.source", source=str(path), status="loaded")
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    @staticmethod
    def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ConfigManager._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    def load(self) -> CoreConfig:
        merged = get_defaults()
        logger.info("config.source", source="defaults", status="loaded")

        base_path = self.config_dir / DEFAULT_CONFIG_FILENAME
        merged = self._merge_dicts(merged, self._load_yaml_file(base_path))

        profile_path = self.config_dir / f"config.{self.profile}.yaml"
        merged = self._merge_dicts(merged, self._load_yaml_file(profile_path))

        env_values = _EnvSettings().model_dump(exclude_none=True)
        if env_values:
            logger.info("config.source", source="environment", status="loaded", keys=sorted(env_values))
        else:
            logger.info("config.source", source="environment", status="skipped", reason="empty")
        merged = self._merge_dicts(merged, env_values)

        if self.overrides:
            logger.info("config.source", source="overrides", status="loaded", keys=sorted(self.overrides))
            merged = self._merge_dicts(merged, self.overrides)
        else:
            logger.info("config.source", source="overrides", status="skipped", reason="empty")

        merged["profile"] = self.profile

        try:
            self._config = CoreConfig.model_validate(merged)
            return self._config
        except ValidationError as exc:
            raise ConfigValidationError("Failed to validate configuration", details={"errors": exc.errors()}) from exc

    def get(self) -> CoreConfig:
        if self._config is None:
            raise ConfigurationError("Configuration not loaded")
        return self._config

    def reload(self) -> CoreConfig:
        return self.load()

    def get_extension(self, namespace: str) -> dict:
        return dict(self.get().extensions.get(namespace, {}))

    def save_current(self, path: Path) -> None:
        cfg = self.get().model_dump(mode="python")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(cfg, handle, sort_keys=True)
