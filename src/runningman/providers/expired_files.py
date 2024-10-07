import logging
from pathlib import Path
from datetime import datetime
from .provider import TriggeredProvider

logger = logging.getLogger(__name__)


class ExpiredFiles(TriggeredProvider):

    def __init__(self, triggers, path, max_age_seconds, pattern="*", recursive=True):
        args = (Path(path), max_age_seconds)
        kwargs = dict(pattern=pattern, recursive=recursive)
        super().__init__(ExpiredFiles.run, triggers, args=args, kwargs=kwargs)
        logger.debug(f"Init {self}")

    @staticmethod
    def run(queues, path, max_age_seconds, pattern="*", recursive=True):
        files = path.rglob(pattern) if recursive else path.glob(pattern)
        now = datetime.now()
        for file in files:
            dt = (now - datetime.fromtimestamp(file.stat().st_mtime)).total_seconds()
            if dt < max_age_seconds:
                continue
            for q in queues:
                q.put(file)


class GlobFiles(TriggeredProvider):

    def __init__(self, triggers, path, pattern="*", recursive=True):
        args = (Path(path),)
        kwargs = dict(pattern=pattern, recursive=recursive)
        super().__init__(GlobFiles.run, triggers, args=args, kwargs=kwargs)
        logger.debug(f"Init {self}")

    @staticmethod
    def run(queues, path, pattern="*", recursive=True):
        files = path.rglob(pattern) if recursive else path.glob(pattern)
        for file in files:
            for q in queues:
                q.put(file)
