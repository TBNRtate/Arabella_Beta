from __future__ import annotations

import platform
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import psutil
import structlog

logger = structlog.get_logger(__name__)


class PlatformCapability(Enum):
    PROCESS_MONITORING = "process_monitoring"
    FILESYSTEM_WATCHING = "filesystem_watching"
    NETWORK_MONITORING = "network_monitoring"
    CLIPBOARD_ACCESS = "clipboard_access"
    SYSTEM_NOTIFICATIONS = "system_notifications"
    CONTAINER_ISOLATION = "container_isolation"
    SERVICE_MANAGEMENT = "service_management"
    IPC_SOCKETS = "ipc_sockets"
    HARDWARE_SENSORS = "hardware_sensors"


class BasePlatformLayer(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        ...

    @abstractmethod
    def get_available_capabilities(self) -> set[PlatformCapability]:
        ...

    def has_capability(self, cap: PlatformCapability) -> bool:
        return cap in self.get_available_capabilities()

    @abstractmethod
    def get_system_info(self) -> dict:
        ...

    @abstractmethod
    def get_ipc_socket_path(self) -> str:
        ...

    @abstractmethod
    def get_default_data_dir(self) -> Path:
        ...

    @abstractmethod
    def get_default_config_dir(self) -> Path:
        ...

    @abstractmethod
    def get_default_log_dir(self) -> Path:
        ...

    def warn_missing_capability(self, cap: PlatformCapability) -> None:
        logger.warning("platform.capability_unavailable", platform=self.platform_name, capability=cap.value)


def build_system_info(platform_name: str) -> dict:
    return {
        "platform": platform_name,
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "cpu_count": psutil.cpu_count(),
        "total_ram_bytes": psutil.virtual_memory().total,
        "python_version": sys.version,
    }
