from mqtt_sn_gateway import messages


class TestPublish:
    def test_parse(self):

        data = b'\xa2\x0c\xa0\x00\x01\xc7\x92{"TS":"2021-07-05T18:00:00Z","ID":224396,"E":184,"U":"kWh","V":6580,"VU":"l","P":0,"PU":"W","F":0,"FU":"l/h","FT":0,"TU":"C","RT":0,"RU":"C","EF":"0x0421"}'
        msg = messages.Publish.from_bytes(data)
        assert msg.data == b'{"TS":"2021-07-05T18:00:00Z","ID":224396,"E":184,"U":"kWh","V":6580,"VU":"l","P":0,"PU":"W","F":0,"FU":"l/h","FT":0,"TU":"C","RT":0,"RU":"C","EF":"0x0421"}'
        assert msg.length == len(data)
        assert msg.msg_type == messages.MessageType.PUBLISH
        assert msg.topic_id == 1
        assert msg.msg_id == b"\xc7\x92"
