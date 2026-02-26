import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from core_framework.config.schema import ComponentConfig, EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.events.schema import Event, PrivacyClass
from observability.collector import MetricsCollector
from observability import metrics


class _ConfigManagerStub:
    def __init__(self, extension=None):
        self._extension = extension or {"prometheus_port": 9100, "poll_interval_seconds": 1}

    def get_extension(self, namespace: str):
        if namespace == "observability":
            return self._extension
        return {}


@pytest.mark.asyncio
async def test_metrics_collector_subscribes():
    bus = EventBus(EventBusConfig())
    await bus.start()
    collector = MetricsCollector(ComponentConfig(), bus, None, _ConfigManagerStub())
    await collector.start()

    await bus.publish(
        Event.create(
            "tester",
            "hardware.status",
            {
                "cpu_percent": 33.0,
                "ram_percent": 71.0,
                "ram_used_bytes": 2048,
                "disk_read_bytes_sec": 11,
                "disk_write_bytes_sec": 12,
                "net_sent_bytes_sec": 13,
                "net_recv_bytes_sec": 14,
            },
        )
    )
    await asyncio.sleep(0.05)

    assert metrics.cpu_usage_percent._value.get() == 33.0
    assert metrics.ram_usage_percent._value.get() == 71.0
    assert metrics.ram_used_bytes._value.get() == 2048.0

    await collector.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_prohibited_events_ignored():
    bus = EventBus(EventBusConfig())
    await bus.start()
    collector = MetricsCollector(ComponentConfig(), bus, None, _ConfigManagerStub())
    await collector.start()

    before = metrics.cpu_usage_percent._value.get()
    await bus.publish(
        Event.create(
            "tester",
            "hardware.status",
            {"cpu_percent": 99},
            privacy_class=PrivacyClass.PROHIBITED,
        )
    )
    await asyncio.sleep(0.05)

    assert metrics.cpu_usage_percent._value.get() == before

    await collector.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_emotion_event_updates_gauges():
    bus = EventBus(EventBusConfig())
    await bus.start()
    collector = MetricsCollector(ComponentConfig(), bus, None, _ConfigManagerStub())
    await collector.start()

    await bus.publish(
        Event.create(
            "tester",
            "mind.emotion.state_update",
            {"emotions": {"joy": 0.8, "trust": 0.6}},
        )
    )
    await asyncio.sleep(0.05)

    assert metrics.emotion_joy._value.get() == 0.8

    await collector.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_tool_event_increments_counters():
    bus = EventBus(EventBusConfig())
    await bus.start()
    collector = MetricsCollector(ComponentConfig(), bus, None, _ConfigManagerStub())
    await collector.start()

    attempted = metrics.tool_calls_attempted_total.labels("search")
    succeeded = metrics.tool_calls_succeeded_total.labels("search")
    before_attempted = attempted._value.get()
    before_succeeded = succeeded._value.get()

    await bus.publish(Event.create("tester", "tool.execution.announced", {"tool_name": "search"}))
    await bus.publish(Event.create("tester", "tool.execution.complete", {"tool_name": "search"}))
    await asyncio.sleep(0.05)

    assert attempted._value.get() == before_attempted + 1
    assert succeeded._value.get() == before_succeeded + 1

    await collector.stop()
    await bus.stop()
