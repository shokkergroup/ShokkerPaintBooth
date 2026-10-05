"""
clean_boot.py - Fresh start before running the V5 server
==========================================================
Kills anything that could interfere: processes on the app port and any
other Shokker server (Python) processes from this project. Run this at
launch so every start is a clean boot.

Usage: Called automatically when you run server_v5.py. Or run standalone:
  python clean_boot.py
then start server_v5.py yourself (clean_boot does not start the server).
"""

import os
import sys
import time
import subprocess


def _norm(path):
    return os.path.normpath(os.path.abspath(path)).lower()


def kill_processes_on_port(port: int) -> list:
    """Kill all processes listening on the given port. Returns list of killed PIDs."""
    killed = []
    try:
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if out.returncode != 0:
            return killed
        needle = f":{port}"
        for line in out.stdout.splitlines():
            if needle in line and "LISTENING" in line.upper():
                parts = line.split()
                if parts:
                    try:
                        pid = int(parts[-1])
                        if pid > 0:
                            subprocess.run(
                                ["taskkill", "/PID", str(pid), "/F"],
                                capture_output=True,
                                timeout=5,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                            )
                            killed.append(pid)
                    except (ValueError, IndexError):
                        pass
    except Exception:
        pass
    return killed


def kill_other_shokker_servers(root_dir: str) -> list:
    """Kill any other Python process running server_v5.py or server.py from root_dir. Returns list of killed PIDs."""
    killed = []
    my_pid = os.getpid()
    root_norm = _norm(root_dir)
    try:
        # One line per process: "PID|CommandLine"
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
            "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=root_dir,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if out.returncode != 0:
            return killed
        for line in out.stdout.splitlines():
            line = line.strip()
            if "|" not in line:
                continue
            idx = line.index("|")
            try:
                pid = int(line[:idx])
            except ValueError:
                continue
            if pid == my_pid:
                continue
            cmd = line[idx + 1:].lower()
            if root_norm not in _norm(cmd):
                continue
            if "server_v5.py" not in cmd and "server.py" not in cmd:
                continue
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                killed.append(pid)
            except Exception:
                pass
    except Exception:
        pass
    return killed


def clean_boot(port: int, root_dir: str, quiet: bool = False) -> None:
    """
    Ensure a clean start: free the port and stop any other Shokker server from this project.
    Call this at the very start of server_v5.py main.
    """
    if not quiet:
        print("[Clean boot] Stopping anything that could interfere...")
    killed_port = kill_processes_on_port(port)
    if killed_port and not quiet:
        print(f"  [Clean boot] Freed port {port} (stopped PIDs: {killed_port})")
    killed_other = kill_other_shokker_servers(root_dir)
    if killed_other and not quiet:
        print(f"  [Clean boot] Stopped other Shokker server process(es): PIDs {killed_other}")
    if killed_port or killed_other:
        time.sleep(1.2)
        if not quiet:
            print("[Clean boot] Ready for fresh start.")
    elif not quiet:
        print("[Clean boot] Port free, no other server found - clean start.")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import CFG
    clean_boot(CFG.PORT, CFG.ROOT_DIR)
    print("Run:  python server_v5.py")
