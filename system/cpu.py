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

    def get_temp(self):
        if not hasattr(psutil, "sensors_temperatures"):
            return None
        
        temps = psutil.sensors_temperatures()

        for name in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz"):
            entries = temps.get(name)
            if not entries:
                continue

            for entry in entries:
                if any(tag in (entry.label or "") for tag in ("Package", "Tctl", "Tdie")):
                    return entry.current

            return entries[0].current
        return None
    
###