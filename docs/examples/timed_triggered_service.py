import argparse
import datetime
import runningman as rm

parser = argparse.ArgumentParser()
parser.add_argument("name")
args = parser.parse_args()


def say_hello(logger, name):
    print(f"[{datetime.datetime.now()}] hello {name}")


ctl = rm.Manager()

ctl.triggers["my_timer"] = rm.triggers.Timed(
    interval_sec=10.0,
    trigger_directly=True,
)
ctl.triggers["my_cron"] = rm.triggers.Cron(
    cron="*/1 * * * *",
    trigger_directly=False,
)
ctl.services["say_hello"] = rm.TriggeredService(
    function=say_hello,
    kwargs={"name": args.name},
    triggers=[
        ctl.triggers["my_timer"],
        ctl.triggers["my_cron"],
    ],
    providers=[],
)

ctl.setup_logging()
ctl.run()
