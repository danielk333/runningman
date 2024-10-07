#!/usr/bin/env python
import json
from .commands import add_command
from ..client import send_control_message


def parser_build(parser):
    parser.add_argument("host")
    parser.add_argument("port")
    parser.add_argument("service")
    return parser


def main(args, service_cmd):
    response = send_control_message(
        args.host,
        args.port,
        service_cmd,
        {"name": args.service},
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
