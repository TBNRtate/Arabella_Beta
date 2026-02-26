from __future__ import annotations

import asyncio
import fnmatch
from collections import deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog

from core_framework.config.schema import EventBusConfig
from core_framework.events.schema import Event, PrivacyClass
from core_framework.exceptions import EventBusNotRunningError

logger = structlog.get_logger(__name__)


class EventBus:
    def __init__(self, config: EventBusConfig):
        self.config = config
        self._input_queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=config.max_queue_size)
        self._history: deque[Event] = deque(maxlen=500)
        self._subscriptions: dict[str, dict] = {}
        self._dispatch_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("eventbus.started", transport=self.config.transport)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._dispatch_task is not None:
            await self._input_queue.join()
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        logger.info("eventbus.stopped")

    async def publish(self, event: Event) -> None:
        if not self._running:
            raise EventBusNotRunningError("Event bus is not running")
        await self._input_queue.put(event)

    def subscribe(self, pattern: str, handler: Callable[[Event], Awaitable[None]], replay_last: int = 0) -> str:
        sub_id = str(uuid4())
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self.config.max_queue_size)
        worker = asyncio.create_task(self._subscriber_worker(sub_id))
        self._subscriptions[sub_id] = {
            "pattern": pattern,
            "handler": handler,
            "queue": queue,
            "worker": worker,
        }

        if replay_last > 0:
            for event in self.get_history(pattern=pattern, limit=replay_last):
                self._safe_put(queue, event)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        sub = self._subscriptions.pop(subscription_id, None)
        if sub:
            sub["worker"].cancel()

    def get_subscription_count(self) -> int:
        return len(self._subscriptions)

    def get_history(self, pattern: str = "*", limit: int = 100) -> list[Event]:
        matching = [event for event in self._history if fnmatch.fnmatch(event.type, pattern)]
        return matching[-limit:]

    @property
    def is_running(self) -> bool:
        return self._running

    def _safe_put(self, queue: asyncio.Queue[Event], event: Event) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("eventbus.subscriber_queue_full", event_type=event.type)

    async def _dispatch_loop(self) -> None:
        while True:
            event = await self._input_queue.get()
            try:
                if event.privacy_class == PrivacyClass.PROHIBITED:
                    logger.warning("eventbus.prohibited_dropped", event_type=event.type)
                    continue
                self._history.append(event)
                coros = []
                for sub in self._subscriptions.values():
                    if fnmatch.fnmatch(event.type, sub["pattern"]):
                        self._safe_put(sub["queue"], event)
                        coros.append(asyncio.sleep(0))
                if coros:
                    await asyncio.gather(*coros, return_exceptions=True)
            finally:
                self._input_queue.task_done()

    async def _subscriber_worker(self, sub_id: str) -> None:
        sub = self._subscriptions[sub_id]
        queue = sub["queue"]
        handler = sub["handler"]
        while True:
            event = await queue.get()
            try:
                await handler(event)
            except Exception as exc:  # noqa: BLE001
                logger.exception("eventbus.handler_error", error=str(exc), event_type=event.type)
            finally:
                queue.task_done()
