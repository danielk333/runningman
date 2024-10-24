from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .provider import Provider
from runningman.status import ProviderStatus, thread_status


class NewFiles(Provider):

    class EventHandler(FileSystemEventHandler):
        def __init__(self, queues, logger):
            self.logger = logger
            self.queues = queues

        def on_created(self, event: FileSystemEvent) -> None:
            self.logger.debug(f"Providing {event.src_path}")
            for q in self.queues:
                q.put((Path(event.src_path),))

    def __init__(self, path, recursive=True):
        super().__init__(function=None)
        self.path = path
        self.recursive = recursive

    def execute(self):
        pass

    def start(self):
        self.logger.debug("Starting")
        self.event_handler = NewFiles.EventHandler(self.queues, self.logger)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.observer.start()

    def stop(self):
        self.logger.debug("Stopping")
        self.observer.stop()
        self.observer.join()


class NewClosedFiles(Provider):

    class EventHandler(FileSystemEventHandler):
        def __init__(self, queues, logger):
            self.logger = logger
            self.queues = queues
            self.pending = {}  # Use hash map for speed

        def on_closed(self, event: FileSystemEvent) -> None:
            """
            Handles file-closed events, taking pending files and adding them to the new file list.
            """
            pending = self.pending.pop(event.src_path, False)
            if not pending:
                return
            self.logger.debug(f"Providing {event.src_path}")
            for q in self.queues:
                q.put((Path(event.src_path),))

        def on_created(self, event: FileSystemEvent) -> None:
            """
            Handles file-created events, marking the file as pending.
            """
            self.pending[event.src_path] = True

    def __init__(self, path, recursive=True):
        super().__init__(function=None)
        self.path = path
        self.recursive = recursive

    def execute(self):
        pass

    def start(self):
        self.logger.debug("Starting")
        self.event_handler = NewClosedFiles.EventHandler(self.queues, self.logger)
        self.proc = Observer()
        self.proc.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.proc.start()
        self.status = ProviderStatus.Started

    def stop(self):
        self.logger.debug("Stopping")
        self.proc.stop()
        self.proc.join()
        self.status = ProviderStatus.Stopped

    def get_status(self):
        return self.status, thread_status(self.proc)


class NewClosedFileSet(Provider):
    """TODO

    The set identifer function should take in the file Path and return two identifiers:
    - first a unique set id
    - second index within that set
    once a set is complete it will be provided to the queues

    NOTE: this is by definition memory-leaky if sets are never completed.
    solution could be to implement uncompleted set lifetimes.
    """

    class EventHandler(FileSystemEventHandler):
        def __init__(self, queues, set_identifier, set_size, logger):
            self.logger = logger
            self.set_identifier = set_identifier
            self.set_size = set_size
            self.queues = queues
            self.pending = {}
            self.sets = {}

        def on_closed(self, event: FileSystemEvent) -> None:
            """
            Handles file-closed events, taking pending files and adding them to the new file list.
            """
            pending = self.pending.pop(event.src_path, False)
            if not pending:
                return
            file = Path(event.src_path)
            set_id, set_index = self.set_identifier(file)

            if set_id not in self.sets:
                self.sets[set_id] = {}
            self.sets[set_id][set_index] = file

            if len(self.sets[set_id]) == self.set_size:
                file_set = self.sets.pop(set_id)
                self.logger.debug(f"Providing {event.src_path}")
                for q in self.queues:
                    q.put((file_set, ))

        def on_created(self, event: FileSystemEvent) -> None:
            """
            Handles file-created events, marking the file as pending.
            """
            self.pending[event.src_path] = True

    def __init__(self, path, set_identifier, set_size, recursive=True):
        super().__init__(function=None)
        self.set_identifier = set_identifier
        self.set_size = set_size
        self.path = path
        self.recursive = recursive

    def execute(self):
        pass

    def start(self):
        self.logger.debug("Starting")
        self.event_handler = NewClosedFileSet.EventHandler(
            self.queues,
            self.set_identifier,
            self.set_size,
        )
        self.proc = Observer()
        self.proc.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.proc.start()
        self.status = ProviderStatus.Started

    def stop(self):
        self.logger.debug("Stopping")
        self.proc.stop()
        self.proc.join()
        self.status = ProviderStatus.Stopped

    def get_status(self):
        return self.status, thread_status(self.proc)
