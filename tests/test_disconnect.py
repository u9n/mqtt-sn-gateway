from mqtt_sn_gateway import messages


class TestDisconnect:
    def test_parse(self):
        data = b'\x02\x18'
        msg = messages.Disconnect.from_bytes(data)
        assert msg.length == len(data)
        assert msg.msg_type == messages.MessageType.DISCONNECT
        assert msg.duration is None


    def test_to_bytes(self):

        msg = messages.Disconnect()
        assert msg.to_bytes() == b'\x02\x18'

    def test_parse_with_duration(self):
        data = b'\x04\x18\x00\x0a'
        msg = messages.Disconnect.from_bytes(data)
        assert msg.length == len(data)
        assert msg.msg_type == messages.MessageType.DISCONNECT
        assert msg.duration == 10

    def test_to_bytes_with_duration(self):

        msg = messages.Disconnect(duration=10
        )
        assert msg.to_bytes() == b'\x04\x18\x00\x0a'

