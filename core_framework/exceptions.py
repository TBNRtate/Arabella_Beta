from __future__ import annotations

from typing import Any


class CoreFrameworkError(Exception):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message


class ConfigurationError(CoreFrameworkError):
    pass


class ConfigFileNotFoundError(ConfigurationError):
    pass


class ConfigValidationError(ConfigurationError):
    pass


class ConfigProfileNotFoundError(ConfigurationError):
    pass


class EventBusError(CoreFrameworkError):
    pass


class EventBusNotRunningError(EventBusError):
    pass


class EventPublishError(EventBusError):
    pass


class EventSubscriptionError(EventBusError):
    pass


class ComponentError(CoreFrameworkError):
    pass


class ComponentNotFoundError(ComponentError):
    pass


class ComponentStartupError(ComponentError):
    pass


class ComponentShutdownError(ComponentError):
    pass


class ComponentAlreadyRegisteredError(ComponentError):
    pass


class PlatformError(CoreFrameworkError):
    pass


class UnsupportedPlatformError(PlatformError):
    pass


class PlatformCapabilityUnavailableError(PlatformError):
    pass


class LifecycleError(CoreFrameworkError):
    pass


class InvalidStateTransitionError(LifecycleError):
    pass


class DependencyResolutionError(LifecycleError):
    pass
