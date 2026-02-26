from ._base import BoundLogger


class BoundLogger(BoundLogger):
    pass


class LoggerFactory:
    def __call__(self, *args, **kwargs):
        return BoundLogger()


def add_log_level(logger, method_name, event_dict):
    event_dict["level"] = method_name
    return event_dict
