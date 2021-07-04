import attr
from enum import IntEnum
from typing import *



PROTOCOL_ID = 0x01  # Always this for MQTT:SB


class MessageType(IntEnum):
    ADVERTISE = 0
    GWINFO = 0x02
    CONNECT = 0x04
    WILLTOPICREQ = 0x06
    WILLMSGREQ = 0x08
    REGISTER = 0x0A
    PUBLISH = 0x0C
    PUBCOMP = 0x0E
    PUBREL = 0x10
    SUBSCRIBE = 0x12
    UNSUBSCRIBE = 0x14
    PINGREQ = 0x16
    DISCONNECT = 0x18
    WILLTOPICUPD = 0x1A
    WILLMSGUPD = 0x1C
    SEARCHGW = 0x01
    CONNACK = 0x05
    WILLTOPIC = 0x07
    WILLMSG = 0x09
    REGACK = 0x0B
    PUBACK = 0x0D
    PUBREC = 0x0F
    SUBACK = 0x13
    UNSUBACK = 0x15
    PINGRESP = 0x17
    WILLTOPICRESP = 0x1B
    WILLMSGRESP = 0x1D
    ENCAPSULATED = 0xFE


class TopicType(IntEnum):
    NORMAL = 0b00
    PREDEFINED = 0b01
    SHORT = 0b10


class ReturnCode(IntEnum):
    ACCEPTED = 0x00
    CONGESTION = 0x01
    INVALID_TOPIC = 0x02
    NOT_SUPPORTED = 0x03


class MqttSnMessage(Protocol):
    msg_type: MessageType

    def from_bytes(self, source_bytes: bytes):
        ...

    def to_bytes(self) -> bytes:
        ...



@attr.s(auto_attribs=True)
class Header:
    """
    Length can be either 1 octet or 3. If messages are shorter than 256 1 octet is
    enough and if they are longer than 255 and shorter than 65535 the 3 octet should be
    used. First octet holds b"\x01" and the last 2 holds the length.
    """

    length: int
    type: MessageType


@attr.s(auto_attribs=True)
class Flags:
    dup: bool = attr.ib(default=False)
    qos: int = attr.ib(default=1)  # TODO: only 0-2
    retain: bool = attr.ib(default=False)
    will: bool = attr.ib(default=False)
    clean_session: bool = attr.ib(default=False)
    topic_type: TopicType = attr.ib(default=TopicType.NORMAL)


@attr.s(auto_attribs=True)
class Connect:
    msg_type: ClassVar[MessageType] = MessageType.CONNECT
    flags: Flags
    duration: int
    client_id: bytes

    @property
    def length(self) -> int:
        return 5 + len(self.client_id)

    def to_bytes(self):
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type.value)
        out.extend(b"\x00")
        out.extend(self.duration.to_bytes(2, "big"))
        out.extend(self.client_id)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        # TODO: Check if length is 3 bytes
        msg_type = MessageType(data.pop(0))
        # print(msg_type)
        if msg_type is not MessageType.CONNECT:
            raise ValueError()
        flags = data.pop(0)
        duration = int.from_bytes(data[:2], "big")
        client_id = bytes(data[2:])
        return cls(flags=Flags(), duration=duration, client_id=client_id)


@attr.s(auto_attribs=True)
class Connack:

    msg_type: ClassVar[MessageType] = MessageType.CONNACK
    return_code: ReturnCode
    @property
    def length(self) -> int:
        return 2

    def to_bytes(self) -> bytes:
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type.value)
        out.append(self.return_code.value)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        return cls


