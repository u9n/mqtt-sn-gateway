import socket

HOST, PORT = "localhost", 9999

msg = b'\x0f\x04\x00\x00dtestclient'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
s.sendto(msg, (HOST, PORT))
