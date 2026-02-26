class ConsoleRenderer:
    def __init__(self, colors=True):
        self.colors = colors

    def __call__(self, logger, method_name, event_dict):
        return event_dict
