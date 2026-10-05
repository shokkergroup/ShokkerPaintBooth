# -*- coding: utf-8 -*-
"""Memory-safe arming of the SPB render-time gate baseline.

A single `perf_gate.py --full` run times the WHOLE catalog in ONE process, and
the engine's internal render/noise caches accumulate across ~1,300 finishes — on
2026-06-13 that leaked to ~39GB over 6.5h. This orchestrator instead runs the gate
in N BATCHES, each a FRESH subprocess: every batch times ~total/N finishes,
appends its timings to the shared cache (_audit/perf_gate_cache.json), and EXITS —
so the OS reclaims that batch's RAM before the next one starts. A final
`--report-only` pass reads the complete cache and prints the authoritative board.

Run on an IDLE machine (timings inflate under load):
    python scripts/arm_perf_gate.py            # default 24 batches
    python scripts/arm_perf_gate.py 32         # finer batches = lower peak RAM

After it finishes, the cache is armed and `scripts/preflight.py` enforces the
4.0s ceiling incrementally (only re-timing finishes whose code changed).
"""
import os
import sys
import subprocess

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
PY = sys.executable
GATE = os.path.join(ROOT, "scripts", "perf_gate.py")


def main():
    n = 24
    if len(sys.argv) > 1:
        try:
            n = max(1, int(sys.argv[1]))
        except ValueError:
            pass
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    print("Arming perf-gate baseline in %d fresh-process batches (memory-safe)..." % n, flush=True)
    failed = 0
    for k in range(n):
        print("\n=== batch %d/%d ===" % (k + 1, n), flush=True)
        r = subprocess.run([PY, "-B", GATE, "--batch", "%d/%d" % (k, n)], cwd=ROOT, env=env)
        if r.returncode not in (0, 1):  # 0 pass / 1 fail are both fine; other = error
            failed += 1
            print("  (batch %d returned %s)" % (k, r.returncode), flush=True)
    print("\n=== FINAL BOARD (report-only, no rendering) ===", flush=True)
    rep = subprocess.run([PY, "-B", GATE, "--report-only"], cwd=ROOT, env=env)
    print("\nDone. batches with errors: %d. Gate exit: %s (1 = some finish over the ceiling)."
          % (failed, rep.returncode), flush=True)
    return rep.returncode


if __name__ == "__main__":
    sys.exit(main())
