from __future__ import annotations

import os
from dataclasses import MISSING, dataclass, field
from typing import Any, Dict, get_args, get_origin, get_type_hints


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
    def _coerce_value(cls, annotation, value):
        origin = get_origin(annotation)
        args = get_args(annotation)

        if isinstance(annotation, type) and issubclass(annotation, BaseModel) and isinstance(value, dict):
            return annotation.model_validate(value)

        if origin in {dict, Dict} and args and len(args) == 2 and isinstance(value, dict):
            _, val_t = args
            if isinstance(val_t, type) and issubclass(val_t, BaseModel):
                return {
                    k: (v if isinstance(v, val_t) else val_t.model_validate(v) if isinstance(v, dict) else v)
                    for k, v in value.items()
                }
        return value

    @classmethod
    def model_validate(cls, data: dict):
        try:
            coerced = dict(data)
            for field_name, annotation in get_type_hints(cls).items():
                if field_name in coerced:
                    coerced[field_name] = cls._coerce_value(annotation, coerced[field_name])
            return cls(**coerced)
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
