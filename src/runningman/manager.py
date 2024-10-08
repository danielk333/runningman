from threading import Thread, Event
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
import signal
import logging

logger = logging.getLogger(__name__)

DEFAULT_ADDRESS = ("localhost", 9876)


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
    def __init__(self, interface_password=None, control_address=DEFAULT_ADDRESS):
        """
            Parameters
            ----------
            interface_password : str
                Optional password for securing the control interface.
            control_address : tuple
                Address (host, port) for the ZeroMQ control interface.
        """
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
            logger.info(f"Manager::Starting service {name}")
            service.start()

    def start_triggers(self):
        """
        Starts all registered triggers.
        """
        for name, trigger in self.triggers.items():
            logger.info(f"Manager::Starting trigger {name}")
            trigger.start()

    def start_providers(self):
        """
        Starts all registered providers.
        """
        for name, provider in self.providers.items():
            logger.info(f"Manager::Starting provider {name}")
            provider.start()

    def stop_services(self):
        """
        Stops all registered services.
        """
        for name, service in self.services.items():
            logger.info(f"Manager::Stopping service {name}")
            service.stop()

    def stop_triggers(self):
        """
        Stops all registered triggers.
        """
        for name, trigger in self.triggers.items():
            logger.info(f"Manager::Stopping trigger {name}")
            trigger.stop()

    def stop_providers(self):
        """
        Stops all registered providers.
        """
        for name, provider in self.providers.items():
            logger.info(f"Manager::Stopping provider {name}")
            provider.stop()

    def run(self):
        """
        Starts the manager, initializes and starts components,
        and handles graceful shutdown upon receiving a signal.
        """
        logger.info("Manager::starting")
        self.start()
        self.start_services()
        self.start_providers()
        self.start_triggers()

        try:
            signal.pause()
        except KeyboardInterrupt:
            logger.info("Manager::KeyboardInterrupt -> exiting")
            pass

        self.stop_triggers()
        self.stop_providers()
        self.stop_services()
        self.stop()
        logger.info("Manager::stopping")

    def control_interface(self):
        """
        Runs the control interface, which listens for incoming ZeroMQ
        commands and handles component control actions. If a password
        is provided, it sets up plain authentication for the interface.

        The loop runs until `exit_event` is set.
        """
        logger.debug(f"Manager::Setting up zmq interface on {self.control_address}")
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
            logger.debug("Manager::Setting up zmq plain auth")
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
            logger.info(f"Manager::received {request=}")
            cmd = request["command"]
            if cmd not in self.comand_map:
                server.send_json({"command": f"command {cmd} does not exist"})
                continue
            func = self.comand_map[cmd]
            try:
                response = func(request["data"])
            except Exception as e:
                err_msg = f"command {cmd} failed with {e}"
                logging.exception(err_msg)
                server.send_json({"command": err_msg})
                continue

            server.send_json(response)

        # auth.stop()
        logger.debug("Manager::Exiting control interface")
