import json
import requests
import threading
import re
import sys

class MyZabbix:
    id = 1
    token = None
    def __init__(self, host, login = "Admin", password = "zabbix"):
        self.host = 'http://'+host+'/api_jsonrpc.php'
        self.token = self.Auth(login, password)

    def Auth(self, login, password):
        params = {"user": login, "password": password}
        return self.SendCommand("user.login", params)

    def SendCommand(self, method, params):
        headers = {'content-type': 'application/json'}
        sendpost = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.id,
            "auth": self.token
        }
        sendpost = json.dumps(sendpost)
        responce = requests.post(self.host, data=sendpost, headers=headers)
        self.id += 1
        #print(json.loads(responce.text))
        return json.loads(responce.text)["result"]
    
    def GroupGetByName(self, name, count=False):
        params = {
            "countOutput": count,
            "output": "extend",
            "filter": {
                "name": name
            }
        }
        return self.SendCommand("hostgroup.get", params)
    
    def GroupCreate(self, name):
        params = {
            "name": name
        }
        return self.SendCommand("hostgroup.create", params)
    
    def HostGetByIp(self, ip):
        params = {
            "filter": {
                    "ip": ip
            }
        }
        return self.SendCommand("hostinterface.get", params)

    def HostGetByID(self, id:int):
        params = {
            "output": ["hostid", "name"],
            "selectGroups": "extend",
            "hostids": id
        }
        return self.SendCommand("host.get", params)
    
    def GetHostsByGroup(self, grpid:int):
        params = {
            "output": ["hostid", "name"],
            "groupids": grpid
        }
        return self.SendCommand("host.get", params)
    
    def HostDelete(self, hostid = []):
        return self.SendCommand("host.delete", hostid)
    
    def HostCreate(self, ip, name, groupsList = [], templateList = []):
        groups = []
        templates = []
        for group in groupsList:
            groups.append(
                {"groupid": group}
            )
        for templat in templateList:
            templates.append(
                {"templateid": templat}
            )
        params = {
            "host": ip,
            "name": name,
            "interfaces": [
                {
                    "type": 1,
                    "ip": ip,
                    "dns": "",
                    "port": "10050",
                    "useip": 1,
                    "main": 1
                }
            ],
            "groups": groups,
            "templates": templates
        }
        try:
            return self.SendCommand("host.create", params)
        except:
            params = {
                "host": ip,
                "name": ip,
                "interfaces": [
                    {
                        "type": 1,
                        "ip": ip,
                        "dns": "",
                        "port": "10050",
                        "useip": 1,
                        "main": 1
                    }
                ],
                "groups": groups,
                "templates": templates
            }
            return self.SendCommand("host.create", params)
    
    def HostUpdate(self, hostid, name, groupsList = [], templateList = []):
        groups = []
        templates = []
        for group in groupsList:
            groups.append(
                {"groupid": group}
            )
        for templat in templateList:
            templates.append(
                {"templateid": templat}
            )
        params = {
            "hostid": hostid,
            "name": name,
            "groups": groups,
            "templates": templates
            }
        try:
            return self.SendCommand("host.update", params)
        except:
            params = {
                "hostid": hostid,
                "groups": groups,
                "templates": templates
                }
            return self.SendCommand("host.update", params)


zbx = MyZabbix("192.168.1.100")
servergroupforzbx = [53] # группы для серверов
servertempforzbx = [10605]# шаблоны для серверов

camgroupforzbx = [79]
camtempforzbx = [10672]

class Cam():
    def __init__(self, camIP:str, camName:str):
        self.Ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', camIP).group(1)
        self.Name = camName
        # self.ServerIp = re.search(r'(\d+\.\d+\.\d+\.\d+)', serverIp).group(1)
        # self.ServerName = serverName
    
class Server():
    def __init__(self, serverIp:str, serverName:str):
        self.Ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', serverIp).group(1)
        self.Name = serverName
        self.Cams = []
    def AddCam(self, obj):
        self.Cams.append(obj)



with open(sys.argv[1], encoding="utf-8") as f:
    configs = json.load(f)

CAMS = []
SERVERS = []
servergroupforzbx.sort()
servertempforzbx.sort()

