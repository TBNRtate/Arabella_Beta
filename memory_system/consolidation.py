from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from core_framework.config.schema import ComponentConfig
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from memory_system.models import ArchivalEntry, ThoughtEvent


class ConsolidationScheduler(BaseComponent):
    def __init__(self, config: dict, event_bus, platform_layer, episodic_store, semantic_store, archival_store, thought_log):
        metadata = ComponentMetadata(
            name="consolidation_scheduler",
            display_name="Memory Consolidation Scheduler",
            version="0.1.0",
            description="Compresses episodic memory and promotes facts during idle periods",
            dependencies=["episodic_store", "semantic_store", "archival_store", "thought_log"],
            tags=["memory"],
        )
        super().__init__(metadata=metadata, config=ComponentConfig(), event_bus=event_bus, platform_layer=platform_layer)
        self._cfg = config
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store
        self.archival_store = archival_store
        self.thought_log = thought_log
        self._task: asyncio.Task | None = None
        self._subs: list[str] = []

    async def start(self) -> None:
        self._set_state(ComponentState.STARTING)
        self._subs = [
            self.event_bus.subscribe("session.idle", self._noop_event),
            self.event_bus.subscribe("conversation.turn.complete", self._noop_event),
        ]
        self._task = asyncio.create_task(self._idle_loop())
        self._set_state(ComponentState.RUNNING)

    async def _noop_event(self, event):
        return None

    async def stop(self) -> None:
        self._set_state(ComponentState.STOPPING)
        for sub in self._subs:
            self.event_bus.unsubscribe(sub)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok", "task_running": self._task is not None and not self._task.done()}

    async def _idle_loop(self) -> None:
        idle_threshold = int(self._cfg.get("consolidation_idle_threshold_seconds", 300))
        while True:
            await asyncio.sleep(idle_threshold)
            await self._run_consolidation_cycle()

    async def _run_consolidation_cycle(self) -> None:
        self.emit("memory.consolidation.begin", {})
        batch_size = int(self._cfg.get("consolidation_batch_size", 50))
        fragments = await self.episodic_store.get_recent(limit=batch_size)
        if not fragments:
            self.emit("memory.consolidation.complete", {"count": 0})
            return

        ascending = sorted(fragments, key=lambda x: x.timestamp)
        groups = []
        current = [ascending[0]]
        for fragment in ascending[1:]:
            delta = (fragment.timestamp - current[-1].timestamp).total_seconds()
            if delta <= 3600:
                current.append(fragment)
            else:
                groups.append(current)
                current = [fragment]
        groups.append(current)

        consolidated_count = 0
        for group in groups:
            summary_lines = [f"[{f.timestamp.isoformat()}] {f.text}" for f in group]
            summary_text = "\n".join(summary_lines)
            emotions: dict[str, float] = {}
            for f in group:
                for name, value in f.emotional_tag.items():
                    emotions[name] = emotions.get(name, 0.0) + value
            entry = ArchivalEntry(
                entry_id=str(uuid4()),
                summary_text=summary_text,
                source_fragment_ids=[f.fragment_id for f in group],
                timestamp_range_start=group[0].timestamp,
                timestamp_range_end=group[-1].timestamp,
                emotional_summary=emotions,
                created_at=datetime.now(timezone.utc),
            )
            await self.archival_store.store(entry)
            await self.thought_log.log(
                ThoughtEvent(
                    event_id=str(uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    event_type="consolidation",
                    content=f"Consolidated {len(group)} fragments",
                    metadata={"entry_id": entry.entry_id},
                )
            )
            consolidated_count += len(group)
        self.emit("memory.consolidation.complete", {"count": consolidated_count})
