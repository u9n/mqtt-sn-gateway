import socket

HOST, PORT = "localhost", 9999

msg = b'\x0e\x0c\x00\x00\x01\x00\x01testdata'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
count = 0
while True:
    s.sendto(msg, (HOST, PORT))
    count += 1
    print(count)