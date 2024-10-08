"""

To run this example, first start the manager

```
python docs/examples/network_control.py 1234
```

Enter the password and then command the manager with the client

```
runningman stop localhost 1234 hello -p
```

"""
import logging
import argparse
import datetime
import runningman as rm
from getpass import getpass


parser = argparse.ArgumentParser()
parser.add_argument("port")
args = parser.parse_args()

password = getpass("Enter control server password: ")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s",
    level=logging.INFO,
)


def say_hello():
    print(f"[{datetime.datetime.now()}] hello Ben Richards")


ctl = rm.Manager(interface_password=password, control_address=("*", 1234))

ctl.triggers["my_timer"] = rm.triggers.Timed(
    interval_sec=1.0,
    trigger_directly=True,
)
ctl.services["hello"] = rm.TriggeredService(
    function=say_hello,
    triggers=[
        ctl.triggers["my_timer"],
    ],
    providers=[],
)

ctl.run()
