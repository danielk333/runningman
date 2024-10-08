import logging
from pathlib import Path
from datetime import datetime
import fnmatch
from ctypes import c_bool
from multiprocessing import Array

from .provider import TriggeredProvider

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


def get_file_time(file):
    """
    Get the modification time of a file.

    Parameters
    ----------
    file : Path
        The file to check.

    Returns
    -------
    datetime
        The modification time of the file.
    """
    return datetime.fromtimestamp(file.stat().st_mtime)


class ExpiredFiles(TriggeredProvider):
    """
    Monitors a directory for expired files and provides those files when triggered.
    Uses a initial cache list of files in the directory together with a watchdog to
    reduce computational load inured by each trigger.
    """

    class EventHandler(FileSystemEventHandler):
        def __init__(self, pattern):
            self.new_files = []
            self.pattern = pattern
            self.pending = {}  # Use hash map for speed

        def on_closed(self, event: FileSystemEvent) -> None:
            """
            Handles file-closed events, taking pending files and adding them to the new file list.
            """
            fname = Path(event.src_path).name
            if not fnmatch.fnmatch(fname, self.pattern):
                return
            pending = self.pending.pop(event.src_path, False)
            if not pending:
                return
            self.new_files.append(Path(event.src_path))

        def on_created(self, event: FileSystemEvent) -> None:
            """
            Handles file-created events, marking the file as pending.
            """
            fname = Path(event.src_path).name
            if not fnmatch.fnmatch(fname, self.pattern):
                return
            self.pending[event.src_path] = True

    def __init__(self, triggers, path, max_age_seconds, pattern="*", recursive=True):
        """
        Parameters
        ----------
        triggers : list
            List of triggers that will trigger this provider.
        path : str or Path
            The directory to monitor for expired files.
        max_age_seconds : int
            Maximum allowed file age in seconds.
        pattern : str, optional
            Filename pattern to match (default is "*").
        recursive : bool, optional
            Whether to scan directories recursively (default is True).
        """
        super().__init__(ExpiredFiles.run, triggers, callback=self.filter_files_callback)
        logger.debug(f"Init {self}")
        self.path = path
        self.recursive = recursive
        self.max_age_seconds = max_age_seconds
        self.pattern = pattern

    def start(self):
        self.populate_files()
        self.event_handler = ExpiredFiles.EventHandler(self.pattern)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.observer.start()
        super().start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        super().stop()

    def execute(self):
        if self.proc is not None and self.proc.is_alive():
            return
        if self.callback_proc is not None:
            self.callback_proc.join()
        self.files += self.event_handler.new_files
        self.event_handler.new_files.clear()
        self.files_pushed = Array(c_bool, [False] * len(self.files))

        self.args = (self.files, self.files_pushed, self.max_age_seconds)
        super().execute()

    def filter_files_callback(self):
        """
        Filter out the files that have already been provided as expired.
        """
        self.files = [file for file, pushed in zip(self.files, self.files_pushed) if not pushed]

    def populate_files(self):
        """
        Populate the initial list of files to be monitored based on the provided pattern.
        """
        if self.recursive:
            self.files = list(self.path.rglob(self.pattern))
        else:
            self.files = list(self.path.glob(self.pattern))

    @staticmethod
    def run(queues, files, files_pushed, max_age_seconds):
        """
        Check if files have exceeded the max age and push them to the queues if they have.

        Parameters
        ----------
        queues : list
            List of multiprocessing queues to push expired files into.
        files : list
            List of files to check.
        files_pushed : multiprocessing.Array
            Shared array indicating whether a file has been pushed to a queue.
        max_age_seconds : float
            Maximum allowed file age in seconds.
        """
        now = datetime.now()
        for ind, file in enumerate(files):
            files_pushed[ind] = (now - get_file_time(file)).total_seconds() > max_age_seconds
            if files_pushed[ind]:
                for q in queues:
                    q.put((file,))


class SimpleExpiredFiles(TriggeredProvider):
    """
    A simpler version of the `ExpiredFiles` provider
    that checks for expired files without event handling.
    """

    def __init__(self, triggers, path, max_age_seconds, pattern="*", recursive=True):
        """
        Parameters
        ----------
        triggers : list
            List of triggers that will trigger this provider.
        path : str or Path
            The directory to monitor for expired files.
        max_age_seconds : int
            Maximum allowed file age in seconds.
        pattern : str, optional
            Filename pattern to match (default is "*").
        recursive : bool, optional
            Whether to scan directories recursively (default is True).
        """
        args = (Path(path), max_age_seconds)
        kwargs = dict(pattern=pattern, recursive=recursive)
        super().__init__(ExpiredFiles.run, triggers, args=args, kwargs=kwargs)
        logger.debug(f"Init {self}")

    @staticmethod
    def run(queues, path, max_age_seconds, pattern="*", recursive=True):
        """
        Check for expired files and push them to the queues if they have exceeded the max age.

        Parameters
        ----------
        queues : list
            List of multiprocessing queues to push expired files into.
        path : Path
            Directory to scan for expired files.
        max_age_seconds : int
            Maximum allowed file age in seconds.
        pattern : str, optional
            Filename pattern to match (default is "*").
        recursive : bool, optional
            Whether to scan directories recursively (default is True).
        """
        files = path.rglob(pattern) if recursive else path.glob(pattern)
        now = datetime.now()
        for file in files:
            dt = (now - datetime.fromtimestamp(file.stat().st_mtime)).total_seconds()
            if dt < max_age_seconds:
                continue
            for q in queues:
                q.put(file)


class GlobFiles(TriggeredProvider):
    """
    Provides a list of files that match a specific pattern in a directory.
    """

    def __init__(self, triggers, path, pattern="*", recursive=True):
        """
        Parameters
        ----------
        triggers : list
            List of triggers that will trigger this provider.
        path : str or Path
            Directory to search for files.
        pattern : str, optional
            Filename pattern to match (default is "*").
        recursive : bool, optional
            Whether to search directories recursively (default is True).
        """
        args = (Path(path),)
        kwargs = dict(pattern=pattern, recursive=recursive)
        super().__init__(GlobFiles.run, triggers, args=args, kwargs=kwargs)
        logger.debug(f"Init {self}")

    @staticmethod
    def run(queues, path, pattern="*", recursive=True):
        """
        Search for files that match the pattern and push them to the queues.
        """
        files = path.rglob(pattern) if recursive else path.glob(pattern)
        for file in files:
            for q in queues:
                q.put(file)
