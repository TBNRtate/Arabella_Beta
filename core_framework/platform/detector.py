from __future__ import annotations

import sys

from core_framework.exceptions import UnsupportedPlatformError
from core_framework.platform.base import BasePlatformLayer
from core_framework.platform.linux import LinuxPlatformLayer
from core_framework.platform.macos import MacOSPlatformLayer
from core_framework.platform.windows import WindowsPlatformLayer


class PlatformDetector:
    @staticmethod
    def detect(override: str | None = None) -> BasePlatformLayer:
        normalized = (override or "").lower().strip()
        if normalized:
            mapping = {
                "linux": LinuxPlatformLayer,
                "macos": MacOSPlatformLayer,
                "windows": WindowsPlatformLayer,
            }
            if normalized not in mapping:
                raise UnsupportedPlatformError(f"Unsupported platform override: {override}")
            return mapping[normalized]()

        sys_platform = sys.platform.lower()
        if sys_platform.startswith("linux"):
            return LinuxPlatformLayer()
        if sys_platform == "darwin":
            return MacOSPlatformLayer()
        if sys_platform in {"win32", "windows"}:
            return WindowsPlatformLayer()
        raise UnsupportedPlatformError(f"Unsupported platform: {sys.platform}")
