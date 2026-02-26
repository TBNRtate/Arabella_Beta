from __future__ import annotations


class ComponentContextProcessor:
    def __call__(self, logger, method_name, event_dict):
        if "component_name" in event_dict:
            event_dict["component_name"] = event_dict["component_name"]
        if "component_state" in event_dict:
            event_dict["component_state"] = event_dict["component_state"]
        return event_dict


class EventBusContextProcessor:
    def __call__(self, logger, method_name, event_dict):
        if "correlation_id" in event_dict:
            event_dict["correlation_id"] = event_dict["correlation_id"]
        return event_dict
