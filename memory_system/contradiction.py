from __future__ import annotations

from core_framework.events.schema import Event


class ContradictionHandler:
    def __init__(self, semantic_store):
        self.semantic_store = semantic_store

    async def check_and_flag(self, key: str, new_value: str) -> bool:
        existing_fact = await self.semantic_store.get_fact(key)
        if existing_fact is None:
            return False
        if existing_fact.value == new_value:
            return False
        await self.semantic_store.flag_contradiction(existing_fact.fact_id)
        if self.semantic_store.event_bus.is_running:
            await self.semantic_store.event_bus.publish(
                Event.create(
                    source="semantic_store",
                    type="memory.contradiction.detected",
                    payload={"key": key, "existing": existing_fact.value, "new": new_value},
                )
            )
        return True

    async def resolve(self, fact_id_keep: str, fact_id_discard: str, resolution_method: str) -> None:
        await self.semantic_store.clear_contradiction(fact_id_keep)
        await self.semantic_store.touch_last_confirmed(fact_id_keep)
        if self.semantic_store.event_bus.is_running:
            await self.semantic_store.event_bus.publish(
                Event.create(
                    source="semantic_store",
                    type="memory.contradiction.resolved",
                    payload={
                        "fact_id_keep": fact_id_keep,
                        "fact_id_discard": fact_id_discard,
                        "resolution_method": resolution_method,
                    },
                )
            )
