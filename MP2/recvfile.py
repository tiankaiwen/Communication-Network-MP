"""
Receive a file using the MP2 transport
"""

import sys
import os
if os.environ.get("MP2_TEST", None) == "yes":
    from transport_cffi import MP2Socket, MP2SocketError
else:
    from transport import MP2Socket, MP2SocketError

if len(sys.argv) != 3:
    print("Usage: python {} <port> <filename>".format(__file__))
    sys.exit(1)

port = int(sys.argv[1])
filename = sys.argv[2]

f = open(filename, 'wb')

socket = MP2Socket()
try:
    (client_host, client_port) = socket.accept(port)
except MP2SocketError:
    print("Error connecting to host")
    sys.exit(1)

print("Got connection from {}:{}".format(client_host, client_port))
while True:
    data = socket.recv(1024)
    if not data:
        break
    f.write(data)

f.close()
socket.close()
print("Receiving successful")
