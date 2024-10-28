import logging
from multiprocessing import Process
from threading import Thread

from runningman.status import ProviderStatus, process_status


class Provider:
    def __init__(self, function, args=(), kwargs = {}):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Init")
        self.function = function
        self.proc = None
        self.kwargs = kwargs
        self.args = args
        self.queues = []
        self.status = ProviderStatus.NotStarted

    def start(self):
        if self.status == ProviderStatus.Started:
            self.logger.debug("Already started")
            return
        self.logger.debug(f"Starting with {len(self.queues)} queues")
        self.proc = Process(
            target=self.function,
            args=(self.queues, self.logger) + self.args,
            kwargs=self.kwargs,
            daemon=True
        )
        self.proc.start()
        self.status = ProviderStatus.Started

    def stop(self):
        if self.status == ProviderStatus.Stopped:
            self.logger.debug("Already stopped")
            return
        self.logger.debug("Stopping")
        self.proc.terminate()
        self.proc.join()
        self.status = ProviderStatus.Stopped

    def get_status(self):
        return self.status, process_status(self.proc)

    def get_exitcode(self):
        if self.proc is None:
            return None
        return self.proc.exitcode


class TriggeredProvider(Provider):
    def __init__(self, function, triggers, args=(), kwargs = {}, callback=None):
        super().__init__(function, args=args, kwargs=kwargs)
        self.triggers = triggers
        self.callback = callback
        self.callback_proc = None

    def start(self):
        if self.status == ProviderStatus.Started:
            self.logger.debug("Already started")
            return
        self.logger.debug(f"Starting with {len(self.queues)} queues")
        for t in self.triggers:
            t.targets.append(self.execute)
        self.status = ProviderStatus.Started

    def stop(self):
        if self.status == ProviderStatus.Stopped:
            self.logger.debug("Already stopped")
            return
        self.logger.debug("Stopping")
        for t in self.triggers:
            t.targets.remove(self.execute)
        if self.proc is not None and self.proc.is_alive():
            self.proc.terminate()
            self.proc.join()
        self.status = ProviderStatus.Stopped

    def execute(self):
        self.logger.debug("Executing")
        if self.proc is not None and self.proc.is_alive():
            return
        self.proc = Process(
            target=self.function,
            args=(self.queues, self.logger) + self.args,
            kwargs=self.kwargs,
            daemon=True,
        )
        self.proc.start()
        if self.callback is not None:
            self.callback_proc = Thread(target=self.callback_handler)
            self.callback_proc.start()

    def callback_handler(self):
        self.proc.join()
        self.callback()
