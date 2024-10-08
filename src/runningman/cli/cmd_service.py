#!/usr/bin/env python
import json
from getpass import getpass

from .commands import add_command
from ..client import send_control_message


def parser_build(parser):
    parser.add_argument("host")
    parser.add_argument("port")
    parser.add_argument("service")
    parser.add_argument("-p", "--password", action="store_true")
    parser.add_argument("--timeout", type=int, default=200)
    return parser


def main(args, service_cmd):
    if args.password:
        password = getpass("Enter manager password: ")
    else:
        password = None
    response = send_control_message(
        args.host,
        args.port,
        service_cmd,
        {"name": args.service},
        password=password,
        timeout=args.timeout,
    )

    print(json.dumps(response, indent=4))


add_command(
    name="start",
    function=lambda args: main(args, "start"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Start a service in the station software",
    ),
)

add_command(
    name="stop",
    function=lambda args: main(args, "stop"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Stop a service in the station software",
    ),
)

add_command(
    name="restart",
    function=lambda args: main(args, "restart"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Restart a service in the station software",
    ),
)

add_command(
    name="status",
    function=lambda args: main(args, "status"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Get status of a service in the station software",
    ),
)
