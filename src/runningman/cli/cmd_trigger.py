#!/usr/bin/env python
from .commands import add_command
from ..triggers import send_trigger


def parser_build(parser):
    parser.add_argument("host")
    parser.add_argument("port")
    parser.add_argument("token")
    parser.add_argument("--timeout", type=int, default=500, help="Milliseconds timeout")
    return parser


def main(args):
    send_trigger(
        args.host,
        args.port,
        args.token,
        timeout=args.timeout,
    )


add_command(
    name="trigger",
    function=main,
    parser_build=parser_build,
    add_parser_args=dict(
        description="Send a network trigger",
    ),
)
