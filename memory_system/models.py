from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core_framework.events.schema import PrivacyClass


class EpisodicFragment(BaseModel):
    fragment_id: str
    text: str
    timestamp: datetime
    source_interface: str
    privacy_class: PrivacyClass
    emotional_tag: dict[str, float] = Field(default_factory=dict)
    cluster_id: str | None = None
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticFact(BaseModel):
    fact_id: str
    key: str
    value: str
    confidence: float
    provenance: str
    created_at: datetime
    last_confirmed_at: datetime
    contradiction_flag: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchivalEntry(BaseModel):
    entry_id: str
    summary_text: str
    source_fragment_ids: list[str]
    timestamp_range_start: datetime
    timestamp_range_end: datetime
    emotional_summary: dict[str, float]
    created_at: datetime


class ThoughtEvent(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryWriteIntent(BaseModel):
    text: str
    source_interface: str
    privacy_class: PrivacyClass
    emotional_tag: dict[str, float] = Field(default_factory=dict)
    suggested_facts: list[dict[str, Any]] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    fragments: list[EpisodicFragment]
    facts: list[SemanticFact]
    retrieval_latency_ms: float
