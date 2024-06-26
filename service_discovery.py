# service_discovery.py
import socket
import threading
import time

class ServiceDiscovery:
    def __init__(self, port=50000, broadcast_ip="255.255.255.255"):
        self.port = port
        self.broadcast_ip = broadcast_ip
        self.server_addresses = set()
        self.local_ip = self.get_local_ip()

    def is_valid_ip(self, ip):
        return ip.startswith("192.168.0.") and ip != "127.0.0.1"  #return LAN and not localhost

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = socket.gethostbyname(socket.gethostname())
        finally:
            s.close()
        return ip

    def send_broadcast(self):
        message = b'SERVICE_DISCOVERY'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((self.local_ip, 0))
        while True:
            sock.sendto(message, (self.broadcast_ip, self.port))
            #print(f"Broadcast sent from {self.local_ip} to {self.broadcast_ip}:{self.port}")
            time.sleep(5)

    def listen_for_broadcast(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.port))
        while True:
            data, addr = sock.recvfrom(1024)
            #print(f"Received broadcast from {addr}: {data}")
            if data == b'SERVICE_DISCOVERY' and self.is_valid_ip(addr[0]) and addr[0] not in self.server_addresses:
                self.server_addresses.add(addr[0])
                print(f"Discovered server: {addr[0]}")
                self.notify_existing_servers(addr[0])

    def notify_existing_servers(self, new_server_ip):
        notification_message = f'NEW_SERVER:{new_server_ip}'.encode()
        for server_ip in self.server_addresses:
            if server_ip != new_server_ip:
                self.send_notification(server_ip, notification_message)

    def send_notification(self, server_ip, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(message, (server_ip, self.port))
            print(f"Notification sent to {server_ip}: {message.decode()}")
        except Exception as e:
            print(f"Error sending notification to {server_ip}: {e}")
        finally:
            sock.close()

    def start(self):
        threading.Thread(target=self.send_broadcast, daemon=True).start()
        threading.Thread(target=self.listen_for_broadcast, daemon=True).start()

    def get_servers(self):
        return list(self.server_addresses)
