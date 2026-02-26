from __future__ import annotations

import json
from datetime import datetime

import aiosqlite

from core_framework.config.schema import ComponentConfig
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from memory_system.models import ArchivalEntry


class ArchivalStore(BaseComponent):
    def __init__(self, config: dict, event_bus, platform_layer):
        metadata = ComponentMetadata(
            name="archival_store",
            display_name="Archival Memory Store",
            version="0.1.0",
            description="SQLite-backed archival memory store",
            dependencies=[],
            tags=["memory"],
        )
        super().__init__(metadata=metadata, config=ComponentConfig(), event_bus=event_bus, platform_layer=platform_layer)
        self._cfg = config
        self._conn: aiosqlite.Connection | None = None

    async def start(self) -> None:
        self._set_state(ComponentState.STARTING)
        db_path = self._cfg.get("db_path", "archival_memory.sqlite")
        self._conn = await aiosqlite.connect(db_path)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS archival_entries (
                entry_id TEXT PRIMARY KEY,
                summary_text TEXT NOT NULL,
                source_fragment_ids TEXT NOT NULL,
                timestamp_range_start TEXT NOT NULL,
                timestamp_range_end TEXT NOT NULL,
                emotional_summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await self._conn.commit()
        self._set_state(ComponentState.RUNNING)

    async def stop(self) -> None:
        self._set_state(ComponentState.STOPPING)
        if self._conn is not None:
            await self._conn.close()
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok", "count": await self.get_count()}

    async def store(self, entry: ArchivalEntry) -> None:
        await self._conn.execute(
            """
            INSERT INTO archival_entries(
                entry_id, summary_text, source_fragment_ids,
                timestamp_range_start, timestamp_range_end,
                emotional_summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.entry_id,
                entry.summary_text,
                json.dumps(entry.source_fragment_ids),
                entry.timestamp_range_start.isoformat(),
                entry.timestamp_range_end.isoformat(),
                json.dumps(entry.emotional_summary),
                entry.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def get_all(self, limit: int = 100) -> list[ArchivalEntry]:
        cursor = await self._conn.execute(
            "SELECT * FROM archival_entries ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [
            ArchivalEntry(
                entry_id=row[0],
                summary_text=row[1],
                source_fragment_ids=json.loads(row[2]),
                timestamp_range_start=datetime.fromisoformat(row[3]),
                timestamp_range_end=datetime.fromisoformat(row[4]),
                emotional_summary=json.loads(row[5]),
                created_at=datetime.fromisoformat(row[6]),
            )
            for row in rows
        ]

    async def get_count(self) -> int:
        cursor = await self._conn.execute("SELECT COUNT(*) FROM archival_entries")
        count = int((await cursor.fetchone())[0])
        self.emit("memory.archival.count", {"count": count})
        return count
