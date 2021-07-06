import socket

HOST, PORT = "localhost", 2883

msg = b'\x0e\x0a\x00\x00\x00\x01testtopic'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
s.sendto(msg, (HOST, PORT))
