# -*- coding: utf-8 -*-
"""SPB boot/ship preflight — catches the classes of breakage that have cost time:

  1. server.py won't import (e.g. the concurrent-edit `logger`-ordering race that
     killed boot on 2026-06-02) — runs `import server` in a clean subprocess.
  2. Route inheritance too thin (server_v5 needs >=50 routes from server.py).
  3. 3-copy runtime drift (root vs electron-app/server vs pyserver/_internal).
  4. A `?v=` cache token in paint-booth-v2.html points at a file that doesn't exist.
  5. A core JS asset fails to parse (node --check).
  6. finish-data special-group / section references that dangle (a group named in
     SPECIALS_SECTIONS but missing from the group maps — the exact shape of the
     Angle-SHOKK/Metals&Forged cleanup).

Exit code 0 = all green; 1 = at least one failure. Use before any restart/ship.

Usage:  python -B scripts/preflight.py [--no-server]   (--no-server skips the heavy import)
"""
import os, re, sys, json, subprocess, argparse

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
PY = sys.executable
NODE = "node"

ap = argparse.ArgumentParser()
ap.add_argument("--no-server", action="store_true", help="skip the heavy `import server` boot check")
ap.add_argument("--no-perf", action="store_true", help="skip the render-time hard gate (perf_gate.py)")
args = ap.parse_args()

PASS, FAIL = [], []


def ok(name, detail=""):
    PASS.append(name)
    print("  [ OK ] %-34s %s" % (name, detail))


def bad(name, detail=""):
    FAIL.append(name)
    print("  [FAIL] %-34s %s" % (name, detail))


