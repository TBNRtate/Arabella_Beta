from __future__ import annotations

import asyncio
import signal
from pathlib import Path

from core_framework.config.manager import ConfigManager
from core_framework.config.schema import CoreConfig
from core_framework.events.bus import EventBus
from core_framework.logging.setup import get_logger, setup_logging
from core_framework.platform.base import BasePlatformLayer
from core_framework.platform.detector import PlatformDetector
from core_framework.registry.component import BaseComponent
from core_framework.registry.lifecycle import LifecycleManager


class Runtime:
    def __init__(self, config_dir: Path | None = None, profile: str = "default", config_overrides: dict | None = None):
        self._config_dir = config_dir or Path.cwd()
        self._profile = profile
        self._config_overrides = config_overrides or {}
        self._config: CoreConfig | None = None
        self._event_bus: EventBus | None = None
        self._platform: BasePlatformLayer | None = None
        self._lifecycle: LifecycleManager | None = None
        self._logger = get_logger(__name__)

    async def initialize(self) -> None:
        self._platform = PlatformDetector.detect()
        manager = ConfigManager(self._config_dir, profile=self._profile, overrides=self._config_overrides)
        self._config = manager.load()
        setup_logging(self._config.logging)
        self._logger.info("runtime.init.platform", platform=self._platform.platform_name)
        self._logger.info("runtime.init.config_loaded", profile=self._config.profile)
        self._event_bus = EventBus(self._config.event_bus)
        await self._event_bus.start()
        self._logger.info("runtime.init.event_bus_started")
        self._lifecycle = LifecycleManager(self._config, self._event_bus)
        self._logger.info("runtime.init.lifecycle_ready")

    def register_component(self, component: BaseComponent) -> None:
        if self._lifecycle is None:
            raise RuntimeError("Runtime is not initialized")
        self._lifecycle.register(component)

    async def start(self) -> None:
        await self.lifecycle.start_all()

    async def stop(self) -> None:
        await self.lifecycle.stop_all()
        await self.event_bus.stop()

    async def run_until_signal(self) -> None:
        await self.initialize()
        await self.start()

        stop_event = asyncio.Event()

        def _handler(*_):
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handler)
            except NotImplementedError:
                signal.signal(sig, lambda *_args: stop_event.set())

        self._logger.info("runtime.running")
        await stop_event.wait()
        self._logger.info("runtime.signal_received")
        await self.stop()

    @property
    def config(self) -> CoreConfig:
        if self._config is None:
            raise RuntimeError("Runtime not initialized")
        return self._config

    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            raise RuntimeError("Runtime not initialized")
        return self._event_bus

    @property
    def platform(self) -> BasePlatformLayer:
        if self._platform is None:
            raise RuntimeError("Runtime not initialized")
        return self._platform

    @property
    def lifecycle(self) -> LifecycleManager:
        if self._lifecycle is None:
            raise RuntimeError("Runtime not initialized")
        return self._lifecycle
