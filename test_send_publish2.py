import socket
import time
HOST, PORT = "localhost", 2883

msg = b'\x5a\x0c\x00\x00\x01\x00\x01testdata0000000000000000000000000000000000000000000000000000000000000000000000000001'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
count = 0
while True:
    s.sendto(msg, (HOST, PORT))
    count += 1
    print(count)

    time.sleep(0.0005)