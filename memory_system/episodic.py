from __future__ import annotations

import json
import time
from datetime import datetime
from uuid import uuid4

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from core_framework.config.schema import ComponentConfig
from core_framework.events.schema import PrivacyClass
from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from memory_system.models import EpisodicFragment


class EpisodicStore(BaseComponent):
    def __init__(self, config: dict, event_bus, platform_layer):
        metadata = ComponentMetadata(
            name="episodic_store",
            display_name="Episodic Memory Store",
            version="0.1.0",
            description="Vector-backed episodic memory store",
            dependencies=[],
            tags=["memory"],
        )
        super().__init__(metadata=metadata, config=ComponentConfig(), event_bus=event_bus, platform_layer=platform_layer)
        self._cfg = config
        self._client = None
        self._collection = None
        self._readonly = False

    async def start(self) -> None:
        self._set_state(ComponentState.STARTING)
        store_path = self._cfg.get("store_path", ".memory_chroma")
        embedding_fn = self._cfg.get("embedding_function") or DefaultEmbeddingFunction()
        self._client = chromadb.PersistentClient(path=store_path)
        self._collection = self._client.get_or_create_collection("episodic_memory", embedding_function=embedding_fn)
        self._set_state(ComponentState.RUNNING)
        self.emit("memory.episodic.ready", {"collection": "episodic_memory"})

    async def stop(self) -> None:
        self._set_state(ComponentState.STOPPING)
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok", "count": await self.get_count()}

    def set_readonly(self, readonly: bool) -> None:
        self._readonly = readonly

    async def store(self, fragment: EpisodicFragment) -> str:
        if self._readonly:
            raise PermissionError("EpisodicStore is in read-only mode")
        if fragment.privacy_class == PrivacyClass.PROHIBITED:
            raise ValueError("Cannot store PROHIBITED content")
        metadata = {
            "timestamp": fragment.timestamp.isoformat(),
            "source_interface": fragment.source_interface,
            "privacy_class": fragment.privacy_class.value,
            "cluster_id": fragment.cluster_id or "",
            "emotional_tag": json.dumps(fragment.emotional_tag),
            "metadata": json.dumps(fragment.metadata),
        }
        self._collection.add(documents=[fragment.text], ids=[fragment.fragment_id], metadatas=[metadata])
        self.emit("memory.store.write", {"fragment_id": fragment.fragment_id, "source": fragment.source_interface})
        return fragment.fragment_id

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        privacy_filter: set[PrivacyClass] | None = None,
    ) -> list[EpisodicFragment]:
        start = time.perf_counter()
        result = self._collection.query(query_texts=[query], n_results=top_k)
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]

        fragments: list[EpisodicFragment] = []
        for fid, text, meta in zip(ids, documents, metadatas, strict=False):
            privacy = PrivacyClass(meta.get("privacy_class", PrivacyClass.INTERNAL.value))
            if privacy_filter and privacy not in privacy_filter:
                continue
            fragments.append(
                EpisodicFragment(
                    fragment_id=fid,
                    text=text,
                    timestamp=datetime.fromisoformat(meta["timestamp"]),
                    source_interface=meta.get("source_interface", "internal"),
                    privacy_class=privacy,
                    cluster_id=meta.get("cluster_id") or None,
                    emotional_tag=json.loads(meta.get("emotional_tag", "{}")),
                    metadata=json.loads(meta.get("metadata", "{}")),
                )
            )
        latency_ms = (time.perf_counter() - start) * 1000
        self.emit("memory.retrieve.complete", {"latency_ms": latency_ms, "count": len(fragments)})
        return fragments

    async def delete(self, fragment_id: str) -> None:
        self._collection.delete(ids=[fragment_id])

    async def get_count(self) -> int:
        return int(self._collection.count())

    async def get_recent(self, limit: int = 20) -> list[EpisodicFragment]:
        result = self._collection.get(include=["documents", "metadatas"])
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        fragments: list[EpisodicFragment] = []
        for fid, text, meta in zip(ids, documents, metadatas, strict=False):
            fragments.append(
                EpisodicFragment(
                    fragment_id=fid,
                    text=text,
                    timestamp=datetime.fromisoformat(meta["timestamp"]),
                    source_interface=meta.get("source_interface", "internal"),
                    privacy_class=PrivacyClass(meta.get("privacy_class", PrivacyClass.INTERNAL.value)),
                    cluster_id=meta.get("cluster_id") or None,
                    emotional_tag=json.loads(meta.get("emotional_tag", "{}")),
                    metadata=json.loads(meta.get("metadata", "{}")),
                )
            )
        fragments.sort(key=lambda f: f.timestamp, reverse=True)
        return fragments[:limit]


__all__ = ["EpisodicStore", "EpisodicFragment", "PrivacyClass", "uuid4"]
