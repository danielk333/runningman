"""

## Three ways to profile performance

### `py-spy`

Run this file with
`py-spy top --subprocesses python docs/examples/profiling_performance.py`

to live profile the runtime. Alternatively, generate a output file with

`py-spy record --subprocesses python docs/examples/profiling_performance.py`

which can be viewed using the viewers that support the format used.

WARNING: `py-spy` interfeers with normal termination of `runningman`
and will probably need to be killed manually.

### Manual profiling

We are also manually profiling the `custom_service` function by using the shared
multiprocessing value object already implemented for convenience.

Too see this profiling, run this example regularly with `python`.

### Built-in triggered service profiling

Simply enable the built in triggered profiling like with the `make_new_files`
triggered service.

"""
import pathlib
import runningman as rm
from multiprocessing import Value
import pprint
import logging


set_logger = logging.getLogger("set_identifier")

HERE = pathlib.Path(__file__).parent

FILE_INDEX = Value("i", 0)
PROFILE = rm.make_profile()


def math_func():
    x = 0.0
    for ind in range(1_000_000):
        x += 1
        x -= 23039287.0 / 101.0
        x += 12342487.0 / 101.0


def custom_service(queue, logger, profile=None):
    logger.info("Start getting queue values...")
    profiler = rm.MPPorfiler(profile)
    while True:
        file_set = queue.get()
        profiler.start()
        # do some work
        math_func()
        logger.info(f"custom_service {file_set}")
        profiler.stop()


def del_file(logger, paths):
    logger.info(f"GOT {pprint.pformat(paths, indent=4)}")
    for index, path in paths.items():
        if path.is_file():
            path.unlink()


def touch_file(logger, path: pathlib.Path, index):
    ind = index.value
    file = path / f"test_{ind}.file"
    logger.info(f"making {file.name=}")
    file.touch()
    with index.get_lock():
        index.value += 1


def set_identifier(file):
    # this take way longer than it should!
    math_func()  # and this is the reason!
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
ctl.providers["new_files"] = rm.providers.NewFiles(
    path=HERE / "data",
    recursive=False,
)
ctl.services["check_new_files"] = rm.Service(
    function=custom_service,
    providers=[ctl.providers["new_files"]],
    kwargs={"profile": PROFILE}
)
ctl.services["make_new_files"] = rm.TriggeredService(
    function=touch_file,
    kwargs={
        "path": HERE / "data",
        "index": FILE_INDEX,
    },
    triggers=[ctl.triggers["fast"]],
    providers=[],
    enable_profiler=True,
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

print("`custom_service` PROFILE:")
if PROFILE.executions > 0:
    print(f"{PROFILE.executions=}\n{PROFILE.total_walltime=} s")
    print(f"avg exec time {PROFILE.total_walltime / PROFILE.executions} s")

p = ctl.services["make_new_files"].profiler
print("`make_new_files` PROFILE:")
if PROFILE.executions > 0:
    print(f"{p.executions=}\n{p.total_walltime=} s")
    print(f"avg exec time {p.total_walltime / p.executions} s")
