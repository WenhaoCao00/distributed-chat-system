import socket
import threading
import time
import uuid
from service_discovery import ServiceDiscovery
from lamport_clock import LamportClock

class ChatClient:
    def __init__(self):
        self.service_discovery = ServiceDiscovery()
        self.clock = LamportClock()
        self.server_port = 10001
        self.client_name = None
        self.leader_address = None
        self.client_socket = None

    def receive_messages(self):
        while True:
            try:
                data, server = self.client_socket.recvfrom(1024)
                message = data.decode()
                if message.startswith("REJECTED"):
                    print("\rName already taken. Please enter a different name.\n", end='', flush=True)
                    return False
                elif message.startswith("ACCEPTED"):
                    print("\rName accepted. You can start sending messages.\n", end='', flush=True)
                    return True
                elif message.startswith("NOT_LEADER"):
                    print("\rConnected to a non-leader server, reinitiating connection.\n", end='', flush=True)
                    return "NOT_LEADER"
                elif not message.startswith("SERVER_ACK"):
                    print(f"\r{message}\n{self.client_name}: ", end='', flush=True)
            except OSError as e:
                print(f"\rError receiving data: {e}\n", end='', flush=True)
                break

    def register_name(self):
        while True:
            name = input("Enter your name: ")
            register_message = f'REGISTER:{name}'
            self.client_socket.sendto(register_message.encode(), (self.leader_address, self.server_port))
            result = self.receive_messages()
            if result == "NOT_LEADER":
                return "NOT_LEADER"
            elif result:
                self.client_name = name
                return name

    def send_messages(self):
        try:
            while True:
                message = input(f"{self.client_name}: ")
                if message.strip().lower() == "exit":
                    print("Exiting...")
                    break
                self.clock.increment()
                message_id = str(uuid.uuid4())
                full_message = f'CLIENT:{message_id}:{self.clock.get_time()}:{self.client_name}:{message}'
                self.client_socket.sendto(full_message.encode(), (self.leader_address, self.server_port))
        except KeyboardInterrupt:
            print("Client is closing.")

    def find_leader(self, server_addresses):
        self.create_socket()  # Ensure the socket is created before trying to use it
        for server_address in server_addresses:
            try:
                self.client_socket.sendto(b'IS_LEADER', (server_address, self.server_port))
                data, server = self.client_socket.recvfrom(1024)
                message = data.decode()
                if message == 'LEADER':
                    return server_address
            except ConnectionResetError:
                print(f"Connection to {server_address} was reset. Trying next server...")
                continue
        return None

    def discover_servers(self):
        self.service_discovery.start()
        time.sleep(5)
        return [ip[0] for ip in self.service_discovery.get_servers()]

    def create_socket(self):
        if self.client_socket:
            self.client_socket.close()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_socket.bind(('0.0.0.0', 0))

    def main(self):
        server_addresses = self.discover_servers()
        print("Discovered servers:", server_addresses)

        if not server_addresses:
            print("No servers discovered, exiting.")
            return
        self.leader_address = self.find_leader(server_addresses)
        if self.leader_address is None:
            print("No leader found, exiting.")
            return

        while True:
            self.create_socket()
            print(f'Client bound to port {self.client_socket.getsockname()[1]}')

            client_name = self.register_name()
            if client_name == "NOT_LEADER":
                self.leader_address = self.find_leader(server_addresses)
                if self.leader_address is None:
                    print("No leader found after reattempt, exiting.")
                    return
                continue

            receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receiver_thread.start()

            self.send_messages()

            self.client_socket.close()
            print('Socket closed')
            break

if __name__ == '__main__':
    client = ChatClient()
    client.main()
