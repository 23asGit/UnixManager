import psutil

class ProcessManager:
    def __init__(self):

        self.cpu_count = psutil.cpu_count(logical=True)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

#######

    def get_processes(self):
        procs= []
        for proc in psutil.process_iter(
         ['pid', 'name', 'memory_percent']
         ):
         try:
             cpu_usage = min(proc.cpu_percent(interval=None) / self.cpu_count, 100.0)
             procs.append({
             'pid': proc.info['pid'],
             'name': proc.info['name'],
             'memory_percent': proc.info['memory_percent'],
             'memory_bytes': proc.memory_info().rss,
             'cpu_percent': cpu_usage
         })
         except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
             pass
        return procs

#######

    def get_top_memory(self, limit=5):
        procs = self.get_processes()
        return sorted(
        procs,
        key=lambda process: process["memory_percent"],
        reverse=True
    )[:limit]

#######

    def get_top_cpu(self, limit=5):
        procs = self.get_processes()

        return sorted(
        procs,
        key=lambda process: process["cpu_percent"],
        reverse=True
    )[:limit]

#######
    def nested(self, sort_by="memory", limit=5):
        if sort_by == "memory":
            child_key = "memory_bytes"
            group_key = "total_memory_bytes"
        else:
            child_key = "cpu_percent"
            group_key = "total_cpu_percent"
        nests = {}
        for proc in self.get_processes():
            name = proc["name"]

            if name not in nests:
                nests[name] = {
                "name": name,
                "total_memory_bytes": 0.0,
                "memory_percent": 0.0,
                "total_cpu_percent": 0.0,
                "count": 0,
                "children": []
                }
            nest=nests[name]
            nest["total_memory_bytes"] += proc["memory_bytes"]
            nest["memory_percent"] += proc["memory_percent"]
            nest["total_cpu_percent"] += proc["cpu_percent"]
            nest["count"] += 1
            nest["children"].append(proc)

        result = list(nests.values())

        for nest in result:
            nest["total_cpu_percent"] = min(nest["total_cpu_percent"], 100.0)
            nest["children"].sort(key=lambda process: process[child_key], reverse=True)
        result.sort(key=lambda n: n[group_key], reverse=True)

        return result[:limit]
