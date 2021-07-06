
from mqtt_sn_gateway import messages

class TestConnack:

    def test_parse(self):
        data = bytes.fromhex("030500")
        msg = messages.Connack.from_bytes(data)
        assert msg.length == 3
        assert msg.msg_type == messages.MessageType.CONNACK
        assert msg.return_code == messages.ReturnCode.ACCEPTED

    def test_to_bytes(self):

        msg = messages.Connack(return_code=messages.ReturnCode.ACCEPTED)
        assert msg.to_bytes() == bytes.fromhex("030500")