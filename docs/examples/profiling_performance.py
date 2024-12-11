"""
Run this file with
`py-spy top --subprocesses python docs/examples/profiling_performance.py`

to live profile the runtime. Alternatively, generate a output file with

`py-spy record --subprocesses python docs/examples/profiling_performance.py`

which can be viewed using the viewers that support the format used.
"""
import pathlib
import runningman as rm
from multiprocessing import Value
import pprint
import logging
import subprocess

set_logger = logging.getLogger("set_identifier")

HERE = pathlib.Path(__file__).parent

FILE_INDEX = Value("i", 0)


def del_file(logger, paths):
    logger.info(f"GOT {pprint.pformat(paths, indent=4)}")
    for index, path in paths.items():
        if path.is_file():
            path.unlink()


def touch_file(logger, path: pathlib.Path, index):
    ind = index.value
    file = path / f"test_{ind}.file"
    logger.info(f"making {file.name=}")
    subprocess.run(["touch", str(file.absolute())])
    with index.get_lock():
        index.value += 1


def set_identifier(file):
    # this take way longer than it should!
    x = 0.0
    for ind in range(100000):
        x += 1
        x -= 230379287.0 / 10.0
        x += 230379287.0 / 10.0
    num = int(file.stem.split("_")[-1])
    set_id = int(num / 7)
    set_index = num % 7
    set_logger.info(f"{set_id=}, {set_index=}")
    return set_id, set_index


ctl = rm.Manager()
ctl.add_external_logger(set_logger)

ctl.triggers["fast"] = rm.triggers.Timed(
    interval_sec=1.0,
    trigger_directly=True,
)
ctl.triggers["slow"] = rm.triggers.Timed(
    interval_sec=5.0,
    trigger_directly=True,
)
ctl.providers["file_set"] = rm.providers.NewClosedFileSet(
    path=HERE / "data",
    set_identifier=set_identifier,
    set_size=7,
    recursive=False,
)

ctl.services["make_new_files"] = rm.TriggeredService(
    function=touch_file,
    kwargs={
        "path": HERE / "data",
        "index": FILE_INDEX,
    },
    triggers=[ctl.triggers["fast"]],
    providers=[],
)

ctl.services["remove_set"] = rm.TriggeredService(
    function=del_file,
    triggers=[ctl.triggers["slow"]],
    providers=[ctl.providers["file_set"]],
)

ctl.setup_logging()
ctl.run()

for file in (HERE / "data").glob("test*.file"):
    ctl.logger.info(f"removing leftover file {file}")
    file.unlink()