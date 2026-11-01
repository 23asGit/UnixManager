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
from system.utils import bytesformat , speedformat, progressbar
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

def corerows(per_core):
    lines = []
    for start in range(0, len(per_core), 2):
        row= ""
        for number in range (start, min(start + 2, len(per_core))):
            usage = per_core[number]
            row += f"Core {number:<2} {progressbar(usage, 12)} {usage:5.1f}%    "
        lines.append(row.rstrip())
    return lines


def cpudef(cpu_watchdog, show_cores):
    cpu_usage = cpu_watchdog.get_cpu_usage()
    temp = cpu_watchdog.get_temp()
    print("CPU status")
    print(f"CPU Usage: {cpu_usage['percent']:.2f}%")
    print(f"CPU Cores: {cpu_usage['core']}")
    print(f"CPU Threads: {cpu_usage['threads']}")
    if cpu_usage["frequency"] is not None:
       print(f"CPU Frequency: {cpu_usage['frequency']:.2f} MHz")
    print()
    if temp is not None:
        print(f"CPU Temperature: {temp:.1f} °C")
    else:
        print("CPU Temperature: N/A")
    if show_cores:
        print()
        for line in corerows(cpu_usage["cores"]):
            print(line)
    print()

#memory
def memorydef():
    memory = get_memory_usage()
    totalram = bytesformat(memory["total"])
    usedram = bytesformat(memory["used"])
    availableram = bytesformat(memory["available"])
    print("Memory status")
    print(f"Memory Usage: {memory['percent']}% {progressbar(memory['percent'])}")
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
    print(f"Disk Usage: {disk['percent']}% {progressbar(disk['percent'])}")
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
def processesdef(process_manager, sort_by, expand, namefilter):
    nests = process_manager.nested(sort_by, namefilter=namefilter)
    title = "Top Processes running"
    if namefilter:
        title += f"  (filter: '{namefilter}')"
    print(title)
    print("=" * 80)
    print(f"{'NAME':<25}{'MEMORY(GB/MB)':<22}{'MEMORY(%)':<15}{'CPU':<15}")
    print("-" * 80)

    if not nests:
        print("No process matches this filter")

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

def na(value):
    return value if value is not None else "N/A"

def detailscpudef(process_manager, pid):
    details = process_manager.cpudetails(pid)
    width = shutil.get_terminal_size().columns
    print(f"Process details - PID {pid}   (press x to close)")
    print("-" * min(width, 80))
    if details is None:
        print("This process no longer exists!!\n")
        return
    command = details["command"] or "N/A"
    if len(command) > width - 12:
        command = command[:width - 13] + "..."

    memory = bytesformat(details["memory_bytes"]) if details["memory_bytes"] is not None else "N/A"
    print(f"Name:     {na(details['name'])}")
    print(f"Status:   {na(details['status'])}")
    print(f"User:     {na(details['user'])}")
    print(f"Parent:   {na(details['parent'])}")
    print(f"Threads:  {na(details['threads'])}")
    print(f"Started:  {na(details['started'])}")
    print(f"Memory:   {memory}")
    print(f"Command:  {command}")
    print()


#####
#framerender
#####

def framerender(cpu_watchdog, network_watchdog, process_manager, sort_by , expand, show_cores, namefilter, details_pid):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        banner()
        if details_pid is not None:
            detailscpudef(process_manager, details_pid)
        cpudef(cpu_watchdog, show_cores)
        memorydef()
        diskdef()
        networkdef(network_watchdog)
        processesdef(process_manager, sort_by, expand, namefilter)
    return buffer.getvalue().splitlines()

def drawframe(frame_lines, scroll, sort_by, expand, show_cores, prompt ):
    size = shutil.get_terminal_size()
    view_height = max(size.lines - 1, 1)
    max_scroll = max(len(frame_lines) - view_height, 0)
    scroll = min(max(scroll, 0), max_scroll)

    view = frame_lines[scroll:scroll + view_height]
    view = [line + "\033[K" for line in view]

    if prompt is not None:
        footer = prompt
    else:
        showen_end = scroll + len(view)
        footer = (
        f" ↑↓ / scroll | m RAM | c CPU | e expand:{'on' if expand else 'off'}"
        f"|t cores:{'on' if show_cores else 'off'} | '/' find | i info | q quit | [{scroll + 1}-{showen_end} / {len(frame_lines)}]"
        )
    footer = footer[:size.columns]
    
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
    "\x1b[5~": "pageup", "\x1b[6~": "pagedown",
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
#prompt for testing
#####
def editprompt(key, text):
    """Returns (new_text, action). action is none, "submit" or "cancel" """
    if key in ("\r", "\n"):
        return text, "submit"
    if key == "\x1b":
        return text, "cancel"
    if key in ("\x7f", "\x08"):
        return text[:-1], None
    if len(key) == 1 and key.isprintable():
        return text + key, None
    return text, None


#####
#MAIN
#####
def main():
    cpu_watchdog = cpuwatchdog()
    network_watchdog = Networkwatchdog()
    process_manager = ProcessManager()
    sort_by = "memory"
    expand = False
    show_cores = False
    namefilter = ""
    details_pid = None
    mode = "normal"
    prompt_text = ""
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
                        cpu_watchdog, network_watchdog, process_manager, sort_by, expand, show_cores,
                        namefilter, details_pid
                    )
                    next_refresh = now + REFRESH_SECONDS
                prompt = None
                if mode == "filter":
                    prompt = f" Filter by name: {prompt_text}█    Enter = apply | Esc = cancel"
                elif mode == "info":
                    prompt = f" Show details for PID: {prompt_text}█    Enter = open | Esc = cancel"
                
                scroll = drawframe(frame_lines, scroll, sort_by, expand, show_cores, prompt)

                page = max(shutil.get_terminal_size().lines - 2, 1)
                for key in rkeys(next_refresh - time.monotonic()):
####                 typing mode
                    if mode != "normal":
                        prompt_text, action = editprompt(key, prompt_text)
                        if action == "cancel":
                            mode = "normal"
                        elif action == "submit":
                            value = prompt_text.strip()
                            if mode == "filter":
                                namefilter = value
                                scroll = 0
                            elif mode == "info":
                                details_pid = int(value) if value.isdigit() else None
                            mode = "normal"
                            next_refresh = 0.0 
                        continue

####                  normal mode                    
                    if key == "up":
                        scroll -= 1
                    elif key == "down":
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
                    elif key == "t":
                        show_cores = not show_cores
                    elif key == "/":
                        mode = "filter"
                        prompt_text = namefilter
                    elif key == "i":
                        mode = "info"
                        prompt_text = ""
                    elif key == "x":
                        details_pid = None
                        next_refresh = 0.0
                    elif key == "q":
                        running = False
    except KeyboardInterrupt:
        pass

    print("\nTaskUnixManager stopped")        

if __name__ == "__main__":
    main()