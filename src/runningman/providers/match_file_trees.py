import logging
from pathlib import Path
from .provider import TriggeredProvider

logger = logging.getLogger(__name__)


class MatchFileTree(TriggeredProvider):

    def __init__(
        self, triggers, source_path, target_path, pattern="*", recursive=True, name_modifier=None
    ):
        args = (Path(source_path), Path(target_path))
        kwargs = dict(pattern=pattern, recursive=recursive, name_modifier=name_modifier)
        super().__init__(MatchFileTree.run, triggers, args=args, kwargs=kwargs)

    @staticmethod
    def run(queues, source_path, target_path, pattern="*", recursive=True, name_modifier=None):
        if recursive:
            src_files = source_path.rglob(pattern)
        else:
            src_files = source_path.glob(pattern)

        for file in src_files:
            rel_pth = file.relative_to(source_path)
            exp_pth = target_path / rel_pth
            if name_modifier is not None:
                exp_pth = name_modifier(exp_pth)
            args = (file, exp_pth)
            if exp_pth.is_file():
                continue
            for q in queues:
                logger.debug(f"Providing {file} from 'MatchFileTree' to {q}")
                q.put(args)
