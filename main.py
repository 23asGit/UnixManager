#lib imports
import time
import io
import shutil
import os
import select
import sys
import termios
import tty
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from system.cpu import cpuwatchdog
from system.memory import get_memory_usage
from system.disk import get_disk_usage
from system.network import Networkwatchdog
from system.processes import ProcessManager
from system.utils import bytesformat , speedformat
from contextlib import redirect_stdout, contextmanager

### 
REFRESH_SECONDS = 1
###

#pyfiglet and rich console setup
console = Console()
##figlet = Figlet(font="slant")


def banner():
    columns = shutil.get_terminal_size().columns
    
    if columns >= 88:
        font = "slant"
    elif columns >= 76:
        font = "small"
    else:
        console.print("[bold red]TaskUnixManager[/bold red]")
        return
        
    title = Figlet(font=font, width=200).renderText("TaskUnixManager")

    console.print(Panel(
        title,
        title="TaskUnixManager",
        border_style="red"
    ))


#psutil library

#cpu
def cpudef(cpu_watchdog):
    cpu_usage = cpu_watchdog.get_cpu_usage()
    print("CPU status")
    print(f"CPU Usage: {cpu_usage['percent']:.2f}%")
    print(f"CPU Cores: {cpu_usage['core']}")
    print(f"CPU Threads: {cpu_usage['threads']}")
    if cpu_usage["frequency"] is not None:
       print(f"CPU Frequency: {cpu_usage['frequency']:.2f} MHz\n")
    print()

#memory
def memorydef():
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
def diskdef():
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
def networkdef(network_watchdog):  
    print("network speed")
    network = network_watchdog.get_network_speed()
    downspeedmb = speedformat(network["downspeed"])
    upspeedmb = speedformat(network["upspeed"])
    print(f"Download Speed: {downspeedmb}")
    print(f"Upload Speed: {upspeedmb}\n")

#processes
def processesdef(process_manager, sort_by, expand):
    nests = process_manager.nested(sort_by)
    print("Top Processes running")
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
        if expand:
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


#####
#framerender
#####

def framerender(cpu_watchdog, network_watchdog, process_manager, sort_by , expand):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        banner()
        cpudef(cpu_watchdog)
        memorydef()
        diskdef()
        networkdef(network_watchdog)
        processesdef(process_manager, sort_by, expand)
    return buffer.getvalue().splitlines()

def drawframe(frame_lines, scroll, sort_by, expand):
    size = shutil.get_terminal_size()
    view_height = max(size.lines - 1, 1)
    max_scroll = max(len(frame_lines) - view_height, 0)
    scroll = min(max(scroll, 0), max_scroll)

    view = frame_lines[scroll:scroll + view_height]
    view = [line + "\033[K" for line in view]

    showen_end = scroll + len(view)
    footer = (
        f" ↑↓/PgUp/PgDn scroll | m RAM | c CPU | e expand:{'on' if expand else 'off'} | q quit"
        f"   [{scroll + 1}-{showen_end} of {len(frame_lines)}] sort:{sort_by}"
        )

    print(
        "\033[H" + "\n".join(view) + "\033[J"
        + f"\033[{size.lines};1H\033[7m{footer}\033[K\033[0m", end = "" , flush = True
    )
    return scroll


#####
#Keys
#####

keys = {
    "\x1b[A": "up",    "\x1bOA": "up",
    "\x1b[B": "down",  "\x1bOB": "down",
    "\x1b[5~": "page_up", "\x1b[6~": "page_down",
    "\x1b[H": "home",  "\x1b[F": "end",
}

def rkeys(timeout):
    ready, _, _ = select.select([sys.stdin], [], [], max(timeout, 0))
    if not ready:
        return []
    data = os.read(sys.stdin.fileno(), 64).decode(errors="ignore")
    keysl= []
    i = 0
    while i < len(data):
        for seq, name in keys.items():
            if data.startswith(seq, i):
                keysl.append(name)
                i += len(seq)
                break
        else:
            keysl.append(data[i])
            i += 1
    return keysl

@contextmanager
def terminal():
    td = sys.stdin.fileno()
    old_settings = termios.tcgetattr(td)
    try:
        tty.setcbreak(td)
        print("\033[?1049h\033[?25l", end="", flush=True)
        yield
    finally:
        termios.tcsetattr(td, termios.TCSADRAIN, old_settings)
        print("\033[?25h\033[?1049l", end="", flush=True)



#####
#MAIN
#####
def main():
    cpu_watchdog = cpuwatchdog()
    network_watchdog = Networkwatchdog()
    process_manager = ProcessManager()
    sort_by = "memory"
    expand = False
    scroll = 0
    frame_lines = []
    next_refresh = 0.0
    running = True

    try:
        with terminal():
            while running:
                now = time.monotonic()
                if now >= next_refresh:
                    frame_lines = framerender(
                        cpu_watchdog, network_watchdog, process_manager, sort_by, expand
                    )
                    next_refresh = now + REFRESH_SECONDS

                scroll = drawframe(frame_lines, scroll, sort_by, expand)

                page = max(shutil.get_terminal_size().lines - 2, 1)
                for key in rkeys(next_refresh - time.monotonic()):
                    if key in ("up", "k"):
                        scroll -= 1
                    elif key in ("down", "j"):
                        scroll += 1
                    elif key == "pageup":
                        scroll -= page
                    elif key == "pagedown":
                        scroll += page
                    elif key == "home":
                        scroll = 0
                    elif key == "end":
                        scroll = len(frame_lines)
                    elif key == "m":
                        sort_by = "memory"
                    elif key == "c":
                        sort_by = "cpu"
                    elif key == "e":
                        expand = not expand
                    elif key == "q":
                        running = False
    except KeyboardInterrupt:
        pass

    print("\nTaskUnixManager stopped")        

if __name__ == "__main__":
    main()