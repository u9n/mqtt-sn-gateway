from mqtt_sn_gateway import messages


class TestPuback:
    def test_parse(self):
        data = b'\x07\r\x00\x01q\xf6\x00'
        msg = messages.Puback.from_bytes(data)
        assert msg.length == len(data)
        assert msg.msg_type == messages.MessageType.PUBACK
        assert msg.return_code == messages.ReturnCode.ACCEPTED
        assert msg.msg_id == b"q\xf6"
        assert msg.topic_id == 1

    def test_to_bytes(self):

        msg = messages.Puback(
            topic_id=1, msg_id=b"q\xf6", return_code=messages.ReturnCode.ACCEPTED
        )
        assert msg.to_bytes() == b'\x07\r\x00\x01q\xf6\x00'

