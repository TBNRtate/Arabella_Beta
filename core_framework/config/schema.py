from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core_framework.constants import (
    APP_NAME,
    COMPONENT_SHUTDOWN_TIMEOUT_SECONDS,
    COMPONENT_STARTUP_TIMEOUT_SECONDS,
    EVENT_BUS_DEFAULT_PORT,
    IPC_SOCKET_PATH,
    MAX_EVENT_QUEUE_SIZE,
)


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    level: str = "INFO"
    format: str = "json"
    output_file: str | None = None


class EventBusConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    transport: str = "ipc"
    ipc_path: str = IPC_SOCKET_PATH
    tcp_host: str = "127.0.0.1"
    tcp_port: int = EVENT_BUS_DEFAULT_PORT
    max_queue_size: int = MAX_EVENT_QUEUE_SIZE


class ComponentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    startup_timeout: int = COMPONENT_STARTUP_TIMEOUT_SECONDS
    shutdown_timeout: int = COMPONENT_SHUTDOWN_TIMEOUT_SECONDS


class PlatformConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    override: str | None = None
    capability_warnings: bool = True


class CoreConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    profile: str = "default"
    app_name: str = APP_NAME
    debug: bool = False
    offline_mode: bool = True
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    event_bus: EventBusConfig = Field(default_factory=EventBusConfig)
    components: dict[str, ComponentConfig] = Field(default_factory=dict)
    platform: PlatformConfig = Field(default_factory=PlatformConfig)
    extensions: dict[str, Any] = Field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.logging, dict):
            self.logging = LoggingConfig(**self.logging)
        if isinstance(self.event_bus, dict):
            self.event_bus = EventBusConfig(**self.event_bus)
        if isinstance(self.platform, dict):
            self.platform = PlatformConfig(**self.platform)
        if isinstance(self.components, dict):
            self.components = {
                k: (v if isinstance(v, ComponentConfig) else ComponentConfig(**v))
                for k, v in self.components.items()
            }
