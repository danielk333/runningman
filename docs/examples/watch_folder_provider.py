import pathlib
import logging
import runningman as rm

HERE = pathlib.Path(__file__).parent


def del_file(logger, path):
    logger.info(f"del_file GOT {path=}")
    if path.is_file():
        path.unlink()


def touch_file(logger, path):
    ind = 0
    while True:
        file = path / f"test{ind}.file"
        if not file.is_file():
            logger.info(f"touch_file making {file=}")
            file.touch()
            break
        ind += 1


ctl = rm.Manager()

ctl.providers["new_files"] = rm.providers.NewClosedFiles(path=HERE / "data")

ctl.triggers["fast"] = rm.triggers.Timed(
    interval_sec=5.0,
    trigger_directly=True,
)
ctl.triggers["slow"] = rm.triggers.Timed(
    interval_sec=20.0,
    trigger_directly=True,
)

ctl.services["make_new_files"] = rm.TriggeredService(
    function=touch_file,
    kwargs={"path": HERE / "data"},
    triggers=[ctl.triggers["fast"]],
    providers=[],
)

ctl.services["remove_new_files"] = rm.TriggeredService(
    function=del_file,
    triggers=[ctl.triggers["slow"]],
    providers=[ctl.providers["new_files"]],
)

ctl.setup_logging(logger_level=logging.DEBUG, term_level=logging.DEBUG)
ctl.run()

for file in (HERE / "data").glob("test*.file"):
    ctl.logger.info(f"removing leftover file {file}")
    file.unlink()
