import zmq


def send_control_message(host, port, command, data):
    context = zmq.Context()
    client = context.socket(zmq.REQ)
    # client.plain_username = b'admin'
    # client.plain_password = b'secret'
    client.connect(f"tcp://{host}:{port}")
    client.send_json({"command": command, "data": data})
    response = client.recv_json(0)
    return response
