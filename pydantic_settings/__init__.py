from __future__ import annotations

import os

from pydantic import BaseModel


class SettingsConfigDict(dict):
    pass


class BaseSettings(BaseModel):
    model_config = SettingsConfigDict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def model_dump(self, exclude_none=False):
        prefix = self.model_config.get("env_prefix", "")
        delim = self.model_config.get("env_nested_delimiter", "__")
        parsed = {}
        for k, v in os.environ.items():
            if not k.startswith(prefix):
                continue
            key = k[len(prefix) :].lower()
            parts = key.split(delim.lower())
            cursor = parsed
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            val = v
            if isinstance(val, str) and val.lower() in {"true", "false"}:
                val = val.lower() == "true"
            elif isinstance(val, str) and val.isdigit():
                val = int(val)
            cursor[parts[-1]] = val
        if exclude_none:
            return {k: v for k, v in parsed.items() if v is not None}
        return parsed
