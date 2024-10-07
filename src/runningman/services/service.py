from abc import abstractmethod
from enum import Enum
from types import FunctionType
from multiprocessing import Process, Queue
from threading import Thread, Event
from queue import Empty
import logging

from ..triggers import Trigger
from ..providers import Provider

logger = logging.getLogger(__name__)


class Status(Enum):
    NotStarted = 0
    Running = 1
    Completed = 2
    Failed = 3


class BaseService:
    """Base class to make sure signature is correct.
    """
    def __init__(
        self,
        function: FunctionType,
        providers: list[Provider],
        kwargs: dict = {},
    ):
        self.providers = providers
        self.input_queue = Queue()
        self.proc = None
        self.function = function
        self.runner = None
        self.kwargs = kwargs

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def execute(self):
        pass


class Service(BaseService):
    """Generic service meant to be executed once and the kept running,
    handing the control loop over to the input process.

    Notes
    -----
    The function signature must take the input queue as its first and only positional argument.

    """

    def start(self):
        logger.debug(f"Starting {self}")
        self.execute()
        for p in self.providers:
            p.queues.append(self.input_queue)

    def stop(self):
        logger.debug(f"Stopping {self}")
        for p in self.providers:
            p.queues.remove(self.input_queue)
        self.proc.terminate()
        self.proc.join()

    def execute(self):
        self.proc = Process(
            target=self.function,
            args=(self.input_queue, ),
            kwargs=self.kwargs,
            daemon=True,
        )
        self.proc.start()

    def check_status(self):
        # TODO: make this better
        if self.proc is None:
            return Status.NotStarted
        elif self.proc.is_alive():
            return Status.Running
        elif self.proc.exitcode != 0 and self.proc.exitcode is not None:
            return Status.Failed
        else:
            return Status.Completed


class TriggeredService(BaseService):
    """Generic service based on processing inputs from a queue

    The execute function will be run by the associated triggers,
    while the providers generate a stream of inputs for the triggered
    services to handle.
    """
    def __init__(
        self,
        function: FunctionType,
        triggers: list[Trigger],
        providers: list[Provider],
        kwargs: dict = {},
    ):
        super().__init__(function, providers, kwargs=kwargs)
        self.triggers = triggers
        self.exit_event = Event()

    def start(self):
        logger.debug(f"Starting {self}")
        for t in self.triggers:
            t.targets.append(self.execute)
        for p in self.providers:
            p.queues.append(self.input_queue)

    def stop(self):
        logger.debug(f"Stopping {self}")
        for t in self.triggers:
            t.targets.remove(self.execute)
        for p in self.providers:
            p.queues.remove(self.input_queue)
        if self.runner is not None and self.runner.is_alive():
            self.proc.terminate()
        self.exit_event.set()

    def execute(self):
        if self.runner is not None and self.runner.is_alive():
            return
        self.exit_event.clear()
        if len(self.providers) == 0:
            self.runner = Thread(target=self.run_without_provider)
        else:
            self.runner = Thread(target=self.run)
        self.runner.start()

    def run_without_provider(self):
        self.proc = Process(
            target=self.function,
            kwargs=self.kwargs,
        )
        self.proc.start()
        self.proc.join()

    def run(self):
        while not self.exit_event.is_set():
            try:
                args = self.input_queue.get(block=False)
            except Empty:
                self.exit_event.set()
                break
            self.proc = Process(
                target=self.function,
                args=args,
                kwargs=self.kwargs,
            )
            self.proc.start()
            self.proc.join()

    def check_status(self):
        # TODO: make this better
        if self.proc is None:
            return Status.NotStarted
        elif self.proc.is_alive():
            return Status.Running
        elif self.proc.exitcode != 0 and self.proc.exitcode is not None:
            return Status.Failed
        else:
            return Status.Completed
