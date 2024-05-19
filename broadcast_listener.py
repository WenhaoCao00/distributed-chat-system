import socket

if __name__ == '__main__':
    BROADCAST_PORT = 5973
    BROADCAST_ADDRESS = '0.0.0.0'

    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind((BROADCAST_ADDRESS, BROADCAST_PORT))

    print("Listening to broadcast messages on all interfaces")

    while True:
        data, addr = listen_socket.recvfrom(1024)
        if data:
            print("Received broadcast message:", data.decode())
