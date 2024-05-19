import socket
import threading
import time

class ServiceDiscovery:
    def __init__(self, port=50000, broadcast_ip="255.255.255.255"):
        self.port = port
        self.broadcast_ip = broadcast_ip
        self.server_addresses = set()

    def send_broadcast(self):
        message = b'SERVICE_DISCOVERY'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            sock.sendto(message, (self.broadcast_ip, self.port))
            time.sleep(5)  # 每5秒发送一次广播

    def listen_for_broadcast(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许重用地址和端口
        sock.bind(('', self.port))
        while True:
            data, addr = sock.recvfrom(1024)
            if data == b'SERVICE_DISCOVERY' and addr[0] not in self.server_addresses:
                self.server_addresses.add(addr[0])
                print(f"Discovered server: {addr[0]}")

    def start(self):
        threading.Thread(target=self.send_broadcast, daemon=True).start()
        threading.Thread(target=self.listen_for_broadcast, daemon=True).start()

    def get_servers(self):
        return list(self.server_addresses)
