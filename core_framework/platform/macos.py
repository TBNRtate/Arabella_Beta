from pathlib import Path

from core_framework.constants import APP_NAME, IPC_SOCKET_PATH
from core_framework.platform.base import BasePlatformLayer, PlatformCapability, build_system_info


class MacOSPlatformLayer(BasePlatformLayer):
    @property
    def platform_name(self) -> str:
        return "macos"

    def get_available_capabilities(self) -> set[PlatformCapability]:
        caps = set(PlatformCapability)
        caps.remove(PlatformCapability.CONTAINER_ISOLATION)
        caps.remove(PlatformCapability.SERVICE_MANAGEMENT)
        return caps

    def get_system_info(self) -> dict:
        return build_system_info(self.platform_name)

    def get_ipc_socket_path(self) -> str:
        return IPC_SOCKET_PATH

    def get_default_data_dir(self) -> Path:
        return Path.home() / "Library" / "Application Support" / APP_NAME

    def get_default_config_dir(self) -> Path:
        return Path.home() / "Library" / "Preferences" / APP_NAME

    def get_default_log_dir(self) -> Path:
        return Path.home() / "Library" / "Logs" / APP_NAME
