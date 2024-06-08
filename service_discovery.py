# service_discovery.py
import socket
import threading
import time
import json

class ServiceDiscovery:
    def __init__(self, port=50000, broadcast_ip="255.255.255.255"):
        self.port = port
        self.broadcast_ip = broadcast_ip
        self.server_addresses = []
        self.local_ip = self.get_local_ip()
        self.initiate_election = None

    def is_valid_ip(self, ip):
        return ip.startswith("192.168.0.") and ip != "127.0.0.1"  #return LAN and not localhost

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80)) #触发系统选择一个合适的本地 IP 地址和端口，以便进行通信。
            ip = s.getsockname()[0] #s.getsockname() 返回一个包含本地 IP 地址和端口的元组，[0] 提取其中的 IP 地址。
        except Exception:
            ip = socket.gethostbyname(socket.gethostname())
        finally:
            s.close()
        return ip

    def send_broadcast(self):
        message = b'SERVICE_DISCOVERY'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #创建一个套接字（socket）对象
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) #设置套接字选项，使其能够发送广播消息。
        sock.bind((self.local_ip, 0)) #将套接字绑定到本地地址和任意可用端口。
        while True:
            sock.sendto(message, (self.broadcast_ip, self.port)) # 对所有端口广播
            #print(f"Broadcast sent from {self.local_ip} to {self.broadcast_ip}:{self.port}")
            time.sleep(5)

    def listen_for_broadcast(self):
        _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _sock.bind(('', self.port)) #将套接字绑定到指定端口，并监听来自任何 IP 地址的连接。
        while True:
            data, addr = _sock.recvfrom(1024)
            if data == b'SERVICE_DISCOVERY' and self.is_valid_ip(addr[0]) and addr[0] not in [ip[0] for ip in
                                                                                              self.server_addresses]:
                self.server_addresses.append([addr[0], False])
                print(f"Discovered server: {addr[0]}")
                self.notify_existing_servers(addr[0])
            else:
                try:
                    message = json.loads(data.decode())
                    if 'isLeader' in message:
                        self.update_leader(addr[0])
                        if addr[0] not in [ip[0] for ip in self.server_addresses]:
                            self.server_addresses.append([addr[0], message['isLeader']])
                            self.notify_existing_servers(addr[0])
                except json.JSONDecodeError:
                    pass

    def notify_existing_servers(self, new_server_ip): #addr[0]
        notification_message = json.dumps({"mid": new_server_ip, "isLeader": False}).encode()
        for server_ip in self.server_addresses:
            if server_ip != new_server_ip:
                self.send_notification(server_ip[0], notification_message)

    def send_notification(self, server_ip, message):
        _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            _sock.sendto(message, (server_ip, self.port))
            print(f"Notification sent to {server_ip}: {message.decode()}")
        except Exception as e:
            print(f"Error sending notification to {server_ip}: {e}")
        finally:
            _sock.close()

    def update_leader(self, leader_ip):
        for server in self.server_addresses:
            server[1] = (server[0] == leader_ip)

    def start(self):
        threading.Thread(target=self.send_broadcast, daemon=True).start()
        threading.Thread(target=self.listen_for_broadcast, daemon=True).start()

    def get_servers(self):
        return list(self.server_addresses)
