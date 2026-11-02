import psutil
import os
from datetime import datetime
from pathlib import Path

class ProcessManager:
    def __init__(self):

        self.cpu_count = psutil.cpu_count(logical=True)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        self.log_path = Path(__file__).resolve().parent.parent / "kills.log"

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
    def nested(self, sort_by="memory", limit=5 , namefilter=""):
        if sort_by == "memory":
            child_key = "memory_bytes"
            group_key = "total_memory_bytes"
        else:
            child_key = "cpu_percent"
            group_key = "total_cpu_percent"
        namefilter = namefilter.lower()
        nests = {}
        for proc in self.get_processes():
            name = proc["name"]

            if namefilter and namefilter not in (name or "").lower():
                continue

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

######

    def cpudetails(self, pid):
        try:
            proc = psutil.Process(pid)
            info = proc.as_dict(
                attrs=["name", "status", "username", "ppid", "num_threads",
                       "create_time", "cmdline", "memory_info"],
                ad_value=None,
            )
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return None
        
        parent = None
        if info["ppid"]:
            try:
                parent = f"{psutil.Process(info['ppid']).name()} ({info['ppid']})"
            except psutil.Error:
                parent = str(info["ppid"])

        started = None
        if info["create_time"]:
            started = datetime.fromtimestamp(info["create_time"]).strftime("%Y-%m-%d %H:%M:%S")

        memory = info["memory_info"]

        return {
            "pid": pid,
            "name": info["name"],
            "status": info["status"],
            "user": info["username"],
            "parent": parent,
            "threads": info["num_threads"],
            "started": started,
            "command": " ".join(info["cmdline"]) if info["cmdline"] else None,
            "memory_bytes": memory.rss if memory else None,
        }

    #####

    def check_kill(self, pid):
        if pid in (0, 1):
            return False, f"Refusing: PID {pid} is a system task", None
        if pid == os.getpid():
            return False, "Refusing: this is UnixManager", None
        try:
            if pid in [parent.pid for parent in psutil.Process().parents()]:
                return False, "Refusing: this is the shell that running UnixManager", None
            name = psutil.Process(pid).name()
        except psutil.ZombieProcess:
            return False, f"PID {pid} is a zombie task only its parent can remove it", None
        except psutil.NoSuchProcess:
            return False, f"PID {pid} does not exist.", None
        except psutil.AccessDenied:
            return False, f"Permission for PID {pid} denied; try Sudo", None
        return True, "", name

#####

    def log_kill(self, pid, name, action, ok):
        try:
            who = psutil.Process().username()
            sudo_user = os.environ.get("SUDO_USER")
            if sudo_user:
                who = f"{who} (sudo by {sudo_user})"

            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"{stamp} | user={who} | pid={pid} | name={name} | action={action} | ok={ok}\n"
            with open(self.log_path, "a", encoding="utf-8") as log_file:
                log_file.write(line)
        except OSError:
            pass

#####

    def _stop(self, pid, force, timeout):
        action = "forcekill" if force else "terminate"
        name = "?"
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            if force:
                proc.kill()
            else:
                proc.terminate()
            _, alive = psutil.wait_procs([proc], timeout=timeout)
        except psutil.NoSuchProcess:
            return (False, f"PID {pid} is already gone.")
        except psutil.AccessDenied:
            return (False, f"Permission denied PID {pid} maybe try sudo.")
        else:
            if alive:
                result = (False, f"{name} ({pid}) is still running. try force kill.")
            else:
                result = (True, f"{name} ({[pid]}) ended.")

        self.log_kill(pid, name, action, result[0])
        return result


    def terminate(self, pid, timeout=2.0):
        return self._stop(pid, False, timeout)

####

    def forcekill(self, pid, timeout=2.0):
        return self._stop(pid, True, timeout) 
    
    ####

    def planfail(self, reason):
        return{"ok": False, "reason": reason, "pids": [], "label": ""}

    ####

    def plankill(self, text):
        text = text.strip()
        tree = False
        if text.lower().startswith("tree "):
            tree = True
            text = text[5:].strip()

        if not text:
            return self.planfail("Type a PID or an app name.")

        if text.isdigit():
            pid= int(text)
            allowed, reason, name = self.check_kill(pid)
            if not allowed:
                return self.planfail(reason)

            if not tree:
                return {"ok": True, "reason": "", "pids": [pid], "label": f"{name} (PID {pid})"}

            try:
                children = [child.pid for child in psutil.Process(pid).children(recursive=True)]
            except psutil.NoSuchProcess:
                return self.planfail(f"PID {pid} does not exist")
            candidates = children + [pid]
            kind = f"{name} (PID {pid} and its related processes"
        else:
            if tree:
                return self.planfail("'tree' needs a PID, for example : tree 123456")

            wanted = text.lower()
            candidates = [
                proc.pid for proc in psutil.process_iter(["name"])
                if (proc.info["name"] or "").lower() == wanted
            ]
            if not candidates:
                similar = sorted({
                    proc.info["name"] for proc in psutil.process_iter(["name"])
                    if proc.info["name"] and wanted in proc.info["name"].lower()
                })[:3]
                hint= f" Similar: {', '.join(similar)}" if similar else ""
                return self.planfail(f"No process is named '{text} .{hint}")
            kind = f"all '{text} processes"

        pids = [candidate for candidate in candidates if self.check_kill(candidate)[0]]
        skipped = len(candidates) - len(pids)
        if not pids:
            return self.planfail("Nothing to end: every match is protected")
        label = f"{len(pids)} processes: {kind}"
        if skipped:
            label += f" ({skipped} protected skipped)"
        return {"ok": True, "reason": "", "pids": pids, "label": label}

    #####

    def stopmany(self, pids, force, timeout):
        action = "forcekill" if force else "terminate"
        signalled = []
        denied = 0

        for pid in pids:
            try:
                proc = psutil.Process(pid)
                name = proc.name()
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                signalled.append((proc, name))
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                denied += 1
                self.log_kill(pid, "?", action, False)
        if not signalled and not denied:
            return False, "Those processes are already gone"

        _, alive = psutil.wait_procs([proc for proc, _ in signalled], timeout=timeout)
        alivepids = {proc.pid for proc in alive}

        for proc, name in signalled:
            self.log_kill(proc.pid, name, action, proc.pid not in alivepids)

        ended = len(signalled) - len(alivepids)
        parts = [f"Ended {ended} of {len(signalled)} processes"]
        if alivepids:
            parts.append(f"{len(alivepids)} still running (try force kill)")
        if denied:
            parts.append(f"{denied} permission denied")

        return (not alivepids and denied == 0), ", ".join(parts) + "."

    ####

    def endtargets(self, pids, force=False, timeout=2.0):
        if len(pids) == 1:
            return self._stop(pids[0], force, timeout)
        return self.stopmany(pids, force, timeout)

    ####
                         

