"""Spec Sculpt SNAPSHOT regression (2026-06-26).

Fingerprints the spec output of each mode on fixed synthetic liveries (a 24x24x3 downsample of the
composite) and compares to a stored baseline — so ANY material change to the spec pipeline (not just the
named quality properties) is flagged, with the offending (mode, livery) named.

Portable: uses synthetic paints, runs anywhere. To RE-BASELINE after an intentional change:
    SNAPSHOT_UPDATE=1 python -m pytest tests_v2/test_spec_sculpt_snapshot.py
The baseline lives in tests_v2/_spec_sculpt_snapshot.json (commit it alongside the change).
"""
from __future__ import annotations
import os, json

import numpy as np
import cv2
import pytest

from engine.spec_sculpt.generate import scratch_spec_from_any_paint, zoned_auto_spec

BASELINE = os.path.join(os.path.dirname(__file__), "_spec_sculpt_snapshot.json")
TOL = 8.0           # per-statistic drift that counts as a MATERIAL change
SEED = 4242


def _liveries(n=384):
    rng = np.random.default_rng(20260626)
    out = {}
    a = np.zeros((n, n, 3), np.float32)
    a[: n // 2] = [0.85, 0.10, 0.12]
    a[n // 2:] = [0.05, 0.06, 0.10]
    a[n // 3: n // 3 + 50, n // 4: n // 4 + 160] = [0.95, 0.95, 0.95]
    out["two_tone"] = a
    yy = np.linspace(0, 1, n)[:, None]
    out["candy_grad"] = np.stack([0.2 + 0.7 * yy.repeat(n, 1), 0.05 + 0.2 * (1 - yy).repeat(n, 1),
                                  0.3 + 0.5 * yy.repeat(n, 1)], axis=2).astype(np.float32)
    b = np.zeros((n, n, 3), np.float32)
    for (y0, y1, col) in [(0, n // 4, [0.1, 0.3, 0.85]), (n // 4, n // 2, [0.9, 0.8, 0.1]),
                          (n // 2, 3 * n // 4, [0.85, 0.1, 0.5]), (3 * n // 4, n, [0.1, 0.7, 0.3])]:
        b[y0:y1] = col
    out["multi_block"] = np.clip(b + rng.normal(0, 0.04, b.shape).astype(np.float32), 0, 1)
    return out


LIVERIES = _liveries()
# Snapshot ZONED (fully deterministic, the structural per-panel feature most worth drift-protection).
# scratch's per-pixel flake is render-order-dependent (global-RNG), so it can't be exact-snapshotted —
# its MATERIAL properties (decorrelation corr, clearcoat depth, iron, render time) are locked by the
# property gate in test_spec_sculpt_quality_gate.py instead.
MODES = {
    "zoned": lambda tex: np.asarray(zoned_auto_spec(tex, SEED)),
}


def _fingerprint(spec):
    """Channel STATISTICS — stable to seed-driven flake placement (PYTHONHASHSEED), sensitive to MATERIAL
    changes (decorrelation breaking -> corr jumps; clearcoat vanishing -> Cc mean/std drops; zoning shift ->
    means move). Verified byte-identical across processes."""
    s = spec[:, :, :3].astype(np.float32)
    M, R, Cc = s[:, :, 0], s[:, :, 1], s[:, :, 2]
    def corr(a, b):
        a = a.ravel() - a.mean(); b = b.ravel() - b.mean()
        d = np.sqrt((a * a).sum()) * np.sqrt((b * b).sum())
        return float((a * b).sum() / d) * 100.0 if d > 1e-6 else 0.0
    p = lambda ch, q: float(np.percentile(ch, q))   # percentiles catch distribution-shape changes
    return [float(M.mean()), float(M.std()), float(R.mean()), float(R.std()),
            float(Cc.mean()), float(Cc.std()), corr(M, R), corr(M, Cc), corr(R, Cc),
            p(M, 10), p(M, 90), p(R, 10), p(R, 90), p(Cc, 10), p(Cc, 90)]


def _current():
    fp = {}
    for mname, fn in MODES.items():
        for lname, tex in LIVERIES.items():
            fp[f"{mname}/{lname}"] = _fingerprint(fn(tex))
    return fp


def test_spec_outputs_match_snapshot():
    # create the baseline automatically on a fresh checkout / when re-baselining; compare thereafter.
    if os.environ.get("SNAPSHOT_UPDATE") == "1" or not os.path.exists(BASELINE):
        json.dump(_current(), open(BASELINE, "w"), indent=0)
        pytest.skip("baseline created/updated")
    base = json.load(open(BASELINE))
    cur = _current()
    drifted = []
    for key, cur_fp in cur.items():
        if key not in base:
            drifted.append(f"{key}: NEW (no baseline)")
            continue
        d = float(np.abs(np.array(cur_fp) - np.array(base[key])).mean())
        if d > TOL:
            drifted.append(f"{key}: drift {d:.1f} (>{TOL})")
    assert not drifted, "Spec output changed materially vs snapshot:\n  " + "\n  ".join(drifted) + \
        "\n  If intentional, re-baseline: SNAPSHOT_UPDATE=1 python -m pytest tests_v2/test_spec_sculpt_snapshot.py"
