from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from core_framework.config.schema import EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.platform.base import BasePlatformLayer, PlatformCapability
from memory_system.models import SemanticFact
from memory_system.semantic import SemanticStore


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
async def test_contradiction_detection(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    store = SemanticStore({"db_path": str(tmp_path / "semantic.sqlite")}, bus, DummyPlatform())
    await store.start()

    now = datetime.now(timezone.utc)
    first = SemanticFact(
        fact_id=str(uuid4()),
        key="user.city",
        value="Paris",
        confidence=0.8,
        provenance="user_stated",
        created_at=now,
        last_confirmed_at=now,
    )
    await store.store_fact(first)

    second = SemanticFact(
        fact_id=str(uuid4()),
        key="user.city",
        value="Berlin",
        confidence=0.7,
        provenance="conversation",
        created_at=now,
        last_confirmed_at=now,
    )
    await store.store_fact(second)

    old = [f for f in await store.get_all_facts("user.city") if f.fact_id == first.fact_id][0]
    assert old.contradiction_flag is True

    import asyncio

    await asyncio.sleep(0.05)
    history = bus.get_history("memory.contradiction.detected", limit=5)
    assert history
    assert history[-1].payload["key"] == "user.city"

    await store.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_contradiction_resolution(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    store = SemanticStore({"db_path": str(tmp_path / "semantic.sqlite")}, bus, DummyPlatform())
    await store.start()

    now = datetime.now(timezone.utc)
    first = SemanticFact(
        fact_id=str(uuid4()),
        key="user.pet",
        value="cat",
        confidence=0.8,
        provenance="user_stated",
        created_at=now,
        last_confirmed_at=now,
    )
    second = SemanticFact(
        fact_id=str(uuid4()),
        key="user.pet",
        value="dog",
        confidence=0.7,
        provenance="conversation",
        created_at=now,
        last_confirmed_at=now,
    )
    await store.store_fact(first)
    await store.store_fact(second)

    await store.contradiction_handler.resolve(second.fact_id, first.fact_id, "manual")

    facts = {f.fact_id: f for f in await store.get_all_facts("user.pet")}
    assert facts[second.fact_id].contradiction_flag is False
    assert facts[first.fact_id].contradiction_flag is True

    await store.stop()
    await bus.stop()
