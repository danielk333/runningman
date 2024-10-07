import argparse
import logging
from ..version import __version__

logger = logging.getLogger(__name__)

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

COMMANDS = dict()


def build_parser():
    """
    Build parser object from commands.
    """
    parser = argparse.ArgumentParser(description="Runtime manager CLI")

    # Top level functionality
    parser.add_argument("-v", "--version", action="store_true", help="package version")
    parser.add_argument(
        "-log",
        "--log",
        default="info",
        help=("Provide logging level. " "Example --log debug (default: %(default)s)"),
    )

    # Sub level parsers
    subparsers = parser.add_subparsers(
        help="available command line interfaces", dest="command"
    )

    for name, dat in COMMANDS.items():
        parser_builder, add_parser_args = dat["parser"]
        cmd_parser = subparsers.add_parser(name, **add_parser_args)
        parser_builder(cmd_parser)

    return parser


def add_command(name, function, parser_build, add_parser_args={}):
    """
    Add a new command.
    Used by CLI scripts in order register new commands
    """
    global COMMANDS
    COMMANDS[name] = dict()
    COMMANDS[name]["function"] = function
    COMMANDS[name]["parser"] = (parser_build, add_parser_args)


def main():
    """
    Main parser.
    """
    parser = build_parser()
    args = parser.parse_args()

    level = LOG_LEVELS.get(args.log.lower())
    if level is None:
        raise ValueError(
            "log level given: {} -- must be one of: {}".format(
                args.log, " | ".join(LOG_LEVELS.keys())
            )
        )

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s: %(message)s",
        level=level,
    )

    if args.command is None:
        # Handle non-commands
        if args.version:
            print(__version__)
            exit()
    else:
        cmd_function = COMMANDS[args.command]["function"]
        logger.info(f"Executing command '{args.command}'")
        cmd_function(args)
