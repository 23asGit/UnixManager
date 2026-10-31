import psutil
def get_processes(limit=5):
    procs= []
    for proc in psutil.process_iter(
     ['pid', 'name', 'memory_percent']
     ):
     try:
         info = proc.info
         procs.append(info)
     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
         pass
    procs.sort(
        key=lambda processes: processes['memory_percent'],
        reverse=True)
    return procs[:limit]
