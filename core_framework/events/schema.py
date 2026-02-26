from __future__ import annotations

from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    DEBUG = 4


class PrivacyClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    PROHIBITED = "prohibited"


class Event(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    type: str
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL
    payload: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    correlation_id: str | None = None
    schema_version: str = "1.0"

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls.model_validate(d)

    def to_dict(self) -> dict:
        return self.model_dump(mode="python")

    @classmethod
    def create(cls, source: str, type: str, payload: dict[str, Any], **kwargs: Any) -> "Event":
        return cls(source=source, type=type, payload=payload, **kwargs)
