import socket

HOST, PORT = "localhost", 1883

msg = b"'\n\x00\x00\xff\xcbmr/94193A04010020B8/standard/json"

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
s.sendto(msg, (HOST, PORT))
