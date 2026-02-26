from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from core_framework.config.schema import ComponentConfig
from core_framework.events.schema import Event
from core_framework.exceptions import InvalidStateTransitionError


class ComponentState(Enum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    DEGRADED = "degraded"


class ComponentMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    display_name: str
    version: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    optional_dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


LEGAL_TRANSITIONS = {
    ComponentState.REGISTERED: {ComponentState.STARTING},
    ComponentState.STARTING: {ComponentState.RUNNING, ComponentState.FAILED, ComponentState.DEGRADED},
    ComponentState.RUNNING: {ComponentState.STOPPING, ComponentState.DEGRADED, ComponentState.FAILED},
    ComponentState.DEGRADED: {ComponentState.STOPPING, ComponentState.RUNNING, ComponentState.FAILED},
    ComponentState.STOPPING: {ComponentState.STOPPED, ComponentState.FAILED},
    ComponentState.STOPPED: {ComponentState.STARTING},
    ComponentState.FAILED: {ComponentState.STARTING},
}


class BaseComponent(ABC):
    def __init__(self, metadata: ComponentMetadata, config: ComponentConfig, event_bus, platform_layer):
        self.metadata = metadata
        self.config = config
        self.event_bus = event_bus
        self.platform_layer = platform_layer
        self._state = ComponentState.REGISTERED

    @property
    def state(self) -> ComponentState:
        return self._state

    @property
    def name(self) -> str:
        return self.metadata.name

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        ...

    async def on_event(self, event: Event) -> None:
        return None

    def emit(self, event_type: str, payload: dict, **kwargs) -> None:
        async def _emit() -> None:
            if getattr(self.event_bus, "is_running", False):
                await self.event_bus.publish(Event.create(source=self.name, type=event_type, payload=payload, **kwargs))

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        asyncio.create_task(_emit())

    def _set_state(self, new_state: ComponentState) -> None:
        if self._state == new_state:
            return
        allowed = LEGAL_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid state transition for {self.name}: {self._state.value} -> {new_state.value}",
                details={"from": self._state.value, "to": new_state.value, "component": self.name},
            )
        old = self._state
        self._state = new_state
        self.emit(
            "component.lifecycle.state_changed",
            {"component": self.name, "from": old.value, "to": new_state.value},
        )
