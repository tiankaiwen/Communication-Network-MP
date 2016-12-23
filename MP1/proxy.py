# -*- coding: utf-8 -*-

#hey kev, what's up
#so basically I added a lot of comments that tell you
#what you need to do to implement your cache into my
#code. I wrote some pseudo code around those areas
#that you'll need to change to fit your cache design.
#to test the code, do the following:
#   open a terminal and type:
#       python proxy.py 12000        (if 12000 is busy, use 12001, if 12001 is busy, use 12002....)
#   open another terminal and type:
#       python client.py 12000
#
#   then make your requests in the second terminal
#       GET http://serveur.fr/ HTTP/1.1
#       Host: serveur.fr
#
#   then hit enter twice
#
#
#since I cant connect to nikitas servers since im not
#on school's wifi, I can't guarentee the code I wrote
#works completely... implement your cache as best
#you can and we'll go over it on tuesday. be warned,
#I'll be getting back to school at 10pm on tuesday.


import sys, socket, datetime, time
from time import gmtime, strftime

class Cache(object):
    def __init__(self, cacheType, maxAge, header, data):
        self.cacheType = cacheType
        self.maxAge = maxAge
        self.currAge = 0
        self.header = header
        self.data = data
        self.lastCache = 0
        self.cacheData()

    def cacheData(self):
        if sys.getsizeof(self.data) <= 10000000:
            print("caching")
            self.lastCache = time.time()
            if self.cacheType == "public":
                #Save data if data is less than or equal to 10 MB
                self.header = self.header
                self.data = self.data
            elif self.cacheType == "private":
                #If private don't save data but save header
                self.header = self.header
                self.data = None
            else:
                self.header = None
                self.data = None

        else:
            #If data is greater than 10 MB then refuse cache
            self.data = None
        return self

    def getFullDict(self):
        self.currAge = time.time() - self.lastCache

        return self.header

    def hasTimedOut(self):
        self.currAge = time.time() - self.lastCache

        print("this has been in the cache for: "+str(self.currAge))
        print("this is expired at: "+str(self.maxAge))

        print(int(self.currAge) <= int(self.maxAge))

        if int(self.currAge) <= int(self.maxAge):
            #If not cache has not expired then just return cached object
            print("this has not expired")
            return False
        else:
            print("this has expired")
            #If cache has expired then send valdiation request
            return True

    def getFrenchDate(self):
        return dateToFrench(strftime("%a, %d %b %Y %H:%M:%S", gmtime(self.lastCache)))

    def resetTime(self,maxAge):
        maxAge = int(maxAge)
        self.maxAge = maxAge
        self.lastCache = time.time()
        return

    def getCurrAge(self):
        self.currAge = time.time() - self.lastCache
        return self.currAge

#constants:
BACKLOG = 1 #number of queued connections to socket
BUFSIZE = 1024 #the value of bufsize should be a relatively small power of 2, for example, 4096.

#SERVER_PORT = 8253
#SERVER_NAME = "borisov-mac.crhc.illinois.edu"

SERVER_PORT = 5800
SERVER_NAME = "ladushki.nikita.ca"
URL_CACHE = {}


