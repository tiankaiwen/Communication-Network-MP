import sys
import fileinput

import socket
import copy
import time
import select

ASNum = int(sys.argv[1])
tcpPort = int(sys.argv[2])

prefixes = []
routes = []
peerASes = {}
customerASes = {}
providerASes = {}

clientSockets = {}#key = port client socket is connected to, data = the socket object


#Whenever a TCP connection is received we also have to add that connection to the dicts
def connectAS(type, host, port):
    #Establish a TCP connection here
    if host in peerASes or host in customerASes or host in providerASes:
        return

    connectToAS(port)
    if type == "customer":
        reverseType = "provider"
    elif type == "provider":
        reverseType = "customer"
    else:
        reverseType = "peer"

    connectMessage = "connect " + str(reverseType) + " " + str(ASNum)  + ":"+ str(tcpPort)
    sendMessageToAS(port, connectMessage)
    time.sleep(0.1)
    if host == "localhost":
        return
    #Add the AS number to each connection type dictionary and the value holds
    #All of the arrays contain the IP's each AS contains
    if type == "peer":
        peerASes[host] = port
        for route in routes:
            if len(route) == 1:
                time.sleep(0.1)
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                sendMessageToAS(port, message)
            elif route[1] in customerASes and host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(port, message)

    if type == "customer":
        customerASes[host] = port
        for route in routes:
            if len(route) == 1:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                time.sleep(0.1)
                sendMessageToAS(port, message)
            elif host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(port, message)

    if type == "provider":
        providerASes[host] = port
        for route in routes:
            if len(route) == 1:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                time.sleep(0.1)
                sendMessageToAS(port, message)
            elif route[1] in customerASes and host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(port, message)

def disconnectAS(host, port):
    #Disconnect from TCP here
    if host not in peerASes and host not in customerASes and host not in providerASes:
        return

    if host == "localhost":
        return

    for route in routes:
        if len(route) > 1:
            if host == route[1]:
                message = "W"
                for val in route:
                    message += " "
                    message += str(val)
                recvRoute(message)
        else:
            if host in customerASes:
                message = "W " + route[0] + " " + str(ASNum)
                sendMessageToAS(customerASes[host], message)
                time.sleep(0.1)
            if host in peerASes:
                message = "W " + route[0] + " " + str(ASNum)
                sendMessageToAS(peerASes[host], message)
                time.sleep(0.1)
            if host in providerASes:
                message = "W " + route[0] + " " + str(ASNum)
                sendMessageToAS(providerASes[host], message)
                time.sleep(0.1)

    if host in peerASes:
        peerASes.pop(host, None)
    if host in customerASes:
        customerASes.pop(host, None)
    if host in providerASes:
        providerASes.pop(host, None)

    disconnectMessage = "disconnect " + str(ASNum) + ":" + str(tcpPort)
    time.sleep(0.1)
    sendMessageToAS(port, disconnectMessage)
    time.sleep(0.1)
    closeConnectionToAS(port)

