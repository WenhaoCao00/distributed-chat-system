import socket

def broadcast(ip, port, broadcast_message):
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_socket.sendto(broadcast_message.encode(), (ip, port))
    broadcast_socket.close()

if __name__ == '__main__':
    BROADCAST_IP = "255.255.255.255"
    BROADCAST_PORT = 5973
    message = "Hello, this is a broadcast message!"
    broadcast(BROADCAST_IP, BROADCAST_PORT, message)