# 1+2) server.py imports + route count
def check_server():
    probe = (
        "import os,sys;"
        "os.environ['SHOKKER_SKIP_SPEC_PREBAKE']='1';os.environ['SHOKKER_NO_CLEAN']='1';"
        "sys.path.insert(0, r'%s');"
        "import server;"
        "print('ROUTES', len(list(server.app.url_map.iter_rules())))" % ROOT
    )
    try:
        r = subprocess.run([PY, "-B", "-c", probe], capture_output=True, text=True, timeout=180,
                           cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired:
        bad("server import", "timed out (>180s)")
        return
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        bad("server import", "import FAILED: " + " | ".join(tail))
        return
    m = re.search(r"ROUTES (\d+)", r.stdout)
    n = int(m.group(1)) if m else 0
    (ok if n >= 50 else bad)("server import + routes", "%d routes" % n)


# 3) 3-copy sync
def check_sync():
    script = os.path.join(ROOT, "scripts", "sync-runtime-copies.js")
    if not os.path.exists(script):
        bad("3-copy sync", "sync-runtime-copies.js missing")
        return
    try:
        r = subprocess.run([NODE, script, "--check"], capture_output=True, text=True, timeout=180, cwd=ROOT)
    except Exception as e:
        bad("3-copy sync", str(e)[:80])
        return
    out = (r.stdout + r.stderr)
    if r.returncode == 0 and "drift detected" not in out:
        ok("3-copy sync", "in sync")
        return
    # Three-way classify: MANAGED code (ship-blocker on drift) vs ENGINE
    # (check-only/owner-managed per the manifest -> warn) vs assets (informational).
    paths = re.findall(r"^\s+([\w./\\-]+\.\w+)\s*->", out, re.M)
    def _cls(p):
        pp = p.replace("\\", "/").lower()
        if "reference_textures" in pp or pp.startswith("assets/") or "/assets/" in pp:
            return "asset"
        if pp.startswith("engine/") or "/engine/" in pp:
            return "engine"   # check_only_directories in runtime-sync-manifest.json
        if pp.endswith((".js", ".css", ".html", ".py")):
            return "code"
        return "other"
    code = sorted({p for p in paths if _cls(p) == "code"})
    eng = sorted({p for p in paths if _cls(p) == "engine"})
    tot = re.search(r"drift detected in (\d+)", out)
    total = int(tot.group(1)) if tot else len(paths)
    if code:
        bad("3-copy sync (code)", "%d MANAGED code file(s) drifted: %s" % (len(code), ", ".join(os.path.basename(c) for c in code[:5])))
    elif eng:
        ok("3-copy sync", "no managed-code drift; %d engine file(s) drift (check-only/owner-managed: %s) + assets" % (len(eng), ", ".join(os.path.basename(e) for e in eng[:3])))
    else:
        ok("3-copy sync", "%d drifted, all assets/textures — informational" % total)


# 4) cache tokens resolve to real files
def check_tokens():
    html = os.path.join(ROOT, "paint-booth-v2.html")
    if not os.path.exists(html):
        bad("cache tokens", "paint-booth-v2.html missing")
        return
    txt = open(html, encoding="utf-8", errors="replace").read()
    refs = re.findall(r'(?:href|src)="([^":?]+\.(?:js|css))\?v=[^"]*"', txt)
    missing = [p for p in sorted(set(refs)) if not os.path.exists(os.path.join(ROOT, p.replace("/", os.sep)))]
    if missing:
        bad("cache tokens", "%d tokened file(s) missing: %s" % (len(missing), ", ".join(missing[:4])))
    else:
        ok("cache tokens", "%d tokened assets all present" % len(set(refs)))


# 5) core JS parses
def check_js_parse():
    targets = ["paint-booth-0-finish-data.js", "paint-booth-2-state-zones.js"]
    broken = []
    for t in targets:
        p = os.path.join(ROOT, t)
        if not os.path.exists(p):
            broken.append(t + " (missing)")
            continue
        r = subprocess.run([NODE, "--check", p], capture_output=True, text=True)
        if r.returncode != 0:
            broken.append(t)
    if broken:
        bad("core JS parse", "broken: " + ", ".join(broken))
    else:
        ok("core JS parse", "%d files parse clean" % len(targets))


# 5b) finish-data actually EVALUATES (catch runtime bricks node --check misses, e.g. MC_DEFS)
def check_finish_data_runtime():
    loader = os.path.join(ROOT, "scripts", "check_finish_data_loads.js")
    fd = os.path.join(ROOT, "paint-booth-0-finish-data.js")
    if not os.path.exists(loader):
        bad("finish-data runtime", "loader script missing")
        return
    try:
        r = subprocess.run([NODE, loader, fd], capture_output=True, text=True, timeout=60)
    except Exception as e:
        bad("finish-data runtime", str(e)[:80])
        return
    tail = (r.stdout or r.stderr).strip().splitlines()
    if r.returncode == 0:
        ok("finish-data runtime", "evaluates + catalog builds")
    else:
        bad("finish-data runtime", tail[-1] if tail else "load failed (catalog would brick)")


# 6) finish-data special-group references resolve (no dangling group keys)
def check_finish_data_refs():
    p = os.path.join(ROOT, "paint-booth-0-finish-data.js")
    if not os.path.exists(p):
        bad("finish-data group refs", "file missing")
        return
    txt = open(p, encoding="utf-8", errors="replace").read()
    # SPECIALS_SECTIONS maps a section -> [group names]; every group name must be a key
    # in one of the _SPECIALS_* group dicts (i.e. appear as `"Name": [`).
    sec = re.search(r"SPECIALS_SECTIONS\s*=\s*\{(.+?)\n\}", txt, re.S)
    if not sec:
        ok("finish-data group refs", "SPECIALS_SECTIONS not found (skipped)")
        return
    # Groups populated dynamically at runtime (no static "Name": [ definition).
    DYNAMIC_GROUPS = {"SHOKK DROP"}  # user-import lane; empty until imports exist
    referenced = set(re.findall(r'"([^"]+)"', sec.group(1)))
    # drop the section keys themselves (lines like `"SHOKKER": [`)
    section_keys = set(re.findall(r'"([^"]+)"\s*:\s*\[', sec.group(1)))
    referenced -= section_keys
    defined = set(re.findall(r'"([^"]+)"\s*:\s*\[', txt))  # every "Name": [ in the file
    dangling = sorted(g for g in referenced if g not in defined and g not in DYNAMIC_GROUPS)
    if dangling:
        bad("finish-data group refs", "%d section ref(s) with no group: %s" % (len(dangling), ", ".join(dangling[:4])))
    else:
        ok("finish-data group refs", "all section->group refs resolve")


# 7) RENDER-TIME HARD GATE — every finish must render <= 4.0s @2048 (owner mandate
# 2026-06-13, after the Spectrum Shift family shipped at 9-21s because prior audits
# SAMPLED instead of covering every finish). Incremental: perf_gate.py re-times only
# finishes whose code changed (hash-cached), so this is fast once a baseline exists.
# Establish/refresh the baseline on a QUIET machine: `python scripts/perf_gate.py --full`.
def check_perf_gate():
    gate = os.path.join(ROOT, "scripts", "perf_gate.py")
    cache = os.path.join(ROOT, "_audit", "perf_gate_cache.json")
    if not os.path.exists(gate):
        bad("render-time gate", "perf_gate.py missing")
        return
    # An ABSENT or near-empty cache means "not armed". Critically, we must NOT run the
    # gate against an empty cache: every finish would be a cache-miss, re-timing the WHOLE
    # catalog inside preflight (the 6.5h/39GB runaway of 2026-06-13). Require a populated
    # baseline (>500 bytes ~= many entries) before the gate is allowed to run.
    if not os.path.exists(cache) or os.path.getsize(cache) < 500:
        ok("render-time gate", "no baseline yet — run `python scripts/perf_gate.py --full` (quiet machine) to arm it")
        return
    try:
        r = subprocess.run([PY, "-B", gate], capture_output=True, text=True, timeout=1800,
                           cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired:
        bad("render-time gate", "perf_gate timed out (>30m) — many uncached finishes; run --full baseline")
        return
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"FAIL \(>[\d.]+s\): (\d+)", out)
    nfail = int(m.group(1)) if m else (0 if r.returncode == 0 else -1)
    if r.returncode == 0:
        mp = re.search(r"PASS \(<[\d.]+s\): (\d+)", out)
        ok("render-time gate", "every finish <= 4.0s @2048 (%s optimal)" % (mp.group(1) + " under 1.5s" if mp else "ok"))
    else:
        worst = re.findall(r"^\s+([\d.]+)s\s+\w+\s+(\S+)", out, re.M)[:3]
        wtxt = ", ".join("%s@%ss" % (fid, sec) for sec, fid in worst)
        bad("render-time gate", "%d finish(es) OVER 4.0s ceiling: %s" % (nfail if nfail >= 0 else 0, wtxt))


print("=" * 60)
print("  SPB PREFLIGHT")
print("=" * 60)
check_tokens()
check_js_parse()
check_finish_data_runtime()
check_finish_data_refs()
check_sync()
if not args.no_perf:
    check_perf_gate()
else:
    print("  (render-time gate skipped: --no-perf)")
if not args.no_server:
    print("  (running server import check — this loads the engine, ~10-30s)")
    check_server()
else:
    print("  (server import check skipped: --no-server)")

print("-" * 60)
print("  RESULT: %d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("  FAILED: " + ", ".join(FAIL))
print("=" * 60)
sys.exit(1 if FAIL else 0)
