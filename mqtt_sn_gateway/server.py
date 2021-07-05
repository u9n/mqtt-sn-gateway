from __future__ import annotations

import asyncio
import asyncio_dgram
from asyncio_dgram.aio import DatagramStream
from asyncio_mqtt import Client as MqttClient
from asyncio_mqtt import MqttError
import logging
from mqtt_sn_gateway import messages, topics
from contextlib import AsyncExitStack

LOG = logging.getLogger(__name__)
import attr
from typing import *
from datetime import datetime, timedelta, timezone

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

    @staticmethod
    def key_from_remote_addr(remote_addr: Tuple[str, int]) -> str:
        return f"{remote_addr[0]}:{remote_addr[1]}"

    def add_client(self, client: MqttSnClient):
        self.clients[self.key_from_remote_addr(client.remote_addr)] = client

    def get_client(self, remote_addr: Tuple[str, int]):
        return self.clients.get(self.key_from_remote_addr(remote_addr), None)

    def delete_client(self, remote_addr: Tuple[str, int]):
        del self.clients[self.key_from_remote_addr(remote_addr)]


async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@attr.s(auto_attribs=True)
class MQTTSNGatewayServer:
    """
    An async MQTT-SN Gateway
    """

    host: str
    port: int
    broker_host: str
    broker_port: int = attr.ib(default=1883)
    broker_connections: int = attr.ib(default=10)

    client_store: ClientStore = attr.ib(factory=InMemoryClientStore)
    topic_store: topics.TopicStore = attr.ib(factory=topics.InMemoryTopicStore)

    back_pressure_limit: int = attr.ib(default=1000)

    reader_task: Optional[asyncio.Task] = attr.ib(init=False)
    datagram_queue: asyncio.Queue[Tuple[bytes, Tuple[str, int]]] = attr.ib(
        default=attr.Factory(
            lambda self: asyncio.Queue(maxsize=self.back_pressure_limit),
            takes_self=True,
        )
    )
    write_queue: asyncio.Queue[WriteEvent] = attr.ib(factory=asyncio.Queue, init=False)
    writer_task: Optional[asyncio.Task] = attr.ib(init=False)
    message_dispatcher_task: Optional[asyncio.Task] = attr.ib(init=False)
    message_tasks: Set[asyncio.Task] = attr.ib(factory=set, init=False)

    broker_clients: List[MqttClient] = attr.ib(factory=list, init=False)

    @property
    def mqtt_client(self) -> Optional[MqttClient]:
        """
        For every request to use an mqtt_client the first one is taken from the list
        and then put at the back. This gives a simple round robin behaviour when
        balancing the data over all available clients.
        """
        if self.broker_clients:
            client = self.broker_clients.pop(0)
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
        LOG.info(f"Received {msg} from {new_client}")

        self.client_store.add_client(new_client)
        # TODO: check for last will and testament.
        # If all is ok we send a CONACK message
        connack = messages.Connack(return_code=messages.ReturnCode.ACCEPTED)
        LOG.info(f"Sending {connack} to {new_client}")
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
            LOG.info(f"Received {msg} from {client}")
            topic_id = self.topic_store.add_topic_for_client(
                topic_name=msg.topic_name, client_id=client.client_id
            )
            regack = messages.Regack(
                topic_id=topic_id,
                msg_id=msg.msg_id,
                return_code=messages.ReturnCode.ACCEPTED,
            )
            LOG.info(f"Topic {topic_id}:{msg.topic_name} registered for {client}. ")
            LOG.info(f"Sending {regack} to {client}")
            await self.write_queue.put(
                WriteEvent(regack.to_bytes(), client.remote_addr)
            )

        else:
            # assuming of the client has not registered we are not supporting the client
            # and a NOT_SUPPORTED should be sent.
            LOG.info(f"Received {msg} from unknown client at {remote_addr}")
            regack = messages.Regack(
                topic_id=None,
                msg_id=msg.msg_id,
                return_code=messages.ReturnCode.NOT_SUPPORTED,
            )
            LOG.info(f"Sending {regack} to unknown client at {remote_addr}")
            await self.write_queue.put(WriteEvent(regack.to_bytes(), remote_addr))

    async def handle_publish(self, msg: messages.Publish, remote_addr: Tuple[str, int]):
        client = self.client_store.get_client(remote_addr)
        if client:
            LOG.info(f"Received {msg} from {client}")
            topic = self.topic_store.get_topic_for_client(
                client.client_id, topic_id=msg.topic_id
            )
            if topic:
                try:
                    mqtt = self.mqtt_client
                    if mqtt:
                        await mqtt.publish(topic=topic, payload=msg.data, qos=1)
                        LOG.info(f"Published {msg.data!r} to MQTT with topic {topic}")
                        puback = messages.Puback(
                            topic_id=msg.topic_id,
                            msg_id=msg.msg_id,
                            return_code=messages.ReturnCode.ACCEPTED,
                        )
                        LOG.info(f"Sending {puback} for {client}")
                        await self.write_queue.put(
                            WriteEvent(puback.to_bytes(), remote_addr)
                        )
                    else:
                        # No MQTT connections available
                        puback = messages.Puback(
                            topic_id=msg.topic_id,
                            msg_id=msg.msg_id,
                            return_code=messages.ReturnCode.CONGESTION,
                        )
                        LOG.info(
                            f"Sending {puback} due to no available MQTT connections for {client}"
                        )
                        await self.write_queue.put(
                            WriteEvent(puback.to_bytes(), remote_addr)
                        )
                except MqttError as e:
                    LOG.error(e)
                    puback = messages.Puback(
                        topic_id=msg.topic_id,
                        msg_id=msg.msg_id,
                        return_code=messages.ReturnCode.CONGESTION,
                    )
                    LOG.info(f"Sending {puback} due to MQTT error for {client}")
                    await self.write_queue.put(
                        WriteEvent(puback.to_bytes(), remote_addr)
                    )

                    raise

            else:
                LOG.info(
                    f"Could not find a registered topic for {msg.topic_id} on {client}"
                )
                puback = messages.Puback(
                    topic_id=msg.topic_id,
                    msg_id=msg.msg_id,
                    return_code=messages.ReturnCode.INVALID_TOPIC,
                )
                LOG.info(f"Sending {puback} for {client}")
                await self.write_queue.put(WriteEvent(puback.to_bytes(), remote_addr))
        else:
            LOG.info(f"Received {msg} from unknown client at {remote_addr}")
            puback = messages.Puback(
                topic_id=msg.topic_id,
                msg_id=msg.msg_id,
                return_code=messages.ReturnCode.NOT_SUPPORTED,
            )
            LOG.info(f"Sending {puback} to unknown client at {remote_addr}")
            await self.write_queue.put(WriteEvent(puback.to_bytes(), remote_addr))

    async def run(self):
        LOG.info("Starting MQTT-SN Gateway")
        LOG.info(f"Binding UDP socket to ({self.host}:{self.port})")
        udp_stream = await asyncio_dgram.bind((self.host, self.port))
        self.reader_task = asyncio.create_task(self.datagram_reader(udp_stream))
        LOG.info(f"Listening on incoming UDP-packets on ({self.host}:{self.port})")
        self.writer_task = asyncio.create_task(
            self.datagram_writer(udp_stream, self.write_queue)
        )
        LOG.info(f"Starting message dispatch task")
        self.message_dispatcher_task = asyncio.create_task(self.message_dispatcher())

        should_reconnect = True
        while should_reconnect:
            try:
                async with AsyncExitStack() as stack:
                    stack.push_async_callback(cancel_tasks, self.message_tasks)
                    LOG.info(
                        f"Setting up {self.broker_connections} connections to MQTT "
                        f"broker at {self.broker_host}:{self.broker_port} "
                    )

                    clients = [
                        await stack.enter_async_context(
                            MqttClient(hostname=self.broker_host, port=self.broker_port)
                        )
                        for _ in range(0, self.broker_connections)
                    ]
                    self.broker_clients = clients

                    LOG.info(f"Connected to MQTT broker")
                    should_stop = False
                    while not should_stop:
                        # TODO: check for errors in the static tasks to see if they
                        #  need to be restarted.
                        if self.message_tasks:
                            finished_tasks, pending_tasks = await asyncio.wait(
                                self.message_tasks, timeout=0.5
                            )

                            for task in finished_tasks:
                                # Calling result on a done task will
                                # propagate any unhandled exception to our context
                                try:
                                    task.result()

                                except MqttError as mqtt_error:
                                    LOG.error(f"MQTT_ERROR: {mqtt_error}")
                                    # Releasing the tasks check loop to initiate
                                    # restart of broker connections.
                                    should_stop = True

                                except Exception as e:
                                    LOG.error(f"An unknown error occurred in task")
                                    LOG.exception(e)

                                finally:
                                    # removed finished tasks
                                    self.message_tasks.difference_update(finished_tasks)

                        else:
                            await asyncio.sleep(0.5)
            except MqttError as e:
                LOG.error(e)
                LOG.info("MQTT Broker Error. Reconnection in 5 seconds")
                await asyncio.sleep(5)

    async def teardown(self):
        LOG.info("Starting teardown of MQTT-SN Gateway")
        LOG.info("Cancelling reader task")
        self.reader_task.cancel()
        LOG.info("Canceling writer task")
        self.writer_task.cancel()

    async def datagram_reader(self, udp_stream: DatagramStream):
        while True:
            data, remote_addr = await udp_stream.recv()
            LOG.debug(
                f"Received UDP packet of {len(data)} bytes ({data}) from {remote_addr}"
            )
            await self.datagram_queue.put((data, remote_addr))

    async def datagram_writer(
        self, udp_stream: DatagramStream, queue: asyncio.Queue[WriteEvent]
    ):
        while True:
            write_event = await queue.get()
            LOG.debug(
                f"Sending {len(write_event.data)} bytes ({write_event.data}) to {write_event.remote_addr}"
            )
            await udp_stream.send(write_event.data, write_event.remote_addr)

    async def message_dispatcher(self):
        while True:
            data, remote_addr = await self.datagram_queue.get()
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
                LOG.error(f"Gateway cannot handle {msg}")
