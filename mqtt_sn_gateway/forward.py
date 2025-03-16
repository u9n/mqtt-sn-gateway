from typing import Protocol

from attrs import define

from kombu import Connection, Exchange
from kombu.pools import producers

import structlog
from kombu.transport.virtual import exchange

LOG = structlog.get_logger(__name__)


class MqttSnForwarder(Protocol):
    """
    A MQTT-SN forwarder handles where and how to send reveived MQTT-SN published data.
    """

    def forward_publish(self, topic: str, payload: bytes, qos: int) -> None:
        ...


@define
class AmqpForwarder:
    """
    Forwards MQTT-SN published data on to an AMQP broker, like RabbitMQ.
    There is automatica conversion between MQTT and AMQP in RabbitMQ, but it requires the MQTT-plugin to be enabled.
    If messages are not used at all via MQTT it is possible to just send them directly as AMQP and have a bit better
    exchange handling.

    Topic names needs to be rewritten to work with AMQP.
    See more here: https://www.rabbitmq.com/docs/mqtt#topic-level-separator-and-wildcards

    """

    exchange: Exchange
    connection: Connection

    @staticmethod
    def format_amqp_topic(mqtt_topic: bytes) -> str:
        mqtt_topic_string = mqtt_topic.decode()
        return mqtt_topic_string.replace("/", ".").replace("+", "*")

    def forward_publish(self, topic: str, payload: bytes, qos: int) -> None:
        amqp_topic = self.format_amqp_topic(topic)
        LOG.info(f"Forwarding data to AMQP", exchange=self.exchange.name, amqp_topic=amqp_topic,
                 broker_host=self.connection.hostname, broker_port=self.connection.port)
        with producers[self.connection].acquire(block=True) as producer:
            producer.publish(
                payload,
                exchange=self.exchange,
                routing_key=amqp_topic,
                declare=[self.exchange]
            )
