import logging
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .trigger import Trigger

logger = logging.getLogger(__name__)


class FileCreated(Trigger):
    """
    A trigger that activates when a file is created within a specified directory.

    This trigger uses the `watchdog` library to monitor file system events,
    specifically file creation events, and invokes the attached targets when
    a new file is detected.
    """

    class EventHandler(FileSystemEventHandler):
        """
        Event handler class to capture file creation events and trigger actions.

        Parameters
        ----------
        targets : list
            A list of target functions to invoke when a file creation event is detected.
        """
        def __init__(self, targets):
            self.targets = targets

        def on_created(self, event: FileSystemEvent) -> None:
            logger.debug(f"Pulling the trigger from {self}")
            for target in self.targets:
                target()

    def __init__(self, path):
        """
        Parameters
        ----------
        path : str or Path
            The directory path to monitor for new file creation events.
        """
        super().__init__()
        self.path = Path(path)
        self.event_handler = FileCreated.EventHandler(self.targets)

    def run(self):
        pass

    def start(self):
        """
        Start the file system observer to monitor the specified path.
        """
        self.runner = Observer()
        self.runner.schedule(self.event_handler, self.path, recursive=True)
        self.runner.start()

    def stop(self):
        """
        Stop the file system observer to monitor the specified path.
        """
        self.runner.stop()
        self.runner.join()
