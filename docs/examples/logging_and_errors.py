import logging
import pathlib
from multiprocessing import Queue
from queue import Empty
import runningman as rm
import random
import time

provider_fail = 1.0
trigger_fail = 3.0
service_fail = 2.0
t0 = time.time()

HERE = pathlib.Path(__file__).parent
ctl = rm.Manager()


for file in (HERE / "logs").glob("*.log"):
    ctl.logger.info(f"removing leftover log {file}")
    file.unlink()


def say_hello(queue: Queue, logger, t0=None, service_fail=None):
    while True:
        if service_fail is not None and time.time() - t0 > service_fail:
            raise Exception("Oh my this service failed!")

        try:
            size = queue.get(timeout=1.0)
        except Empty:
            continue
        for ind in range(size):
            print("hello")


def get_size(queues, logger, t0, provider_fail):
    if provider_fail is not None and time.time() - t0 > provider_fail:
        raise Exception("Oh my this provider failed!")

    for q in queues:
        q.put(random.randint(1, 5))


class MyTimed(rm.triggers.Timed):
    def run(self):
        while not self.exit_event.is_set():
            if trigger_fail is not None and time.time() - t0 > trigger_fail:
                raise Exception("Oh my this trigger failed!")
            for target in self.targets:
                target()
            self.exit_event.wait(self.interval_sec)


ctl.triggers["fast"] = MyTimed(
    interval_sec=1.0,
    trigger_directly=True,
)

ctl.providers["sizes"] = rm.TriggeredProvider(
    function=get_size,
    triggers=[ctl.triggers["fast"]],
    args=(t0, provider_fail),
)

ctl.services["make_new_files"] = rm.Service(
    function=say_hello,
    providers=[ctl.providers["sizes"]],
    kwargs=dict(t0=t0, service_fail=service_fail),
)


ctl.setup_logging(
    log_folder=HERE / "logs",
    term_level=logging.DEBUG,
    logger_level=logging.DEBUG,
    file_level=logging.DEBUG,
)
ctl.run()
