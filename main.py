#lib imports
import psutil
import time
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from system.cpu import cpuwatchdog
from system.memory import get_memory_usage
from system.disk import get_disk_usage
from system.network import Networkwatchdog
from system.processes import ProcessManager
from system.utils import bytesformat , speedformat

#network variable
network_watchdog = Networkwatchdog()


#pyfiglet and rich console setup
console = Console()
figlet = Figlet(font="slant")


def banner():
    title = figlet.renderText("TaskUnixManager")

    console.print(Panel(
    title,
    title="TaskUnixManager",
    border_style="red"
    ))


#psutil library

#cpu
cpu_watchdog = cpuwatchdog()
cpu_usage = cpu_watchdog.get_cpu_usage()
print("CPU status")
print(f"CPU Usage: {cpu_usage['percent']}%")
print(f"CPU Cores: {cpu_usage['core']}")
print(f"CPU Threads: {cpu_usage['threads']}")
if cpu_usage["frequency"] is not None:
    print(f"CPU Frequency: {cpu_usage['frequency']:.2f} MHz\n")

#memory
memory = get_memory_usage()
totalram = bytesformat(memory["total"])
usedram = bytesformat(memory["used"])
availableram = bytesformat(memory["available"])
print("Memory status")
print(f"Memory Usage: {memory['percent']}%")
print(f"Used RAM: {usedram}")
print(f"Available RAM: {availableram}")
print(f"Total RAM: {totalram}\n")

#disk
print("Disk status")
disk = get_disk_usage()
totaldisk = bytesformat(disk["total"])
useddisk = bytesformat(disk["used"])
freedisk = bytesformat(disk["free"])
print(f"Disk Usage: {disk['percent']}%")
print(f"Total Disk: {totaldisk}")
print(f"Used Disk: {useddisk}")
print(f"Free Disk: {freedisk}\n")

#network
print("network speed")
network = network_watchdog.get_network_speed()
time.sleep(0.01)  #test delete later
network = network_watchdog.get_network_speed() #test delete later
downspeedmb = speedformat(network["downspeed"])
upspeedmb = speedformat(network["upspeed"])
print(f"Download Speed: {downspeedmb}")
print(f"Upload Speed: {upspeedmb}\n")

#processes
p = ProcessManager()
print("Top Processes running")
print("Enter the Sorting way (1=Ram/2=CPU):")
while True:
    input_choice = input("Enter your choice: ")
    if input_choice == "1" or input_choice == "2":
        break
    print("Invalid choice. Please enter 1 or 2.")
EXPAND = False 

sort_by = "memory" if input_choice == "1" else "cpu"
nests = p.nested(sort_by)
print("=" * 80)
print(f"{'NAME':<25}{'MEMORY(GB/MB)':<22}{'MEMORY(%)':<15}{'CPU':<15}")
print("-" * 80)

for nest in nests:
    label = f"{nest['name']} ({nest['count']})"
    memoryp = f"{nest['memory_percent']:.2f}%"
    cpup = f"{nest['total_cpu_percent']:.2f}%"

    print(
        f"{label:<25}"
        f"{bytesformat(nest['total_memory_bytes']):<22}"
        f"{memoryp:<15}"
        f"{cpup:<15}"
    )
    if EXPAND:
        for child in nest["children"]:
            child_label = f"  └─ PID: {child['pid']}"
            child_memoryp = f"{child['memory_percent']:.2f}%"
            child_cpup = f"{child['cpu_percent']:.2f}%"

            print(
                f"{child_label:<25}"
                f"{bytesformat(child['memory_bytes']):<22}"
                f"{child_memoryp:<15}"
                f"{child_cpup:<15}"
            )