def init():
    if(len(sys.argv)!=2):
        print("ERROR: pass in one argument - port number")
    else:
        portNumber = int(sys.argv[1])

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("",portNumber)) # "" = localhost
            sock.listen(BACKLOG) # listen for connections made to the socket.
        except socket.error as mesg:
            print(mesg)
            sys.exit(1)

        while 1:
            conn, addr = sock.accept()  # accept a connectiothe
                                        # conn is a new socket object, can send/recieve data
                                        # addr is the address bound to the socket

            URL = None

            cachedSent = False
            msg = conn.recv(BUFSIZE)
            requestVals = msg.split("\n");
            for request in requestVals:
                parameters = request.split(" ")
                if(parameters[0]=="Host:"):

                    URL = parameters[1]

                    print("The URL is: "+URL)

                    #If the cache has not timed out then return the cached data
                    if(URL in URL_CACHE.keys()):

                        print("The URL is in the cache")

                        if(not URL_CACHE[URL].hasTimedOut()):

                            print("The URL in the cache has not timed out")

                            CACHED_DATA_DICT = URL_CACHE[URL].getFullDict()#this is what you need to obtain from the cache
                                                                    #remeber to change the "AGE" header to show the
                                                                    #amount of time the item has been in the cache for

                            print("----------------------------------------")
                            print(CACHED_DATA_DICT)

                            tempAge = URL_CACHE[URL].getCurrAge()

                            retToClient = dictToResponse(CACHED_DATA_DICT,tempAge)

                            print("here is what we are giving the client:")
                            print("-------------START")
                            print(retToClient)
                            print("-------------END")

                            conn.send(retToClient)
                            cachedSent = True
                            break


                        else:
                            print("The URL in the cache has timed out")


            if(cachedSent):
                continue



            #HEY KEVIN!!!
            #so this function takes an english request such as:
            #     GET http://serveur.fr/ HTTP/1.1
            #     Host: serveur.fr
            #and turns it into a french request such as:
            #     OBTENIR / PdTHT/1.0
            #     Hôte: serveur.fr
            #     Via: 1.1 myproxy
            #BUT HERE'S WHERE YOU COME IN:
            #if this request has been cached BUT has passed
            #its max age, then we need to see if the response
            #from the server has changed.
            #we send a "Si-Modifié-Depuis:" in our header, this
            #tells the server that we dont want data, we just
            #want to see if the data has changed
            #if the server sends back a 304 Pas Modifié,
            #then the data has not changed, just send back
            #our cached data and increase the time on the cache
            #BUT, if we dont get back a 304 Pas Modifié,
            #then we need to make another request to the
            #server, this time asking for the data itself.
            #in this case, this is basically the same
            #as never having the data in the first place,
            #so we just do what we would do if a url came in

            #so, once you understand what I wrote above, go
            #to the processReq() function to see what you
            #have to do

            print("The URL is either not in the cache OR is in the cache but has timed out")

            convertedReq = processReq(msg,conn)


            #this means that the server told us the data
            #we were trying to get was not old enough and
            #thus we returned it from the cache
            #AKA we hit a 304
            if(convertedReq==False):

                print("the data was cached but timed out but did not change (304)")
                continue


            print("the url we requested has never been cached")

            print("here is the french request we made from the english request:")
            print("---------START")
            print(convertedReq)
            print("----------END")

            try:

                print("sending our french request to the server")

                #sends french request, gets english dict back
                engDict = sendToServer(convertedReq)

                print("the engDict we got back from the server:")
                print("---------START")
                print(engDict)
                print("----------END")

                #makes string of english dict
                engRes = dictToResponse(engDict,0)

                if(URL):

                    cacheType = engDict["Cache-Control"].split(",")[0]
                    maxAge = engDict["Cache-Control"].split("=")[1]
                    data = engDict["DATA"]

                    print("caching for url: "+URL)

                    URL_CACHE[URL] = Cache(cacheType,maxAge,engDict,data)

                    print("here is our current cache:")
                    print("-----------start")
                    print(URL_CACHE)
                    print("------------end")


                print("sending eng res: ")
                print("---------------------sss")
                print(engRes)
                print("----------end")



                conn.send(engRes)
                continue



            except socket.error as mesg:
                print(mesg)
                sys.exit(1)


