import sys
import getopt
import hashlib
import requests
import os
import time
import threading
import re
from xml.etree import ElementTree as et
from collections import OrderedDict
from getpass import getpass

class Item(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.id = 0
        self.AgreementInfo = 'own'
        self.realId = 0
        self.name = ''
        self.url = ''
        self.num = 1
        self.status = 'open'
        self.directory = ""
        self.progress = None
        
    def getProgress(self):
        if self.progress is None:
            return "{:>2s}. {: <20s} : {}".format(str(self.num), self.name[:20], "En cola...",)
        else:
            return self.progress
        
    def download_chunk(self, start_byte, end_byte):
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}
        response = requests.get(self.url, headers=headers, stream=True, verify=True, allow_redirects=True)
        return response
        
    def format_time(self, seconds):
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = int(seconds % 60)
            return "{:02d}h {:02d}m {:02d}s".format(hours, minutes, seconds)
        elif seconds >= 60:
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return "{:02d}m {:02d}s".format(minutes, seconds)
        else:
            return "{:02d}s".format(int(seconds))
            
    def run(self):
        self.status = 'inprogress'
        path = self.directory + '/' + self.name
        try:
            file_size = os.path.getsize(path)
        except:
            file_size = 0
        r = requests.get(self.url, stream=True, verify=True, allow_redirects=True)
        total_length = int(r.headers.get('content-length'))
        file_attr = 'wb'
        if total_length > file_size and file_size > 0:
            file_attr = 'ab'
            resume_header = {'Range': f'bytes={file_size}-'}
            r = requests.get(self.url, headers=resume_header,  stream=True, verify=True, allow_redirects=True)
        if file_size < total_length:
            with open(path, file_attr) as fd:
                dl_size = file_size
                start_time = time.time()
                prev_time = start_time
                num_parts = 4  # Number of parts into which the discharge will be divided
                for part_num in range(num_parts):
                    start_byte = int(file_size + part_num * (total_length - file_size) / num_parts)
                    end_byte = int(file_size + (part_num + 1) * (total_length - file_size) / num_parts) - 1
                    response = self.download_chunk(start_byte, end_byte)
                    for chunk in response.iter_content(chunk_size=128):
                        dl_size += len(chunk)
                        progress = dl_size * 100. / total_length
                        now = time.time()
                        elapsed_time = now - start_time
                        speed = (dl_size - file_size) / elapsed_time  # Actual download speed (bytes/second)
                        speed_mb = speed / (1024 * 1024)  # Actual download speed (MB/second)
                        remaining_size = total_length - dl_size
                        if speed_mb > 0:
                            estimated_time = remaining_size / speed  # seconds
                        else:
                            estimated_time = 0
                        downloaded_mb = dl_size / (1024 * 1024)  # MB
                        if downloaded_mb > 1024:
                            downloaded_gb = downloaded_mb / 1024  # GB
                            downloaded_str = "{:.2f} GB".format(downloaded_gb)
                        else:
                            downloaded_str = "{:.2f} MB".format(downloaded_mb)
                        self.progress = "{:>2s}. {: <20s} {: >10s} {: >3d}% [{: <25s}] Velocidad:{: >6.2f} MB/s | Tiempo restante: {}".format(
                            str(self.num), self.name[:20], downloaded_str, int(progress), "#" * int(progress/4), speed_mb, self.format_time(estimated_time))
                        fd.write(chunk)
            self.status = 'done'
        elif file_size == total_length:
            self.progress = "{:>2s}. {: <20s} : {}".format(str(self.num), self.name[:20], "El archivo existe en el disco")
            self.status = 'done'
            
