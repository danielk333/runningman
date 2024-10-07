from typing import Optional
from datetime import datetime
import logging
from croniter import croniter

from .trigger import Trigger

logger = logging.getLogger(__name__)


class Cron(Trigger):
    def __init__(self, cron: str, start: Optional[datetime] = None, trigger_directly: bool = False):
        super().__init__()
        if start is None:
            start = datetime.now()
        self.iter = croniter(cron, start)
        self.trigger_directly = trigger_directly

    def run(self):
        self.__first_iter = not self.trigger_directly
        while not self.exit_event.is_set():
            # pull the triggers
            if not self.__first_iter:
                logger.debug(f"Pulling the trigger from {self}")
                for target in self.targets:
                    target()
            else:
                self.__first_iter = False

            next_time = self.iter.get_next(datetime)
            now = datetime.now()
            time_to_next = (next_time - now).total_seconds()
            if time_to_next < 0:
                continue

            self.exit_event.wait(time_to_next)
