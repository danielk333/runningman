import logging
import pathlib
import runningman as rm

logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s",
    level=logging.DEBUG,
)

HERE = pathlib.Path(__file__).parent


def del_file(path):
    print(f"del_file GOT {path=}")
    if path.is_file():
        path.unlink()


def touch_file(path):
    ind = 0
    while True:
        file = path / f"test{ind}.file"
        if not file.is_file():
            print(f"touch_file making {file=}")
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

ctl.run()

for file in (HERE / "data").glob("test*.file"):
    print(f"removing leftover file {file}")
    file.unlink()
