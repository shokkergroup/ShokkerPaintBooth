#!/usr/bin/env python3
"""spb_doctor.py -- one-command PREFLIGHT / HEALTH CHECK for Shokker Paint Booth.

Purpose
-------
A fast, skimmable preflight for the multi-agent team (and the owner). It runs a
series of *independent* checks and prints a clear PASS / WARN / FAIL report so
you can tell, at a glance, whether the workspace is healthy before you start
editing, rendering, or shipping.

Each check is wrapped so that one failure never aborts the rest -- a check that
throws is reported as a FAIL with its error and the doctor moves on. The
process exits 0 when there are no FAILs (WARNs are tolerated) and 1 otherwise,
so it is safe to wire into CI or a pre-flight gate.

What it checks
--------------
  1. Python interpreter + key deps importable (numpy, scipy, PIL, cv2, flask,
     noise) with versions.
  2. Engine imports (shokker_engine_v2) and the 4 stable registries
     (BASE_REGISTRY, PATTERN_REGISTRY, FINISH_REGISTRY, MONOLITHIC_REGISTRY)
     load + are non-empty (reports counts).
  3. 3-copy sync status -- shells out to ``node scripts/sync-runtime-copies.js
     --check --check-orphans`` and summarizes writable drift vs. report-only
     (engine) drift + orphan count. Report-only engine drift is treated as a
     WARN, never a FAIL (converging finish-output modules is the owner's call).
     This only ever runs the sync script in --check mode; it never writes.
  4. Catalog integrity -- registry consistency from Python: metadata registries
     (BASE/PATTERN) have a non-empty 'name'; function registries (FINISH/MONO)
     have callable spec + paint. (dict keys are unique, so duplicate ids within
     a registry are impossible -- non-dict registries are flagged instead.)
  5. Manifest is valid JSON and no obviously-broken root state (key root JSON
     files parse).
  6. Port availability for the default server port (read from config.py;
     just checks if the port is bindable right now).
  7. Git branch + dirty-file count (informational).

run: python scripts/spb_doctor.py

Tip: add an npm alias so the team can run ``npm run doctor``:
  "scripts": { "doctor": "python scripts/spb_doctor.py" }

Exit codes
----------
  0  no FAILs (WARNs allowed)
  1  one or more FAILs
"""
from __future__ import annotations

import importlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths -- the project ROOT is the parent of this scripts/ directory. We never
# assume the current working directory is the project root (agents reset cwd).
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# The four stable registries documented in shokker_engine_v2's module docstring.
REGISTRY_NAMES = (
    "BASE_REGISTRY",
    "PATTERN_REGISTRY",
    "FINISH_REGISTRY",
    "MONOLITHIC_REGISTRY",
)
# Registries whose values are metadata dicts (expected to carry a 'name').
METADATA_REGISTRIES = ("BASE_REGISTRY", "PATTERN_REGISTRY")
# Registries whose values map to spec + paint callables.
FUNCTION_REGISTRIES = ("FINISH_REGISTRY", "MONOLITHIC_REGISTRY")

# ---------------------------------------------------------------------------
# Result model + status constants
# ---------------------------------------------------------------------------
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


