from threading import Thread, Event
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
import signal
import logging

logger = logging.getLogger(__name__)


class Manager:
    def __init__(self, interface_password=None, control_address=("localhost", 9876)):
        self.interface_password = interface_password
        self.control_address = control_address

        self.exit_event = Event()
        self.services = {}
        self.triggers = {}
        self.providers = {}
        self.comand_map = {
            "start": self.start_service,
            "stop": self.stop_service,
            "restart": self.restart_service,
            "status": self.status_service,
        }

    def status_service(self, data):
        service = self.services[data["name"]]
        return {"status": str(service.get_status())}

    def start_service(self, data):
        self.services[data["name"]].start()
        return self.status_service(data)

    def stop_service(self, data):
        self.services[data["name"]].stop()
        return self.status_service(data)

    def restart_service(self, data):
        self.services[data["name"]].stop()
        self.services[data["name"]].start()
        return self.status_service(data)

    def start(self):
        self.exit_event.clear()
        self.interface_thread = Thread(target=self.control_interface)
        self.interface_thread.start()

    def stop(self):
        self.exit_event.set()
        self.interface_thread.join()

    def start_services(self):
        for name, service in self.services.items():
            logger.info(f"Manager::Starting service {name}")
            service.start()

    def start_triggers(self):
        for name, trigger in self.triggers.items():
            logger.info(f"Manager::Starting trigger {name}")
            trigger.start()

    def start_providers(self):
        for name, provider in self.providers.items():
            logger.info(f"Manager::Starting provider {name}")
            provider.start()

    def stop_services(self):
        for name, service in self.services.items():
            logger.info(f"Manager::Stopping service {name}")
            service.stop()

    def stop_triggers(self):
        for name, trigger in self.triggers.items():
            logger.info(f"Manager::Stopping trigger {name}")
            trigger.stop()

    def stop_providers(self):
        for name, provider in self.providers.items():
            logger.info(f"Manager::Stopping provider {name}")
            provider.stop()

    def run(self):
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
