from asyncio.transports import DatagramTransport
import asyncio
import time
HOST, PORT = "localhost", 9999
import socket



class EchoClientProtocol:
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        #print('Send:', self.message)
        self.transport.sendto(self.message)
        self.transport.close()

    def connection_lost(self, exc):
        #print("Connection closed")
        self.on_con_lost.set_result(True)

async def push_data():
    #writer = DatagramTransport()
    #writer.sendto(b"testetste", ("localhost", 9999))
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: EchoClientProtocol(b'\x0f\x04\x00\x00dtestclient', on_con_lost),
        remote_addr=('127.0.0.1', 9999))
    #s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #s.sendto(b'\x0f\x04\x00\x00dtestclient', (HOST, PORT))
    return on_con_lost



async def async_main():
    start = time.time()
    tasks = []
    errors = 0
    for _ in range(0, 10000):
        tasks.append(asyncio.create_task(push_data()))

    done, pending = await asyncio.wait(tasks)
    for task in done:
        try:
            task.result()
        except Exception:
            errors = +1

    stop = time.time()
    duration = stop - start
    print(duration)
    print(errors)


if __name__ == "__main__":
    asyncio.run(async_main())
