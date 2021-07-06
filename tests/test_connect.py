import pytest
from mqtt_sn_gateway import messages


class TestConnect:

    def test_parse(self):
        data = b'\x16\x04\x04\x01\xfd 94193A04010020B8'
        msg = messages.Connect.from_bytes(data)

        assert msg.length == 22
        assert msg.msg_type == messages.MessageType.CONNECT
        assert msg.flags == messages.Flags(dup=False, qos=0, retain=False, will=False, clean_session=True, topic_type= messages.TopicType.NORMAL)
        assert msg.duration == int.from_bytes(b"\xfd ", 'big')
        assert msg.client_id == b'94193A04010020B8'

