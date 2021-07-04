from __future__ import annotations

import asyncio
import asyncio_dgram
import uvloop
from asyncio_dgram.aio import DatagramStream
from asyncio_mqtt import Client, MqttError
import logging
import messages
import topics
from contextlib import AsyncExitStack
from asyncio_connection_pool import ConnectionPool, ConnectionStrategy

LOG = logging.getLogger(__name__)
import attr
from typing import *
from datetime import datetime, timedelta, timezone

# TODO: it is not really QoS1 since we are not waiting for the ack from the MQTT broker.
# TODO: we should limit the amount of inflight publishes. So that the server is not atacked out of memory


@attr.s(auto_attribs=True)
class MqttSnClient:
    client_id: bytes
    keep_alive_to: datetime
    remote_addr: Tuple[str, int]


@attr.s(auto_attribs=True)
class WriteEvent:
    data: bytes
    remote_addr: Tuple[str, int]


class ClientStore(Protocol):
    def add_client(self, client: MqttSnClient) -> None:
        ...

    def get_client(self, remote_addr: Tuple[str, int]) -> Optional[MqttSnClient]:
        ...

    def delete_client(self, remote_addr: Tuple[str, int]) -> None:
        ...


@attr.s(auto_attribs=True)
class InMemoryClientStore:

    clients: Dict[str, MqttSnClient] = attr.ib(factory=dict)

    def key_from_remote_addr(self, remote_addr: Tuple[str, int]) -> str:
        return f"{remote_addr[0]}:{remote_addr[1]}"

    def add_client(self, client: MqttSnClient):
        self.clients[self.key_from_remote_addr(client.remote_addr)] = client

    def get_client(self, remote_addr: Tuple[str, int]):
        return self.clients.get(self.key_from_remote_addr(remote_addr), None)

    def delete_client(self, remote_addr: Tuple[str, int]):
        del self.clients[self.key_from_remote_addr(remote_addr)]


async def send_to_mqtt(queue: asyncio.Queue):

    async with Client("localhost") as client:
        while True:
            topic, data, response_queue = await queue.get()
            try:
                await client.publish(topic, payload=data, qos=1)
                LOG.info(f"Published {data} to {topic}")

                await response_queue.put(True)
            except MqttError as e:
                LOG.info(f"Error publishing to MQTT {data} to {topic}, {e}")
                await response_queue.put(False)


