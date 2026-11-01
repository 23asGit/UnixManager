import psutil


class cpuwatchdog:
    def __init__(self):
        psutil.cpu_percent(interval=None, percpu=True)



    def get_cpu_usage(self):
        cores = psutil.cpu_percent(interval=None, percpu=True)
        cores = [min(core, 100.0) for core in cores]
        totalcores = sum(cores) / len(cores)
        freq = psutil.cpu_freq()
        
        return {
        "percent": min(totalcores, 100.0),
        "cores": cores,
        "core": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
        "frequency": freq.current if freq else None

    }