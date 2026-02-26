from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Value:
    _v: float = 0.0

    def get(self) -> float:
        return self._v

    def set(self, value: float) -> None:
        self._v = float(value)

    def inc(self, amount: float = 1.0) -> None:
        self._v += float(amount)


class _MetricBase:
    def __init__(self, name: str, documentation: str, labelnames: list[str] | tuple[str, ...] | None = None):
        self.name = name
        self.documentation = documentation
        self._labelnames = tuple(labelnames or ())
        self._value = _Value()
        self._children: dict[tuple[str, ...], _MetricBase] = {}

    def labels(self, *labelvalues: str, **labels: str):
        if labels:
            labelvalues = tuple(labels[name] for name in self._labelnames)
        if len(labelvalues) != len(self._labelnames):
            raise ValueError("Incorrect label count")
        key = tuple(str(v) for v in labelvalues)
        if key not in self._children:
            child = self.__class__(self.name, self.documentation, self._labelnames)
            self._children[key] = child
        return self._children[key]


class Gauge(_MetricBase):
    def set(self, value: float) -> None:
        self._value.set(value)


class Counter(_MetricBase):
    def inc(self, amount: float = 1.0) -> None:
        self._value.inc(amount)



def start_http_server(_port: int) -> None:
    return None