def AddCamToZabbix(camip, camname, groupIdForCam, camtempforzbx):
    if(len(zbx.HostGetByIp(camip)) == 0):
            zbx.HostCreate(camip, camname, groupIdForCam, camtempforzbx)
    else:
        hostid = zbx.HostGetByIp(camip)[0]["hostid"]
        host_info = zbx.HostGetByID(hostid)[0]
        host_info_groups_id = []
        for group in host_info["groups"]:
            host_info_groups_id.append(int(group["groupid"]))
        host_info_groups_id.sort()
        if host_info["name"] != camname or groupIdForCam != host_info_groups_id:
            zbx.HostUpdate(hostid, camname, groupIdForCam, camtempforzbx)

def GetOtdel(name:str):
    try:
        if ":" in name:
            otdel = name.split(":")
            return otdel[0]
        return "Без группы"
    except:
        return "Без группы"

for config in configs["objects"]:
    if config["type"] == "CAM":
        grabberParams = [x["params"] for x in configs["objects"] if (x["id"] == config["params"]["parent_id"] and x["type"] == "GRABBER")][0]
        serverParams = [x["params"] for x in configs["objects"] if (x["id"] == grabberParams["parent_id"] and x["type"] == "SLAVE")][0]
        cam = Cam(grabberParams["ip"], config["params"]["name"])
        server = Server(serverParams["ip_address"], serverParams["name"])
        if server.Ip not in [x.Ip for x in SERVERS] and server.Name not in [x.Name for x in SERVERS]:
            SERVERS.append(server)
        [x for x in SERVERS if (x.Ip == serverParams["ip_address"]) and x.Name == serverParams["name"]][0].AddCam(cam)

# for server in SERVERS:
#     print(server.ServerIp, server.ServerName, len(server.Cams))
# for cams in [x.Cams for x in SERVERS if (x.ServerName == "Компьютер NVR-1 (Карцер)")]:
#     for cam in cams:
#         print(cam.CamName)
#     print(len(cams))

for server in SERVERS:
    #Проверяем существование сервера и группы, если нет создаем
    groupIdForCam = [] # Содержит id груп для камеры
    if len(zbx.GroupGetByName(server.Name)) == 0:
        groupIdForCam.append(int(zbx.GroupCreate(server.Name)["groupids"][0]))
    else:
        groupIdForCam.append(int(zbx.GroupGetByName(server.Name)[0]["groupid"]))
    groupIdForCam = groupIdForCam + camgroupforzbx
    groupIdForCam.sort()
    #Добавляем или изменяем сервера
    if(len(zbx.HostGetByIp(server.Ip)) == 0):
        zbx.HostCreate(server.Ip, server.Name, servergroupforzbx, servertempforzbx)
    else:
        hostid = zbx.HostGetByIp(server.Ip)[0]["hostid"]
        host_info = zbx.HostGetByID(hostid)[0]
        host_info_groups_id = []
        for group in host_info["groups"]:
            host_info_groups_id.append(int(group["groupid"]))
        host_info_groups_id.sort()
        if host_info["name"] != server.Name or servergroupforzbx != host_info_groups_id:
            zbx.HostUpdate(hostid, server.Name, servergroupforzbx, servertempforzbx)

    print(server.Name, " - ", server.Ip)
    tr = []
    for cam in server.Cams:
        otdel = GetOtdel(cam.Name)
        grp =[]
        if len(zbx.GroupGetByName(otdel)) == 0:
            grp.append(int(zbx.GroupCreate(otdel)["groupids"][0]))
        else:
            grp.append(int(zbx.GroupGetByName(otdel)[0]["groupid"]))
        grp = groupIdForCam + grp
        grp.sort()
        t = threading.Thread(target=AddCamToZabbix, args = (cam.Ip, cam.Name, grp, camtempforzbx))
        tr.append(t)
        t.start()

    for x in tr:
        x.join()


delHosts = []
for server in SERVERS:
    hosts = zbx.GetHostsByGroup(int(zbx.GroupGetByName(server.Name)[0]["groupid"]))
    camsName = [x.Name for x in server.Cams]
    camsIp = [x.Ip for x in server.Cams]
    for host in hosts:
        if host["name"] not in camsName and host["name"] not in camsIp:
            print(host["name"])
            delHosts.append(int(host["hostid"]))
zbx.HostDelete(delHosts)