@attr.s(auto_attribs=True)
class Register:
    msg_type: ClassVar[MessageType] = MessageType.REGISTER

    msg_id: bytes
    topic_name: str
    topic_id: Optional[int]

    @property
    def length(self) -> int:
        # TODO: handle large payload length
        return 1 + 2 + 2 + len(self.topic_name)

    @classmethod
    def from_bytes(cls, source_bytes: bytes):
        data = bytearray(source_bytes)
        initial_length = data.pop(0)
        if initial_length == 1:
            # Indicates that 3 bytes are used for the length.
            # Next 2 bytes indicates the lenght.
            length = int.from_bytes(data[:2], "big")
            data = data[2:]
        else:
            length = initial_length
        if length != len(data):
            raise ValueError("lenght is not correct")

        message_type = MessageType(data.pop(0))

        topic_id = bytes(data[:2])
        if topic_id == b"\x00\x00":
            topic_id = None
        else:
            topic_id = int.from_bytes(topic_id, 'big')
        data = data[2:]

        msg_id = bytes(data[:2])
        data = data[2:]

        topic_name = bytes(data).decode()

        return cls(msg_id=msg_id, topic_name=topic_name, topic_id=topic_id)


@attr.s(auto_attribs=True)
class Regack:
    msg_type: ClassVar[MessageType] = MessageType.REGACK
    topic_id: Optional[int]
    msg_id: bytes
    return_code: ReturnCode
    @property
    def length(self) -> int:
        return 1 + 2 + 2 + 1

    def to_bytes(self):
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type.value)
        if self.topic_id:
            out.extend(self.topic_id.to_bytes(2, 'big'))
        else:
            out.extend(b"\x00\x00")
        out.extend(self.msg_id)
        out.append(self.return_code.value)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        return cls


@attr.s(auto_attribs=True)
class Publish:
    msg_type: ClassVar[MessageType] = MessageType.PUBLISH
    flags: Flags
    topic_id: int
    msg_id: bytes
    data: bytes

    @classmethod
    def from_bytes(cls, source_bytes: bytes):
        data = bytearray(source_bytes)
        initial_length = data.pop(0)
        if initial_length == 1:
            # Indicates that 3 bytes are used for the length.
            # Next 2 bytes indicates the lenght.
            length = int.from_bytes(data[:2], "big")
            data = data[2:]
        else:
            length = initial_length
        if length != len(data):
            raise ValueError("lenght is not correct")

        message_type = MessageType(data.pop(0))
        if message_type != MessageType.PUBLISH:
            raise ValueError("Not a publish message")

        flags = data.pop(0)
        topic_id = int.from_bytes(data[:2], 'big')
        data = data[2:]
        msg_id = bytes(data[:2])
        payload = bytes(data)

        return cls(flags=Flags(), topic_id=topic_id, msg_id=msg_id, data=payload)


@attr.s(auto_attribs=True)
class Puback:
    msg_type: ClassVar[MessageType] = MessageType.PUBACK
    topic_id: int
    msg_id: bytes
    return_code: ReturnCode
    
    @property
    def length(self) -> int:
        return 1 + 2 + 2 + 1

    def to_bytes(self):
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type)
        out.extend(self.topic_id.to_bytes(2, 'big'))
        out.extend(self.msg_id)
        out.append(self.return_code)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        return cls


@attr.s(auto_attribs=True)
class Disconnect:
    msg_type: ClassVar[MessageType] = MessageType.DISCONNECT
    length: int
    duration: int

    @classmethod
    def from_bytes(cls, source_bytes):
        return cls


@attr.s(auto_attribs=True)
class MessageFactory:
    @staticmethod
    def from_bytes(soure_bytes: bytes) -> MqttSnMessage:
        data = bytearray(soure_bytes)
        initial_length = data.pop(0)
        if initial_length == 1:
            # Indicates that 3 bytes are used for the length.
            # Next 2 bytes indicates the lenght.
            length = int.from_bytes(data[:2], "big")
            data = data[2:]
        else:
            length = initial_length

        message_type = MessageType(data.pop(0))

        if message_type == MessageType.CONNECT:
            return Connect.from_bytes(soure_bytes)
        elif message_type == MessageType.CONNACK:
            return Connack.from_bytes(soure_bytes)
        elif message_type == MessageType.PUBLISH:
            return Publish.from_bytes(soure_bytes)
        elif message_type == MessageType.PUBACK:
            return Puback.from_bytes(soure_bytes)
        elif message_type == MessageType.REGISTER:
            return Register.from_bytes(soure_bytes)
        elif message_type == MessageType.REGACK:
            return Regack.from_bytes(soure_bytes)
        else:
            raise ValueError(f"{message_type} is not supported")


# TODO: What is dup?
