import logging
from pathlib import Path
from .provider import Provider

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class NewFiles(Provider):

    class EventHandler(FileSystemEventHandler):
        def __init__(self, queues):
            self.queues = queues

        def on_created(self, event: FileSystemEvent) -> None:
            logger.debug(f"Providing {event.src_path} from {self}")
            for q in self.queues:
                q.put((Path(event.src_path), ))

    def __init__(self, path, recursive=True):
        super().__init__(function=None)
        logger.debug(f"Init {self}")
        self.event_handler = NewFiles.EventHandler(self.queues)
        self.path = path
        self.recursive = recursive

    def start(self):
        logger.debug(f"Starting {self}")
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.observer.start()

    def stop(self):
        logger.debug(f"Stopping {self}")
        self.observer.stop()
        self.observer.join()


class NewClosedFiles(Provider):

    class EventHandler(FileSystemEventHandler):
        def __init__(self, queues):
            self.queues = queues
            self.pending = []

        def on_closed(self, event: FileSystemEvent) -> None:
            try:
                ind = self.pending.index(event.src_path)
            except ValueError:
                return
            file = self.pending.pop(ind)
            logger.debug(f"Providing {file} from {self}")
            for q in self.queues:
                q.put((Path(file), ))

        def on_created(self, event: FileSystemEvent) -> None:
            self.pending.append(event.src_path)

    def __init__(self, path, recursive=True):
        super().__init__(function=None)
        logger.debug(f"Init {self}")
        self.event_handler = NewFiles.EventHandler(self.queues)
        self.path = path
        self.recursive = recursive

    def start(self):
        logger.debug(f"Starting {self}")
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.observer.start()

    def stop(self):
        logger.debug(f"Stopping {self}")
        self.observer.stop()
        self.observer.join()