class CheckResult:
    """Outcome of a single check: a status, a one-line summary, and detail lines."""

    __slots__ = ("name", "status", "summary", "details")

    def __init__(
        self,
        name: str,
        status: str,
        summary: str,
        details: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.status = status
        self.summary = summary
        self.details = details or []


# ---------------------------------------------------------------------------
# Color helpers -- colorama if available, plain-text fallback otherwise.
# ---------------------------------------------------------------------------
def _make_colors():
    """Return (green, yellow, red, dim, color_enabled).

    Each is a function str->str. When colorama is unavailable (or output is not
    a TTY) every function is the identity so the report stays readable as plain
    text.
    """
    ident: Callable[[str], str] = lambda s: s
    if not sys.stdout.isatty():
        return ident, ident, ident, ident, False
    try:
        import colorama  # type: ignore

        colorama.init()
        from colorama import Fore, Style  # type: ignore

        def green(s: str) -> str:
            return f"{Fore.GREEN}{s}{Style.RESET_ALL}"

        def yellow(s: str) -> str:
            return f"{Fore.YELLOW}{s}{Style.RESET_ALL}"

        def red(s: str) -> str:
            return f"{Fore.RED}{s}{Style.RESET_ALL}"

        def dim(s: str) -> str:
            return f"{Style.DIM}{s}{Style.RESET_ALL}"

        return green, yellow, red, dim, True
    except Exception:
        return ident, ident, ident, ident, False


GREEN, YELLOW, RED, DIM, COLOR_ENABLED = _make_colors()


def _status_badge(status: str) -> str:
    """Colorized status badge."""
    if status == PASS:
        return GREEN("PASS")
    if status == WARN:
        return YELLOW("WARN")
    return RED("FAIL")


# ---------------------------------------------------------------------------
# Engine import is cached so checks 2 + 4 don't pay the (slow) import twice.
# ---------------------------------------------------------------------------
_ENGINE_CACHE: Dict[str, object] = {}


def _import_engine():
    """Import shokker_engine_v2 once; return (module, error_string_or_None)."""
    if "module" in _ENGINE_CACHE or "error" in _ENGINE_CACHE:
        return _ENGINE_CACHE.get("module"), _ENGINE_CACHE.get("error")
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    try:
        mod = importlib.import_module("shokker_engine_v2")
        _ENGINE_CACHE["module"] = mod
        return mod, None
    except Exception as exc:  # noqa: BLE001 - report any import failure
        err = f"{type(exc).__name__}: {exc}"
        _ENGINE_CACHE["error"] = err
        return None, err


# ---------------------------------------------------------------------------
# Individual checks. Each returns a CheckResult and should not raise (the runner
# wraps them too, but keeping them clean makes the report tidy).
# ---------------------------------------------------------------------------
def check_python_and_deps() -> CheckResult:
    """Python interpreter + key third-party deps importable, with versions."""
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    details = [f"python {py} ({sys.executable})"]

    # (import name, version attr or None, hard?) -- "hard" deps are imported at
    # the engine's module top, so a missing one means the engine cannot run
    # (FAIL). `noise` is pinned in requirements.txt but is NOT a top-level engine
    # import (the engine imports and all registries build without it), so a
    # missing `noise` is reported as a WARN rather than a hard FAIL.
    deps = [
        ("numpy", "__version__", True),
        ("scipy", "__version__", True),
        ("PIL", "__version__", True),
        ("cv2", "__version__", True),
        ("flask", "__version__", True),
        ("noise", None, False),  # pinned but lazily/optionally used; no __version__
    ]
    missing_hard: List[str] = []
    missing_soft: List[str] = []
    for mod_name, ver_attr, hard in deps:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, ver_attr, None) if ver_attr else None
            details.append(f"  {mod_name:<7} {ver if ver else 'ok'}")
        except Exception as exc:  # ImportError or a broken native build
            tag = "MISSING" if hard else "MISSING (optional)"
            details.append(f"  {mod_name:<7} {tag} ({type(exc).__name__}: {exc})")
            (missing_hard if hard else missing_soft).append(mod_name)

    if missing_hard:
        return CheckResult(
            "Python + deps",
            FAIL,
            f"{len(missing_hard)} required dep import(s) failed: {', '.join(missing_hard)}",
            details,
        )
    if missing_soft:
        return CheckResult(
            "Python + deps",
            WARN,
            f"core deps OK; optional dep(s) missing: {', '.join(missing_soft)} "
            f"(pinned in requirements.txt; engine still imports)",
            details,
        )
    return CheckResult("Python + deps", PASS, f"python {py} + 6 key deps importable", details)


