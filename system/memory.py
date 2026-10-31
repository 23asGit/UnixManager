import psutil

def get_memory_usage():
    memory = psutil.virtual_memory()
    return {
        "percent": memory.percent,
        "used": memory.used,
        "available": memory.available,
        "total": memory.total
    }