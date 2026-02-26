from __future__ import annotations

from pathlib import Path

import structlog

from core_framework.registry.component import BaseComponent, ComponentMetadata, ComponentState

logger = structlog.get_logger(__name__)


class DashboardServer(BaseComponent):
    def __init__(self, config, event_bus, platform_layer, config_manager):
        metadata = ComponentMetadata(
            name="dashboard_server",
            display_name="Grafana Dashboard Provisioner",
            version="0.1.0",
            description="Writes Grafana provisioning files for dashboards",
            dependencies=["metrics_collector"],
            tags=["observability"],
        )
        super().__init__(metadata=metadata, config=config, event_bus=event_bus, platform_layer=platform_layer)
        self._config_manager = config_manager
        cfg = self._config_manager.get_extension("observability")
        self._grafana_provisioning_dir = Path(
            cfg.get("grafana_provisioning_dir", "/etc/grafana/provisioning/dashboards")
        )
        self._grafana_enabled = bool(cfg.get("grafana_enabled", True))

    async def start(self) -> None:
        if self.state == ComponentState.REGISTERED:
            self._set_state(ComponentState.STARTING)
        if self._grafana_enabled:
            source_dir = Path(__file__).parent / "definitions"
            self._grafana_provisioning_dir.mkdir(parents=True, exist_ok=True)
            for definition in source_dir.glob("*.json"):
                (self._grafana_provisioning_dir / definition.name).write_text(definition.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info("dashboards.provisioned", path=str(self._grafana_provisioning_dir))
        self._set_state(ComponentState.RUNNING)

    async def stop(self) -> None:
        if self.state == ComponentState.RUNNING:
            self._set_state(ComponentState.STOPPING)
        self._set_state(ComponentState.STOPPED)

    async def health_check(self) -> dict:
        return {"status": "ok", "details": f"Dashboards at {self._grafana_provisioning_dir}"}
