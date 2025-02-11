import argparse
import datetime
import runningman as rm

parser = argparse.ArgumentParser()
parser.add_argument("name")
args = parser.parse_args()


def say_hello(logger, name):
    print(f"[{datetime.datetime.now()}] hello {name}")


ctl = rm.Manager()

ctl.triggers["timer1"] = rm.triggers.Timed(
    interval_sec=1.0,
    trigger_directly=True,
)
ctl.triggers["timer2"] = rm.triggers.Timed(
    interval_sec=4.0,
    trigger_directly=True,
)
ctl.services["say_hello"] = rm.TriggeredService(
    function=say_hello,
    kwargs={"name": args.name},
    triggers=[
        ctl.triggers["timer1"],
        ctl.triggers["timer2"],
    ],
    providers=[],
)

ctl.setup_logging()
ctl.set_init_state(triggers={"timer1": False, "timer2": True})
ctl.run()
