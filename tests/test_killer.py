import os
import subprocess
import sys
import time
import psutil
import pytest

from system.processes import ProcessManager

STUBBORN_CODE = (
    "import signal, time\n"
    "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    "print('ready', flush=True)\n"
    "time.sleep(100)\n"
)


@pytest.fixture
def manager(tmp_path):
    manager = ProcessManager()
    manager.log_path = tmp_path / "kills.log"
    return manager


@pytest.fixture
def sleeper():
    """A harmless process we can safely kill. Always cleaned up afterwards."""
    process = subprocess.Popen(["sleep", "100"])
    yield process
    if process.poll() is None:
        process.kill()
        process.wait()


@pytest.fixture
def stubborn():
    """A process that ignores SIGTERM, so only a force kill works."""
    process = subprocess.Popen([sys.executable, "-c", STUBBORN_CODE], stdout=subprocess.PIPE)
    process.stdout.readline()
    yield process
    if process.poll() is None:
        process.kill()
        process.wait()




@pytest.mark.parametrize("pid", [0, 1])
def test_refuses_system_pids(manager, pid):
    allowed, reason, name = manager.check_kill(pid)
    assert allowed is False
    assert "Refusing" in reason
    assert name is None


def test_refuses_own_process(manager):
    allowed, reason, _ = manager.check_kill(os.getpid())
    assert allowed is False
    assert "Refusing" in reason


def test_refuses_parent_shell(manager):
    allowed, reason, _ = manager.check_kill(os.getppid())
    assert allowed is False
    assert "Refusing" in reason


def test_missing_pid_is_not_allowed(manager):
    allowed, reason, _ = manager.check_kill(99999999)
    assert allowed is False
    assert "does not exist" in reason


# allowed case 

def test_normal_process_is_allowed(manager, sleeper):
    allowed, reason, name = manager.check_kill(sleeper.pid)
    assert allowed is True
    assert reason == ""
    assert name == "sleep"


#

@pytest.mark.parametrize("pid", [0, 1, 99999999, os.getpid(), os.getppid()])
def test_check_kill_always_returns_three_values(manager, pid):
    assert len(manager.check_kill(pid)) == 3


#terminate/force kill

def test_terminate_stops_normal_process(manager, sleeper):
    ok, message = manager.terminate(sleeper.pid)
    assert ok is True
    assert "ended" in message
    assert not psutil.pid_exists(sleeper.pid)


def test_terminate_fails_on_stubborn_process(manager, stubborn):
    ok, message = manager.terminate(stubborn.pid, timeout=0.5)
    assert ok is False
    assert "still running" in message
    assert psutil.pid_exists(stubborn.pid)


def test_forcekill_stops_stubborn_process(manager, stubborn):
    ok, message = manager.forcekill(stubborn.pid)
    assert ok is True
    assert not psutil.pid_exists(stubborn.pid)


def test_killing_twice_reports_already_gone(manager, sleeper):
    manager.forcekill(sleeper.pid)
    ok, message = manager.terminate(sleeper.pid)
    assert ok is False
    assert "already gone" in message

@pytest.fixture
def named_sleepers(tmp_path):
    """Three processes sharing a unique name, so we never match real apps."""
    executable = tmp_path / "killtest_sleep"
    os.symlink("/bin/sleep", executable)
    processes = [subprocess.Popen([str(executable), "100"]) for _ in range(3)]
    yield processes
    for process in processes:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_plan_by_name_finds_all_matching(manager, named_sleepers):
    plan = manager.plankill("killtest_sleep")
    assert plan["ok"] is True
    assert sorted(plan["pids"]) == sorted(p.pid for p in named_sleepers)


def test_plan_by_name_is_case_insensitive(manager, named_sleepers):
    assert len(manager.plankill("KillTest_Sleep")["pids"]) == 3


def test_plan_by_name_unknown(manager):
    plan = manager.plankill("no_such_app_xyz")
    assert plan["ok"] is False
    assert "No process is named" in plan["reason"]


def test_plan_skips_the_monitor_itself(manager):
    plan = manager.plankill(psutil.Process().name())
    assert os.getpid() not in plan["pids"]


def test_plan_empty_input(manager):
    assert manager.plankill("   ")["ok"] is False


def test_plan_tree_needs_a_pid(manager):
    plan = manager.plankill("tree opera")
    assert plan["ok"] is False
    assert "needs a PID" in plan["reason"]


def test_plan_single_pid(manager, sleeper):
    plan = manager.plankill(str(sleeper.pid))
    assert plan["ok"] is True
    assert plan["pids"] == [sleeper.pid]


def test_end_targets_kills_the_whole_name_group(manager, named_sleepers):
    plan = manager.plankill("killtest_sleep")
    ok, message = manager.endtargets(plan["pids"])
    assert ok is True
    assert "Ended 3 of 3" in message
    assert not any(psutil.pid_exists(p.pid) for p in named_sleepers)


def test_tree_kill_ends_parent_and_children(manager):
    code = (
        "import subprocess, time\n"
        "subprocess.Popen(['sleep', '100'])\n"
        "subprocess.Popen(['sleep', '100'])\n"
        "time.sleep(100)\n"
    )
    parent = subprocess.Popen([sys.executable, "-c", code])
    try:
        for _ in range(50):
            if len(psutil.Process(parent.pid).children()) == 2:
                break
            time.sleep(0.1)
        children = [c.pid for c in psutil.Process(parent.pid).children()]

        plan = manager.plankill(f"tree {parent.pid}")
        assert plan["ok"] is True
        assert plan["pids"][-1] == parent.pid
        assert sorted(plan["pids"][:-1]) == sorted(children)

        ok, _ = manager.endtargets(plan["pids"])
        assert ok is True
        assert not psutil.pid_exists(parent.pid)
        assert not any(psutil.pid_exists(pid) for pid in children)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()


def test_group_kill_writes_one_log_line_per_process(manager, named_sleepers):
    plan = manager.plankill("killtest_sleep")
    manager.endtargets(plan["pids"])
    assert manager.log_path.read_text().count("name=killtest_sleep") == 3