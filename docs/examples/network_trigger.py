import pathlib
import runningman as rm

HERE = pathlib.Path(__file__).parent


def list_files(logger):
    logger.info("Listing now")
    for file in HERE.glob("*.py"):
        print(file.name)


ctl = rm.Manager()

ctl.triggers["net"] = rm.triggers.Network("localhost", 1234, "my_awsome_token")
ctl.services["make_new_files"] = rm.TriggeredService(
    function=list_files,
    triggers=[
        ctl.triggers["net"],
    ],
    providers=[],
)

print("NOW RUN:")
print("runningman trigger localhost 1234 my_awsome_token")
ctl.setup_logging()
ctl.run()