def check_engine_and_registries() -> CheckResult:
    """Engine imports and the 4 stable registries load and are non-empty."""
    eng, err = _import_engine()
    if eng is None:
        return CheckResult(
            "Engine + registries",
            FAIL,
            f"cannot import shokker_engine_v2: {err}",
        )

    details: List[str] = []
    empty: List[str] = []
    missing: List[str] = []
    counts: Dict[str, int] = {}
    for name in REGISTRY_NAMES:
        reg = getattr(eng, name, None)
        if reg is None:
            missing.append(name)
            details.append(f"  {name:<20} MISSING")
            continue
        try:
            count = len(reg)
        except TypeError:
            count = 0
        counts[name] = count
        details.append(f"  {name:<20} {count}")
        if count == 0:
            empty.append(name)

    if missing:
        return CheckResult(
            "Engine + registries",
            FAIL,
            f"registries missing from engine: {', '.join(missing)}",
            details,
        )
    if empty:
        return CheckResult(
            "Engine + registries",
            FAIL,
            f"registries empty: {', '.join(empty)}",
            details,
        )
    short = ", ".join(
        f"{name.split('_')[0].title()}={counts[name]}" for name in REGISTRY_NAMES
    )
    return CheckResult("Engine + registries", PASS, f"engine OK ({short})", details)


