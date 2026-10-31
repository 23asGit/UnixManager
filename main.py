#lib imports
import psutil
import time
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from system.cpu import get_cpu_usage
from system.memory import get_memory_usage
from system.disk import get_disk_usage
from system.network import get_network_speed
from system.processes import get_processes

#pyfiglet and rich console setup
console = Console()

figlet = Figlet(font="slant")

title = figlet.renderText("TaskUnixManager")

panel = Panel(
    title,
    title="TaskUnixManager",
    border_style="red"
)

console.print(panel)

#defining function

def bytogb(bytes_size):
    return bytes_size / (1024 ** 3)
def bytomb(bytes_size):
    return bytes_size / (1024 ** 2)

#psutil library

#cpu
cpu_usage = get_cpu_usage()
print("CPU status")
print(f"CPU Usage: {cpu_usage}%\n")

#memory
memory = get_memory_usage()
totalram = bytogb(memory["total"])
usedram = bytogb(memory["used"])
availableram = bytogb(memory["available"])
print("Memory status")
print(f"Memory Usage: {memory['percent']}%")
print(f"Used RAM: {usedram:.2f} GB")
print(f"Available RAM: {availableram:.2f} GB")
print(f"Total RAM: {totalram:.2f} GB\n")

#disk
print("Disk status")
disk = get_disk_usage()
totaldisk = bytogb(disk["total"])
useddisk = bytogb(disk["used"])
freedisk = bytogb(disk["free"])
print(f"Disk Usage: {disk['percent']}%")
print(f"Total Disk: {totaldisk:.2f} GB")
print(f"Used Disk: {useddisk:.2f} GB")
print(f"Free Disk: {freedisk:.2f} GB\n")

#network
print("network speed")
network = get_network_speed()
downspeedmb = bytomb(network["downspeed"])
upspeedmb = bytomb(network["upspeed"])
print(f"Download Speed: {downspeedmb:.2f} MB/s")
print(f"Upload Speed: {upspeedmb:.2f} MB/s\n")

#processes
print("Top Processes running")
print("=" * 50)
print(f"{'PID':<10}{'NAME':<20}{'MEMORY':<10}")
print("-" * 50)
procs = get_processes()
for proc in procs:
    print(
        f"{proc['pid']:<10},"
        f"{proc['name']:<20}," 
        f"{proc['memory_percent']:.2f}%\n"
        )
