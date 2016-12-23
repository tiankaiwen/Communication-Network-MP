from socket import *
import sys

def init():
    if(len(sys.argv)!=2):
        print("ERROR: pass in one argument - port number")
    else:
        portNumber = int(sys.argv[1])
        serverName = "localhost"

        clientSocket = socket(AF_INET, SOCK_STREAM)

        clientSocket.connect((serverName,portNumber))

        totalInput = ""
        currInput = raw_input() + "\n"
        totalInput+=currInput

        #headers
        while(currInput!="\n"):
            currInput = raw_input() + "\n"
            totalInput+=currInput

        clientSocket.send(totalInput.encode())

        ret = clientSocket.recv(1024)
        totalRet = ret
        first = True

        while first or len(ret) >= 1024:
            first = False
            ret = clientSocket.recv(1024)
            totalRet += ret






        return totalRet

        #clientSocket.close()

init()