def _run_sync_check() -> Tuple[Optional[int], str]:
    """Shell out to the JS sync checker in report-only mode.

    Returns (returncode, combined output), or (None, message) if node or the
    script could not be launched at all. This only ever runs the script with
    ``--check`` (never ``--write``): it inspects, it does not converge.
    """
    script = os.path.join(SCRIPT_DIR, "sync-runtime-copies.js")
    if not os.path.isfile(script):
        return None, f"sync script not found: {script}"
    cmd = ["node", script, "--check", "--check-orphans", "--no-color"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
    except FileNotFoundError:
        return None, "node not found on PATH (cannot run sync check)"
    except subprocess.TimeoutExpired:
        return None, "sync check timed out after 180s"
    except Exception as exc:  # noqa: BLE001
        return None, f"failed to run sync check: {type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout or ""


def _parse_drift_count(text: str) -> Optional[int]:
    """Extract N from 'drift detected in N file(s)'."""
    m = re.search(r"drift detected in (\d+) file", text)
    return int(m.group(1)) if m else None


def _count_report_only(text: str) -> int:
    """Count report-only drift.

    Prefer the header's parenthetical total -- e.g. "(15 report-only / engine)"
    -- because it is the sync script's own authoritative count and is robust to
    a truncated/tailed body where not every per-line ``[report-only]`` marker is
    visible. Only fall back to counting per-line markers when the header gives
    no parenthetical. (Getting this precedence wrong undercounts report-only and
    overcounts writable drift, which would flip a WARN into a false FAIL.)
    """
    m = re.search(r"\((\d+) report-only", text)
    if m:
        return int(m.group(1))
    return len(re.findall(r"\[report-only\]", text))


def _parse_orphan_count(text: str) -> int:
    """Extract N from 'N orphan file(s)'. Returns 0 when none reported."""
    m = re.search(r"(\d+) orphan file", text)
    return int(m.group(1)) if m else 0


def summarize_sync_output(rc: Optional[int], out: str) -> CheckResult:
    """Classify sync-checker output into a CheckResult (pure; unit-testable).

    Rules:
      * launch failure (rc is None)        -> WARN (doctor stays useful offline)
      * 'no drift detected', no orphans    -> PASS
      * writable drift > 0                  -> FAIL (run sync --write)
      * only report-only/engine drift       -> WARN (owner converges)
      * only orphans                        -> WARN
    """
    if rc is None:
        return CheckResult("3-copy sync", WARN, out, [])

    text = out.strip()
    tail = [ln for ln in text.splitlines() if ln.strip()][-6:]
    orphan_n = _parse_orphan_count(text)

    if "no drift detected" in text:
        if orphan_n > 0:
            return CheckResult(
                "3-copy sync",
                WARN,
                f"copies in sync but {orphan_n} orphan file(s) in target dirs",
                tail,
            )
        return CheckResult("3-copy sync", PASS, "all 3 copies in sync, no orphans", tail)

    total = _parse_drift_count(text)
    report_only = _count_report_only(text)
    writable = max(0, total - report_only) if total is not None else None

    detail = list(tail)
    if orphan_n > 0:
        detail.append(f"orphans: {orphan_n}")

    if writable and writable > 0:
        return CheckResult(
            "3-copy sync",
            FAIL,
            f"{writable} writable copy/copies drifted (run sync --write); "
            f"{report_only} report-only/engine; orphans={orphan_n}",
            detail,
        )

    if report_only > 0:
        return CheckResult(
            "3-copy sync",
            WARN,
            f"{report_only} report-only/engine drift (owner converges); "
            f"writable=0; orphans={orphan_n}",
            detail,
        )

    if orphan_n > 0:
        return CheckResult(
            "3-copy sync",
            WARN,
            f"{orphan_n} orphan file(s) in target dirs",
            detail,
        )

    # Non-zero exit / wording we could not classify -> surface as WARN.
    if rc != 0:
        return CheckResult(
            "3-copy sync",
            WARN,
            "sync check returned non-zero but no writable drift parsed (see detail)",
            detail,
        )
    return CheckResult("3-copy sync", PASS, "sync check completed", detail)


def check_sync_status() -> CheckResult:
    """3-copy sync: summarize writable drift vs report-only (engine) drift + orphans."""
    rc, out = _run_sync_check()
    return summarize_sync_output(rc, out)


# The PATTERN_REGISTRY ships an explicit "no pattern" sentinel whose whole
# purpose is to apply NO texture (texture_fn is None, no image_path). It is a
# valid, intentional entry -- not a defect -- so the catalog check exempts it.
_NO_PATTERN_SENTINELS = frozenset({"none"})


def _bad_metadata_entry(reg_name: str, key, spec) -> bool:
    """True if a BASE/PATTERN metadata entry lacks its required callable(s).

    Real shapes (verified against the live engine registries):
      * BASE_REGISTRY    entry = dict with callable 'paint_fn' + 'base_spec_fn'.
      * PATTERN_REGISTRY entry = dict with callable 'paint_fn' AND a texture
        source -- EITHER a callable 'texture_fn' (procedural patterns) OR a
        non-empty string 'image_path' (image-authored patterns, where
        'texture_fn' is legitimately None). The engine ships ~417 of 617
        patterns as image-authored, so requiring 'texture_fn' would falsely
        fail a perfectly healthy catalog. The documented no-pattern sentinel
        (e.g. ``'none'``) is exempt from the texture-source requirement.
    """
    if not isinstance(spec, dict):
        return True
    if reg_name == "BASE_REGISTRY":
        return not (callable(spec.get("paint_fn")) and callable(spec.get("base_spec_fn")))
    if reg_name == "PATTERN_REGISTRY":
        if not callable(spec.get("paint_fn")):
            return True
        if key in _NO_PATTERN_SENTINELS:
            return False  # intentionally textureless; paint_fn presence is enough
        has_texture_fn = callable(spec.get("texture_fn"))
        img = spec.get("image_path")
        has_image = isinstance(img, str) and bool(img.strip())
        return not (has_texture_fn or has_image)
    return False


def _bad_function_entry(spec) -> bool:
    """True if a FINISH/MONO entry is not a (spec_fn, paint_fn) pair of callables.

    Real shape (verified): FINISH_REGISTRY and MONOLITHIC_REGISTRY values are
    2-tuples ``(spec_fn, paint_fn)``, both callable. A dict carrying
    'spec_fn'/'paint_fn' (the alternate shape some patch modules use) is also
    accepted.
    """
    if isinstance(spec, (tuple, list)):
        return not (len(spec) >= 2 and callable(spec[0]) and callable(spec[1]))
    if isinstance(spec, dict):
        return not (callable(spec.get("spec_fn")) and callable(spec.get("paint_fn")))
    return True


def check_catalog_integrity() -> CheckResult:
    """Registry consistency from Python, matched to each registry's real shape.

    * BASE_REGISTRY / PATTERN_REGISTRY: dict entries carrying their required
      callable factories (paint_fn/base_spec_fn and texture_fn/paint_fn).
    * FINISH_REGISTRY / MONOLITHIC_REGISTRY: (spec_fn, paint_fn) callable pairs.
    * Non-dict registries are flagged. (dict keys are unique, so duplicate ids
      within a single registry are impossible by construction.)
    """
    eng, err = _import_engine()
    if eng is None:
        return CheckResult(
            "Catalog integrity",
            FAIL,
            f"cannot import engine for catalog check: {err}",
        )

    problems: List[str] = []
    scanned = 0

    for reg_name in METADATA_REGISTRIES:
        reg = getattr(eng, reg_name, None)
        if not isinstance(reg, dict):
            problems.append(f"{reg_name} is not a dict")
            continue
        bad = 0
        for key, spec in reg.items():
            scanned += 1
            if _bad_metadata_entry(reg_name, key, spec):
                bad += 1
        if bad:
            problems.append(f"{reg_name}: {bad} entry(ies) missing required callable factories")

    for reg_name in FUNCTION_REGISTRIES:
        reg = getattr(eng, reg_name, None)
        if not isinstance(reg, dict):
            problems.append(f"{reg_name} is not a dict")
            continue
        bad = 0
        for spec in reg.values():
            scanned += 1
            if _bad_function_entry(spec):
                bad += 1
        if bad:
            problems.append(f"{reg_name}: {bad} entry(ies) not a (spec_fn, paint_fn) callable pair")

    details = [f"  entries scanned: {scanned}"]
    if problems:
        details.extend(f"  - {p}" for p in problems[:10])
        if len(problems) > 10:
            details.append(f"  ... +{len(problems) - 10} more")
        return CheckResult(
            "Catalog integrity",
            FAIL,
            f"{len(problems)} registry consistency problem(s)",
            details,
        )
    return CheckResult(
        "Catalog integrity",
        PASS,
        f"{scanned} registry entries consistent (factory callables present)",
        details,
    )


def check_manifest_and_root_state() -> CheckResult:
    """Sync manifest is valid JSON and key root JSON state files parse."""
    details: List[str] = []
    problems: List[str] = []

    manifest = os.path.join(SCRIPT_DIR, "runtime-sync-manifest.json")
    if os.path.isfile(manifest):
        try:
            with open(manifest, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            ver = data.get("version", "?") if isinstance(data, dict) else "?"
            n_files = len(data.get("files", [])) if isinstance(data, dict) else 0
            details.append(f"  manifest OK (v{ver}, {n_files} files)")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"runtime-sync-manifest.json invalid: {type(exc).__name__}: {exc}")
            details.append("  manifest INVALID")
    else:
        problems.append("runtime-sync-manifest.json not found")
        details.append("  manifest MISSING")

    # Root state JSON files -- parse-only; an absent optional file is fine.
    root_json = [
        ("shokker_config.json", True),
        ("custom_finishes.json", False),
        ("finish_ids_canonical.json", False),
    ]
    for fname, required in root_json:
        path = os.path.join(ROOT_DIR, fname)
        if not os.path.isfile(path):
            if required:
                problems.append(f"{fname} not found")
                details.append(f"  {fname}: MISSING")
            else:
                details.append(f"  {fname}: absent (optional)")
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                json.load(fh)
            details.append(f"  {fname}: OK")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fname} is not valid JSON: {type(exc).__name__}: {exc}")
            details.append(f"  {fname}: INVALID")

    if problems:
        return CheckResult(
            "Manifest + root state",
            FAIL,
            "; ".join(problems[:3]) + (" ..." if len(problems) > 3 else ""),
            details,
        )
    return CheckResult("Manifest + root state", PASS, "manifest + root JSON state valid", details)


