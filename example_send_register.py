import socket

HOST, PORT = "localhost", 1883

msg = b"'\n\x00\x00\xff\xcbmr/94193A04010020B8/standard/json"
msg = bytes.fromhex("200a00000cd36d722f393431393341303430333031443934352f393639373935")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
s.sendto(msg, (HOST, PORT))
