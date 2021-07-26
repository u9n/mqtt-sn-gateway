import socket

HOST, PORT = "localhost", 9999

msg = b'\x16\x04\x04\x01\xfd 94193A04010020B8'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
s.sendto(msg, (HOST, PORT))