def check_port_available() -> CheckResult:
    """Read the default server port from config.py and test if it is bindable."""
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    port: Optional[int] = None
    host = "127.0.0.1"
    try:
        cfg_mod = importlib.import_module("config")
        cfg = getattr(cfg_mod, "CFG", None)
        port = int(getattr(cfg, "PORT", 0)) or int(getattr(cfg_mod, "DEFAULT_PORT", 0))
    except Exception:  # noqa: BLE001 - fall back to documented default
        port = None

    if not port:
        port = 59876  # documented default fallback

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(2.0)
        sock.bind((host, port))
        sock.close()
        return CheckResult(
            "Server port",
            PASS,
            f"port {port} is free (bindable now)",
            [f"  host {host} port {port}"],
        )
    except OSError as exc:
        # Already in use is informational (server may be running) -> WARN.
        try:
            sock.close()
        except Exception:
            pass
        reason = getattr(exc, "strerror", None) or str(exc)
        return CheckResult(
            "Server port",
            WARN,
            f"port {port} not bindable -- server may already be running ({reason})",
            [f"  host {host} port {port}"],
        )


def check_git_status() -> CheckResult:
    """Informational: current branch + dirty (uncommitted) file count."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return CheckResult("Git status", WARN, "git not found on PATH", [])
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Git status", WARN, f"git check failed: {type(exc).__name__}: {exc}", [])

    if branch.returncode != 0:
        return CheckResult(
            "Git status",
            WARN,
            "not a git working tree (or git error)",
            [(branch.stdout or "").strip()],
        )
    branch_name = (branch.stdout or "").strip() or "(detached)"

    dirty_count = -1
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
        )
        if status.returncode == 0:
            dirty_count = len([ln for ln in status.stdout.splitlines() if ln.strip()])
    except Exception:  # noqa: BLE001
        dirty_count = -1

    if dirty_count < 0:
        summary = f"branch {branch_name} (dirty count unavailable)"
    else:
        summary = f"branch {branch_name}, {dirty_count} dirty file(s)"
    # Always informational -> PASS so it never blocks the exit code.
    return CheckResult("Git status", PASS, summary, [])


# ---------------------------------------------------------------------------
# Runner + report
# ---------------------------------------------------------------------------
CHECKS: List[Tuple[str, Callable[[], CheckResult]]] = [
    ("Python + deps", check_python_and_deps),
    ("Engine + registries", check_engine_and_registries),
    ("3-copy sync", check_sync_status),
    ("Catalog integrity", check_catalog_integrity),
    ("Manifest + root state", check_manifest_and_root_state),
    ("Server port", check_port_available),
    ("Git status", check_git_status),
]


def _run_one(name: str, fn: Callable[[], CheckResult]) -> CheckResult:
    """Run a single check, converting any unexpected exception into a FAIL."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - one failure never aborts the rest
        return CheckResult(name, FAIL, f"check crashed: {type(exc).__name__}: {exc}", [])


