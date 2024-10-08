#!/usr/bin/env python
import json
from getpass import getpass

from .commands import add_command
from ..client import send_control_message
from ..manager import DEFAULT_ADDRESS


def add_manager_args(parser):
    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default=DEFAULT_ADDRESS[0],
        help="Manager address host (default: %(default)s)",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        default=DEFAULT_ADDRESS[1],
        help="Manager address port (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        action="store_true",
        help="Prompt for password to the manager (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=500,
        help="Timeout in ms for connecting to the manager (default: %(default)s)",
    )


def list_parser_build(parser):
    parser.add_argument(
        "component",
        type=str,
        help="Component type",
        choices=["trigger", "provider", "service"],
    )
    add_manager_args(parser)

    return parser


def parser_build(parser):
    parser.add_argument(
        "component",
        type=str,
        help="Component type",
        choices=["trigger", "provider", "service"],
    )
    parser.add_argument(
        "name",
        type=str,
        help="Name of the component",
    )
    add_manager_args(parser)

    return parser


def main(args, service_cmd):
    if args.password:
        password = getpass("Enter manager password: ")
    else:
        password = None
    data = {"component": args.component}
    if service_cmd != "list":
        data["name"] = args.name

    response = send_control_message(
        args.host,
        args.port,
        service_cmd,
        data,
        password=password,
        timeout=args.timeout,
    )

    print(json.dumps(response, indent=4))


add_command(
    name="start",
    function=lambda args: main(args, "start"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Start a component of the manager",
    ),
)

add_command(
    name="stop",
    function=lambda args: main(args, "stop"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Stop a component of the manager",
    ),
)

add_command(
    name="restart",
    function=lambda args: main(args, "restart"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Restart a component of the manager",
    ),
)

add_command(
    name="status",
    function=lambda args: main(args, "status"),
    parser_build=parser_build,
    add_parser_args=dict(
        description="Get status of a component of the manager",
    ),
)

add_command(
    name="list",
    function=lambda args: main(args, "list"),
    parser_build=list_parser_build,
    add_parser_args=dict(
        description="List the components of the manager",
    ),
)
