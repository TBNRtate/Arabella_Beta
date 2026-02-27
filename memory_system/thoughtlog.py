from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

import aiosqlite

from core_framework.config.schema import ComponentConfig
from core_framework.events.schema import Event
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from memory_system.models import ThoughtEvent


class ThoughtLog(BaseComponent):
    def __init__(self, config: dict, event_bus, platform_layer):
        metadata = ComponentMetadata(
            name="thought_log",
            display_name="Thought Log",
            version="0.1.0",
            description="Append-only thought/event log",
            dependencies=[],
            tags=["memory"],
        )
        super().__init__(metadata=metadata, config=ComponentConfig(), event_bus=event_bus, platform_layer=platform_layer)
        self._cfg = config
        self._conn: aiosqlite.Connection | None = None
        self._subs: list[str] = []

    async def start(self) -> None:
        self._set_state(ComponentState.STARTING)
        db_path = self._cfg.get("db_path", "thought_log.sqlite")
        self._conn = await aiosqlite.connect(db_path)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS thought_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_type ON thought_events(event_type)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_time ON thought_events(timestamp)")
        await self._conn.commit()
        self._subs = [
            self.event_bus.subscribe("tool.*", self._handle_bus_event),
            self.event_bus.subscribe("memory.*", self._handle_bus_event),
            self.event_bus.subscribe("conversation.*", self._handle_bus_event),
        ]
        self._set_state(ComponentState.RUNNING)

    async def stop(self) -> None:
        self._set_state(ComponentState.STOPPING)
        for sub in self._subs:
            self.event_bus.unsubscribe(sub)
        if self._conn is not None:
            await self._conn.close()
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok"}

    async def log(self, event: ThoughtEvent) -> None:
        await self._conn.execute(
            "INSERT INTO thought_events(event_id, timestamp, event_type, content, metadata) VALUES (?, ?, ?, ?, ?)",
            (event.event_id, event.timestamp.isoformat(), event.event_type, event.content, json.dumps(event.metadata)),
        )
        await self._conn.commit()

    async def _handle_bus_event(self, event: Event) -> None:
        event_type = None
        content = ""
        if event.type == "tool.execution.announced":
            event_type = "tool_call"
            content = f"Tool announced: {event.payload.get('command', '')}"
        elif event.type == "memory.store.write":
            event_type = "memory_write"
            content = f"Fragment stored: {event.payload.get('fragment_id', '')}"
        elif event.type == "memory.retrieve.complete":
            event_type = "memory_retrieve"
            content = f"Retrieved {event.payload.get('count', 0)} fragments"
        elif event.type == "memory.consolidation.begin":
            event_type = "consolidation"
            content = "Consolidation cycle started"
        elif event.type == "memory.contradiction.detected":
            event_type = "contradiction"
            content = f"Contradiction at key: {event.payload.get('key', '')}"
        elif event.type == "conversation.turn.complete":
            event_type = "conversation_turn"
            content = f"Turn complete, session: {event.payload.get('session_id', '')}"

        if event_type is None:
            return
        await self.log(
            ThoughtEvent(
                event_id=str(uuid4()),
                timestamp=event.timestamp,
                event_type=event_type,
                content=content,
                metadata=event.payload,
            )
        )

    async def get_recent(self, limit: int = 100, event_type: str | None = None) -> list[ThoughtEvent]:
        if event_type:
            cursor = await self._conn.execute(
                "SELECT event_id, timestamp, event_type, content, metadata FROM thought_events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT event_id, timestamp, event_type, content, metadata FROM thought_events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [
            ThoughtEvent(
                event_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                event_type=row[2],
                content=row[3],
                metadata=json.loads(row[4]),
            )
            for row in rows
        ]
