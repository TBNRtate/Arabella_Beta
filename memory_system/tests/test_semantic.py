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
async def test_semantic_store_roundtrip(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    store = SemanticStore({"db_path": str(tmp_path / "semantic.sqlite")}, bus, DummyPlatform())
    await store.start()

    now = datetime.now(timezone.utc)
    fact = SemanticFact(
        fact_id=str(uuid4()),
        key="user.name",
        value="Alice",
        confidence=0.9,
        provenance="user_stated",
        created_at=now,
        last_confirmed_at=now,
    )
    await store.store_fact(fact)

    retrieved = await store.get_fact("user.name")
    assert retrieved is not None
    assert retrieved.value == "Alice"
    assert retrieved.confidence == 0.9

    await store.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_semantic_readonly_blocks_writes(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    store = SemanticStore({"db_path": str(tmp_path / "semantic.sqlite")}, bus, DummyPlatform())
    await store.start()
    await store.set_readonly(True)

    now = datetime.now(timezone.utc)
    fact = SemanticFact(
        fact_id=str(uuid4()),
        key="user.city",
        value="Paris",
        confidence=0.7,
        provenance="conversation",
        created_at=now,
        last_confirmed_at=now,
    )

    with pytest.raises(PermissionError, match="SemanticStore is in read-only mode"):
        await store.store_fact(fact)

    await store.stop()
    await bus.stop()
