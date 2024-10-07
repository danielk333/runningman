import logging
import zmq
from .trigger import Trigger

logger = logging.getLogger(__name__)


def send_trigger(host, port, token, timeout=None):
    context = zmq.Context()
    if timeout is not None:
        context.setsockopt(zmq.SNDTIMEO, timeout)
        context.setsockopt(zmq.LINGER, timeout)
    client = context.socket(zmq.REQ)
    client.connect(f"tcp://{host}:{port}")
    client.send(token.encode("utf8"))


class Network(Trigger):
    def __init__(self, host, port, token):
        super().__init__()
        self.host = host
        self.port = port
        self.token = token

    def run(self):
        context = zmq.Context()
        context.setsockopt(zmq.SocketOption.RCVTIMEO, 200)
        context.setsockopt(zmq.LINGER, 200)
        server = context.socket(zmq.REP)
        server.bind(f"tcp://{self.host}:{self.port}")

        # TODO proper auth
        while not self.exit_event.is_set():
            try:
                request = server.recv()
            except zmq.Again:
                continue
            logger.info(f"Network(Trigger)::run {request=}")
            token = request.decode("utf8")
            if token != self.token:
                continue

            for target in self.targets:
                target()
