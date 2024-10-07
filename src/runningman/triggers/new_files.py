import logging
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .trigger import Trigger

logger = logging.getLogger(__name__)


class FileCreated(Trigger):

    class EventHandler(FileSystemEventHandler):
        def __init__(self, targets):
            self.targets = targets

        def on_created(self, event: FileSystemEvent) -> None:
            logger.debug(f"Pulling the trigger from {self}")
            for target in self.targets:
                target()

    def __init__(self, path):
        super().__init__()
        self.path = Path(path)
        self.event_handler = FileCreated.EventHandler(self.targets)

    def run(self):
        pass

    def start(self):
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
