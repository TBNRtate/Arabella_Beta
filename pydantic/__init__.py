from __future__ import annotations

import os
from dataclasses import MISSING, dataclass, field
from typing import Any, get_origin


class ValidationError(Exception):
    def __init__(self, errors_data):
        self._errors = errors_data
        super().__init__(str(errors_data))

    def errors(self):
        return self._errors


class ConfigDict(dict):
    pass


def Field(default=MISSING, default_factory=None):
    if default_factory is not None:
        return field(default_factory=default_factory)
    if default is not MISSING:
        return field(default=default)
    return field()


class BaseModel:
    model_config = ConfigDict()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        dataclass(cls)

    @classmethod
    def model_validate(cls, data: dict):
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValidationError([{"msg": str(exc)}]) from exc

    def model_dump(self, mode="python", exclude_none=False):
        out = {}
        for k, v in self.__dict__.items():
            if exclude_none and v is None:
                continue
            if isinstance(v, BaseModel):
                out[k] = v.model_dump(mode=mode, exclude_none=exclude_none)
            elif isinstance(v, dict):
                out[k] = {
                    ik: iv.model_dump(mode=mode, exclude_none=exclude_none) if isinstance(iv, BaseModel) else iv
                    for ik, iv in v.items()
                }
            else:
                out[k] = v
        return out
