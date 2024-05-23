class LamportClock:
    def __init__(self):
        self.time = 0

    def increment(self):
        self.time += 1

    def update(self, received_time):
        self.time = max(self.time, received_time) + 1

    def get_time(self):
        return self.time

def local_event(clock):
    clock.increment()
    print(f'Local event. Lamport timestamp is {clock.get_time()}')

def send_event(clock, pipe):
    clock.increment()
    pipe.send(clock.get_time())
    print(f'Sent event. Lamport timestamp is {clock.get_time()}')

def receive_event(clock, pipe):
    received_time = pipe.recv()
    clock.update(received_time)
    print(f'Received event. Lamport timestamp is {clock.get_time()}')
