import logging
import zmq

logger = logging.getLogger(__name__)


def send_control_message(host, port, command, data, timeout=None, password=None):
    context = zmq.Context()
    if timeout is not None:
        context.setsockopt(zmq.SNDTIMEO, timeout)
        context.setsockopt(zmq.RCVTIMEO, timeout)
        context.setsockopt(zmq.LINGER, 0)
    client = context.socket(zmq.REQ)
    if password is not None:
        client.plain_username = b'admin'
        client.plain_password = password.encode("utf8")
    client.connect(f"tcp://{host}:{port}")
    client.send_json({"command": command, "data": data})
    try:
        response = client.recv_json(0)
    except zmq.Again:
        response = {}
        logger.error("Server not responding")
    return response
