from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from core_framework.events.bus import EventBus
from core_framework.events.schema import PrivacyClass
from core_framework.platform.base import BasePlatformLayer

from memory_system.archival import ArchivalStore
from memory_system.consolidation import ConsolidationScheduler
from memory_system.episodic import EpisodicStore
from memory_system.models import EpisodicFragment, RetrievalResult, SemanticFact
from memory_system.semantic import SemanticStore
from memory_system.thoughtlog import ThoughtLog


class MemorySystem:
    def __init__(self, config: dict, event_bus: EventBus, platform_layer: BasePlatformLayer):
        self.config = config or {}
        self.event_bus = event_bus
        self.platform_layer = platform_layer

        self.episodic_store = EpisodicStore(self.config, event_bus, platform_layer)
        self.semantic_store = SemanticStore(self.config, event_bus, platform_layer)
        self.archival_store = ArchivalStore(self.config, event_bus, platform_layer)
        self.thought_log = ThoughtLog(self.config, event_bus, platform_layer)
        self.consolidation_scheduler = ConsolidationScheduler(
            self.config,
            event_bus,
            platform_layer,
            self.episodic_store,
            self.semantic_store,
            self.archival_store,
            self.thought_log,
        )

    def get_components(self) -> list:
        return [
            self.episodic_store,
            self.semantic_store,
            self.archival_store,
            self.thought_log,
            self.consolidation_scheduler,
        ]

    async def store_episode(
        self,
        text: str,
        source_interface: str,
        privacy_class: PrivacyClass,
        emotional_tag: dict[str, float] = {},
    ) -> str:
        fragment = EpisodicFragment(
            fragment_id=str(uuid4()),
            text=text,
            timestamp=datetime.now(timezone.utc),
            source_interface=source_interface,
            privacy_class=privacy_class,
            emotional_tag=emotional_tag,
        )
        return await self.episodic_store.store(fragment)

    async def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        import time

        start = time.perf_counter()
        fragments = await self.episodic_store.retrieve(query=query, top_k=top_k)
        facts = await self.semantic_store.get_all_facts()
        latency_ms = (time.perf_counter() - start) * 1000
        return RetrievalResult(fragments=fragments, facts=facts, retrieval_latency_ms=latency_ms)

    async def store_fact(self, key: str, value: str, confidence: float, provenance: str) -> None:
        now = datetime.now(timezone.utc)
        await self.semantic_store.store_fact(
            SemanticFact(
                fact_id=str(uuid4()),
                key=key,
                value=value,
                confidence=confidence,
                provenance=provenance,
                created_at=now,
                last_confirmed_at=now,
            )
        )

    async def get_fact(self, key: str) -> SemanticFact | None:
        return await self.semantic_store.get_fact(key)

    async def get_user_profile(self) -> dict[str, str]:
        return await self.semantic_store.get_user_profile()

    async def set_readonly(self, readonly: bool) -> None:
        await self.semantic_store.set_readonly(readonly)
        self.episodic_store.set_readonly(readonly)
