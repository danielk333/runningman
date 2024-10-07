import logging
from multiprocessing import Process

logger = logging.getLogger(__name__)


class Provider:
    def __init__(self, function, args=(), kwargs = {}):
        self.function = function
        self.proc = None
        self.kwargs = kwargs
        self.args = args
        self.queues = []

    def start(self):
        logger.debug(f"Starting {self}")
        self.proc = Process(
            target=self.function,
            args=(self.queues,) + self.args,
            kwargs=self.kwargs,
            daemon=True
        )
        self.proc.start()

    def stop(self):
        logger.debug(f"Stopping {self}")
        self.proc.terminate()
        self.proc.join()


class TriggeredProvider(Provider):
    def __init__(self, function, triggers, args=(), kwargs = {}):
        super().__init__(function, args=args, kwargs=kwargs)
        self.triggers = triggers

    def start(self):
        logger.debug(f"Starting {self}")
        for t in self.triggers:
            t.targets.append(self.execute)

    def stop(self):
        logger.debug(f"Stopping {self}")
        for t in self.triggers:
            t.targets.remove(self.execute)
        if self.proc is not None and self.proc.is_alive():
            self.proc.terminate()
            self.proc.join()

    def execute(self):
        logger.debug(f"Executing {self}")
        if self.proc is not None and self.proc.is_alive():
            return
        self.proc = Process(
            target=self.function,
            args=(self.queues,) + self.args,
            kwargs=self.kwargs,
            daemon=True,
        )
        self.proc.start()
