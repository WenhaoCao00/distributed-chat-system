import socket
import threading
import time
import uuid
from service_discovery import ServiceDiscovery
from ring_election import initiate_election
from lamport_clock import LamportClock

class ChatClient:
    def __init__(self):
        self.service_discovery = ServiceDiscovery()
        self.clock = LamportClock()
        self.server_port = 10001
        self.client_name = None
        self.leader_address = None
        self.client_socket = None
        self.unconfirmed_messages = {}  # 保存未确认的消息
        self.ack_received = threading.Event()

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
                elif message.startswith("NEW_LEADER"):  
                    new_leader_ip = message.split(':')[1]
                    print(f"\rNew leader elected: {new_leader_ip}\n", end='', flush=True)
                    self.leader_address = new_leader_ip
                    self.register_name() # Re-register with the new leader
                elif message.startswith("SERVER_ACK"):
                    msg_id = message.split(':')[1]
                    print(f"\rMessage {msg_id} confirmed by server.\n{self.client_name}: ", end='', flush=True)
                    if msg_id in self.unconfirmed_messages:
                        del self.unconfirmed_messages[msg_id]
                    self.ack_received.set()
                else:
                    
                    print(f"\r{message}\n{self.client_name}: ", end='', flush=True)
            except OSError as e:
                print(f"\rError receiving data: {e}\n", end='', flush=True)
                break

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


    def register_name(self):
        ip = self.get_local_ip()
        port = self.client_socket.getsockname()[1]
        while True:

            name = f"({ip}/{port})"
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
                self.unconfirmed_messages[message_id] = full_message

                while message_id in self.unconfirmed_messages:
                    self.ack_received.clear()
                    self.client_socket.sendto(full_message.encode(), (self.leader_address, self.server_port))
                    if not self.ack_received.wait(5):
                        print("No ACK received, initiating re-election...")
                        self.initiate_re_election()
                        # if self.leader_address is None:
                        #     print("No leader found after re-election, exiting.")
                        #     return
                        break
                        
                        #self.resend_unconfirmed_messages()
                #self.client_socket.sendto(full_message.encode(), (self.leader_address, self.server_port))
        except KeyboardInterrupt:
            print("Client is closing.")

    # def resend_unconfirmed_messages(self):
        
    #     for message_id, full_message in self.unconfirmed_messages.items():
    #         if isinstance(full_message, str):
    #             self.client_socket.sendto(full_message.encode(), (self.leader_address, self.server_port))
    #             print(f"Resent unconfirmed message: {full_message}")
    #         else:
    #             print(f"Message {message_id} is not a string, skipping...")


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
    
    def initiate_re_election(self):
        server_addresses = self.discover_servers()
        if not server_addresses:
            return None
        initiate_election(server_addresses, self.get_local_ip())
        self.leader_address = self.find_leader(server_addresses) 
        if self.leader_address is None:
            print("No leader found after re-election, exiting.")
            return
        # 在新的Leader上重新注册
        self.register_name()
        

    def discover_servers(self):
        self.service_discovery.start()
        time.sleep(5)
        return list(self.service_discovery.get_servers())

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