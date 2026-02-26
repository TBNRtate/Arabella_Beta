from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from core_framework.events.schema import Event
from core_framework.exceptions import (
    ComponentAlreadyRegisteredError,
    ComponentNotFoundError,
    DependencyResolutionError,
)
from core_framework.registry.component import BaseComponent, ComponentState


class LifecycleManager:
    def __init__(self, config, event_bus):
        self.config = config
        self.event_bus = event_bus
        self._components: dict[str, BaseComponent] = {}
        self._running = False
        self._started_once = False

    def register(self, component: BaseComponent) -> None:
        if self._started_once:
            raise ComponentAlreadyRegisteredError("Cannot register components after start_all has been called")
        if component.name in self._components:
            raise ComponentAlreadyRegisteredError(f"Component '{component.name}' already registered")
        self._components[component.name] = component

    def get(self, name: str) -> BaseComponent:
        if name not in self._components:
            raise ComponentNotFoundError(f"Component '{name}' not found")
        return self._components[name]

    def get_all(self) -> dict[str, BaseComponent]:
        return dict(self._components)

    def _topological_levels(self) -> list[list[str]]:
        indegree = {name: 0 for name in self._components}
        graph = defaultdict(list)

        for name, comp in self._components.items():
            for dep in comp.metadata.dependencies:
                if dep not in self._components:
                    raise DependencyResolutionError(f"Dependency '{dep}' required by '{name}' is not registered")
                graph[dep].append(name)
                indegree[name] += 1

        queue = deque([n for n, d in indegree.items() if d == 0])
        levels: list[list[str]] = []
        visited = 0
        while queue:
            current_level = list(queue)
            queue.clear()
            levels.append(current_level)
            for node in current_level:
                visited += 1
                for nxt in graph[node]:
                    indegree[nxt] -= 1
                    if indegree[nxt] == 0:
                        queue.append(nxt)

        if visited != len(self._components):
            cycle_nodes = [name for name, d in indegree.items() if d > 0]
            raise DependencyResolutionError(f"Dependency cycle detected involving: {', '.join(sorted(cycle_nodes))}")
        return levels

    async def start_all(self) -> None:
        await self.event_bus.publish(Event.create("lifecycle", "lifecycle.start_all.begin", {}))
        levels = self._topological_levels()
        self._started_once = True

        for level in levels:
            async def start_component(name: str) -> None:
                component = self._components[name]
                required = component.metadata.dependencies
                if any(self._components[d].state == ComponentState.FAILED for d in required):
                    component._set_state(ComponentState.FAILED)
                    return
                component._set_state(ComponentState.STARTING)
                try:
                    await asyncio.wait_for(component.start(), timeout=component.config.startup_timeout)
                except Exception:  # noqa: BLE001
                    component._set_state(ComponentState.FAILED)

            await asyncio.gather(*(start_component(name) for name in level))

        self._running = True
        await self.event_bus.publish(Event.create("lifecycle", "lifecycle.start_all.complete", {}))

    async def stop_all(self) -> None:
        await self.event_bus.publish(Event.create("lifecycle", "lifecycle.stop_all.begin", {}))
        levels = self._topological_levels()[::-1]
        for level in levels:
            async def stop_component(name: str) -> None:
                component = self._components[name]
                if component.state not in {ComponentState.RUNNING, ComponentState.DEGRADED, ComponentState.FAILED}:
                    return
                try:
                    component._set_state(ComponentState.STOPPING)
                    await asyncio.wait_for(component.stop(), timeout=component.config.shutdown_timeout)
                except Exception:  # noqa: BLE001
                    component._set_state(ComponentState.FAILED)

            await asyncio.gather(*(stop_component(name) for name in level))

        self._running = False
        await self.event_bus.publish(Event.create("lifecycle", "lifecycle.stop_all.complete", {}))

    async def restart(self, name: str) -> None:
        component = self.get(name)
        if component.state in {ComponentState.RUNNING, ComponentState.DEGRADED, ComponentState.FAILED}:
            component._set_state(ComponentState.STOPPING)
            await asyncio.wait_for(component.stop(), timeout=component.config.shutdown_timeout)
        component._set_state(ComponentState.STARTING)
        await asyncio.wait_for(component.start(), timeout=component.config.startup_timeout)

    async def health_check_all(self) -> dict[str, dict]:
        async def check(name: str, comp: BaseComponent):
            if comp.state not in {ComponentState.RUNNING, ComponentState.DEGRADED}:
                return name, {"status": "failed", "details": "not running"}
            return name, await comp.health_check()

        pairs = await asyncio.gather(*(check(n, c) for n, c in self._components.items()))
        return {k: v for k, v in pairs}

    def is_running(self) -> bool:
        return self._running
