import asyncio

import pytest

from core_framework.config.schema import EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.events.schema import Event, PrivacyClass


@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus(EventBusConfig())
    await bus.start()
    events = []

    async def handler(event):
        events.append(event.type)

    bus.subscribe("test.*", handler)
    await bus.publish(Event.create("test", "test.one", {}))
    await asyncio.sleep(0.05)
    assert "test.one" in events
    await bus.stop()


@pytest.mark.asyncio
async def test_wildcard_matching():
    bus = EventBus(EventBusConfig())
    await bus.start()
    events = []

    async def handler(event):
        events.append(event.type)

    bus.subscribe("hardware.*", handler)
    await bus.publish(Event.create("s", "hardware.cpu.spike", {}))
    await bus.publish(Event.create("s", "software.update", {}))
    await asyncio.sleep(0.05)
    assert events == ["hardware.cpu.spike"]
    await bus.stop()


@pytest.mark.asyncio
async def test_prohibited_blocking():
    bus = EventBus(EventBusConfig())
    await bus.start()
    seen = []

    async def handler(event):
        seen.append(event)

    bus.subscribe("*", handler)
    await bus.publish(Event.create("s", "x.y", {}, privacy_class=PrivacyClass.PROHIBITED))
    await asyncio.sleep(0.05)
    assert len(seen) == 0
    await bus.stop()


@pytest.mark.asyncio
async def test_subscriber_exception_isolated():
    bus = EventBus(EventBusConfig())
    await bus.start()
    seen = []

    async def bad(_event):
        raise RuntimeError("boom")

    async def good(event):
        seen.append(event.type)

    bus.subscribe("*", bad)
    bus.subscribe("*", good)
    await bus.publish(Event.create("s", "alpha", {}))
    await asyncio.sleep(0.05)
    assert seen == ["alpha"]
    await bus.stop()


@pytest.mark.asyncio
async def test_history_replay():
    bus = EventBus(EventBusConfig())
    await bus.start()
    await bus.publish(Event.create("s", "replay.one", {}))
    await bus.publish(Event.create("s", "replay.two", {}))
    await asyncio.sleep(0.05)

    seen = []

    async def handler(event):
        seen.append(event.type)

    bus.subscribe("replay.*", handler, replay_last=2)
    await asyncio.sleep(0.05)
    assert seen == ["replay.one", "replay.two"]
    await bus.stop()
