from abc import abstractmethod
from typing import Optional
import logging
from threading import Thread, Event
from runningman.status import TriggerStatus, thread_status

logger = logging.getLogger(__name__)


class Trigger:
    def __init__(self):
        logger.debug(f"Init {self}")
        self.targets = []
        self.runner = None
        self.exit_event = Event()
        self.status = TriggerStatus.NotStarted

    @abstractmethod
    def run(self):
        pass

    def start(self):
        logger.debug(f"Starting {self}")
        self.exit_event.clear()
        self.runner = Thread(target=self.run)
        self.runner.start()
        self.status = TriggerStatus.Started

    def stop(self, timeout: Optional[float] = None):
        logger.debug(f"Stopping {self}")
        self.exit_event.set()
        self.runner.join(timeout)
        self.status = TriggerStatus.Stopped

    def get_status(self):
        return self.status, thread_status(self.runner)
