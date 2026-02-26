# core_framework

Foundational runtime infrastructure for long-running intelligent systems.

## Installation

```bash
pip install -e .
```

## Run tests

```bash
pytest tests/
```

## Module overview

- `core_framework.constants`: shared global constants used across the framework.
- `core_framework.exceptions`: typed exception hierarchy for all framework errors.
- `core_framework.config`: schema, defaults, and layered config loading manager.
- `core_framework.events`: canonical event model and async pub/sub event bus.
- `core_framework.registry`: abstract component contract and lifecycle orchestration.
- `core_framework.platform`: OS abstraction, capability model, and platform detection.
- `core_framework.logging`: structlog setup and custom context processors.
- `core_framework.__init__.Runtime`: top-level orchestrator that wires framework services together.