# input a client's request, output a request to french server
def processReq(request,conn):
    requestVals = request.split("\n");

    retStr = ""

    cacheURL = None

    print("now looking at the request made to the server")

    for request in requestVals:

        print("the current request is: "+request)

        if(request==""):
            continue

        parameters = request.split(" ")



        if(parameters[0]=="GET" or parameters[0]=="POST" or parameters[0]=="HEAD"):
            print("looking at GET POST or HEAD request")
            if(len(parameters)!=3 or parameters[2]!="HTTP/1.1"):
                print("bad request line: "+request)
                return

            # must extract the path from the url
            currChar = 0
            url = parameters[1]

            # find the part of the url where the path starts
            while(currChar<len(url)):
                if(url[currChar]=="/" and (currChar==len(url)-1 or url[currChar+1]!="/") and (currChar==0 or url[currChar-1]!="/")):
                    break
                currChar+=1
            path = url[currChar:]

            if(parameters[0]=="GET"):
                retStr += "OBTENIR"
            elif(parameters[0]=="POST"):
                retStr += "POSTER"
            elif(parameters[0]=="HEAD"):
                retStr += "TÊTE"

            retStr += " " + path + " PdTHT/1.0" + "\n"

        elif(parameters[0]=="Host:"):
            print("Looking at Host request")
            if(len(parameters)!=2):
                print("bad request line: "+request)

            retStr += "Hôte: " + parameters[1] + "\n"
            cacheURL = parameters[1]

        else:
            print("this request is being added as is")
            retStr += request + "\n"




    #OK KEV, IT'S YOUR TIME TO SHINE!!!!
    #here's what you need to do
    #I got you a variable called cacheURL
    #this is the url the user requested
    #look into the cache, if this request has been made
    #then you need to put something like this into our server request:
    #Si-Modifié-Depuis: Yb-9-E 0:D:S
    #I made up some variables just to show you the logic,
    #youll need change those around
    if cacheURL in URL_CACHE.keys(): #if the url has been cached... this code is just to show you the logic, change it around based on how your cache works

        print("this request has been cached, but has timed out. now try to see if data has changed by sending req to server")

        modRetStr = retStr #we make a copy so that if the
                           #result has changed, then
                           #we can use our unmodified retStr
                           #to make a request
        modRetStr += "Si-Modifié-Depuis: "
        KEVIN_DATE_OF_CACHE = URL_CACHE[cacheURL].getFrenchDate()#YOU'll NEED TO FIGURE OUT THIS
                                  #itll be something like "Yb-9-E 0:D:S"
        modRetStr += KEVIN_DATE_OF_CACHE + "\n"
        modRetStr += "Via: 1.1 myproxy\n\n"

        print("sending request to server to see if data has changed:")
        print("-----------START")
        print(modRetStr)
        print("-----------END")

        #send request to server, get back headers
        headerEngDict = sendToServer(modRetStr)

        print("printing english dictionary of header receieved when asking if data has changed:")
        print("-----------START")
        print(headerEngDict)
        print("-----------END")

        #OK KEVIN!, if this is true, then that means
        #that the data we requested is NOT modified, thus
        #all we need to do is send back what we have in
        #the cache and increase the time the data has in the cache
        if(headerEngDict["IS_NOT_MOD"]):

            print("the server has told us the data has NOT been modified")

            time = headerEngDict["Cache-Control"]
            time = time.split("=")[1]
            time = int(time)#need to convert string to int
            #time = sexaToDec(time)

            #OK KEVIN, use the time variable to add time
            #to this item in the cache
            URL_CACHE[cacheURL].resetTime(time)

            #YO YO YO KEVIN, get the cached data in your cache
            #and put it into headerEngDict["DATA"]
            headerEngDict["DATA"] = URL_CACHE[cacheURL].data

            print("sending the cached data to user")
            print("turning the english dict into a response")
            res = dictToResponse(headerEngDict,0)

            print("sending response:")
            print("--------------START")
            print(res)
            print("---------------END")
            conn.send(res)

            return False

        else:
            print("the server has told us the data HAS been modified")

    print("this URL has never been asked for before (its not in our cache)")

    retStr += "Via: 1.1 myproxy\n\n"

    return retStr

