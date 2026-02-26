from __future__ import annotations

import logging
import sys

import structlog

from core_framework.config.schema import LoggingConfig
from core_framework.logging.formatters import ComponentContextProcessor, EventBusContextProcessor


def _add_caller_info(logger, method_name, event_dict):
    frame, name = structlog.processors.CallsiteParameterAdder._find_first_app_frame_and_name(  # noqa: SLF001
        additional_ignores=["structlog", "logging"]
    )
    event_dict["module"] = frame.f_globals.get("__name__", "")
    event_dict["function"] = frame.f_code.co_name
    event_dict["line"] = frame.f_lineno
    return event_dict


def setup_logging(config: LoggingConfig) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        _add_caller_info,
        ComponentContextProcessor(),
        EventBusContextProcessor(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if config.format == "json"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if config.output_file:
        file_handler = logging.FileHandler(config.output_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(file_handler)

    logging.basicConfig(level=getattr(logging, config.level.upper(), logging.INFO), handlers=handlers, force=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
