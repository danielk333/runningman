import pathlib
import runningman as rm


HERE = pathlib.Path(__file__).parent


def print_arg(queue, logger):
    logger.info("Start getting queue values...")
    while True:
        file = queue.get()
        logger.info(f"got {file[0].name}")


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

ctl.setup_logging()
ctl.run()
