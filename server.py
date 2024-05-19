import socket
import threading
import multiprocessing
import os
import time
from service_discovery import ServiceDiscovery
from lamport_clock import LamportClock  # 假设你将LamportClock类保存到这个文件中

class ChatServer(multiprocessing.Process):
    def __init__(self, server_socket, received_data, client_address, connected_clients, client_names, server_addresses, processed_messages, clock):
        super(ChatServer, self).__init__()
        self.server_socket = server_socket
        self.received_data = received_data
        self.client_address = client_address
        self.connected_clients = connected_clients
        self.client_names = client_names
        self.server_addresses = server_addresses
        self.processed_messages = processed_messages
        self.clock = clock

    def run(self):
        data = self.received_data.decode()
        parts = data.split(':', 3)
        message_type = parts[0]

        if message_type == "REGISTER":
            client_name = parts[1]
            if client_name in self.client_names:
                response = f'REJECTED:{client_name}'
                self.server_socket.sendto(response.encode(), self.client_address)
            else:
                self.client_names[client_name] = self.client_address
                response = f'ACCEPTED:{client_name}'
                self.server_socket.sendto(response.encode(), self.client_address)
                print(f'Client {client_name} has joined from {self.client_address}')
                self.connected_clients.append((client_name, self.client_address))  # 添加到 connected_clients 列表

        elif message_type == "CLIENT":
            try:
                message_id, received_time, client_name_and_message = parts[1], int(parts[2]), parts[3]
                client_name, message = client_name_and_message.split(':', 1)

                if message_id in self.processed_messages:
                    return

                self.processed_messages.append(message_id)
                self.clock.update(received_time)

                # Broadcast message to all connected clients
                broadcast_message = f'{client_name}: {message} (Lamport time: {self.clock.get_time()})'

                print("Broadcasting to clients...")
                print(self.connected_clients)
                for client in self.connected_clients:
                    self.server_socket.sendto(broadcast_message.encode(), client[1])

                # Send acknowledgement to the original sender
                ack_message = f'SERVER_ACK:{self.clock.get_time()}:{message}'
                self.server_socket.sendto(ack_message.encode(), self.client_address)
                print(f'Sent to client {self.client_address}: {ack_message}')
            except ValueError as e:
                print(f"Error processing message: {data}, Error: {e}")

        elif message_type == "SERVER_ACK":
            # Process server acknowledgement message if necessary
            pass

def server_listener(server_socket, connected_clients, client_names, server_addresses, processed_messages, clock):
    buffer_size = 1024
    while True:
        data, address = server_socket.recvfrom(buffer_size)
        if data == b'HEARTBEAT':
            server_socket.sendto(b'HEARTBEAT_ACK', address)
        elif data == b'SERVICE_DISCOVERY':
            server_addresses.add(address[0])
        else:
            print(f'Received message \'{data.decode()}\' from {address}')
            p = ChatServer(server_socket, data, address, connected_clients, client_names, server_addresses, processed_messages, clock)
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

    manager = multiprocessing.Manager()
    connected_clients = manager.list()
    client_names = manager.dict()
    processed_messages = manager.list()  # 使用列表代替集合
    clock = LamportClock()
    server_listener(server_socket, connected_clients, client_names, server_addresses, processed_messages, clock)
