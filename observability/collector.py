from __future__ import annotations

import asyncio

import psutil
import structlog
from prometheus_client import start_http_server

from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState
from observability import metrics

logger = structlog.get_logger(__name__)

_STATE_MAP = {
    "unregistered": 0,
    "registered": 1,
    "starting": 2,
    "running": 3,
    "stopping": 4,
    "stopped": 5,
    "failed": 6,
    "degraded": 7,
}


class MetricsCollector(BaseComponent):
    def __init__(self, config, event_bus, platform_layer, config_manager):
        metadata = ComponentMetadata(
            name="metrics_collector",
            display_name="Metrics Collector",
            version="0.1.0",
            description="Collects system vitals and exports Prometheus metrics",
            dependencies=[],
            tags=["observability"],
        )
        super().__init__(metadata=metadata, config=config, event_bus=event_bus, platform_layer=platform_layer)
        self._config_manager = config_manager
        cfg = self._config_manager.get_extension("observability")
        self._prometheus_port = int(cfg.get("prometheus_port", 9090))
        self._poll_interval_seconds = int(cfg.get("poll_interval_seconds", 5))
        self._subscriptions: list[str] = []
        self._polling_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.state == ComponentState.REGISTERED:
            self._set_state(ComponentState.STARTING)
        start_http_server(self._prometheus_port)
        self._subscriptions = [
            self.event_bus.subscribe("hardware.*", self._handle_hardware_event),
            self.event_bus.subscribe("mind.emotion.*", self._handle_emotion_event),
            self.event_bus.subscribe("tool.*", self._handle_tool_event),
            self.event_bus.subscribe("memory.*", self._handle_memory_event),
            self.event_bus.subscribe("lifecycle.*", self._handle_lifecycle_event),
            self.event_bus.subscribe("mind.inference.*", self._handle_inference_event),
        ]
        self._polling_task = asyncio.create_task(self._poll_system_vitals())
        self._set_state(ComponentState.RUNNING)

    async def _poll_system_vitals(self) -> None:
        while True:
            try:
                metrics.cpu_usage_percent.set(psutil.cpu_percent())
                vm = psutil.virtual_memory()
                metrics.ram_usage_percent.set(getattr(vm, "percent"))
                metrics.ram_used_bytes.set(getattr(vm, "used"))
                io = psutil.disk_io_counters()
                metrics.disk_io_read_bytes.set(getattr(io, "read_bytes", 0))
                metrics.disk_io_write_bytes.set(getattr(io, "write_bytes", 0))
                net = psutil.net_io_counters()
                metrics.network_io_sent_bytes.set(getattr(net, "bytes_sent", 0))
                metrics.network_io_recv_bytes.set(getattr(net, "bytes_recv", 0))
                qsize = getattr(self.event_bus, "_input_queue", None)
                if qsize is not None:
                    metrics.event_bus_queue_size.set(self.event_bus._input_queue.qsize())
            except Exception as exc:  # noqa: BLE001
                logger.exception("metrics.poll.error", error=str(exc))
            await asyncio.sleep(self._poll_interval_seconds)

    async def _handle_hardware_event(self, event) -> None:
        payload = event.payload
        mapping = {
            "cpu_percent": metrics.cpu_usage_percent,
            "ram_percent": metrics.ram_usage_percent,
            "ram_used_bytes": metrics.ram_used_bytes,
            "disk_read_bytes_sec": metrics.disk_io_read_bytes,
            "disk_write_bytes_sec": metrics.disk_io_write_bytes,
            "net_sent_bytes_sec": metrics.network_io_sent_bytes,
            "net_recv_bytes_sec": metrics.network_io_recv_bytes,
        }
        for key, gauge in mapping.items():
            if key in payload:
                gauge.set(payload[key])

    async def _handle_emotion_event(self, event) -> None:
        if event.type != "mind.emotion.state_update":
            return
        emotions = event.payload.get("emotions", {})
        mapping = {
            "joy": metrics.emotion_joy,
            "trust": metrics.emotion_trust,
            "fear": metrics.emotion_fear,
            "surprise": metrics.emotion_surprise,
            "sadness": metrics.emotion_sadness,
            "disgust": metrics.emotion_disgust,
            "anger": metrics.emotion_anger,
            "anticipation": metrics.emotion_anticipation,
        }
        for emotion, gauge in mapping.items():
            if emotion in emotions:
                gauge.set(emotions[emotion])
        metrics.emotion_transitions_total.inc()

    async def _handle_tool_event(self, event) -> None:
        payload = event.payload
        tool_name = payload.get("tool_name", "unknown")
        reason = payload.get("reason", "unknown")
        if event.type == "tool.execution.announced":
            metrics.tool_calls_attempted_total.labels(tool_name).inc()
        elif event.type == "tool.execution.complete":
            metrics.tool_calls_succeeded_total.labels(tool_name).inc()
        elif event.type == "tool.execution.blocked":
            metrics.tool_calls_blocked_total.labels(reason).inc()
        elif event.type == "tool.execution.failed":
            metrics.tool_calls_failed_total.labels(tool_name).inc()
        elif event.type == "tool.permission.prompted":
            metrics.permission_prompts_total.inc()

    async def _handle_memory_event(self, event) -> None:
        if event.type == "memory.consolidation.begin":
            metrics.memory_consolidation_cycles_total.inc()
        elif event.type == "memory.contradiction.detected":
            metrics.memory_contradictions_detected_total.inc()

    async def _handle_lifecycle_event(self, event) -> None:
        component = event.payload.get("component")
        to_state = event.payload.get("to")
        if component and to_state:
            numeric_state = _STATE_MAP.get(str(to_state).lower(), -1)
            metrics.component_state.labels(component, str(to_state)).set(numeric_state)

    async def _handle_inference_event(self, event) -> None:
        payload = event.payload
        if event.type == "mind.inference.complete":
            if "tokens_per_sec" in payload:
                metrics.inference_tokens_per_sec.set(payload["tokens_per_sec"])
            if "ttft_ms" in payload:
                metrics.inference_time_to_first_token_ms.set(payload["ttft_ms"])
            if "context_length" in payload:
                metrics.inference_context_length_used.set(payload["context_length"])
        elif event.type == "mind.inference.error":
            metrics.inference_errors_total.inc()
        elif event.type == "mind.inference.start":
            metrics.inference_requests_total.inc()

    async def stop(self) -> None:
        if self.state == ComponentState.RUNNING:
            self._set_state(ComponentState.STOPPING)
        if self._polling_task is not None:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        for subscription_id in self._subscriptions:
            self.event_bus.unsubscribe(subscription_id)
        self._subscriptions.clear()
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok", "details": f"Prometheus on port {self._prometheus_port}"}
