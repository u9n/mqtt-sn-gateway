import socket

HOST, PORT = "10.25.0.218", 1884

msg = b'\x16\x04\x04\x01\xfd 94193A04010020B8'


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
print("sending")
s.sendto(msg, (HOST, PORT))