@attr.s(auto_attribs=True)
class MQTTSNGatewayServer:
    host: str
    port: int

    broker_clients: List[Client] = attr.ib(factory=list)
    reader_task: Optional[asyncio.Task] = attr.ib(init=False)
    writer_task: Optional[asyncio.Task] = attr.ib(init=False)
    write_queue: asyncio.Queue[WriteEvent] = attr.ib(factory=asyncio.Queue, init=False)
    broker_send_tasks: Set[asyncio.Task] = attr.ib(factory=set, init=False)
    upstream_data_queue: asyncio.Queue = attr.ib(factory=asyncio.Queue, init=False)
    client_store: ClientStore = attr.ib(factory=InMemoryClientStore)
    topic_store: topics.TopicStore = attr.ib(factory=topics.InMemoryTopicStore)
    udp_stream: Optional[DatagramStream] = attr.ib(default=None, init=False)
    message_tasks: Set[asyncio.Task] = attr.ib(factory=set, init=False)

    @property
    def mqtt_client(self):
        client = self.broker_clients.pop(0)
        if client:
            self.broker_clients.append(client)
            return client
        else:
            return None

    async def handle_connect(self, msg: messages.Connect, remote_addr: Tuple[str, int]):
        new_client = MqttSnClient(
            client_id=msg.client_id,
            keep_alive_to=(
                datetime.now(tz=timezone.utc) + timedelta(seconds=msg.duration)
            ),
            remote_addr=remote_addr,
        )
        self.client_store.add_client(new_client)
        print(self.client_store)
        # TODO: check for last will and testament.
        # If all is ok we send a CONACK message
        connack = messages.Connack(return_code=messages.ReturnCode.ACCEPTED)
        LOG.info(f"Sending {connack}")
        await self.write_queue.put(
            WriteEvent(
                data=connack.to_bytes(),
                remote_addr=new_client.remote_addr,
            ),
        )

    async def handle_register(
        self, msg: messages.Register, remote_addr: Tuple[str, int]
    ):
        client = self.client_store.get_client(remote_addr)
        if client:
            topic_id = self.topic_store.add_topic_for_client(
                topic_name=msg.topic_name, client_id=client.client_id
            )
            regack = messages.Regack(
                topic_id=topic_id,
                msg_id=msg.msg_id,
                return_code=messages.ReturnCode.ACCEPTED,
            )
            LOG.info(
                f"Topic {topic_id}:{msg.topic_name} registered for {client}. "
                f"Sending {regack}"
            )
            await self.write_queue.put(
                WriteEvent(regack.to_bytes(), client.remote_addr)
            )
            LOG.info(self.topic_store)

        else:
            # assuming of the client has not registered we are not supporting the client
            # and a NOT_SUPPORTED should be sent.

            regack = messages.Regack(
                topic_id=None,
                msg_id=msg.msg_id,
                return_code=messages.ReturnCode.NOT_SUPPORTED,
            )
            LOG.info(f"Could not find client. Sending {regack}")
            await self.write_queue.put(
                WriteEvent(regack.to_bytes(), client.remote_addr)
            )

    async def handle_publish(self, msg: messages.Publish, remote_addr: Tuple[str, int]):
        client = self.client_store.get_client(remote_addr)
        if client:
            topic = self.topic_store.get_topic_for_client(
                client.client_id, topic_id=msg.topic_id
            )
            if topic:
                # async with Client(hostname="localhost", client_id="teset", clean_session=False) as mqtt_client:
                #    LOG.info(f"Publishing {msg.data!r} on topic {topic}")
                #    await mqtt_client.publish(topic=topic, payload=msg.data, qos=1)

                # response_queue = asyncio.Queue()
                # await self.upstream_data_queue.put((topic, msg.data, response_queue))
                # response = await response_queue.get()
                # if response:
                #    puback = messages.Puback(topic_id=msg.topic_id, msg_id=msg.msg_id,
                #                             return_code=messages.ReturnCode.ACCEPTED, )
                # else:
                #    puback = messages.Puback(topic_id=msg.topic_id, msg_id=msg.msg_id,
                #                             return_code=messages.ReturnCode.CONGESTION, )
                try:
                    await self.mqtt_client.publish(topic=topic, payload=msg.data, qos=1)
                    puback = messages.Puback(
                        topic_id=msg.topic_id,
                        msg_id=msg.msg_id,
                        return_code=messages.ReturnCode.ACCEPTED,
                    )
                except MqttError as e:
                    LOG.error(e)
                    puback = messages.Puback(
                        topic_id=msg.topic_id,
                        msg_id=msg.msg_id,
                        return_code=messages.ReturnCode.CONGESTION,
                    )
                LOG.info(f"Sending {puback}")
                await self.write_queue.put(WriteEvent(puback.to_bytes(), remote_addr))

            else:
                LOG.info(
                    f"Could not find a registered topic for topic_id={msg.topic_id} on client={client}"
                )
                puback = messages.Puback(
                    topic_id=msg.topic_id,
                    msg_id=msg.msg_id,
                    return_code=messages.ReturnCode.INVALID_TOPIC,
                )
                await self.write_queue.put(WriteEvent(puback.to_bytes(), remote_addr))
        else:
            LOG.info(f"Could not find a connected client at {remote_addr}")
            puback = messages.Puback(
                topic_id=msg.topic_id,
                msg_id=msg.msg_id,
                return_code=messages.ReturnCode.NOT_SUPPORTED,
            )
            await self.write_queue.put(WriteEvent(puback.to_bytes(), remote_addr))

    async def run(self):
        # await self.client.connect()
        async with AsyncExitStack() as stack:
            for _ in range(0, 100):
                self.broker_clients.append(await stack.enter_async_context(Client("localhost")))

            udp_stream = await asyncio_dgram.bind((self.host, self.port))
            self.reader_task = asyncio.create_task(self.datagram_reader(udp_stream))
            self.writer_task = asyncio.create_task(
                self.datagram_writer(udp_stream, self.write_queue)
            )
            # TODO: do teardown
            while True:
                # TODO: check handler_tasks.
                await asyncio.sleep(5)

    async def start_broker_connections(self):
        for _ in range(0, 5):
            self.broker_send_tasks.add(
                asyncio.create_task(send_to_mqtt(self.upstream_data_queue))
            )

    async def datagram_reader(self, udp_stream: DatagramStream):
        while True:
            data, remote_addr = await udp_stream.recv()
            LOG.debug(f"Received {len(data)} bytes ({data}) from {remote_addr}")
            msg = messages.MessageFactory.from_bytes(data)
            if not msg:
                LOG.info(f"Could not parse {data} as an MQTT-SN message. Dropping")
                continue

            if isinstance(msg, messages.Connect):
                self.message_tasks.add(
                    asyncio.create_task(self.handle_connect(msg, remote_addr))
                )

            elif isinstance(msg, messages.Register):
                self.message_tasks.add(
                    asyncio.create_task(self.handle_register(msg, remote_addr))
                )

            elif isinstance(msg, messages.Publish):
                self.message_tasks.add(
                    asyncio.create_task(self.handle_publish(msg, remote_addr))
                )

            else:

                LOG.info(f"Gateway cannot handle {msg}")

    async def datagram_writer(
        self, udp_stream: DatagramStream, queue: asyncio.Queue[WriteEvent]
    ):
        while True:
            write_event = await queue.get()
            LOG.debug(
                f"Sending {len(write_event.data)} bytes ({write_event.data}) to {write_event.remote_addr}"
            )
            await udp_stream.send(write_event.data, write_event.remote_addr)


async def main():
    # start a server receiving the udp packets
    server = MQTTSNGatewayServer(host="127.0.0.1", port=9999)
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    uvloop.install()
    asyncio.run(main())
