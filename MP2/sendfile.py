"""
Send a file using the MP2 transport
"""

import sys
import os
if os.environ.get("MP2_TEST", None) == "yes":
    from transport_cffi import MP2Socket, MP2SocketError
else:
    from transport import MP2Socket, MP2SocketError


if len(sys.argv) != 4:
    print("Usage: python {} <host> <port> <filename>".format(__file__))
    sys.exit(1)

host = sys.argv[1]
port = int(sys.argv[2])
filename = sys.argv[3]

f = open(filename, 'rb')

socket = MP2Socket()
try:
    socket.connect((host, port))
except MP2SocketError:
    print("Error connecting to host")
    sys.exit(1)

while True:
    data = f.read(1024)
    if not data:
        break
    socket.send(data)

f.close()
socket.close()
print("Sending successful")
