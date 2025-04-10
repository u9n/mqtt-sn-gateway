from attrs import define, field
from enum import IntEnum
from typing import *
import structlog

LOG = structlog.get_logger(__name__)

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


@define
class Header:
    """
    Length can be either 1 octet or 3. If messages are shorter than 256 1 octet is
    enough and if they are longer than 255 and shorter than 65535 the 3 octet should be
    used. First octet holds b"\x01" and the last 2 holds the length.
    """

    length: int
    type: MessageType


@define
class Flags:
    dup: bool = field(default=False)
    qos: int = field(default=1)  # TODO: only 0-2
    retain: bool = field(default=False)
    will: bool = field(default=False)
    clean_session: bool = field(default=False)
    topic_type: TopicType = field(default=TopicType.NORMAL)

    @classmethod
    def from_bytes(cls, source_byte: bytes):
        if len(source_byte) != 1:
            raise ValueError(f"Flags are only 1 byte. Got {len(source_byte)}")
        val = int.from_bytes(source_byte, "big")
        dup = bool(val & 0b10000000)
        qos = (val & 0b01100000) >> 5
        retain = bool(val & 0b00010000)
        will = bool(val & 0b00001000)
        clean_session = bool(val & 0b00000100)
        topic_type = TopicType(val & 0b00000011)
        return cls(
            dup=dup,
            qos=qos,
            retain=retain,
            will=will,
            clean_session=clean_session,
            topic_type=topic_type,
        )

    def to_bytes(self) -> bytes:
        out = 0
        if self.dup:
            out += 0b10000000
        out += self.qos << 5
        if self.retain:
            out += 0b00010000
        if self.will:
            out += 0b00001000
        if self.clean_session:
            out += 0b00000100
        out += self.topic_type.value
        return out.to_bytes(1, "big")


# TODO: Length is including the length bytes!


@define
class Connect:
    msg_type: ClassVar[MessageType] = MessageType.CONNECT
    flags: Flags
    duration: int
    client_id: bytes

    @property
    def length(self) -> int:
        return 6 + len(self.client_id)

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
        if msg_type is not MessageType.CONNECT:
            raise ValueError()

        flags = Flags.from_bytes(data.pop(0).to_bytes(1, "big"))
        protocol_id = data.pop(0)
        if protocol_id != PROTOCOL_ID:
            raise ValueError("Wrong protocol_id")
        duration = int.from_bytes(data[:2], "big")
        client_id = bytes(data[2:])
        return cls(flags=flags, duration=duration, client_id=client_id)


@define
class Connack:
    msg_type: ClassVar[MessageType] = MessageType.CONNACK
    return_code: ReturnCode

    @property
    def length(self) -> int:
        return 3

    def to_bytes(self) -> bytes:
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type.value)
        out.append(self.return_code.value)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        if length != 3:
            raise ValueError("Incorrect length for a CONNACK")
        msg_type = MessageType(data.pop(0))
        if msg_type != MessageType.CONNACK:
            raise ValueError("Data is not a CONNACK")
        return_code = ReturnCode(data.pop(0))
        return cls(return_code=return_code)


@define
class Register:
    msg_type: ClassVar[MessageType] = MessageType.REGISTER

    msg_id: bytes
    topic_name: str
    topic_id: Optional[int]

    @property
    def length(self) -> int:
        # TODO: handle large payload length
        return 2 + 2 + 2 + len(self.topic_name)

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
        if length != len(source_bytes):
            raise ValueError("lenght is not correct")

        message_type = MessageType(data.pop(0))

        topic_id_data = bytes(data[:2])
        if topic_id_data == b"\x00\x00":
            topic_id = None
        else:
            topic_id = int.from_bytes(topic_id_data, "big")
        data = data[2:]

        msg_id = bytes(data[:2])
        data = data[2:]

        topic_name = bytes(data).decode()

        return cls(msg_id=msg_id, topic_name=topic_name, topic_id=topic_id)


@define
class Regack:
    msg_type: ClassVar[MessageType] = MessageType.REGACK
    topic_id: Optional[int]
    msg_id: bytes
    return_code: ReturnCode

    @property
    def length(self) -> int:
        return 2 + 2 + 2 + 1

    def to_bytes(self):
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type.value)
        if self.topic_id:
            out.extend(self.topic_id.to_bytes(2, "big"))
        else:
            out.extend(b"\x00\x00")
        out.extend(self.msg_id)
        out.append(self.return_code.value)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        if length != len(source_bytes):
            raise ValueError("Incorrect length")
        msg_type = MessageType(data.pop(0))
        if msg_type != MessageType.REGACK:
            raise ValueError("Not a REGACK message")
        topic_id = int.from_bytes(data[:2], "big")
        data = data[2:]
        msg_id = bytes(data[:2])
        data = data[2:]
        return_code = ReturnCode(data.pop(0))
        return cls(topic_id=topic_id, msg_id=msg_id, return_code=return_code)


