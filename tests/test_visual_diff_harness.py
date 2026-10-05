"""
tests/test_visual_diff_harness.py — smoke test for scripts/spb_visual_diff.py.

The visual-diff harness is a finish-NEUTRAL *review* tool (audit TEST-06). It is
never a pass/fail gate, so these tests only confirm the script:
  * imports cleanly,
  * can build its curated finish set from the live registries (and always
    anchors the three masterclass references: Viva Mexico / Union Jacked /
    Rising Sun), and
  * can run end-to-end on a single tiny finish without raising and while
    exiting 0.

Kept deliberately tiny (one 96px finish) so it stays well under a second of
real render work. It does NOT touch the committed baselines under _visual_diff/
— it writes into a throwaway output dir via the harness module's path globals.
"""

from __future__ import annotations

import importlib
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
for _p in (PROJECT_ROOT, SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(scope="module")
def harness():
    """Import the harness module once."""
    return importlib.import_module("spb_visual_diff")


def test_harness_imports(harness):
    """Module imports and exposes its public entry points."""
    assert hasattr(harness, "main")
    assert hasattr(harness, "run")
    assert hasattr(harness, "build_curated_set")
    assert callable(harness.main)


def test_curated_set_anchors_masterclass(harness):
    """build_curated_set always includes the 3 masterclass cultural references
    when their families are registered, plus a mix of base/pattern/mono."""
    bmz, base_reg, pattern_reg, mono_reg = harness._load_engine()
    curated = harness.build_curated_set(base_reg, pattern_reg, mono_reg)
    assert curated, "curated set should not be empty"

    ids = {fid for fid, _kind, _label in curated}
    kinds = {kind for _fid, kind, _label in curated}
    # All three structural kinds should be represented.
    assert "base" in kinds
    assert "monolithic" in kinds

    # Masterclass anchors: one id from each cultural family prefix must appear
    # if that family is registered in MONOLITHIC_REGISTRY.
    for prefix in ("vm", "uj", "rs"):
        family_in_reg = any(k.split("_", 1)[0] == prefix for k in mono_reg)
        if family_in_reg:
            assert any(fid.split("_", 1)[0] == prefix for fid in ids), (
                f"masterclass family '{prefix}_*' is registered but no "
                f"representative landed in the curated set"
            )


def test_update_then_review_one_finish(harness, tmp_path, monkeypatch):
    """End-to-end on ONE finish: --update-baselines then a review pass.

    Redirects all output paths into a throwaway dir so the committed
    _visual_diff/ baselines are never disturbed by the test.
    """
    out = tmp_path / "_vd_test"
    base = out / "baselines"
    cur = out / "current"
    monkeypatch.setattr(harness, "OUT_DIR", out, raising=True)
    monkeypatch.setattr(harness, "BASELINE_DIR", base, raising=True)
    monkeypatch.setattr(harness, "CURRENT_DIR", cur, raising=True)
    monkeypatch.setattr(harness, "MANIFEST_PATH", out / "baselines_manifest.json")
    monkeypatch.setattr(harness, "REPORT_HTML", out / "report.html")
    monkeypatch.setattr(harness, "REPORT_JSON", out / "report.json")

    # 1) Create a baseline for a single small, stable base finish.
    rc = harness.run(update_baselines=True, size=96, seed=42, limit=0,
                     only="gloss")
    assert rc == 0
    assert (out / "baselines_manifest.json").exists()
    pngs = list(base.glob("*.png"))
    assert len(pngs) == 1, f"expected 1 baseline png, got {len(pngs)}"

    # 2) Review against that baseline — must be deterministic (unchanged).
    rc2 = harness.run(update_baselines=False, size=96, seed=42, limit=0,
                      only="gloss")
    assert rc2 == 0
    assert (out / "report.html").exists()
    assert (out / "report.json").exists()

    import json
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    counts = report["summary"]["counts"]
    # Same seed + same render code => no visible change.
    assert counts["same"] == 1, f"expected gloss unchanged, got {counts}"
    assert counts["changed"] == 0


def test_main_never_fails_build(harness, tmp_path, monkeypatch):
    """main() always returns 0 (review tool, not a gate) even via argv path."""
    out = tmp_path / "_vd_main"
    monkeypatch.setattr(harness, "OUT_DIR", out, raising=True)
    monkeypatch.setattr(harness, "BASELINE_DIR", out / "baselines", raising=True)
    monkeypatch.setattr(harness, "CURRENT_DIR", out / "current", raising=True)
    monkeypatch.setattr(harness, "MANIFEST_PATH", out / "baselines_manifest.json")
    monkeypatch.setattr(harness, "REPORT_HTML", out / "report.html")
    monkeypatch.setattr(harness, "REPORT_JSON", out / "report.json")

    rc = harness.main(["--size", "96", "--limit", "1"])
    assert rc == 0
