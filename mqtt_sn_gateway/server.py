from socketserver import ThreadingUDPServer, BaseRequestHandler
from typing import *
import paho.mqtt.client as mqtt


from topics import InMemoryTopicStore
import messages


class MQTTSNServer(ThreadingUDPServer):


    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Callable[..., BaseRequestHandler],
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.mqtt_connection = None
        self.topic_store = InMemoryTopicStore()
        self.count = 0
        self.mqtt = mqtt.Client()
        self.mqtt.connect("localhost")
        self.mqtt.loop_start()


class MQTTSNHandler(BaseRequestHandler):
    def __init__(self, request: Any, client_address: Any, server: MQTTSNServer):
        super().__init__(request, client_address, server)


    def handle(self) -> None:
        data = self.request[0]
        socket = self.request[1]
        self.server.count += 1
        #print(self.server.count)
        msg = messages.Connect.from_bytes(data)
        #print(msg)
        self.server.mqtt.publish(f"mytopic/test/now{self.server.count}", b"skjdfnskdjfn")

        if isinstance(msg, messages.Publish):
            self.server.mqtt.publish(f"mytopic/test/now{self.server.count}", msg.data, qos=msg.flags.qos)



if __name__ == "__main__":
    msg = messages.Connect(duration=100, flags=messages.Flags(), client_id=b"testclient")
    print(msg.to_bytes())
    HOST, PORT = "localhost", 9999
    with MQTTSNServer((HOST, PORT), MQTTSNHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.mqtt.loop_stop(force=True)


