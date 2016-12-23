#possible things:
#   read all headers to check if doing things correctly
#   return values of accept()
#   the first time skip for send, possible errors?
#   stop a client from recv and a server from send?

#   will client ever send new stuff to server after finished first?
#       ehh


#   update timeouts of everything after first timeout?
#   what pieces of information used to gage
#   splitting up in send
#



#server has a buffer, need to limit too many packets
#you will send something, wait for ack
#use distance

#congestion control - packet will drop in middle
#once recieved 3 ACK, you know packet has been dropped
#just do linear

#
#AIMD ->

#timeout should be 2*RTT, RTT should be timed myself

#need to use selective repeat

#possible error: concating to MTU

# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import socket
import time
from random import randint

#read only global vars

DATA_SYN = "DATA_SYN"
DATA_ACK = "DATA_ACK"
DATA_KIL = "DATA_KIL"

MTU = 1500 #maximum transmission unit, 1500B
BUFFER_SIZE_B = 100000 #100KB

BUFFER_SIZE = 67 #(BUFFER_SIZE_B / MTU)
SENT_AND_ACKED = -1
SENT_AND_NOT_ACKED = -2
NOT_SENT = -3



ACKED = -4
EXPECTED = -5
ACCEPTABLE = -6

PACKET_LENGTH = 20

TO_HANDSHAKE = 2 #2 seconds for handshake timeout

DROP_PACKETS = True

LOST_PRECISION = .000099

MAX_PACKET_LENGTH = 30

FACTOR = 240


class MP2SocketError(Exception):
    """ Exception base class for protocol errors """
    pass

class MP2Socket:
    def __init__(self):

        #when you do time.time, you need to mult by 1000 to make it millisecs

        self.host = None
        self.port = None

        self.serverSocket = None
        self.clientSocket = None

        self.nextSeqNumBuffer = 0 #for the buffer indexing (bound to buffer)
        self.nextSeqNumACK = 0    #for the ACK nums (not bound to buffer)
        self.sendBaseACK = 0      #(not bound to buffer)
        self.clientBuffer = []    #67 arrays of 3 elements
        for i in range(BUFFER_SIZE):
            self.clientBuffer.append([NOT_SENT,None,None]) #tuple(code,time,data)

        self.rcvBaseACK = 0 #(not bound to buffer)
        self.serverBuffer = []
        for i in range(BUFFER_SIZE):
            self.serverBuffer.append(None)

        self.RTT = .2
        self.CONGESTION_OFFSET = 0
        self.SLOW_NETWORK = False

        self.numBytesExpected = 0#number of bytes expected to send
        self.numBytesRecv = 0

        self.SENDER_EXPECTED_PACKET_NUM = 0
        self.RECIEVER_EXPECTED_PACKET_NUM = 0
        self.SENDER_LAST_SEEN_PACKET_NUM = 0
        self.RECIEVER_LAST_SEEN_PACKET_NUM = 0


        self.IS_CLIENT = False
        self.IS_SERVER = False

        self.totalBPS = 0
        self.numBPS = 0

        self.connectTries = 10

        pass


    def spinClientBuf(self):
        while self.clientBuffer[0][0]==SENT_AND_ACKED:
            self.sendBaseACK+=1
            self.nextSeqNumBuffer-=1
            for i in range(len(self.clientBuffer)-1):
                self.clientBuffer[i] = self.clientBuffer[i+1]
            self.clientBuffer[len(self.clientBuffer)-1] = [NOT_SENT,None,None]

    #returns all in order data that is avaliable
    def spinServerBuf(self):
        ret = ""
        while self.serverBuffer[0]!=None:
            ret += self.serverBuffer[0]
            self.rcvBaseACK+=1
            self.nextSeqNumBuffer-=1
            for i in range(len(self.serverBuffer)-1):
                self.serverBuffer[i] = self.serverBuffer[i+1]
            self.serverBuffer[len(self.serverBuffer)-1] = None
        return ret

