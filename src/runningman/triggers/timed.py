import logging
import time
from .trigger import Trigger

logger = logging.getLogger(__name__)


class Timed(Trigger):
    """
    A trigger that activates at a regular time interval.
    """
    def __init__(self, interval_sec: float, trigger_directly: bool = False):
        """
        Parameters
        ----------
        interval_sec : float
            The interval between trigger activations in seconds.
        trigger_directly : bool, optional
            If True, trigger is activated immediately on the first run (default is False).
        """
        super().__init__()
        self.interval_sec = interval_sec
        self.trigger_directly = trigger_directly

    def run(self):
        self.__first_iter = not self.trigger_directly
        while not self.exit_event.is_set():
            t0 = time.time()
            # pull the triggers
            if not self.__first_iter:
                logger.debug(f"Pulling the trigger from {self}")
                for target in self.targets:
                    target()
            else:
                self.__first_iter = False

            # Calculate elapsed time and wait for the remainder of the interval.
            dt = time.time() - t0
            self.exit_event.wait(self.interval_sec - dt)
