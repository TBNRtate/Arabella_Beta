import os
from pathlib import Path

from core_framework.constants import APP_NAME
from core_framework.platform.base import BasePlatformLayer, PlatformCapability, build_system_info


class WindowsPlatformLayer(BasePlatformLayer):
    @property
    def platform_name(self) -> str:
        return "windows"

    def get_available_capabilities(self) -> set[PlatformCapability]:
        return {
            PlatformCapability.PROCESS_MONITORING,
            PlatformCapability.FILESYSTEM_WATCHING,
            PlatformCapability.CLIPBOARD_ACCESS,
            PlatformCapability.SYSTEM_NOTIFICATIONS,
            PlatformCapability.IPC_SOCKETS,
            PlatformCapability.HARDWARE_SENSORS,
        }

    def get_system_info(self) -> dict:
        return build_system_info(self.platform_name)

    def get_ipc_socket_path(self) -> str:
        """Named pipe path. ZMQ IPC on Windows uses TCP loopback internally."""
        return r"\\.\pipe\core_framework_eventbus"

    def get_default_data_dir(self) -> Path:
        return Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME

    def get_default_config_dir(self) -> Path:
        return self.get_default_data_dir() / "config"

    def get_default_log_dir(self) -> Path:
        return self.get_default_data_dir() / "logs"
