import logging
from datetime import datetime
import pathlib
import runningman as rm


HERE = pathlib.Path(__file__).parent


def del_file(logger, path):
    now = datetime.now()
    file_age = (now - datetime.fromtimestamp(path.stat().st_mtime)).total_seconds()
    logger.info(f"GOT {path.name=} : {file_age=} sec")
    if path.is_file():
        path.unlink()


def touch_file(logger, path):
    ind = 0
    while True:
        file = path / f"test{ind}.file"
        if not file.is_file():
            logger.info(f"making {file.name=}")
            file.touch()
            break
        ind += 1


ctl = rm.Manager()

ctl.triggers["fast"] = rm.triggers.Timed(
    interval_sec=1.0,
    trigger_directly=True,
)
ctl.triggers["slow"] = rm.triggers.Timed(
    interval_sec=5.0,
    trigger_directly=True,
)
ctl.providers["old_files"] = rm.providers.ExpiredFiles(
    triggers=[ctl.triggers["slow"]],
    path=HERE / "data",
    max_age_seconds=2.0,
    pattern="test*.file",
    recursive=False,
)

ctl.services["make_new_files"] = rm.TriggeredService(
    function=touch_file,
    kwargs={"path": HERE / "data"},
    triggers=[ctl.triggers["fast"]],
    providers=[],
)

ctl.services["remove_old_files"] = rm.TriggeredService(
    function=del_file,
    triggers=[ctl.triggers["slow"]],
    providers=[ctl.providers["old_files"]],
)

ctl.setup_logging(
    log_folder=HERE / "logs",
    file_level=logging.DEBUG,
    term_level=logging.INFO,
    logger_level=logging.DEBUG,
)
ctl.run()

for file in (HERE / "data").glob("test*.file"):
    ctl.logger.info(f"removing leftover file {file}")
    file.unlink()
