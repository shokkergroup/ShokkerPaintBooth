"""Watch scorecard/spec monster files for timestamp/hash changes.

Use this while SPB is running to catch background writers without reading the
monster files into chat:

    python scripts/spb_watch_catalog_files.py --seconds 120
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WATCHED = (
    ROOT / "paint-booth-0-catalog-scorecard.js",
    ROOT / "engine" / "spec_patterns.py",
)


def snapshot(path: Path) -> tuple[int, int, float, str]:
    data = path.read_bytes()
    text = data.decode("utf-8")
    lines = len(text.splitlines()) + (1 if text.endswith(("\n", "\r")) else 0)
    stat = path.stat()
    return lines, stat.st_size, stat.st_mtime, hashlib.sha256(data).hexdigest()


def print_process_snapshot() -> None:
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match 'python|node|electron|cmd|powershell' -and "
        "$_.CommandLine -match 'Shokker|spb|paint|scorecard|spec_patterns|server.py|server_v5.py' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | Format-List"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception as exc:
        print(f"PROCESS SNAPSHOT FAILED: {type(exc).__name__}: {exc}")
        return
    output = result.stdout.strip()
    if output:
        print("PROCESS SNAPSHOT")
        print(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--process-snapshot-on-change", action="store_true")
    args = parser.parse_args()

    previous = {path: snapshot(path) for path in WATCHED}
    for path, snap in previous.items():
        print(f"START {path.relative_to(ROOT)} lines={snap[0]} size={snap[1]} mtime={snap[2]:.3f} sha256={snap[3]}")

    deadline = time.monotonic() + max(args.seconds, 0.0)
    changed = False
    while time.monotonic() < deadline:
        time.sleep(max(args.interval, 0.1))
        for path in WATCHED:
            current = snapshot(path)
            if current != previous[path]:
                changed = True
                old = previous[path]
                print(
                    f"CHANGE {path.relative_to(ROOT)} "
                    f"lines {old[0]}->{current[0]} size {old[1]}->{current[1]} "
                    f"mtime {old[2]:.3f}->{current[2]:.3f} sha256 {old[3]}->{current[3]}"
                )
                if args.process_snapshot_on_change:
                    print_process_snapshot()
                previous[path] = current

    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
