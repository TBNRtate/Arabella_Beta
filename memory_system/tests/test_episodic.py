from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from core_framework.config.schema import EventBusConfig
from core_framework.events.bus import EventBus
from core_framework.events.schema import PrivacyClass
from core_framework.platform.base import BasePlatformLayer, PlatformCapability
from memory_system.episodic import EpisodicStore
from memory_system.models import EpisodicFragment


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
async def test_episodic_store_roundtrip(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    store = EpisodicStore({"store_path": str(tmp_path / "chroma")}, bus, DummyPlatform())
    await store.start()

    fragment = EpisodicFragment(
        fragment_id=str(uuid4()),
        text="Alice likes coffee",
        timestamp=datetime.now(timezone.utc),
        source_interface="cli",
        privacy_class=PrivacyClass.INTERNAL,
        emotional_tag={"joy": 0.6},
        metadata={"topic": "preference"},
    )
    await store.store(fragment)
    results = await store.retrieve("coffee")

    assert results
    assert results[0].text == fragment.text
    assert results[0].source_interface == "cli"
    assert results[0].metadata["topic"] == "preference"

    await store.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_episodic_prohibited_rejected(tmp_path):
    bus = EventBus(EventBusConfig())
    await bus.start()
    store = EpisodicStore({"store_path": str(tmp_path / "chroma")}, bus, DummyPlatform())
    await store.start()

    fragment = EpisodicFragment(
        fragment_id=str(uuid4()),
        text="do not store",
        timestamp=datetime.now(timezone.utc),
        source_interface="api",
        privacy_class=PrivacyClass.PROHIBITED,
        emotional_tag={},
    )
    with pytest.raises(ValueError, match="Cannot store PROHIBITED content"):
        await store.store(fragment)

    await store.stop()
    await bus.stop()
