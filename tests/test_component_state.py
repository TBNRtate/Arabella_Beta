import pytest

from core_framework.config.schema import ComponentConfig, EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.exceptions import InvalidStateTransitionError
from core_framework.platform.linux import LinuxPlatformLayer
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState


class DummyComponent(BaseComponent):
    async def start(self):
        self._set_state(ComponentState.RUNNING)

    async def stop(self):
        self._set_state(ComponentState.STOPPED)

    async def health_check(self):
        return {"status": "ok", "details": "ok"}


def make_component():
    return DummyComponent(
        ComponentMetadata(name="dummy", display_name="Dummy", version="1.0.0", description="d"),
        ComponentConfig(),
        EventBus(EventBusConfig()),
        LinuxPlatformLayer(),
    )


def test_legal_transitions():
    c = make_component()
    c._set_state(ComponentState.STARTING)
    c._set_state(ComponentState.RUNNING)
    c._set_state(ComponentState.DEGRADED)
    c._set_state(ComponentState.RUNNING)
    c._set_state(ComponentState.STOPPING)
    c._set_state(ComponentState.STOPPED)
    c._set_state(ComponentState.STARTING)
    c._set_state(ComponentState.FAILED)
    c._set_state(ComponentState.STARTING)


def test_illegal_transition_raises():
    c = make_component()
    with pytest.raises(InvalidStateTransitionError):
        c._set_state(ComponentState.RUNNING)