def recvRoute(routeUpdate):
    #Recieved a route from TCP by a connection
    splitRoute = routeUpdate.split(" ")
    routeType = splitRoute[0]
    splitRoute.pop(0)
    if routeType == "A":
        #If the route is being advertised
        if not routes:
            #If routes is empty add in the routes
            routes.append(splitRoute)
            sendBestRoute(splitRoute)
        else:
            bestRoute = True
            index = 0
            for route in routes:
                if splitRoute == route:
                    break
                if int(route[0].split(".")[0]) > \
                   int(splitRoute[0].split(".")[0]):
                    #If received IP address is less than route in list
                    routes.insert(index, splitRoute)
                    if bestRoute:
                        sendBestRoute(splitRoute)
                    break
                if int(route[0].split(".")[0]) == \
                   int(splitRoute[0].split(".")[0]):

                    if int(route[0].split(".")[1]) > \
                       int(splitRoute[0].split(".")[1]):
                        routes.insert(index, splitRoute)
                        if bestRoute:
                            sendBestRoute(splitRoute)
                        break
                        if int(route[0].split(".")[2]) > \
                           int(splitRoute[0].split(".")[2]):
                            routes.insert(index, splitRoute)
                            if bestRoute:
                                sendBestRoute(splitRoute)
                            break
                    if int(route[0].split("/")[0].replace('.', '')) > \
                       int(splitRoute[0].split("/")[0].replace('.', '')):
                        #If received IP address is less than route in list
                            routes.insert(index, splitRoute)
                            if bestRoute:
                                sendBestRoute(splitRoute)
                            break
                elif route[0].split("/")[0] == splitRoute[0].split("/")[0]:
                    if int(route[0].split("/")[1]) != int(splitRoute[0].split("/")[1]):
                        if int(route[0].split("/")[1]) > int(splitRoute[0].split("/")[1]):
                            #Lowest prefix comes first
                            routes.insert(index, splitRoute)
                            if bestRoute:
                                sendBestRoute(splitRoute)
                            break
                    elif route[1] in customerASes:
                        if splitRoute[1] in customerASes:
                            if len(splitRoute) < len(route):
                                routes.insert(index, splitRoute)
                                if bestRoute:
                                    sendBestRoute(splitRoute)
                                    break
                            else:
                                bestRoute = False
                    elif route[1] in peerASes:
                        if splitRoute[1] in customerASes:
                            routes.insert(index, splitRoute)
                            if bestRoute:
                                sendBestRoute(splitRoute)
                            break
                        elif splitRoute[1] in peerASes:
                            if len(splitRoute) < len(route):
                                routes.insert(index, splitRoute)
                                if bestRoute:
                                    sendBestRoute(splitRoute)
                                break
                            else:
                                bestRoute = False
                    elif route[1] in providerASes:
                        if splitRoute[1] in customerASes:
                            routes.insert(index, splitRoute)
                            if bestRoute:
                                sendBestRoute(splitRoute)
                            break
                        elif splitRoute[1] in peerASes:
                            routes.insert(index, splitRoute)
                            if bestRoute:
                                sendBestRoute(splitRoute)
                            break
                        elif splitRoute[1] in providerASes:
                            if len(splitRoute) > len(route):
                                routes.insert(index, splitRoute)
                                if bestRoute:
                                    sendBestRoute(splitRoute)
                                break
                            else:
                                bestRoute = False
                if route == routes[-1]:
                    routes.append(splitRoute)
                    if bestRoute:
                        sendBestRoute(splitRoute)
                    break
                index += 1

    elif routeType == "W":
        removedRoute = False
        if splitRoute in prefixes:
            prefixes.remove(splitRoute)
            removedRoute = True

        #If route is removed then advertise the next best route
        tempRoutes = routes[:]
        for i in xrange(0, len(tempRoutes)):
            if splitRoute == routes[i]:
                if i != len(routes) - 1:
                    if splitRoute[0] == routes[i + 1][0]:
                        sendBestRoute(routes[i + 1])
                routes.pop(i)
                removedRoute = True
                break

        if removedRoute:
            message = "W" + " " + splitRoute[0] + " " + str(ASNum)
            if len(splitRoute) > 1:
                for val in splitRoute[1:]:
                    message += " "
                    message += val
            for host in customerASes:
                sendMessageToAS(customerASes[host], message)
                time.sleep(0.1)
            for host in peerASes:
                sendMessageToAS(peerASes[host], message)
                time.sleep(0.1)
            for host in providerASes:
                sendMessageToAS(providerASes[host], message)
                time.sleep(0.1)