#sends a french request to server, gets french response back
#and then converts the french request to english and sends
#back a dictionary of key=HTTP header, data=data
def sendToServer(data):

    print("sending data to server")

    #connect to french server
    sockServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockServer.connect((SERVER_NAME,SERVER_PORT))
    sockServer.send(data)

    print("recieving data from server")

    #get data back from server
    retFromServer = sockServer.recv(BUFSIZE)
    totalRetFromServer = retFromServer
    while len(retFromServer)!=0:
        retFromServer = sockServer.recv(BUFSIZE)
        totalRetFromServer += retFromServer
    totalRet = totalRetFromServer

    #all data is recieved, can close socket
    sockServer.close()

    print("here's the data we got:")
    print("------------START")
    print(totalRet)
    print("------------END")

    #get header of response
    currCharIndex = 0
    while currCharIndex < len(totalRet)-3 and \
        (totalRet[currCharIndex]!='\r' or  totalRet[currCharIndex+1]!='\n' or \
        totalRet[currCharIndex+2]!='\r' or  totalRet[currCharIndex+3]!='\n' ):
        currCharIndex+=1
    header = totalRet[0:currCharIndex+2]
    footer = totalRet[currCharIndex+4:]

    print("here is the header of the data:")
    print("------------START")
    print(header)
    print("------------END")


    #make dictionary, key=french HTTP, data=french data
    #headerFreDict = {}
    #keyOn = False
    #currKey = "RESPONSE_CODE"
    #currData = ""
    #for charIndex in range(0,len(header)):
    #    if(header[charIndex]==":"):
    #        keyOn = False
    #    elif(header[charIndex]=="\n"):
    #        keyOn = True
    #        headerFreDict[currKey] = currData[1:]
    #        currKey = ""
    #        currData = ""
    #    else:
    #        if(keyOn):
    #            currKey+=header[charIndex]
    #        else:
    #            currData+=header[charIndex]

    #make headerFreDict from header str

    headerFreDict = {}
    headerArgList = header.split("\r\n")
    for arg in headerArgList:
        if(arg==""):
            continue
        arg = arg.strip()
        print("curr arg: "+arg)
        if not ":" in arg and len(arg)>1:
            headerFreDict["RESPONSE_CODE"] = arg
        else:
            argList = arg.split(":")
            right = ""
            for i in range(1,len(argList)):
                if i == 1:
                    right+=(argList[i])[1:]+":"
                else:
                    right+=argList[i]+":"
            headerFreDict[argList[0]] = right[:-1]

    print("here is the french dictionary we made from the data:")
    print("------------START")
    print(headerFreDict)
    print("------------END")


    #now convert french dict to english dict
    headerEngDict = {}
    headerEngDict["IS_NOT_MOD"] = False
    for freKey in headerFreDict:

        engData = ""
        freData = None
        engKey = ""
        if freKey not in headerFreToEng:
            engKey = freKey
            freData = headerFreDict[freKey]

        else:
            engKey = headerFreToEng[freKey]
            freData = headerFreDict[freKey]


        if(freKey == "RESPONSE_CODE"):

            responseCode = freData.split(" ")
            if(responseCode[1]=="304"):
                headerEngDict["IS_NOT_MOD"] = True #this response has not changed

            engData += "HTTP/1.1 "
            if(responseCode[1]=="200" or responseCode[1]=="304"):
                engData += "200 "
            else:
                engData += responseCode[1]+" "
            engData += "OK"

        elif(freKey == "Longeur-Contenu"):
            engData = sexaToDec(freData)
        elif(freKey == "Contrôle-de-Cache"):
            cacheResponse = freData.split(" ")
            if(cacheResponse[0]=="public,"):
                engData+="public, "
            elif(cacheResponse[0]=="privé,"):
                engData+="private, "
            elif(cacheResponse[0]=="pas-de-cache,"):
                engData+="no-cache, "

            cacheResponse1 = cacheResponse[1].split("=")
            engData+="max-age="+str(sexaToDec(cacheResponse1[1]))

        elif(engKey == "Last-Modified"):
            engData = dateToUS(freData)

        elif(engKey == "Date"):
            engData = dateToUS(freData)

        elif(engKey == "Vary"):
            engData = headerFreToEng[freData]

        elif(engKey == "Connection"):
            engData = headerFreToEng[freData]

        else:
            engData = freData

        headerEngDict[engKey] = engData

    print("here is the english dict we made from the french dict:")
    print("-------------START")
    print(headerEngDict)
    print("------------END")

    headerEngDict["DATA"] = footer

    return headerEngDict


