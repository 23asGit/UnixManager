import psutil
import time

class Networkwatchdog:
    def __init__(self):
        self.prev_sent = psutil.net_io_counters().bytes_sent
        self.prev_recv = psutil.net_io_counters().bytes_recv
        self.prev_time = time.monotonic()
    def get_network_speed(self):
        network = psutil.net_io_counters()
        network_sent = network.bytes_sent
        network_recv = network.bytes_recv
        current_time = time.monotonic()    
        elapsed_time = current_time - self.prev_time

        downspeed = (network_recv - self.prev_recv) / elapsed_time if elapsed_time > 0 else 0
        upspeed = (network_sent - self.prev_sent) / elapsed_time if elapsed_time > 0 else 0
        self.prev_sent = network_sent
        self.prev_recv = network_recv
        self.prev_time = current_time

        return {
        "downspeed": downspeed,
        "upspeed": upspeed
    }
#####