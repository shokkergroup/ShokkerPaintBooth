"""
server_health.py - V5 Server Health & Startup Diagnostics.

Run on startup from server_v5.py and as a standalone diagnostic. The live
`/api/health` route imports this module, so it must exist beside the root
server as well as in Electron runtime mirrors.
"""

from __future__ import annotations

import logging
import os
import sys
import time


logger = logging.getLogger("shokker_v5")


EXPECTED_MINIMUMS = {
    "bases": (180, "Expected the active V5 base registry to be loaded"),
    "patterns": (230, "Expected the active V5 pattern registry to be loaded"),
    "monolithics": (750, "Expected the active V5 monolithic registry to be loaded"),
}

CS_MUST_BE_V5 = [
    "cs_cool",
    "cs_warm",
    "cs_deepocean",
    "cs_solarflare",
    "cs_inferno",
    "cs_nebula",
    "cs_mystichrome",
    "cs_supernova",
    "cs_candypaint",
    "cs_oilslick",
    "cs_rosegold",
    "cs_goldrush",
    "cs_toxic",
    "cs_darkflame",
]

OUTPUT_MAX_AGE_MINUTES = 90


def check_registry_sizes(base_reg, pat_reg, mono_reg):
    issues = []
    for label, reg, (minimum, msg) in [
        ("bases", base_reg, EXPECTED_MINIMUMS["bases"]),
        ("patterns", pat_reg, EXPECTED_MINIMUMS["patterns"]),
        ("monolithics", mono_reg, EXPECTED_MINIMUMS["monolithics"]),
    ]:
        count = len(reg or {})
        if count < minimum:
            issues.append(f"Registry '{label}' too small: {count} < {minimum}. {msg}")
    return issues


def check_cs_overrides(mono_reg):
    missing = [k for k in CS_MUST_BE_V5 if k not in (mono_reg or {})]
    if missing:
        return [f"CS V5 overrides missing: {missing}"]
    return []


def check_output_folder(output_dir):
    issues = []
    if not output_dir or not os.path.exists(output_dir):
        return issues
    files = [
        f
        for f in os.listdir(output_dir)
        if os.path.isfile(os.path.join(output_dir, f))
    ]
    if len(files) > 500:
        total_mb = sum(
            os.path.getsize(os.path.join(output_dir, f)) for f in files
        ) / 1024 / 1024
        issues.append(
            f"Output folder has {len(files)} files ({total_mb:.0f}MB). "
            "Consider running: python server_health.py --cleanup"
        )
    return issues


def cleanup_output_folder(output_dir, max_age_minutes=OUTPUT_MAX_AGE_MINUTES):
    if not output_dir or not os.path.exists(output_dir):
        return 0
    cutoff = time.time() - (max_age_minutes * 60)
    deleted = 0
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    deleted += 1
            except (PermissionError, OSError):
                pass
    return deleted


def check_config():
    try:
        from config import CFG

        if CFG.PORT not in range(1024, 65535):
            return [f"Config port {CFG.PORT} is out of valid range"]
        return []
    except ImportError as exc:
        return [f"config.py import failed: {exc}"]


def check_html_exists():
    root = os.path.dirname(os.path.abspath(__file__))
    html = os.path.join(root, "paint-booth-v2.html")
    if not os.path.exists(html):
        return [f"paint-booth-v2.html NOT FOUND at {html}"]
    size_mb = os.path.getsize(html) / 1024 / 1024
    if size_mb < 0.03:
        return [f"paint-booth-v2.html seems too small ({size_mb:.2f}MB) - may be corrupt"]
    return []


def check_server_log_size():
    root = os.path.dirname(os.path.abspath(__file__))
    log = os.path.join(root, "server_log.txt")
    if os.path.exists(log):
        mb = os.path.getsize(log) / 1024 / 1024
        if mb > 50:
            return [f"server_log.txt is {mb:.0f}MB - consider archiving it"]
    return []


def run_startup_checks(base_reg=None, pat_reg=None, mono_reg=None, output_dir=None):
    all_issues = []
    t0 = time.time()

    all_issues += check_config()
    all_issues += check_html_exists()
    all_issues += check_server_log_size()

    if base_reg is not None:
        all_issues += check_registry_sizes(base_reg, pat_reg, mono_reg)
        all_issues += check_cs_overrides(mono_reg)

    if output_dir:
        all_issues += check_output_folder(output_dir)
        deleted = cleanup_output_folder(output_dir)
        if deleted:
            logger.info("[Health] Auto-cleaned %s old output files", deleted)

    elapsed = time.time() - t0
    if all_issues:
        logger.warning("[Health] %s startup issue(s) found:", len(all_issues))
        for issue in all_issues:
            logger.warning("  ! %s", issue)
    else:
        logger.info("[Health] All startup checks PASSED (%.0fms)", elapsed * 1000)

    return all_issues


def run_standalone():
    print("\n" + "=" * 60)
    print("  SHOKKER V5 - SERVER HEALTH CHECK")
    print("=" * 60)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("\nLoading registry...")
    try:
        from config import CFG
        from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY

        print(
            f"  Loaded: {len(BASE_REGISTRY)} bases, {len(PATTERN_REGISTRY)} patterns, "
            f"{len(MONOLITHIC_REGISTRY)} monolithics"
        )
        issues = run_startup_checks(
            BASE_REGISTRY,
            PATTERN_REGISTRY,
            MONOLITHIC_REGISTRY,
            output_dir=CFG.OUTPUT_DIR,
        )
    except Exception as exc:
        print(f"  [FAIL] Registry load failed: {exc}")
        return

    from config import CFG

    out_dir = CFG.OUTPUT_DIR
    if os.path.exists(out_dir):
        files = os.listdir(out_dir)
        total_mb = sum(
            os.path.getsize(os.path.join(out_dir, f))
            for f in files
            if os.path.isfile(os.path.join(out_dir, f))
        ) / 1024 / 1024
        print(f"\nOutput folder: {len(files)} files, {total_mb:.1f}MB")

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_log.txt")
    if os.path.exists(log_path):
        print(f"server_log.txt: {os.path.getsize(log_path) / 1024 / 1024:.1f}MB")

    print("\n" + "=" * 60)
    if issues:
        print(f"  [FAIL] {len(issues)} issues found:")
        for issue in issues:
            print(f"    -> {issue}")
    else:
        print("  [ALL CLEAR] No issues found")
    print("=" * 60 + "\n")

    if "--cleanup" in sys.argv:
        print("Running output folder cleanup...")
        deleted = cleanup_output_folder(out_dir, max_age_minutes=0)
        print(f"  Deleted {deleted} files from output/")


if __name__ == "__main__":
    run_standalone()
