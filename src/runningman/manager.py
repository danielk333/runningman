from threading import Thread, Event
from itertools import chain
from pathlib import Path
from typing import Optional, Union
import signal
import logging
import os
import sys

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator

package_logger = logging.getLogger("runningman")
DEFAULT_ADDRESS = ("localhost", 9876)


def exception_handler(type, value, tb):
    package_logger.exception(str(value))


def get_logger_name(obj, name):
    return f"{obj.__class__.__name__}({name})"


def get_logger_fname(obj, name):
    return f"{obj.__class__.__name__}__{name}__"


def check_file_handler(logger: logging.Logger) -> bool:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    if logger.propagate and logger.parent is not None:
        return check_file_handler(logger.parent)
    return None


def check_term_handler(logger: logging.Logger) -> Optional[logging.Handler]:
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            return handler
    if logger.propagate and logger.parent is not None:
        return check_term_handler(logger.parent)
    return None


class Manager:
    """
    The `Manager` class coordinates the lifecycle and execution of
    three different components: services, triggers, and providers.
    It also provides a control interface for managing these
    components through a ZeroMQ server. Components can be started,
    stopped, restarted, and queried for status via commands sent
    to the control interface.

    Attributes
    ----------
    interface_password : str
        Optional password for securing the control interface.
    control_address : tuple
        Address (host, port) for the ZeroMQ control interface.
    exit_event : Event
        Event object to signal the shutdown of the control interface.
    services : dict
        Dictionary holding registered services.
    triggers : dict
        Dictionary holding registered triggers.
    providers : dict
        Dictionary holding registered providers.
    component_map : dict
        Maps component types (service, trigger, provider) to their respective containers.
    comand_map : dict
        Maps control commands (start, stop, restart, status, list) to their handler methods.
    """

    def __init__(
        self,
        interface_password: Optional[str] = None,
        control_address: tuple[str, int] = DEFAULT_ADDRESS,
    ):
        """
        Parameters
        ----------
        interface_password : str
            Optional password for securing the control interface.
        control_address : tuple
            Address (host, port) for the ZeroMQ control interface.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.interface_password = interface_password
        self.control_address = control_address

        self.exit_event = Event()
        self.services = {}
        self.triggers = {}
        self.providers = {}
        self.component_map = {
            "service": self.services,
            "trigger": self.triggers,
            "provider": self.providers,
        }
        self.comand_map = {
            "start": self.start_component,
            "stop": self.stop_component,
            "restart": self.restart_component,
            "status": self.status_component,
            "list": self.list_component,
        }

    def setup_logging(
        self,
        name: Optional[str] = None,
        logger_level: int = logging.INFO,
        file_level: int = logging.INFO,
        term_level: int = logging.INFO,
        term_output: bool = True,
        log_folder: Optional[Union[str, bytes, os.PathLike]] = None,
        force_add_handlers: bool = False,
        format_str: str = (
            "%(asctime)s - %(levelname)s - "
            "%(name)s.%(funcName)s: %(message)s"
        ),
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        msecfmt: str = "%s.%03d",
        skip_components: dict[str, str] = {},
    ):
        """Creates new loggers and sets them up for all the currently available components."""

        if log_folder is not None:
            log_folder = Path(log_folder)
            if not log_folder.is_dir():
                log_folder.mkdir()

        if name is not None:
            self.logger = logging.getLogger(get_logger_name(self, name))
        self.logger._fname = get_logger_fname(self, self.logger.name)

        components = chain(
            self.services.items(),
            self.triggers.items(),
            self.providers.items(),
        )
        for name, cmp in components:
            cmp.logger = logging.getLogger(get_logger_name(cmp, name))
            cmp.logger._fname = get_logger_fname(cmp, name)

        all_loggers = chain(
            [
                ("runningman", package_logger),
                (self.logger._fname, self.logger),
            ],
            [(cmp.logger._fname, cmp.logger) for name, cmp in self.services.items()],
            [(cmp.logger._fname, cmp.logger) for name, cmp in self.triggers.items()],
            [(cmp.logger._fname, cmp.logger) for name, cmp in self.providers.items()],
        )

        for fname, logger in all_loggers:
            logger.setLevel(logger_level)
            if log_folder is not None:
                fh = check_file_handler(logger)
                if force_add_handlers or fh is None:
                    fh = logging.FileHandler(log_folder / f"{fname}.log")
                    fmt = logging.Formatter(format_str)
                    fmt.default_time_format = datefmt
                    fmt.default_msec_format = msecfmt
                    logger.addHandler(fh)
                fh.setLevel(file_level)
                fh.setFormatter(fmt)
            if term_output:
                sh = check_term_handler(logger)
                if force_add_handlers or sh is None:
                    sh = logging.StreamHandler(sys.stdout)
                    fmt = logging.Formatter(format_str)
                    fmt.default_time_format = datefmt
                    fmt.default_msec_format = msecfmt
                    logger.addHandler(sh)
                sh.setLevel(term_level)
                sh.setFormatter(fmt)

        # Pipe all exceptions into package logger
        sys.excepthook = exception_handler

    def get_component(self, data):
        container = self.component_map[data["component"]]
        component = container.get(data["name"], None)
        return container, component

    def list_component(self, data):
        container = self.component_map[data["component"]]
        return {data["component"]: list(container.keys())}

    def status_component(self, data):
        container, component = self.get_component(data)
        if component is None:
            return {"error": f"{data['component']} {data['name']} does not exist"}
        else:
            return {"status": str(component.get_status())}

    def start_component(self, data):
        container, component = self.get_component(data)
        if component is not None:
            component.start()
        return self.status_component(data)

    def stop_component(self, data):
        container, component = self.get_component(data)
        if component is not None:
            component.stop()
        return self.status_component(data)

    def restart_component(self, data):
        container, component = self.get_component(data)
        if component is not None:
            component.stop()
            component.start()
        return self.status_component(data)

    def start(self):
        """
        Starts the control interface thread, which listens for incoming commands.
        """
        self.exit_event.clear()
        self.interface_thread = Thread(target=self.control_interface)
        self.interface_thread.start()

    def stop(self):
        """
        Stops the control interface thread and waits for it to exit.
        """
        self.exit_event.set()
        self.interface_thread.join()

    def start_services(self):
        """
        Starts all registered services.
        """
        for name, service in self.services.items():
            self.logger.info(f"Starting service {name}")
            service.start()

    def start_triggers(self):
        """
        Starts all registered triggers.
        """
        for name, trigger in self.triggers.items():
            self.logger.info(f"Starting trigger {name}")
            trigger.start()

    def start_providers(self):
        """
        Starts all registered providers.
        """
        for name, provider in self.providers.items():
            self.logger.info(f"Starting provider {name}")
            provider.start()

    def stop_services(self):
        """
        Stops all registered services.
        """
        for name, service in self.services.items():
            self.logger.info(f"Stopping service {name}")
            service.stop()

    def stop_triggers(self):
        """
        Stops all registered triggers.
        """
        for name, trigger in self.triggers.items():
            self.logger.info(f"Stopping trigger {name}")
            trigger.stop()

    def stop_providers(self):
        """
        Stops all registered providers.
        """
        for name, provider in self.providers.items():
            self.logger.info(f"Stopping provider {name}")
            provider.stop()

    def run(self):
        """
        Starts the manager, initializes and starts components,
        and handles graceful shutdown upon receiving a signal.
        """
        self.logger.info("::run")
        self.start()
        self.start_services()
        self.start_providers()
        self.start_triggers()

        try:
            signal.pause()
        except KeyboardInterrupt:
            self.logger.info("::run::KeyboardInterrupt -> exiting")
            pass

        self.stop_triggers()
        self.stop_providers()
        self.stop_services()
        self.stop()
        self.logger.info("run::exiting")

    def control_interface(self):
        """
        Runs the control interface, which listens for incoming ZeroMQ
        commands and handles component control actions. If a password
        is provided, it sets up plain authentication for the interface.

        The loop runs until `exit_event` is set.
        """
        self.logger.debug(f"control_interface::Setting up zmq interface on {self.control_address}")
        context = zmq.Context()
        if self.interface_password is not None:
            auth = ThreadAuthenticator(context)
            auth.start()
            auth.configure_plain(
                domain="*",
                passwords={
                    "admin": self.interface_password,
                },
            )
            self.logger.debug("control_interface::Setting up zmq plain auth")
        else:
            auth = None

        server = context.socket(zmq.REP)
        if auth is not None:
            server.plain_server = True
        host, port = self.control_address
        server.bind(f"tcp://{host}:{port}")

        while not self.exit_event.is_set():
            try:
                request = server.recv_json(zmq.NOBLOCK)
            except zmq.Again:
                self.exit_event.wait(0.2)
                continue
            self.logger.info(f"control_interface::received {request=}")
            cmd = request["command"]
            if cmd not in self.comand_map:
                server.send_json({"command": f"command {cmd} does not exist"})
                continue
            func = self.comand_map[cmd]
            try:
                response = func(request["data"])
            except Exception as e:
                err_msg = f"command {cmd} failed with {e}"
                self.logger.exception(err_msg)
                server.send_json({"command": err_msg})
                continue

            server.send_json(response)

        # auth.stop()
        self.logger.debug("control_interface::Exiting control interface")
