import logging


class BoundLogger:
    def __init__(self, name=None):
        self._logger = logging.getLogger(name)

    def bind(self, **kwargs):
        return self

    def info(self, event, **kwargs):
        self._logger.info(f"{event} {kwargs}")

    def warning(self, event, **kwargs):
        self._logger.warning(f"{event} {kwargs}")

    def exception(self, event, **kwargs):
        self._logger.exception(f"{event} {kwargs}")


_config = {}


def configure(**kwargs):
    _config.update(kwargs)


def get_logger(name=None):
    return BoundLogger(name)
