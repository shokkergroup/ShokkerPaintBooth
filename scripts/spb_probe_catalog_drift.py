"""Probe whether spec-registry actions mutate the generated scorecard.

This is intentionally small and read-focused: it records line counts and hashes
before/after each stage, then exits non-zero if the catalog changed.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORECARD = ROOT / "paint-booth-0-catalog-scorecard.js"
sys.path.insert(0, str(ROOT))
SAMPLE_NAMES = (
    "exhaust_pipe_scorch",
    "rain_droplet_beads",
    "brushstroke_bold",
    "abstract_bauhaus_forms",
)


def snapshot(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    text = data.decode("utf-8")
    lines = len(text.splitlines()) + (1 if text.endswith(("\n", "\r")) else 0)
    return lines, hashlib.sha256(data).hexdigest()


def report_stage(stage: str, before: tuple[int, str]) -> tuple[bool, tuple[int, str]]:
    after = snapshot(SCORECARD)
    changed = before != after
    status = "DRIFT" if changed else "OK"
    print(f"{status}: {stage}: {before[0]}->{after[0]} {before[1]}->{after[1]}")
    return changed, after


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-samples", action="store_true")
    args = parser.parse_args()

    had_drift = False
    before = snapshot(SCORECARD)

    from engine.spec_patterns import PATTERN_CATALOG

    drifted, before = report_stage("import engine.spec_patterns", before)
    had_drift = had_drift or drifted

    for name in SAMPLE_NAMES:
        _ = PATTERN_CATALOG[name]
    drifted, before = report_stage("lookup sample PATTERN_CATALOG entries", before)
    had_drift = had_drift or drifted

    if args.render_samples:
        import numpy as np

        for name in SAMPLE_NAMES:
            arr = PATTERN_CATALOG[name]((64, 64), 987, 1.0)
            if arr.shape != (64, 64) or arr.dtype != np.float32:
                raise AssertionError(f"{name} returned unexpected output {arr.shape} {arr.dtype}")
        drifted, before = report_stage("render sample PATTERN_CATALOG entries", before)
        had_drift = had_drift or drifted

    return 1 if had_drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
