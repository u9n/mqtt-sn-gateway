import socket

HOST, PORT = "localhost", 9999

msg = b'\x0b\x09\x00'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
s.sendto(msg, (HOST, PORT))
