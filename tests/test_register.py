from mqtt_sn_gateway import messages

class TestRegister:

    def test_parse(self):
        data = b"'\n\x00\x00\xff\xcbmr/94193A04010020B8/standard/json"
        msg = messages.Register.from_bytes(data)

        assert msg.length == len(data)
        assert msg.msg_type == messages.MessageType.REGISTER
        assert msg.topic_id is None  # alway zeros on client register
        assert msg.msg_id == b"\xff\xcb"
        assert msg.topic_name == "mr/94193A04010020B8/standard/json"