#input english dict, get out string of response
def dictToResponse(engDict,age):

    print("turning a dict into a res")

    res = ""
    res += engDict["RESPONSE_CODE"] + "\n"
    for key in engDict:
        if(key == "DATA" or key=="RESPONSE_CODE" or key=="IS_NOT_MOD"):
            continue
        res += key + ": " + str(engDict[key]) + "\n"
    res += "Via: 1.1 myproxy" + "\n"
    res += "Age: "+str(age) + "\n"
    res += "\n"
    if("DATA" in engDict):
        res+=engDict["DATA"]+"\n\n"

    print("here is the response:")
    print("----------START")
    print(res)
    print("_=--------------END")

    return res


#0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21
#0  1  2  3  4  5  6  7  8  9   A  B  C  D  E  F  G  H  I  J  K  L

#22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43
# M  N  P  Q  R  S  T  U  V  W  X  Y  Z  a  b  c  d  e  f  g  h  i

#44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 ...
# j  k  m  n  o  p  q  r  s  t  u  v  w  x  y  z 10 11 12 13 14 15 ...
def decToSexa(dec):
    conversion = ["0","1","2","3","4","5","6","7","8","9","A","B","C",
        "D","E","F","G","H","I","J","K","L","M","N","P","Q","R","S","T",
        "U","V","W","X","Y","Z","a","b","c","d","e","f","g","h","i","j",
        "k","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]
    ret = ""
    if dec == 0:
        return "0"

    while(dec>0):
        ret = (conversion[dec%60])+ret
        dec/=60
    return ret


def sexaToDec(sexa):
    dict = {
        "0":0,  "1":1,  "2":2,  "3":3,  "4":4,  "5":5,  "6":6,  "7":7  ,
        "8":8,  "9":9,  "A":10, "B":11, "C":12, "D":13, "E":14, "F":15 ,
        "G":16, "H":17, "I":18, "J":19, "K":20, "L":21, "M":22, "N":23 ,
        "P":24, "Q":25, "R":26, "S":27, "T":28, "U":29, "V":30, "W":31 ,
        "X":32, "Y":33, "Z":34, "a":35, "b":36, "c":37, "d":38, "e":39 ,
        "f":40, "g":41, "h":42, "i":43, "j":44, "k":45, "m":46, "n":47 ,
        "o":48, "p":49, "q":50, "r":51, "s":52, "t":53, "u":54, "v":55 ,
        "w":56, "x":57, "y":58, "z":59
    }
    sexa = str(sexa)
    sexa = sexa.strip()
    factor = 1
    ret = 0
    for currCharIndex in range(len(sexa)-1,-1,-1):
        ret+=dict[sexa[currCharIndex]]*factor
        factor*=60

    return ret

#english to french
def dateToFrench(date):
    ret = ""
    inputDate = date.split()
    ret += decToSexa(int(inputDate[3]))
    ret += "-"
    if inputDate[2] == "Jan":
        ret += "1"
    elif inputDate[2] == "Feb":
        ret += "2"
    elif inputDate[2] == "Mar":
        ret += "3"
    elif inputDate[2] == "Apr":
        ret += "4"
    elif inputDate[2] == "May":
        ret += "5"
    elif inputDate[2] == "Jun":
        ret += "6"
    elif inputDate[2] == "Jul":
        ret += "7"
    elif inputDate[2] == "Aug":
        ret += "8"
    elif inputDate[2] == "Sep":
        ret += "9"
    elif inputDate[2] == "Oct":
        ret += "A"
    elif inputDate[2] == "Nov":
        ret += "B"
    else:
        ret += "C"
    ret += "-"
    ret += decToSexa(int(inputDate[1]))
    ret += " "
    time = inputDate[4].split(":")
    ret += decToSexa((int(time[0]) + 2) % 24) + ":"
    ret += decToSexa(int(time[1])) + ":"
    ret += decToSexa(int(time[2]))
    return ret



def dateToUS(date):
    ret = ""
    findDay = ""
    print(date)
    split = date.split(" ")
    print(split)
    tempDate = split[0].split("-")
    tempTime = split[1].split(":")
    ret += str(sexaToDec(tempDate[2])) + " "
    findDay += ret
    if tempDate[1] == "1":
        ret += "Jan"
        findDay += "Jan"
    elif tempDate[1] == "2":
        ret += "Feb"
        findDay += "Feb"
    elif tempDate[1] == "3":
        ret += "Mar"
        findDay += "Mar"
    elif tempDate[1] == "4":
        ret += "Apr"
        findDay += "Apr"
    elif tempDate[1] == "5":
        ret += "May"
        findDay += "May"
    elif tempDate[1] == "6":
        ret += "Jun"
        findDay += "Jun"
    elif tempDate[1] == "7":
        ret += "Jul"
    elif tempDate[1] == "8":
        ret += "Aug"
        findDay += "Aug"
    elif tempDate[1] == "9":
        ret += "Sep"
        findDay += "Sep"
    elif tempDate[1] == "A":
        ret += "Oct"
        findDay += "Oct"
    elif tempDate[1] == "B":
        ret += "Nov"
        findDay += "Nov"
    else:
        ret += "Dec"
        findDay += "Dec"
    ret += " "
    findDay += " "
    ret += str(sexaToDec(tempDate[0])) + " "
    findDay += str(sexaToDec(tempDate[0]))
    ret += str((sexaToDec(tempTime[0]) + 22) % 24) + ":"
    ret += str(sexaToDec(tempTime[1])) + ":"
    ret += str(sexaToDec(tempTime[2]))
    ret = datetime.datetime.strptime(findDay, '%d %b %Y').strftime('%a') + "," + " " + ret
    return ret


headerFreToEng = {}
headerFreToEng["Hôte"] = "Host"
headerFreToEng["Longeur-Contenu"] = "Content-Length"
headerFreToEng["Encodage-de-Transfert"] = "Transfer-Encoding"
headerFreToEng["Connexion"] = "Connection"
headerFreToEng["Contrôle-de-Cache"] = "Cache-Control"
headerFreToEng["Date"] = "Date"
headerFreToEng["Dernière-Modification"] = "Last-Modified"
headerFreToEng["Si-Modifié-Depuis"] = "If-Modified-Since"
headerFreToEng["Âge"] = "Age"
headerFreToEng["Varier"] = "Vary"
headerFreToEng["Via"] = "Via"
headerFreToEng["Gamme"] = "Range"
headerFreToEng["Accepte"] = "Accept"
headerFreToEng["Accepte-Carjeu"] = "Accept-Charset"
headerFreToEng["Accepte-Encodage"] = "Accept-Encoding"
headerFreToEng["Accepte-Langue"] = "Accept-Language"
headerFreToEng["Type-de-Contenu"] = "Content-Type"
headerFreToEng["Biscuit"] = "Cookie"
headerFreToEng["Encodage-de-Contenu"] = "Content-Enconding"
headerFreToEng["Langue-de-Contenu"] = "Content-Language"
headerFreToEng["Emplacement"] = "Location"
headerFreToEng["Serveur"] = "Server"
headerFreToEng["Référenceur"] = "Referer"
headerFreToEng["Dêfinir-Biscut"] = "Set-Cookie"
headerFreToEng["Agent-Utilisateur"] = "User-Agent"
headerFreToEng["fermer"] = "close"
headerFreToEng[""] = ""





init()
