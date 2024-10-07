import logging
import pathlib
import runningman as rm


HERE = pathlib.Path(__file__).parent
logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s",
    level=logging.INFO,
)


def print_arg(queue):
    print("Start getting queue values...")
    while True:
        file = queue.get()
        print(file)


ctl = rm.Manager()

ctl.triggers["timed"] = rm.triggers.Timed(interval_sec=5.0)
ctl.providers["glob"] = rm.providers.GlobFiles(
    triggers=[ctl.triggers["timed"]],
    path=HERE,
    pattern="*.py",
)
ctl.services["make_new_files"] = rm.Service(
    function=print_arg,
    providers=[ctl.providers["glob"]],
)

ctl.run()
