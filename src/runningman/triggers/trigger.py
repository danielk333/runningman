from abc import abstractmethod
from typing import Optional
import logging
from threading import Thread, Event

logger = logging.getLogger(__name__)


class Trigger:
    def __init__(self):
        logger.debug(f"Init {self}")
        self.targets = []
        self.runner = None
        self.exit_event = Event()

    @abstractmethod
    def run(self):
        pass

    def stop(self, timeout: Optional[float] = None):
        logger.debug(f"Stopping {self}")
        self.exit_event.set()
        self.runner.join(timeout)

    def start(self):
        logger.debug(f"Starting {self}")
        self.exit_event.clear()
        self.runner = Thread(target=self.run)
        self.runner.start()
