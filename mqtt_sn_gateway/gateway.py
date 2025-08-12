from typing import Tuple

from attrs import define, field

from mqtt_sn_gateway import messages, forward, client_store, topic_store
import structlog

LOG = structlog.get_logger(__name__)


class MessageError(Exception):
    """"""


class ForwardingError(Exception):
    """Error when forwarding a message"""


@define
class MqttSnGateway:
    remote_address: Tuple[str, int]
    topic_store: topic_store.TopicStore
    client_store: client_store.ClientStore
    forwarder: forward.MqttSnForwarder
    extend_store_ttl_on_publish: bool = field(default=True)

    def forward(self, topic: str, payload: bytes, qos: int):
        try:
            self.forwarder.forward_publish(topic=topic, payload=payload, qos=qos)
        except Exception:
            LOG.exception("Error when forwarding message")
            raise ForwardingError

    def dispatch(self, data: bytes):
        try:
            message = messages.MessageFactory.from_bytes(data)
            LOG.info(f"Received MQTT-SN message", message=message)
            if isinstance(message, messages.Connect):
                response = self.handle_connect(message)
            elif isinstance(message, messages.Register):
                response = self.handle_register(message)

            elif isinstance(message, messages.Publish):
                response = self.handle_publish(message)
            elif isinstance(message, messages.Pingreq):
                response = self.handle_ping(message)
            else:
                raise MessageError(f"Gateway cannot handle message")
            LOG.info(f"Returning MQTT-SN message", message=response)
            return response
        except messages.ParsingError:
            LOG.exception("MQTT-SN Parsing Error", data=data)
            raise MessageError("MQTT-SN Parsing")

    def handle_ping(self, message: messages.Pingreq):
        if message.client_id:
            structlog.contextvars.bind_contextvars(client_id=message.client_id)
        LOG.info(f"Received PINGREG, returning PINGRESP")
        return messages.Pingresp()

    def handle_connect(self, message: messages.Connect):
        """
        Clients need to connec and set up last will and testament. We dont handle last will and testament so
        it is possible to just return a CONNACK
        """
        client_id = message.client_id

        structlog.contextvars.bind_contextvars(client_id=client_id)

        if message.flags.clean_session:
            LOG.info(f"Client requested clean session. Deleting saved topics.", client_id=client_id)
            self.topic_store.delete_all_topics(client_id)

        try:
            self.client_store.add_client(client_id, remote_addr=self.remote_address)
            LOG.info(f"Client stored",
                     client_store=self.client_store)
        except client_store.ConnectionError:
            LOG.error(f"Unable to connect to client store. Returning CONGESTION", client_store=self.client_store)
            return messages.Connack(return_code=messages.ReturnCode.CONGESTION)
        except Exception:
            LOG.exception("Unable to add client to client store",
                          client_store=self.client_store)
            return messages.Connack(return_code=messages.ReturnCode.CONGESTION)

        response = messages.Connack(return_code=messages.ReturnCode.ACCEPTED)
        return response

    def handle_register(self, message: messages.Register):
        """
        Registers topics from the client.
        """
        try:
            client_id = self.client_store.get_client(self.remote_address)
            structlog.contextvars.bind_contextvars(client_id=client_id)
        except client_store.ClientDoesNotExist:
            LOG.info(f"Received a REGISTER message from an unknown client, sending DISCONNECT")
            return messages.Disconnect()
        except client_store.ConnectionError:
            LOG.error(f"Unable to connect to client store. Returning CONGESTION", client_store=self.client_store)
            return messages.Regack(topic_id=None, msg_id=message.msg_id, return_code=messages.ReturnCode.CONGESTION)
        except Exception:
            LOG.exception("Unable to retrieve client_id from client store")
            return messages.Regack(topic_id=None, msg_id=message.msg_id, return_code=messages.ReturnCode.CONGESTION)

        try:
            topic_id = self.topic_store.add_topic_for_client(
                topic_name=message.topic_name, client_id=client_id
            )
        except topic_store.ConnectionError:
            LOG.error(f"Unable to connect to topic store. Returning CONGESTION", topic_store=self.topic_store)
            return messages.Regack(topic_id=None, msg_id=message.msg_id, return_code=messages.ReturnCode.CONGESTION)
        except Exception:
            LOG.exception("Unable to retrieve topic_id from topic store")
            return messages.Regack(topic_id=None, msg_id=message.msg_id, return_code=messages.ReturnCode.CONGESTION)

        LOG.info(
            f"Registered topic",
            topic_id=topic_id,
            topic_name=message.topic_name,
        )

        return messages.Regack(
            topic_id=topic_id,
            msg_id=message.msg_id,
            return_code=messages.ReturnCode.ACCEPTED,
        )

    def handle_publish(self, message: messages.Publish):
        try:
            client_id = self.client_store.get_client(self.remote_address)
            structlog.contextvars.bind_contextvars(client_id=client_id)
        except client_store.ClientDoesNotExist:
            LOG.error(f"Received a PUBLISH from an unknown client, sending DISCONNECT")
            return messages.Disconnect()
        except client_store.ConnectionError:
            LOG.error(f"Unable to connect to client store. Returning CONGESTION", client_store=self.client_store)
            return messages.Puback(topic_id=message.topic_id, msg_id=message.msg_id,
                                   return_code=messages.ReturnCode.CONGESTION)
        except Exception:
            LOG.exception("Unable to retrieve client_id from client store")
            return messages.Puback(topic_id=message.topic_id, msg_id=message.msg_id,
                                   return_code=messages.ReturnCode.CONGESTION)

        if message.flags.qos not in [0, 1]:
            LOG.error(f"Received a PUBLISH with unsupported QOS", message=message)
            return messages.Puback(
                topic_id=message.topic_id,
                msg_id=message.msg_id,
                return_code=messages.ReturnCode.NOT_SUPPORTED,
            )

        try:
            topic = self.topic_store.get_topic_for_client(
                client_id, topic_id=message.topic_id)
        except topic_store.TopicDoesNotExist:
            LOG.error(f"Registered client tried to publish to a topic that is not registered", topic=message.topic_id)
            return messages.Puback(
                topic_id=message.topic_id,
                msg_id=message.msg_id,
                return_code=messages.ReturnCode.INVALID_TOPIC,
            )
        except topic_store.ConnectionError:
            LOG.error(f"Unable to connect to topic store. Returning CONGESTION", topic_store=self.topic_store)
            return messages.Puback(topic_id=message.topic_id, msg_id=message.msg_id,
                                   return_code=messages.ReturnCode.CONGESTION)
        except Exception:
            LOG.exception(f"Unable to retrieve topic", topic_id=message.topic_id)
            return messages.Puback(topic_id=message.topic_id, msg_id=message.msg_id,
                                   return_code=messages.ReturnCode.CONGESTION)

        try:
            self.forward(topic=topic, payload=message.data, qos=message.flags.qos)
        except ForwardingError:
            LOG.error("Unable to forward message", forarder=self.forwarder, topic=topic,
                      payload=message.data)
            return messages.Puback(topic_id=message.topic_id, msg_id=message.msg_id,
                                   return_code=messages.ReturnCode.CONGESTION)
        except Exception:
            LOG.exception("Unable to forward MQTT-SN message")
            return messages.Puback(topic_id=message.topic_id, msg_id=message.msg_id,
                                   return_code=messages.ReturnCode.CONGESTION)

        if self.extend_store_ttl_on_publish:
            try:
                LOG.debug(f"Extending TTL of client store and topic store")
                self.client_store.extend_client_ttl(remote_addr=self.remote_address)
                self.topic_store.extend_topic_ttl(client_id=client_id)
            except client_store.ConnectionError:
                # We don't care that much that we could not set expire
                LOG.error(f"Unable to connect to client store when extending client ttl")
                pass
            except topic_store.ConnectionError:
                LOG.error(f"Unable to connect to topic store when extending topic ttl")
                pass


        return messages.Puback(
            topic_id=message.topic_id,
            msg_id=message.msg_id,
            return_code=messages.ReturnCode.ACCEPTED,
        )
