from abc import abstractmethod
from types import FunctionType
from multiprocessing import Process, Queue
from threading import Thread, Event
from queue import Empty
import logging

from ..triggers import Trigger
from ..providers import Provider
from ..profiling import Porfiler
from runningman.status import ServiceStatus, process_status
from runningman import wrappers


class BaseService:
    """Base class to make sure signature is correct."""

    def __init__(
        self,
        function: FunctionType,
        providers: list[Provider],
        kwargs: dict = {},
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.providers = providers
        self.input_queue = Queue()
        self.proc = None
        self.function = function
        self.runner = None
        self.kwargs = kwargs
        self.status = ServiceStatus.NotStarted

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    def get_status(self):
        return self.status, process_status(self.proc)

    def get_exitcode(self):
        if self.proc is None:
            return None
        return self.proc.exitcode


class Service(BaseService):
    """Generic service meant to be executed once and the kept running,
    handing the control loop over to the input process.

    Notes
    -----
    The function signature must only have the input queue and the logger
    as its first and second positional arguments.

    """

    def start(self):
        if self.status == ServiceStatus.Started:
            self.logger.debug("Already started")
            return
        self.logger.debug("Starting")
        self.execute()
        for p in self.providers:
            p.queues.append(self.input_queue)
        self.status = ServiceStatus.Started

    def stop(self):
        if self.status == ServiceStatus.Stopped:
            self.logger.debug("Already stopped")
            return
        if self.status == ServiceStatus.NotStarted:
            self.logger.debug("Not started")
            return
        self.logger.debug("Stopping")
        for p in self.providers:
            p.queues.remove(self.input_queue)
        self.proc.terminate()
        self.proc.join()
        self.status = ServiceStatus.Stopped

    def execute(self):
        self.logger.debug("Executing")
        self.proc = Process(
            target=wrappers.exception_handler(self.function, 1),
            args=(self.input_queue, self.logger),
            kwargs=self.kwargs,
            daemon=True,
        )
        self.proc.start()


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
        enable_profiler: bool = False,
        kwargs: dict = {},
    ):
        super().__init__(function, providers, kwargs=kwargs)
        self.triggers = triggers
        self.exit_event = Event()
        self.enable_profiler = enable_profiler
        self.profiler = Porfiler()

    def start(self):
        if self.status == ServiceStatus.Started:
            self.logger.debug("Already started")
            return
        self.logger.debug("Starting")
        for t in self.triggers:
            t.targets.append(self.execute)
        for p in self.providers:
            p.queues.append(self.input_queue)
        self.status = ServiceStatus.Started

    def stop(self):
        if self.status == ServiceStatus.Stopped:
            self.logger.debug("Already stopped")
            return
        self.logger.debug("Stopping")
        for t in self.triggers:
            t.targets.remove(self.execute)
        for p in self.providers:
            p.queues.remove(self.input_queue)
        if self.runner is not None and self.runner.is_alive():
            self.proc.terminate()
        self.exit_event.set()
        self.status = ServiceStatus.Stopped

    def execute(self):
        self.logger.debug("Executing")
        if self.runner is not None and self.runner.is_alive():
            return
        self.exit_event.clear()
        if len(self.providers) == 0:
            self.runner = Thread(target=self.run_without_provider)
        else:
            self.runner = Thread(target=self.run)
        self.runner.start()

    def run_without_provider(self):
        if self.enable_profiler:
            self.profiler.start()
        self.proc = Process(
            target=wrappers.exception_handler(self.function, 0),
            args=(self.logger,),
            kwargs=self.kwargs,
        )
        self.proc.start()
        self.proc.join()
        if self.enable_profiler:
            self.profiler.stop()

    def run(self):
        # TODO: this could be changed so that when a trigger happends
        # this thread empties the queue and feeds the list into
        # the function, that way vectorization/batching can be used
        # to optimize performance
        while not self.exit_event.is_set():
            try:
                args = self.input_queue.get(block=False)
            except Empty:
                self.exit_event.set()
                break
            if self.enable_profiler:
                self.profiler.start()
            self.proc = Process(
                target=self.function,
                args=(self.logger,) + args,
                kwargs=self.kwargs,
            )
            self.proc.start()
            self.proc.join()
            if self.enable_profiler:
                self.profiler.stop()