class Chomyk:
    def __init__(self, username, password, maxThreads, directory):
        self.isLogged = True
        self.lastLoginTime = 0
        self.hamsterId = 0
        self.token = ''
        self.items = 0
        self.threads = []
        self.accBalance = None
        self.maxThreads = int(maxThreads)
        self.directory = directory
        self.threadsChecker = None
        self.totalItems = 0
        self.username = username
        self.password = hashlib.md5(password.encode("utf-8")).hexdigest()
        self.cls()
        self.checkThreads()
        self.login()
        
    def cls(self):
        os.system('cls' if os.name=='nt' else 'clear')

    def printline(self, line, text):
        sys.stdout.write(f"\x1b7\x1b[{line};2f{text}\x1b8")
        sys.stdout.flush()
        
    def checkThreads(self):
        threadsInprogress = 0
        threadsOpen = 0
        threadsDone = 0
        for it in self.threads:
            self.printline(it.num+3, it.getProgress())
            if it.status == 'inprogress':
                threadsInprogress += 1
            if it.status == 'open':
                threadsOpen += 1
                if threadsInprogress < self.maxThreads:
                    threadsInprogress += 1
                    threadsOpen -= 1
                    it.start()
                    # it.join()  # Uncomment this line if you want to wait for each thread to finish before starting the next one.
            if it.status == 'done':
                threadsDone += 1
        if threadsDone == self.totalItems and threadsDone > 0 and threadsOpen == 0:
            self.threadsChecker.cancel()
            self.cls()
            print("\r\nSe han descargado todos los archivos")
            print("\r")
        else:
            self.threadsChecker = threading.Timer(1.0, self.checkThreads)
            self.threadsChecker.start()
            
    def postData(self, postVars):
        url = "http://box.chomikuj.pl/services/ChomikBoxService.svc"
        body = postVars.get("body")
        headers = {
            "SOAPAction": postVars.get("SOAPAction"),
            "Content-Encoding": "identity",
            "Content-Type": "text/xml;charset=utf-8",
            "Content-Length": str(len(body)),
            "Connection": "Keep-Alive",
            "Accept-Encoding": "identity",
            "Accept-Language": "pl-PL,en,*",
            "User-Agent": "Mozilla/5.0",
            "Host": "box.chomikuj.pl",
        }
        response = requests.post(url, data=body.encode("utf-8"), headers=headers)
        self.parseResponse(response.content)

    def dl(self, url):
        fileUrl = re.search(r'[http|https]://chomikuj.pl(.*)', url).group(1)
        rootParams = {"xmlns:s": "http://schemas.xmlsoap.org/soap/envelope/", "s:encodingStyle": "http://schemas.xmlsoap.org/soap/encoding/"}
        root = et.Element('s:Envelope', rootParams)
        body = et.SubElement(root, "s:Body")
        downloadParams = {"xmlns": "http://chomikuj.pl/"}
        download = et.SubElement(body, "Download", downloadParams)
        downloadSubtree = OrderedDict([
            ("token", self.token,),
            ("sequence", [("stamp", "123456789"), ("part", "0"), ("count", "1")]),
            ("disposition", "download"),
            ("list",  [("DownloadReqEntry", [("id", fileUrl),])])
        ])
        self.add_items(download, downloadSubtree)
        xmlDoc = f"""<?xml version="1.0" encoding="UTF-8"?>{et.tostring(root, encoding='unicode', method='xml')}"""
        dts = {"body": xmlDoc, "SOAPAction": "http://chomikuj.pl/IChomikBoxService/Download"}
        self.postData(dts)

    def dl_step_2(self, idx, agreementInfo, cost=0):
        rootParams = {"xmlns:s": "http://schemas.xmlsoap.org/soap/envelope/", "s:encodingStyle": "http://schemas.xmlsoap.org/soap/encoding/"}
        root = et.Element('s:Envelope', rootParams)
        body = et.SubElement(root, "s:Body")
        downloadParams = {"xmlns": "http://chomikuj.pl/"}
        download = et.SubElement(body, "Download", downloadParams)
        downloadSubtree = OrderedDict([
            ("token", self.token,),
            ("sequence", [("stamp", "123456789"), ("part", "0"), ("count", "1")]),
            ("disposition", "download"),
            ("list",  [("DownloadReqEntry", [("id", idx),("agreementInfo", [("AgreementInfo", [("name", agreementInfo),("cost", cost),])])])])
        ])
        self.add_items(download, downloadSubtree)
        xmlDoc = f"""<?xml version="1.0" encoding="UTF-8"?>{et.tostring(root, encoding='unicode', method='xml')}"""
        dts = {"body": xmlDoc, "SOAPAction": "http://chomikuj.pl/IChomikBoxService/Download"}
        self.postData(dts)

    def login(self):
        rootParams = {"xmlns:s": "http://schemas.xmlsoap.org/soap/envelope/", "s:encodingStyle": "http://schemas.xmlsoap.org/soap/encoding/"}
        root = et.Element('s:Envelope', rootParams)
        body = et.SubElement(root, "s:Body")
        authParams = {"xmlns": "http://chomikuj.pl/"}
        auth = et.SubElement(body, "Auth", authParams)
        authSubtree = OrderedDict([
            ("name", self.username,),
            ("passHash", self.password,),
            ("ver", "4"),
            ("client", OrderedDict([("name", "chomikbox"), ("version", "2.0.8.2"),]))
        ])
        self.add_items(auth, authSubtree)
        xmlDoc = f"""<?xml version="1.0" encoding="UTF-8"?>{et.tostring(root, encoding='unicode', method='xml')}"""
        dts = {"body": xmlDoc, "SOAPAction": "http://chomikuj.pl/IChomikBoxService/Auth"}
        self.postData(dts)

    def add_items(self, root, items):
        if type(items) is OrderedDict:
            for name, text in items.items():
                if type(text) is str:
                    elem = et.SubElement(root, name)
                    elem.text = text
                if type(text) is list:
                    subroot = et.SubElement(root, name)
                    self.add_items(subroot, text)
        elif type(items) is list:
            for name, text in items:
                if type(text) is str:
                    elem = et.SubElement(root, name)
                    elem.text = text
                if type(text) is list:
                    subroot = et.SubElement(root, name)
                    self.add_items(subroot, text)

    def parseResponse(self, resp):
        self.printline (3, 'Descargas paralelas: ' + str(self.maxThreads))
        respTree = et.fromstring(resp)
        #Authorization
        for dts in respTree.findall(".//{http://chomikuj.pl/}AuthResult/{http://chomikuj.pl}status"):
            status = dts.text
            if status.upper() == "OK":
                self.isLogged = True
                self.lastLoginTime = time.time()
                self.token = respTree.findall(".//{http://chomikuj.pl/}AuthResult/{http://chomikuj.pl}token")[0].text
                self.hamsterId = respTree.findall(".//{http://chomikuj.pl/}AuthResult/{http://chomikuj.pl}hamsterId")[0].text
                self.printline (1,"Inicio de sesion: OK")
            else:
                 self.isLogged = False
                 self.printline (1,"Inicio de sesion: " + status)
        #File urls downloaded
        accBalance = respTree.find(".//{http://chomikuj.pl/}DownloadResult/{http://chomikuj.pl}accountBalance/{http://chomikuj.pl/}transfer/{http://chomikuj.pl/}extra")
        if accBalance is not None:
            self.accBalance = accBalance.text
        for dts in respTree.findall(".//{http://chomikuj.pl/}DownloadResult/{http://chomikuj.pl}status"):
            status = dts.text
            if status.upper() == "OK":
                dlfiles = respTree.findall(".//{http://chomikuj.pl/}files/{http://chomikuj.pl/}FileEntry")
                if (len(dlfiles) > self.totalItems):
                    self.totalItems = len(dlfiles)
                    self.printline (2,"Archivos: " + str(self.totalItems))
                for dlfile in dlfiles:
                    url = dlfile.find('{http://chomikuj.pl/}url')
                    idx = dlfile.find('{http://chomikuj.pl/}id').text
                    cost = dlfile.find('{http://chomikuj.pl/}cost')
                    if url.text == None:
                        agreementInfo = dlfile.find("{http://chomikuj.pl/}agreementInfo/{http://chomikuj.pl/}AgreementInfo/{http://chomikuj.pl/}name").text
                        costInfo = dlfile.find("{http://chomikuj.pl/}agreementInfo/{http://chomikuj.pl/}AgreementInfo/{http://chomikuj.pl/}cost")
                        if costInfo.text == None:
                            cost = 0
                        else:
                            cost = costInfo.text
                        if int(self.accBalance) >= int(cost):
                            self.dl_step_2(idx, agreementInfo,cost)
                        else:
                            self.printline (2,"Error: limite de transferencia insuficiente")
                    else:
                        self.items = self.items +1
                        it = Item()
                        it.id = idx
                        it.directory = self.directory
                        it.num = self.items
                        it.url = url.text
                        it.name = dlfile.find('{http://chomikuj.pl/}name').text
                        it.daemon = True
                        self.threads.append(it)
                        
def main(argv):
    url = ''
    output = ''
    username = ''
    password = ''
    threads = 4
    directory = os.getcwd()+"/"
    try:
        opts, args = getopt.getopt(argv,"h:u:p:i:t:d:o",["help","username","password","ifile","ofile"])
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("Ayuda:")
            printUsage()
            sys.exit()
        elif opt in ("-i", "--ifile"):
            url = arg
        elif opt in ("-o", "--ofile"):
            output = arg
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-t", "--threads"):
            threads = arg
        elif opt in ("-d", "--directory"):
            directory = arg 
    if len(username) == 0:
        username = input("Usuario: ")
    if len(password) == 0:
        password = getpass("Contraseña: ")
    if len(url) == 0:
        url = input("URL: ")
    if len(password) > 0 and len(username) >0 and len(url)>0:
        try:
            os.makedirs(directory)
        except OSError:
            pass
        ch = Chomyk(username,password,threads,directory)
        ch.dl(str(url))
    else:
        printUsage()

def printUsage():
    print ('chomyk.py --u username --p password --i <url>')
    sys.exit(2)

if __name__ == "__main__":
   main(sys.argv[1:])
