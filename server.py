# server.py
import socket
import multiprocessing
import os
import time
from service_discovery import ServiceDiscovery
from lamport_clock import LamportClock
from ring_election import initiate_election

class ChatServer(multiprocessing.Process):
    def __init__(self, server_socket, received_data, client_address, connected_clients, client_names, server_addresses, processed_messages, clock, is_leader):
        super(ChatServer, self).__init__()
        self.server_socket = server_socket
        self.received_data = received_data
        self.client_address = client_address
        self.connected_clients = connected_clients
        self.client_names = client_names
        self.server_addresses = server_addresses
        self.processed_messages = processed_messages
        self.clock = clock
        self.is_leader = is_leader

    def run(self):
        data = self.received_data.decode()
        parts = data.split(':', 3)
        message_type = parts[0]

        if message_type == "REGISTER":
            if self.is_leader:
                client_name = parts[1]
                if client_name in self.client_names:
                    response = f'REJECTED:{client_name}'
                    self.server_socket.sendto(response.encode(), self.client_address)
                else:
                    self.client_names[client_name] = self.client_address
                    response = f'ACCEPTED:{client_name}'
                    self.server_socket.sendto(response.encode(), self.client_address)
                    print(f'Client {client_name} has joined from {self.client_address}')
                    self.connected_clients.append((client_name, self.client_address))
            else:
                response = 'NOT_LEADER'
                self.server_socket.sendto(response.encode(), self.client_address)

        elif message_type == "CLIENT":
            if self.is_leader:
                try:
                    message_id, received_time, client_name_and_message = parts[1], int(parts[2]), parts[3]
                    client_name, message = client_name_and_message.split(':', 1)

                    if message_id in self.processed_messages:
                        return

                    self.processed_messages.append(message_id)
                    self.clock.update(received_time)

                    #this is with Lamport time
                    broadcast_message = f'{client_name}: {message} (Lamport time: {self.clock.get_time()})'

                    print("Broadcasting to clients...")
                    for client in self.connected_clients:
                        if client[1] != self.client_address:  # Skip the sender
                            self.server_socket.sendto(broadcast_message.encode(), client[1])

                except ValueError as e:
                    print(f"Error processing message: {data}, Error: {e}")

        elif message_type == "NEW_SERVER":
            new_server_ip = parts[1]
            if new_server_ip not in self.server_addresses:
                self.server_addresses.append(new_server_ip)
                print(f"New server added: {new_server_ip}")
                leader = initiate_election(self.server_addresses, self.client_address[0])
                self.is_leader = (leader == self.client_address[0])
                print(f'I am the leader: {self.is_leader}')

def server_listener(server_socket, connected_clients, client_names, server_addresses, processed_messages, clock, is_leader):
    buffer_size = 1024
    while True:
        data, address = server_socket.recvfrom(buffer_size)
        if data == b'HEARTBEAT':
            server_socket.sendto(b'HEARTBEAT_ACK', address)
        elif data == b'SERVICE_DISCOVERY':
            server_addresses.add(address[0])
        elif data.startswith(b'NEW_SERVER:'):
            new_server_ip = data.decode().split(':')[1]
            if new_server_ip not in server_addresses:
                server_addresses.append(new_server_ip)
                print(f"New server added: {new_server_ip}")
                leader = initiate_election(server_addresses, my_ip)
                is_leader = (leader == my_ip)
                print(f'I am the leader: {is_leader}')
        elif data == b'IS_LEADER':
            if is_leader:
                server_socket.sendto(b'LEADER', address)
            else:
                server_socket.sendto(b'NOT_LEADER', address)
        else:
            print(f'Received message \'{data.decode()}\' from {address}')
            p = ChatServer(server_socket, data, address, connected_clients, client_names, server_addresses, processed_messages, clock, is_leader)
            p.start()
            p.join()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = socket.gethostbyname(socket.gethostname())
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    service_discovery = ServiceDiscovery()
    service_discovery.start()

    time.sleep(10)

    server_addresses = list(service_discovery.get_servers())
    my_ip = get_local_ip()
    if my_ip not in server_addresses:
        server_addresses.append(my_ip)
    print("Discovered servers:", server_addresses)
    print(f"My IP is {my_ip}")

    leader = initiate_election(server_addresses, my_ip)
    is_leader = (leader == my_ip)
    print(f'I am the leader: {is_leader}')

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 10001))
    print(f'Server up and running on 0.0.0.0:10001')

    manager = multiprocessing.Manager()
    connected_clients = manager.list()
    client_names = manager.dict()
    processed_messages = manager.list()
    clock = LamportClock()
    server_listener(server_socket, connected_clients, client_names, server_addresses, processed_messages, clock, is_leader)