def sendBestRoute(route):
    if len(route) == 1:
        for host in customerASes:
            message = "A" + " " + str(route[0]) + " " + str(ASNum)
            time.sleep(0.1)
            sendMessageToAS(customerASes[host], message)
        for host in peerASes:
            message = "A" + " " + str(route[0]) + " " + str(ASNum)
            time.sleep(0.1)
            sendMessageToAS(peerASes[host], message)
        for host in providerASes:
            message = "A" + " " + str(route[0]) + " " + str(ASNum)
            time.sleep(0.1)
            sendMessageToAS(providerASes[host], message)
    elif route[1] in customerASes:
        for host in providerASes:
            if host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(providerASes[host], message)
                time.sleep(0.1)
        for host in peerASes:
            if host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(peerASes[host], message)
        for host in customerASes:
            if host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(customerASes[host], message)
                time.sleep(0.1)
    elif route[1] in peerASes:
        for host in customerASes:
            if host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(customerASes[host], message)
                time.sleep(0.1)
    elif route[1] in providerASes:
        for host in customerASes:
            if host not in route:
                message = "A" + " " + str(route[0]) + " " + str(ASNum)
                for val in route[1:]:
                    message += " "
                    message += str(val)
                time.sleep(0.1)
                sendMessageToAS(customerASes[host], message)
                time.sleep(0.1)

def advertiseAS(prefix):
    if not prefixes:
        prefixes.append(prefix)
    #Sort prefixes in the AS based on ip
    else:
        index = 0
        for val in prefixes:
            if val.split("/")[0] > prefix.split("/")[0]:
                prefixes.insert(index, prefix)
                break
            elif val.split("/")[0] == prefix.split("/")[0]:
                if int(val.split("/")[1]) == int(prefix.split("/")[1]):
                    break
                if int(val.split("/")[1]) > int(prefix.split("/")[1]):
                    prefixes.insert(index, prefix)
                    break
            if val == prefixes[-1]:
                prefixes.append(prefix)
                break
            index += 1
    #Add prefix into routes as a route of length 0
    if not routes:
        tempRoute = []
        tempRoute.append(prefix)
        routes.append(tempRoute)
        sendBestRoute(prefix)
    else:
        index = 0
        for route in routes:
            if int(route[0].split("/")[0].replace('.', '')) > \
               int(prefix.split("/")[0].replace('.', '')):
                tempRoute = []
                tempRoute.append(prefix)
                routes.insert(index, tempRoute)
                sendBestRoute(prefix)
                break
            elif route[0].split("/")[0] == prefix.split("/")[0]:
                if route[0].split("/")[1] > prefix.split("/")[1]:
                    tempRoute = []
                    tempRoute.append(prefix)
                    routes.insert(index, tempRoute)
                    break
            if route == routes[-1]:
                tempRoute = []
                tempRoute.append(prefix)
                routes.append(tempRoute)
                break
            index += 1

    for host in customerASes:
        message = "A" + " " + str(prefix) + " " + str(ASNum)
        time.sleep(0.1)
        sendMessageToAS(customerASes[host], message)
    for host in peerASes:
        time.sleep(0.1)
        message = "A" + " " + str(prefix) + " " + str(ASNum)
        sendMessageToAS(peerASes[host], message)
    for host in providerASes:
        message = "A" + " " + str(prefix) + " " + str(ASNum)
        time.sleep(0.1)
        sendMessageToAS(providerASes[host], message)

def withdrawAS(prefix):
    deleteRoute = "W " + str(prefix)
    recvRoute(deleteRoute)

def routesAS():
    print("BEGIN ROUTE LIST")
    for route in routes:
        routeString = ""
        for val in route:
            routeString += str(val)
            if val != route[-1]:
                routeString += " "
        print(routeString)
    print("END ROUTE LIST")

def bestIP(ip):
    bestRoute = ""
    for prefix in prefixes:
        if int(ip.replace('.', ''))>>int(prefix.split("/")[1]) == \
           int(prefix.split("/")[0].replace('.', ''))>>int(prefix.split("/")[1]):
            bestRoute = prefix
            return
        else:
            if bestRoute != "":
                print(bestRoute)
                return

    for route in routes:
        routeString = ""
        if int(ip.replace('.', ''))>>int(route[0].split("/")[1]) ==\
           int(route[0].split("/")[0].replace('.', ''))>>int(route[0].split("/")[1]):
            routeString = ""
            for val in route:
                routeString += val
                if val != route[-1]:
                    routeString += " "
        elif routeString != "":
            print(routeString)
            break
        elif route == routes[-1]:
            #If route is last route in routes and no match
            print("None")

