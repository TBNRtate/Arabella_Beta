"""Minimal YAML compatibility shim for offline test environments."""

import json
from typing import Any


def safe_load(data) -> Any:
    if hasattr(data, "read"):
        data = data.read()
    data = data.strip()
    if not data:
        return None
    return json.loads(data)


def safe_dump(data: Any, stream=None, sort_keys: bool = False) -> str:
    text = json.dumps(data, indent=2, sort_keys=sort_keys)
    if stream is not None:
        stream.write(text)
        return ""
    return text
