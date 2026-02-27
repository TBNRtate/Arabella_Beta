from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from core_framework.config.schema import EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.events.schema import Event
from core_framework.events.schema import PrivacyClass
from core_framework.platform.base import BasePlatformLayer, PlatformCapability
from memory_system.archival import ArchivalStore
from memory_system.consolidation import ConsolidationScheduler
from memory_system.episodic import EpisodicStore
from memory_system.models import EpisodicFragment, ThoughtEvent
from memory_system.thoughtlog import ThoughtLog


class DummyPlatform(BasePlatformLayer):
    @property
    def platform_name(self) -> str:
        return "dummy"

    def get_available_capabilities(self) -> set[PlatformCapability]:
        return set()

    def get_system_info(self) -> dict:
        return {}

    def get_ipc_socket_path(self) -> str:
        return ""

    def get_default_data_dir(self) -> Path:
        return Path(".")

    def get_default_config_dir(self) -> Path:
        return Path(".")

    def get_default_log_dir(self) -> Path:
        return Path(".")


@pytest.mark.asyncio
async def test_thoughtlog_append_only(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    thought_log = ThoughtLog({"db_path": str(tmp_path / "thought.sqlite")}, bus, DummyPlatform())
    await thought_log.start()

    await thought_log.log(
        ThoughtEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type="memory_write",
            content="Stored fragment",
            metadata={"a": 1},
        )
    )
    await thought_log.log(
        ThoughtEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type="memory_retrieve",
            content="Retrieved 1 fragment",
            metadata={},
        )
    )

    recent = await thought_log.get_recent(limit=10)
    assert len(recent) == 2
    assert not hasattr(thought_log, "delete")

    await thought_log.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_thoughtlog_bus_event_uses_unique_ids(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    thought_log = ThoughtLog({"db_path": str(tmp_path / "thought.sqlite")}, bus, DummyPlatform())
    await thought_log.start()

    bus_event = Event.create(
        source="tester",
        type="memory.store.write",
        payload={"fragment_id": "frag-1"},
    )

    await thought_log._handle_bus_event(bus_event)
    await thought_log._handle_bus_event(bus_event)

    recent = await thought_log.get_recent(limit=10, event_type="memory_write")
    assert len(recent) == 2
    assert recent[0].event_id != recent[1].event_id

    await thought_log.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_consolidation_cycle(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    platform = DummyPlatform()
    episodic = EpisodicStore({"store_path": str(tmp_path / "chroma")}, bus, platform)
    archival = ArchivalStore({"db_path": str(tmp_path / "archival.sqlite")}, bus, platform)
    thought_log = ThoughtLog({"db_path": str(tmp_path / "thought.sqlite")}, bus, platform)

    class DummySemantic:
        pass

    await episodic.start()
    await archival.start()
    await thought_log.start()

    base = datetime.now(timezone.utc)
    ids = []
    for idx in range(3):
        fid = str(uuid4())
        ids.append(fid)
        await episodic.store(
            EpisodicFragment(
                fragment_id=fid,
                text=f"event {idx}",
                timestamp=base + timedelta(minutes=idx * 10),
                source_interface="cli",
                privacy_class=PrivacyClass.INTERNAL,
            )
        )

    scheduler = ConsolidationScheduler(
        {"consolidation_batch_size": 10, "consolidation_idle_threshold_seconds": 9999},
        bus,
        platform,
        episodic,
        DummySemantic(),
        archival,
        thought_log,
    )
    await scheduler.start()
    await scheduler._run_consolidation_cycle()

    entries = await archival.get_all()
    assert entries
    assert set(entries[0].source_fragment_ids) == set(ids)

    await scheduler.stop()
    await thought_log.stop()
    await archival.stop()
    await episodic.stop()
    await bus.stop()
