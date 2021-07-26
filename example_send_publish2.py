import socket
import time
HOST, PORT = "localhost", 9999

msg = b'\xa2\x0c\xa0\x00\x01\xc7\x92{"TS":"2021-07-05T18:00:00Z","ID":224396,"E":184,"U":"kWh","V":6580,"VU":"l","P":0,"PU":"W","F":0,"FU":"l/h","FT":0,"TU":"C","RT":0,"RU":"C","EF":"0x0421"}'

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("localhost", 33000))
count = 0
while True:
    s.sendto(msg, (HOST, PORT))
    count += 1
    print(count)

    time.sleep(0.0005)