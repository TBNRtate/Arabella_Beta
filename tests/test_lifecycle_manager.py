import asyncio

import pytest

from core_framework.config.schema import ComponentConfig, CoreConfig, EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.exceptions import ComponentAlreadyRegisteredError, DependencyResolutionError
from core_framework.platform.linux import LinuxPlatformLayer
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from core_framework.registry.lifecycle import LifecycleManager


class TrackingComponent(BaseComponent):
    def __init__(self, *args, tracker: list[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.tracker = tracker

    async def start(self):
        await asyncio.sleep(0.01)
        self.tracker.append(f"start:{self.name}")
        self._set_state(ComponentState.RUNNING)

    async def stop(self):
        await asyncio.sleep(0.01)
        self.tracker.append(f"stop:{self.name}")
        self._set_state(ComponentState.STOPPED)

    async def health_check(self):
        return {"status": "ok", "details": self.name}


def build_component(name, deps, tracker):
    return TrackingComponent(
        ComponentMetadata(name=name, display_name=name, version="1.0.0", description=name, dependencies=deps),
        ComponentConfig(),
        EventBus(EventBusConfig()),
        LinuxPlatformLayer(),
        tracker=tracker,
    )


@pytest.mark.asyncio
async def test_register_and_collision():
    bus = EventBus(EventBusConfig())
    await bus.start()
    lm = LifecycleManager(CoreConfig(), bus)
    t = []
    a = build_component("a", [], t)
    lm.register(a)
    with pytest.raises(ComponentAlreadyRegisteredError):
        lm.register(a)
    await bus.stop()


@pytest.mark.asyncio
async def test_startup_shutdown_dependency_order():
    bus = EventBus(EventBusConfig())
    await bus.start()
    lm = LifecycleManager(CoreConfig(), bus)
    tracker = []
    a = build_component("a", [], tracker)
    b = build_component("b", ["a"], tracker)
    lm.register(a)
    lm.register(b)

    await lm.start_all()
    assert tracker.index("start:a") < tracker.index("start:b")

    await lm.stop_all()
    assert tracker.index("stop:b") < tracker.index("stop:a")
    await bus.stop()


@pytest.mark.asyncio
async def test_cycle_detection():
    bus = EventBus(EventBusConfig())
    await bus.start()
    lm = LifecycleManager(CoreConfig(), bus)
    tracker = []
    a = build_component("a", ["b"], tracker)
    b = build_component("b", ["a"], tracker)
    lm.register(a)
    lm.register(b)

    with pytest.raises(DependencyResolutionError):
        await lm.start_all()
    await bus.stop()
