import socket
import threading
import os
import time
import uuid
from service_discovery import ServiceDiscovery
from lamport_clock import LamportClock

def receive_messages(client_socket):
    while True:
        try:
            data, server = client_socket.recvfrom(1024)
            message = data.decode()
            if message.startswith("REJECTED"):
                print("Name already taken. Please enter a different name.")
                return False
            elif message.startswith("ACCEPTED"):
                print("Name accepted. You can start sending messages.")
                return True
            elif message.startswith("NOT_LEADER"):
                print("Connected to a non-leader server, reinitiating connection.")
                return "NOT_LEADER"
            else:
                print(f'Received message: {message}')
        except OSError as e:
            print(f"Error receiving data: {e}")
            break

def register_name(client_socket, server_address, server_port):
    while True:
        name = input("Enter your name: ")
        register_message = f'REGISTER:{name}'
        client_socket.sendto(register_message.encode(), (server_address, server_port))
        result = receive_messages(client_socket)
        if result == "NOT_LEADER":
            return "NOT_LEADER"
        elif result:
            return name

def send_messages(client_socket, server_address, server_port, clock, client_name):
    try:
        while True:
            message = input("Enter message to send: ")
            if message.strip().lower() == "exit":
                print("Exiting...")
                break
            clock.increment()
            message_id = str(uuid.uuid4())  # 生成唯一消息ID
            full_message = f'CLIENT:{message_id}:{clock.get_time()}:{client_name}:{message}'
            client_socket.sendto(full_message.encode(), (server_address, server_port))
            print(f'Sent to server {server_address}:{server_port}: {full_message}')
    except KeyboardInterrupt:
        print("Client is closing.")

def main():
    service_discovery = ServiceDiscovery()
    service_discovery.start()

    # 等待一段时间以发现服务器
    time.sleep(5)

    # 获取发现的服务器地址
    server_addresses = list(service_discovery.get_servers())
    print("Discovered servers:", server_addresses)

    if not server_addresses:
        print("No servers discovered, exiting.")
        return

    while True:
        clock = LamportClock()
        server_address = server_addresses[0]  # 连接到第一个发现的服务器
        server_port = 10001

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.bind(('0.0.0.0', 0))  # 绑定到一个临时端口
        print(f'Client bound to port {client_socket.getsockname()[1]}')

        # 注册名字
        client_name = register_name(client_socket, server_address, server_port)
        if client_name == "NOT_LEADER":
            continue

        # 启动接收消息的线程
        receiver_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
        receiver_thread.start()

        # 启动发送消息的逻辑
        send_messages(client_socket, server_address, server_port, clock, client_name)

        # 关闭socket
        client_socket.close()
        print('Socket closed')
        break

if __name__ == '__main__':
    main()
