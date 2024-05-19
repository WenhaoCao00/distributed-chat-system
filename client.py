import socket
import threading
import os
import time
from service_discovery import ServiceDiscovery

def receive_messages(client_socket):
    while True:
        try:
            data, server = client_socket.recvfrom(1024)
            print(f'Received message: {data.decode()}')
        except OSError as e:
            print(f"Error receiving data: {e}")
            break

def send_message(server_address, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('0.0.0.0', 0))  # 绑定到一个临时端口

    # 启动接收消息的线程
    receiver_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
    receiver_thread.start()

    try:
        while True:
            message = input("Enter message to send: ")
            client_socket.sendto(message.encode(), (server_address, server_port))
            print(f'Sent to server: {message}')
    except KeyboardInterrupt:
        print("Client is closing.")
    finally:
        client_socket.close()
        print('Socket closed')

if __name__ == '__main__':
    service_discovery = ServiceDiscovery()
    service_discovery.start()

    # 等待一段时间以发现服务器
    time.sleep(5)

    # 获取发现的服务器地址
    server_addresses = service_discovery.get_servers()
    print("Discovered servers:", server_addresses)

    if not server_addresses:
        print("No servers discovered, exiting.")
    else:
        server_address = server_addresses[0]  # 连接到第一个发现的服务器
        send_message(server_address, 10001)
