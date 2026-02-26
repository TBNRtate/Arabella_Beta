from dataclasses import dataclass
import os


def cpu_count():
    return os.cpu_count() or 1


@dataclass
class _VMem:
    total: int


def virtual_memory():
    return _VMem(total=8 * 1024 * 1024 * 1024)
