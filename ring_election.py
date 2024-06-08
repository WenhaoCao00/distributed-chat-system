import socket
import json
import time

def form_ring(members):
    sorted_binary_ring = sorted([socket.inet_aton(member) for member in members])
    sorted_ip_ring = [socket.inet_ntoa(node) for node in sorted_binary_ring]
    return sorted_ip_ring

def get_neighbour(ring, current_node_ip, direction='left'):
    current_node_index = ring.index(current_node_ip)
    if direction == 'left':
        return ring[(current_node_index + 1) % len(ring)]
    else:
        return ring[(current_node_index - 1) % len(ring)]

def initiate_election(members, my_ip):
    if my_ip not in members:
        members.append(my_ip)
    ring = form_ring(members)
    neighbour = get_neighbour(ring, my_ip, 'left')
    election_message = {"mid": my_ip, "isLeader": False}
    election_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Ring: {ring}")
    print(f"My IP: {my_ip}")
    print(f"Neighbour IP: {neighbour}")

    try:
        election_socket.bind(('0.0.0.0', 10002))
        print("Socket successfully bound to 0.0.0.0:10002")
    except OSError as e:
        print(f"Error binding socket: {e}")
        return None

    try:
        election_socket.sendto(json.dumps(election_message).encode(), (neighbour, 10002))
        print(f"Election message sent to {neighbour}:10002")
    except OSError as e:
        print(f"Error sending election message: {e}")
        return None

    election_socket.settimeout(8)  # 设置超时时间为10秒

    while True:
        try:
            data, addr = election_socket.recvfrom(1024)
            message = json.loads(data.decode())
            print(f"Received election message: {message} from {addr}")
            if message['isLeader']:
                print(f"Leader elected: {message['mid']}")
                return message['mid']
            if message['mid'] < my_ip:
                new_message = {"mid": my_ip, "isLeader": False}
                election_socket.sendto(json.dumps(new_message).encode(), (neighbour, 10002))
            elif message['mid'] > my_ip:
                election_socket.sendto(data, (neighbour, 10002))
            elif message['mid'] == my_ip:
                leader_message = {"mid": my_ip, "isLeader": True}
                election_socket.sendto(json.dumps(leader_message).encode(), (neighbour, 10002))
                return my_ip
        except socket.timeout:
            print("Election timeout, no response received.")
            break
        except OSError as e:
            print(f"Error receiving or processing message: {e}")
            break

    return None  # 超时或出错时返回None
