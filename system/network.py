import psutil
import time

def get_network_speed():
    network1 = psutil.net_io_counters()
    network_sent1 = network1.bytes_sent
    network_recv1 = network1.bytes_recv
    start_time = time.monotonic()
    time.sleep(1)
    network2 = psutil.net_io_counters()
    network_sent2 = network2.bytes_sent
    network_recv2 = network2.bytes_recv
    end_time = time.monotonic()
    elapsed_time = end_time - start_time
    downspeed = (network_recv2 - network_recv1) / elapsed_time
    upspeed = (network_sent2 - network_sent1) / elapsed_time

    return {
        "downspeed": downspeed,
        "upspeed": upspeed
    }