###  CLIENT  ###


    #socket is blocking here
    def connect(self, addr):
        """
        Connects to a remote MP2 transport server. Address is specified by a
        pair `(host,port)`, where `host` is a string with either an IP address
        or a hostname, and `port` is a UDP port where data will arrive

        A client must call `connect` as the first operation on the socket.

        This call raises MP2SocketError if a connection cannot be established.
        It does not return any value on success

        similar to client, uses send
        """

        self.IS_CLIENT = True


        if len(addr) != 2:
            raise MP2SocketError

        self.host = addr[0]
        self.port = addr[1]

        self.clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        #performing handshake
        self.clientSocket.settimeout(TO_HANDSHAKE)

        #send a SYN
        self.clientSocket.sendto(DATA_SYN,(self.host,self.port))
        modifiedMessage = None
        try:
            #wait to recieve a SYNACKs
            modifiedMessage, serverAddress = self.clientSocket.recvfrom(2048)
        except socket.timeout:
            self.connectTries -= 1
            if self.connectTries <= 0:
                raise MP2SocketError#SYNACK did not come back in time
                return
            return self.connect(addr)

        if not modifiedMessage:
            raise MP2SocketError#no data came back

        if modifiedMessage != DATA_SYN+DATA_ACK:
            raise MP2SocketError#data came back, was not SYNACK

        #SYNACK came in successfully

        #send an ACK
        #self.clientSocket.sendto(DATA_ACK,(self.host,self.port))

        #must set to non blocking in order to send and recv at same time
        self.clientSocket.setblocking(0)

        pass

    #socket is non blocking in send
    def send(self, data):
        """
        Send data to the remote destination. Data may be of arbitrary length
        and should be split into smaller packets. This call should block
        for flow control, though you can buffer some small amount of data.
        This call should behave like `sendall` in Python; i.e., all data must
        be sent. Does not return any value.

        Should be called on a socket after connect or accept
        """


        #this is used to measure the amount of bytes we think we should get
        #back. this is necessary because when send is last called, there may
        #be some packets still coming back from the server and thus we need
        #to get those packets in .close(), the only way we can know how many
        #bytes to recieve in close is by counting them here
        self.numBytesExpected += len(data)

        #necessary? it never happens
        if len(data)>MTU:
            print("ERROR: TOO LARGE, YOU NEED TO BREAK UP DATA")

        if not self.clientSocket:
            return

        while(1):

            #try to get some ACKs back from server
            try:

                #false is put into clientRecv because false means non blocking
                self.numBytesRecv += self.clientRecv(False)
                continue

            except socket.error:#exception occurs because there is nothing to recieve
                #otherwise, no data from server has come back to process, so
                #either send out data or wait for an ACK to come in

                if self.nextSeqNumBuffer >= (len(self.clientBuffer) - self.CONGESTION_OFFSET):
                    #we have sent as much as our buffer size is, wait for an ACK before
                    #send more data to server
                    continue

                #we can send more data because we have not filled our buffer
                #PACKET_CREATE
                toServerPacket = Packet(self.nextSeqNumACK,data,len(data),getTime(),Packet.getTotalBytes(self.nextSeqNumACK,data,len(data),getTime()))

                if randint(0,10000)>=2500 or not DROP_PACKETS:
                    self.clientSocket.sendto(toServerPacket.toString(), (self.host,self.port))
                #else:
                    #print "---DROPPED PACKET---"

                #tell our buffer that we have sent this part
                self.clientBuffer[self.nextSeqNumBuffer] = [SENT_AND_NOT_ACKED,toServerPacket.timeSent,data]

                #increment our currentSeqNum
                self.nextSeqNumBuffer += 1
                self.nextSeqNumACK += 1

                return#we sent our data, get next data


    #returns length of packet recieved
    #this function trys to recieve an ACK from the server,
    def clientRecv(self,isBlocking):
        #timeout!
        if self.clientBuffer[0][1] and getTime() - self.clientBuffer[0][1] > self.RTT:
            currData = self.clientBuffer[0][2]
            if (self.CONGESTION_OFFSET + (len(self.clientBuffer) - self.CONGESTION_OFFSET)/2) >= 10:
                self.CONGESTION_OFFSET += (len(self.clientBuffer) - self.CONGESTION_OFFSET)/2
            if self.RTT - 0.001 >= 0.04 and not self.SLOW_NETWORK:
                self.RTT -= 0.001
            elif self.RTT + 0.1 <= 1 and self.SLOW_NETWORK:
                self.RTT += 0.1
            #PACKET_CREATE
            toServerPacket = Packet(self.sendBaseACK,currData,len(currData),getTime(),Packet.getTotalBytes(self.sendBaseACK,currData,len(currData),getTime()))

            self.clientSocket.sendto(toServerPacket.toString(), (self.host,self.port))
            self.clientBuffer[0][1] = toServerPacket.timeSent
            return 0

        message = None
        clientAddress = None

        if isBlocking:
            try:
                message, clientAddress = self.clientSocket.recvfrom(2048)
            except:
                return -1

        else:

            #if there is an ACK to recv, this will happen and move on to next line
            #if there is NO ACK to recv, this raises an exception, goes back to
            #send()
            message, clientAddress = self.clientSocket.recvfrom(2048)

        #an ACK from server has come back, process it

        modifiedMessage = message
        modifiedMessage = modifiedMessage[:MTU]#concate to largest size

        fromServerPacket = Packet.stringToPacket(modifiedMessage)

        clientBufferIndex = fromServerPacket.expectedPacketNumber-self.sendBaseACK

        #print("recieving: "+str(fromServerPacket.expectedPacketNumber))

        if self.clientBuffer[clientBufferIndex][0] != SENT_AND_NOT_ACKED:
            print("ERROR: trying to ACK a space that has not been sent")

        self.clientBuffer[clientBufferIndex][0] = SENT_AND_ACKED

        if self.CONGESTION_OFFSET - 1 >= 0:
            self.CONGESTION_OFFSET -= 1
        if self.CONGESTION_OFFSET == 0:
            self.CONGESTION_OFFSET = 67 / 2 #Half the window to allow fairness

        #if self.RTT - 0.01 >= 0.2:
            #self.RTT -= 0.01

        #time it took to send this packet to server and back
        currPacketRTT = 0
        currPacketTimeToServer = 0


        if getTime() - self.clientBuffer[clientBufferIndex][1] > 0:
            currPacketRTT = getTime() - self.clientBuffer[clientBufferIndex][1]

        if (getTime() - self.clientBuffer[clientBufferIndex][1])/2 > 0:
            currPacketTimeToServer = (getTime() - self.clientBuffer[clientBufferIndex][1])/2

        if fromServerPacket.totalBytes:
            currBytesSentToServer = fromServerPacket.totalBytes

        if currPacketTimeToServer > 0:
            print(FACTOR*currBytesSentToServer / currPacketTimeToServer)
            if FACTOR*currBytesSentToServer / currPacketTimeToServer > 100000:
                self.SLOW_NETWORK = False
            else:
                self.SLOW_NETWORK = True



        #update buffer
        #moves all green blocks out until first packet is yellow
        self.spinClientBuf()

        return fromServerPacket.msgBytes


