from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from core_framework.config.schema import ComponentConfig
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from memory_system.models import SemanticFact


class SemanticStore(BaseComponent):
    def __init__(self, config: dict, event_bus, platform_layer):
        metadata = ComponentMetadata(
            name="semantic_store",
            display_name="Semantic Memory Store",
            version="0.1.0",
            description="SQLite-backed semantic facts store",
            dependencies=[],
            tags=["memory"],
        )
        super().__init__(metadata=metadata, config=ComponentConfig(), event_bus=event_bus, platform_layer=platform_layer)
        self._cfg = config
        self._conn: aiosqlite.Connection | None = None
        self._readonly = False
        self.contradiction_handler = None

    async def start(self) -> None:
        from memory_system.contradiction import ContradictionHandler

        self._set_state(ComponentState.STARTING)
        db_path = self._cfg.get("db_path", "semantic_memory.sqlite")
        self._conn = await aiosqlite.connect(db_path)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                provenance TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_confirmed_at TEXT NOT NULL,
                contradiction_flag INTEGER NOT NULL DEFAULT 0,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key)")
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                profile_key TEXT PRIMARY KEY,
                profile_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await self._conn.commit()
        self.contradiction_handler = ContradictionHandler(self)
        self._set_state(ComponentState.RUNNING)

    async def stop(self) -> None:
        self._set_state(ComponentState.STOPPING)
        if self._conn is not None:
            await self._conn.close()
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok", "readonly": self._readonly}

    async def set_readonly(self, readonly: bool) -> None:
        self._readonly = readonly

    def _check_writable(self) -> None:
        if self._readonly:
            raise PermissionError("SemanticStore is in read-only mode")

    async def store_fact(self, fact: SemanticFact) -> None:
        self._check_writable()
        await self.contradiction_handler.check_and_flag(fact.key, fact.value)
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO facts(
                fact_id, key, value, confidence, provenance, created_at,
                last_confirmed_at, contradiction_flag, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact.fact_id,
                fact.key,
                fact.value,
                fact.confidence,
                fact.provenance,
                fact.created_at.isoformat(),
                fact.last_confirmed_at.isoformat(),
                int(fact.contradiction_flag),
                json.dumps(fact.metadata),
            ),
        )
        await self._conn.commit()

    async def get_fact(self, key: str) -> SemanticFact | None:
        cursor = await self._conn.execute(
            "SELECT * FROM facts WHERE key = ? ORDER BY last_confirmed_at DESC LIMIT 1", (key,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_fact(row)

    async def get_all_facts(self, key_prefix: str | None = None) -> list[SemanticFact]:
        if key_prefix:
            cursor = await self._conn.execute(
                "SELECT * FROM facts WHERE key LIKE ? ORDER BY last_confirmed_at DESC", (f"{key_prefix}%",)
            )
        else:
            cursor = await self._conn.execute("SELECT * FROM facts ORDER BY last_confirmed_at DESC")
        rows = await cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    async def update_confidence(self, fact_id: str, confidence: float) -> None:
        self._check_writable()
        await self._conn.execute("UPDATE facts SET confidence = ? WHERE fact_id = ?", (confidence, fact_id))
        await self._conn.commit()

    async def flag_contradiction(self, fact_id: str) -> None:
        self._check_writable()
        await self._conn.execute("UPDATE facts SET contradiction_flag = 1 WHERE fact_id = ?", (fact_id,))
        await self._conn.commit()

    async def clear_contradiction(self, fact_id: str) -> None:
        self._check_writable()
        await self._conn.execute("UPDATE facts SET contradiction_flag = 0 WHERE fact_id = ?", (fact_id,))
        await self._conn.commit()

    async def touch_last_confirmed(self, fact_id: str) -> None:
        self._check_writable()
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute("UPDATE facts SET last_confirmed_at = ? WHERE fact_id = ?", (now, fact_id))
        await self._conn.commit()

    async def get_user_profile(self) -> dict[str, str]:
        cursor = await self._conn.execute("SELECT profile_key, profile_value FROM user_profile")
        rows = await cursor.fetchall()
        return {k: v for k, v in rows}

    async def set_profile_value(self, key: str, value: str) -> None:
        self._check_writable()
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """
            INSERT INTO user_profile(profile_key, profile_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(profile_key) DO UPDATE SET profile_value = excluded.profile_value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        await self._conn.commit()

    def _row_to_fact(self, row) -> SemanticFact:
        return SemanticFact(
            fact_id=row[0],
            key=row[1],
            value=row[2],
            confidence=float(row[3]),
            provenance=row[4],
            created_at=datetime.fromisoformat(row[5]),
            last_confirmed_at=datetime.fromisoformat(row[6]),
            contradiction_flag=bool(row[7]),
            metadata=json.loads(row[8]),
        )