@define
class Publish:
    msg_type: ClassVar[MessageType] = MessageType.PUBLISH
    flags: Flags
    topic_id: int
    msg_id: bytes
    data: bytes

    @property
    def length(self) -> int:
        return 1 + 1 + 1 + 2 + 2 + len(self.data)

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
        if length != len(source_bytes):
            raise ValueError("lenght is not correct")

        message_type = MessageType(data.pop(0))
        if message_type != MessageType.PUBLISH:
            raise ValueError("Not a publish message")

        flags = Flags.from_bytes(data.pop(0).to_bytes(1, "big"))
        topic_id = int.from_bytes(data[:2], "big")
        data = data[2:]
        msg_id = bytes(data[:2])
        data = data[2:]
        payload = bytes(data)

        return cls(flags=flags, topic_id=topic_id, msg_id=msg_id, data=payload)


@define
class Puback:
    msg_type: ClassVar[MessageType] = MessageType.PUBACK
    topic_id: int
    msg_id: bytes
    return_code: ReturnCode

    @property
    def length(self) -> int:
        return 2 + 2 + 2 + 1

    def to_bytes(self):
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type)
        out.extend(self.topic_id.to_bytes(2, "big"))
        out.extend(self.msg_id)
        out.append(self.return_code)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        if length != len(source_bytes):
            raise ValueError("Incorrect length")
        msg_type = MessageType(data.pop(0))
        if msg_type != MessageType.PUBACK:
            raise ValueError("Not a PUBACK message")
        topic_id = int.from_bytes(data[:2], "big")
        data = data[2:]
        msg_id = bytes(data[:2])
        data = data[2:]
        return_code = ReturnCode(data.pop(0))
        return cls(topic_id=topic_id, msg_id=msg_id, return_code=return_code)


@define
class Pingreq:
    msg_type: ClassVar[MessageType] = MessageType.PINGREQ

    client_id: bytes | None

    @property
    def length(self) -> int:
        if self.client_id is None:
            return 2
        else:
            return 2 + len(self.client_id)

    def to_bytes(self):
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type)
        out.extend(self.client_id)
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        if length != len(source_bytes):
            raise ValueError("Incorrect length")
        msg_type = MessageType(data.pop(0))
        if msg_type != MessageType.PINGREQ:
            raise ValueError("Not a PINGREQ message")
        rest = bytes(data)
        if data:
            client_id = rest
        else:
            client_id = None
        return cls(client_id=client_id)


@define
class Pingresp:
    msg_type: ClassVar[MessageType] = MessageType.PINGRESP

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        if length != len(source_bytes):
            raise ValueError("Incorrect length")
        msg_type = MessageType(data.pop(0))
        if msg_type != MessageType.PINGRESP:
            raise ValueError("Not a PINGRESP message")
        return cls()

    def to_bytes(self):
        out = bytearray()
        out.append(2)  # length
        out.append(self.msg_type)
        return bytes(out)


@define
class Disconnect:
    msg_type: ClassVar[MessageType] = MessageType.DISCONNECT
    duration: Optional[int] = field(default=None)

    @property
    def length(self):
        if self.duration:
            return 4
        else:
            return 2

    def to_bytes(self) -> bytes:
        out = bytearray()
        out.append(self.length)
        out.append(self.msg_type)
        if self.duration:
            out.extend(self.duration.to_bytes(2, 'big'))
        return bytes(out)

    @classmethod
    def from_bytes(cls, source_bytes):
        data = bytearray(source_bytes)
        length = data.pop(0)
        msg_type = data.pop(0)
        if msg_type != cls.msg_type:
            raise ValueError("Not a DISCONNECT message")
        if length == 2:
            return cls(duration=None)
        else:
            duration = int.from_bytes(data, 'big')
            return cls(duration=duration)


class ParsingError(Exception):
    """Unable to parse data into MQTT-SN Message"""


@define
class MessageFactory:
    @staticmethod
    def from_bytes(source_bytes: bytes) -> Optional[MqttSnMessage]:
        """
        :raises ParsingError:
        """
        try:
            data = bytearray(source_bytes)
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
                return Connect.from_bytes(source_bytes)
            elif message_type == MessageType.CONNACK:
                return Connack.from_bytes(source_bytes)
            elif message_type == MessageType.PUBLISH:
                return Publish.from_bytes(source_bytes)
            elif message_type == MessageType.PUBACK:
                return Puback.from_bytes(source_bytes)
            elif message_type == MessageType.REGISTER:
                return Register.from_bytes(source_bytes)
            elif message_type == MessageType.REGACK:
                return Regack.from_bytes(source_bytes)
            elif message_type == MessageType.PINGREQ:
                return Pingreq.from_bytes(source_bytes)
            else:
                raise ValueError(f"{message_type} is not supported")
        except Exception:
            raise ParsingError("Unable to create MQTT-SN message")

# TODO: What is dup?