###   SERVER   ###

    #socket is blocking
    def accept(self, port):
        """
        Waits for a connection on a given (UDP) port. Returns a pair
        `(host,port)` representing the client address.

        A server must call `accept` as the first operation on the socket.

        Raises MP2SocketError if an error is encountered (e.g., UDP port
        already in use)

        similar to server, uses recv
        """

        self.IS_SERVER = True

        if not port:
            return

        self.serverSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.serverSocket.bind(("",port))

        #peforming handshake

        #recieving SYN
        message, clientAddress = self.serverSocket.recvfrom(2048)
        modifiedMessage = message

        if modifiedMessage == DATA_SYN:
            #SYN was recieved, send a SYNACK
            self.serverSocket.sendto((DATA_SYN+DATA_ACK),clientAddress)
        else:
            raise MP2SocketError#SYN was not recieved

        """
        #receving an ACK
        message, clientAddress = self.serverSocket.recvfrom(2048)
        modifiedMessage = message

        if modifiedMessage == DATA_ACK:
            #ACK was recieved, this is the end of the handshake
            self.serverSocket.setblocking(0)
            return ("",port)
        else:
            raise MP2SocketError#ACK was not recieved
        #here
        """

        self.serverSocket.setblocking(0)
        return ("",port)

        pass

    #socket is blocking
    def recv(self, length):
        timeRecv = getTime()
        """
        Receive data from the remote destination. Should wait until data
        is available, then return up to `length` bytes. Should return "" when
        the remote end closes the socket
        """

        ret = ""

        #continually ask for data (in order) until you have some to give
        while ret == "":

            try:
                message, clientAddress = self.serverSocket.recvfrom(length+MAX_PACKET_LENGTH)
                modifiedMessage = message

                fromClientPacket = Packet.stringToPacket(modifiedMessage)

                #if the client has called close
                if fromClientPacket.body == DATA_KIL:
                    return ""


                serverBufferIndex = fromClientPacket.expectedPacketNumber-self.rcvBaseACK
                #print(str(fromClientPacket.expectedPacketNumber)+" "+str(self.rcvBaseACK)+" "+str(serverBufferIndex))


                if serverBufferIndex >= len(self.serverBuffer):
                    print("ERROR: trying to access invalid server buffer index")

                #put in body of message into buffer
                self.serverBuffer[serverBufferIndex] = fromClientPacket.body


                #send the client the seqnum of the packet we just recieved
                #PACKET_CREATE
                toClientPacket = Packet(fromClientPacket.expectedPacketNumber,DATA_ACK,fromClientPacket.msgBytes,timeRecv,fromClientPacket.totalBytes)
                self.serverSocket.sendto(toClientPacket.toString(),clientAddress)

            except socket.error:
                yo = None

            ret = self.spinServerBuf()

        return ret

        pass




    def close(self):
        """
        Closes the socket and informs the other end that no more data will
        be sent

        client closes first after sending all data. this lets server know that
        it can stop recv and then server will close

        """

        if self.IS_CLIENT:

            # self.clientSocket.setblocking(1)
            # self.clientSocket.settimeout(self.RTT)

            while self.numBytesRecv < self.numBytesExpected:
                bytesRecv = self.clientRecv(True)
                if bytesRecv == -1:
                    continue
                self.numBytesRecv += bytesRecv




            #tell server to stop
            #PACKET_CREATE
            killPacket = Packet(-1,DATA_KIL,0,getTime(),0)
            self.clientSocket.sendto(killPacket.toString(), (self.host,self.port))

            if self.clientSocket:
                self.clientSocket.close()



        if self.IS_SERVER:
            if self.serverSocket:
                self.serverSocket.close()


        pass

