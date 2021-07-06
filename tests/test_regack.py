from mqtt_sn_gateway import messages


class TestRegack:
    def test_parse(self):
        data = b"\x07\x0b\x00\x01Oi\x00"
        msg = messages.Regack.from_bytes(data)
        assert msg.length == len(data)
        assert msg.msg_type == messages.MessageType.REGACK
        assert msg.return_code == messages.ReturnCode.ACCEPTED
        assert msg.msg_id == b"Oi"
        assert msg.topic_id == 1

    def test_to_bytes(self):

        msg = messages.Regack(
            topic_id=1, msg_id=b"Oi", return_code=messages.ReturnCode.ACCEPTED
        )
        assert msg.to_bytes() == b"\x07\x0b\x00\x01Oi\x00"
