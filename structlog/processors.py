from datetime import datetime, timezone


class TimeStamper:
    def __init__(self, fmt="iso", utc=True):
        self.utc = utc

    def __call__(self, logger, method_name, event_dict):
        now = datetime.now(timezone.utc if self.utc else None)
        event_dict["timestamp"] = now.isoformat()
        return event_dict


class JSONRenderer:
    def __call__(self, logger, method_name, event_dict):
        return event_dict


class StackInfoRenderer:
    def __call__(self, logger, method_name, event_dict):
        return event_dict


def format_exc_info(logger, method_name, event_dict):
    return event_dict


class CallsiteParameterAdder:
    @staticmethod
    def _find_first_app_frame_and_name(additional_ignores=None):
        import inspect

        frame = inspect.currentframe().f_back
        return frame, frame.f_code.co_name