#to add another parameter to header:
#increment NUM_HEADER_ARGS
#add parameter to __init__
#fill out __init__
#fill out toString
#update all packets

#number of items in the header including the body
NUM_HEADER_ARGS = 5
class Packet:#needs to be 20B or less

    def __init__(self,
        expectedPacketNumber,
        body,
        msgBytes,
        timeSent,
        totalBytes):
        self.expectedPacketNumber = expectedPacketNumber
        self.body = body
        self.msgBytes = msgBytes
        self.timeSent = timeSent
        self.totalBytes = totalBytes

        #self.newArg = newArg

    #0:     :body
    def toString(self):
        packetStr = ""
        packetStr+=str(self.expectedPacketNumber)+":"
        packetStr+=str(self.msgBytes)+":"
        packetStr+=str(self.timeSent)+":"
        packetStr+=str(self.totalBytes)+":"

        if len(packetStr) > MAX_PACKET_LENGTH:
            print("ERROR: reached MAX_PACKET_LENGTH")

        #packetStr += self.yourarg+":"

        #fill empty
        #for i in range(PACKET_LENGTH-1 - len(packetStr))
        #    packetStr+=" "
        #packetStr+=":"

        #append body
        packetStr+=self.body



        return packetStr

    @staticmethod
    def stringToPacket(dataStr):
        dataArr = dataStr.split(":")

        bodyStr = ""
        for i in range(NUM_HEADER_ARGS-1,len(dataArr)):
            bodyStr += dataArr[i] + ":"
        bodyStr = bodyStr[:-1]

        return Packet( int(dataArr[0]), bodyStr, int(dataArr[1]), float(dataArr[2]), int(dataArr[3]) )

        #return Packet(int(dataArr[0]),bodyStr,int(dataArr[1]), dataArr[2])

    @staticmethod
    def getTotalBytes(
        expectedPacketNumber,
        body,
        msgBytes,
        timeSent):
        ret = len(str(expectedPacketNumber)) + len(body) + len(str(msgBytes)) + len(str(timeSent)) + NUM_HEADER_ARGS-1
        ret += len(str(ret))
        return ret

def getTime():
    return float(str(time.time() - 1479081281.998683))
