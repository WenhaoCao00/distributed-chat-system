import socket
import threading
import multiprocessing
import os
import time
from service_discovery import ServiceDiscovery

class ChatServer(multiprocessing.Process):
    def __init__(self, server_socket, received_data, client_address, connected_clients, server_addresses):
        super(ChatServer, self).__init__()
        self.server_socket = server_socket
        self.received_data = received_data
        self.client_address = client_address
        self.connected_clients = connected_clients
        self.server_addresses = server_addresses

    def run(self):
        # Broadcast message to other servers
        for server_address in self.server_addresses:
            self.server_socket.sendto(self.received_data, (server_address, 10001))

        # Send message to all connected clients
        for client in self.connected_clients:
            self.server_socket.sendto(self.received_data, client)

        # Send acknowledgement to the original sender
        message = f'Server {os.getpid()} received your message: {self.received_data.decode()}'
        self.server_socket.sendto(message.encode(), self.client_address)
        print(f'Sent to client {self.client_address}: {message}')

def server_listener(server_socket, connected_clients, server_addresses):
    buffer_size = 1024
    while True:
        data, address = server_socket.recvfrom(buffer_size)
        if data == b'HEARTBEAT':
            server_socket.sendto(b'HEARTBEAT_ACK', address)
        elif data == b'SERVICE_DISCOVERY':
            server_addresses.add(address[0])
        else:
            print(f'Received message \'{data.decode()}\' from {address}')
            if address not in connected_clients:
                connected_clients.append(address)
            p = ChatServer(server_socket, data, address, connected_clients, server_addresses)
            p.start()
            p.join()

if __name__ == "__main__":
    service_discovery = ServiceDiscovery()
    service_discovery.start()

    # 等待一段时间以发现其他服务器
    time.sleep(10)

    # 获取发现的服务器地址
    server_addresses = set(service_discovery.get_servers())
    print("Discovered servers:", server_addresses)

    # 启动服务器
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许重用地址和端口
    server_socket.bind(('0.0.0.0', 10001))  # 绑定到所有可用的网络接口
    print('Server up and running')

    connected_clients = []
    server_listener(server_socket, connected_clients, server_addresses)
