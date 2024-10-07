import logging
import argparse
import datetime
import runningman as rm

parser = argparse.ArgumentParser()
parser.add_argument("name")
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s",
    level=logging.INFO,
)


def say_hello(name):
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
ctl.services["make_new_files"] = rm.TriggeredService(
    function=say_hello,
    kwargs={"name": args.name},
    triggers=[
        ctl.triggers["my_timer"],
        ctl.triggers["my_cron"],
    ],
    providers=[],
)

ctl.run()
