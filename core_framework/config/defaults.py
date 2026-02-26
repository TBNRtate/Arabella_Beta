from __future__ import annotations

from core_framework.config.schema import CoreConfig


def get_defaults() -> dict:
    """Return the baseline default config as a plain dict."""
    return CoreConfig().model_dump(mode="python")
