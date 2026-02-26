import asyncio
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark async test")


def pytest_pyfunc_call(pyfuncitem):
    if "asyncio" in pyfuncitem.keywords and inspect.iscoroutinefunction(pyfuncitem.function):
        asyncio.run(pyfuncitem.obj(**pyfuncitem.funcargs))
        return True
    return None