def listPeers():
    print("BEGIN PEER LIST")
    for host in customerASes:
        printString = "customer localhost:" + str(customerASes[host])
        print(printString)
    for host in peerASes:
        printString = "peer localhost:" + str(peerASes[host])
        print(printString)
    for host in providerASes:
        printString = "provider localhost:" + str(providerASes[host])
        print(printString)
    print("END PEER LIST")

def quit():
    for prefix in prefixes:
        withdrawAS(prefix)
        time.sleep(0.1)

    tempCustomerASes = copy.deepcopy(customerASes)
    tempPeerASes = copy.deepcopy(peerASes)
    tempProviderASes = copy.deepcopy(providerASes)
    for host in tempCustomerASes:
        disconnectAS(host, customerASes[host])
    for host in tempPeerASes:
        disconnectAS(host, peerASes[host])
    for host in tempProviderASes:
        disconnectAS(host, providerASes[host])
    sys.exit(0)

def userInput(currInput):
    #print(currInput)
    currInputCommand = currInput.split(" ")[0]

    if currInputCommand == "connect":
        typeParam = currInput.split(" ")[1]
        hostPortParam = currInput.split(" ")[2]
        hostParam = hostPortParam.split(":")[0]
        portParam = hostPortParam.split(":")[1]
        connectAS(typeParam, hostParam, portParam)

    elif currInputCommand == "disconnect":
        hostPortParam = currInput.split(" ")[1]
        hostParam = hostPortParam.split(":")[0]
        portParam = hostPortParam.split(":")[1]
        if portParam in customerASes.itervalues():
            hostParam = customerASes.keys()[customerASes.values().index(portParam)]
        if portParam in peerASes.itervalues():
            hostParam = peerASes.keys()[peerASes.values().index(portParam)]
        if portParam in providerASes.itervalues():
            hostParam = providerASes.keys()[providerASes.values().index(portParam)]
        disconnectAS(hostParam, portParam)

    elif currInputCommand == "advertise":
        prefixParam = currInput.split(" ")[1]
        advertiseAS(prefixParam)

    elif currInputCommand == "withdraw":
        prefixParam = currInput.split(" ")[1]
        withdrawAS(prefixParam)

    elif currInputCommand == "routes":
        routesAS()

    elif currInputCommand == "best":
        ipParam = currInput.split(" ")[1]
        bestIP(ipParam)

    elif currInputCommand == "peers":
        listPeers()

    elif currInputCommand == "A" or currInputCommand == "W":
        if currInput.count('A') > 1:
            advertise1 = "A" + currInput.split("A")[1]
            advertise2 = "A" + currInput.split("A")[2]
            recvRoute(advertise1)
            time.sleep(0.1)
            recvRoute(advertise2)
        else:
            recvRoute(currInput)

    elif currInputCommand == "quit":
        quit()


#connect this AS to another AS
def connectToAS(port):
    port = int(port)
    clientSockets[port] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    clientSockets[port].connect(('',port))
    #print("Connected to: " + str(port))

#send a message to another AS
def sendMessageToAS(port, message):
    port = int(port)
    clientSockets[port].send(message)

#disconnect from another AS
def closeConnectionToAS(port):
    port = int(port)
    clientSockets[port].close()
    #print("Disconneted to: " + str(port))

def main():

    serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    serverSocket.setblocking(0)
    serverSocket.bind(('',tcpPort))
    serverSocket.listen(1)

    inputs = [serverSocket,sys.stdin]
    outputs = []

    while inputs:
        readable,writable,exceptional=select.select(inputs,outputs,inputs)

        for read in readable:
            #a new AS wants to talk to us
            if read is serverSocket:
                connection, client_address = read.accept()
                connection.setblocking(0)
                inputs.append(connection)#a new AS can talk to us

            #user wants to write something in terminal
            elif read is sys.stdin:
                userInput(sys.stdin.readline().split("\n")[0])

            #a seen AS is sending us a message
            else:
                userInput(read.recv(1024))


main()
