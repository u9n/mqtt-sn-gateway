import socketserver

import sentry_sdk
import valkey

from mqtt_sn_gateway.config import Config
from mqtt_sn_gateway import client_store, gateway, topic_store
import structlog
from kombu import Connection, Exchange

from mqtt_sn_gateway.forward import AmqpForwarder
from functools import partial

LOG = structlog.get_logger(__name__)


class MqttSnRequestHandler(socketserver.DatagramRequestHandler):
    """
    This class works similar to the TCP handler class, except that
    self.request consists of a pair of data and client socket, and since
    there is no connection the client address must be given explicitly
    when sending data back via sendto().
    """

    def __init__(
        self,
        request,
        client_address,
        server,
        config: Config,
    ):
        self.config = config
        super().__init__(request, client_address, server)

    def handle(self):
        try:
            data = self.request[0].strip()
            socket = self.request[1]
            structlog.contextvars.bind_contextvars(
                remote_ip=self.client_address[0], remote_port=self.client_address[1]
            )
            LOG.debug("Received UDP data", data=data)
            vk = valkey.Valkey.from_url(self.config.VALKEY_CONNECTION_STRING)
            clients = client_store.ValKeyClientStore(
                valkey=vk, use_port_number=self.config.USE_PORT_NUMBER_IN_CLIENT_STORE
            )
            topics = topic_store.ValKeyTopicStore(valkey=vk)
            amqp_connection = Connection(self.config.AMQP_CONNECTION_STRING)
            amqp_exchange = Exchange(self.config.AMQP_PUBLISH_EXCHANGE, type="topic")
            forwarder = AmqpForwarder(
                exchange=amqp_exchange, connection=amqp_connection
            )
            gw = gateway.MqttSnGateway(
                remote_address=self.client_address,
                client_store=clients,
                topic_store=topics,
                forwarder=forwarder,
                extend_store_ttl_on_publish=self.config.EXTEND_STORE_TTL_ON_PUBLISH,
            )

            response = gw.dispatch(data)
            out_data = response.to_bytes()
            LOG.debug("Sending UDP data", data=out_data)

            socket.sendto(out_data, self.client_address)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise


class ThreadingUdpServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, server_address, RequestHandlerClass, config: Config):
        self.config = config
        request_handler = partial(RequestHandlerClass, config=config)
        socketserver.UDPServer.__init__(self, server_address, request_handler)
