import logging
import zmq
import struct
from .trigger import Trigger

logger = logging.getLogger(__name__)

TRIGGERED = struct.pack("?", True)
NOT_TRIGGERED = struct.pack("?", False)


def send_trigger(host, port, token, timeout=None):
    context = zmq.Context()
    if timeout is not None:
        context.setsockopt(zmq.SNDTIMEO, timeout)
        context.setsockopt(zmq.LINGER, 0)
    client = context.socket(zmq.REQ)
    client.connect(f"tcp://{host}:{port}")
    client.send(token.encode("utf8"))
    result = client.recv()
    return result


class Network(Trigger):
    def __init__(self, host, port, token):
        super().__init__()
        self.host = host
        self.port = port
        self.token = token
        self.timeout = 200

    def run(self):
        context = zmq.Context()
        context.setsockopt(zmq.SocketOption.RCVTIMEO, self.timeout)
        context.setsockopt(zmq.LINGER, 0)
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
                server.send(NOT_TRIGGERED)
                continue

            server.send(TRIGGERED)
            for target in self.targets:
                target()