def main(argv: Optional[List[str]] = None) -> int:
    print()
    print(DIM("=" * 64))
    print(" SPB DOCTOR -- preflight / health check")
    print(DIM(f" root: {ROOT_DIR}"))
    print(DIM("=" * 64))

    results: List[CheckResult] = []
    started = time.time()
    for name, fn in CHECKS:
        res = _run_one(name, fn)
        results.append(res)
        print(f"[{_status_badge(res.status)}] {res.name:<22} {res.summary}")
        for line in res.details:
            print(DIM(f"        {line}"))

    elapsed = time.time() - started
    n_pass = sum(1 for r in results if r.status == PASS)
    n_warn = sum(1 for r in results if r.status == WARN)
    n_fail = sum(1 for r in results if r.status == FAIL)

    print(DIM("-" * 64))
    print(
        f" {GREEN(str(n_pass) + ' PASS')}   "
        f"{YELLOW(str(n_warn) + ' WARN')}   "
        f"{RED(str(n_fail) + ' FAIL')}   "
        f"({elapsed:.1f}s)"
    )
    if n_fail:
        print(RED(" RESULT: FAIL -- fix the FAIL item(s) above before proceeding."))
    elif n_warn:
        print(YELLOW(" RESULT: OK (with warnings) -- review WARN item(s) above."))
    else:
        print(GREEN(" RESULT: ALL CLEAR."))
    print(DIM("=" * 64))
    print()

    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
