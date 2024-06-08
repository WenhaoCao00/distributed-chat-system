import threading
import time
import socket
import json
from service_discovery import ServiceDiscovery
from ring_election import initiate_election

class Heartbeat:
    def __init__(self, service_discovery):
        self.service_discovery = service_discovery

    def check_leader(self):
        while True:
            time.sleep(5)
            server_addresses = self.service_discovery.server_addresses
            leader_exists = any(server[1] for server in server_addresses)

            if not leader_exists:
                new_leader = initiate_election([ip[0] for ip in server_addresses], self.service_discovery.local_ip)

                if new_leader:
                    self.service_discovery.update_leader(new_leader)
                    self.broadcast_new_leader(new_leader)
                else:
                    print("Election failed. No leader selected.")

    def broadcast_new_leader(self, new_leader_ip):
        notification_message = {"mid": new_leader_ip, "isLeader": True}
        message = json.dumps(notification_message).encode()
        for server_ip, _ in self.service_discovery.server_addresses:
            self.send_notification(server_ip, message)

    def send_notification(self, server_ip, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(message, (server_ip, self.service_discovery.port))
            print(f"Notification sent to {server_ip}: {message.decode()}")
        except OSError as e:
            print(f"Error sending notification to {server_ip}: {e}")
        finally:
            sock.close()

if __name__ == "__main__":
    service_discovery = ServiceDiscovery()
    heartbeat = Heartbeat(service_discovery)

    heartbeat_thread = threading.Thread(target=heartbeat.check_leader)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Heartbeat monitor stopped.")
