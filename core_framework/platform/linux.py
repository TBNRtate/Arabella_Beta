from pathlib import Path

from core_framework.constants import APP_NAME, IPC_SOCKET_PATH
from core_framework.platform.base import BasePlatformLayer, PlatformCapability, build_system_info


class LinuxPlatformLayer(BasePlatformLayer):
    @property
    def platform_name(self) -> str:
        return "linux"

    def get_available_capabilities(self) -> set[PlatformCapability]:
        return set(PlatformCapability)

    def get_system_info(self) -> dict:
        return build_system_info(self.platform_name)

    def get_ipc_socket_path(self) -> str:
        return IPC_SOCKET_PATH

    def get_default_data_dir(self) -> Path:
        return Path.home() / ".local" / "share" / APP_NAME

    def get_default_config_dir(self) -> Path:
        return Path.home() / ".config" / APP_NAME

    def get_default_log_dir(self) -> Path:
        return Path.home() / ".local" / "share" / APP_NAME / "logs"
