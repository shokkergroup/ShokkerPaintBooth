from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_staged_semantic_surface_atlas import (
    StagedAtlasError,
    build,
    canonical_sha256,
    unique_index,
)


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_staged_semantic_surface_atlas/run140_job.json"
OUT = ROOT / "_forge_out/codex_full_uv_recovery/run_140_staged_semantic_surface_atlas"


@pytest.fixture(scope="session")
def built():
    return build(JOB, OUT)


def test_exact_native_consensus_surfaces_are_preserved(built):
    report = built["report"]
    assert report["metrics"]["tier_a_exact_surface_count"] == 8
    assert report["metrics"]["tier_a_exact_pixel_count"] == 739912
    assert report["exact_surface_order"] == [
        "left_a_post",
        "left_quarter_window",
        "left_side",
        "left_spoiler_side",
        "right_a_post",
        "right_quarter_window",
        "right_side",
        "right_spoiler_side",
    ]


def test_exact_native_masks_are_disjoint(built):
    index = built["exact_index"]
    assert index.shape == (2048, 2048)
    assert int(np.count_nonzero(index)) == 739912
    assert int(index.max()) == 8


def test_all_or_nothing_capture_debt_is_reduced_but_not_hidden(built):
    metrics = built["report"]["metrics"]
    assert metrics["retired_all_or_nothing_frame_count"] == 220
    assert 0 < metrics["targeted_capture_frame_count"] <= 12
    assert metrics["targeted_capture_role_count"] <= 6
    assert built["report"]["targeted_capture_debt"]


def test_unresolved_front_surfaces_are_not_promoted_to_projectors(built):
    rows = {row["surface_id"]: row for row in built["report"]["surface_readiness"]}
    for surface in ("hood_nose", "left_front_fender", "right_front_fender"):
        assert rows[surface]["ownership_tier"] != "TIER_A_EXACT_NATIVE_MASK"
        assert rows[surface]["projector_ready"] is False
        assert rows[surface]["render_validated"] is False


def test_release_claims_remain_false(built):
    claims = built["report"]["claims"]
    assert claims["staged_surface_evidence"] is True
    assert all(value is False for key, value in claims.items() if key != "staged_surface_evidence")


def test_report_content_hash_is_stable(built):
    report = dict(built["report"])
    claimed = report.pop("report_content_sha256")
    assert canonical_sha256(report) == claimed


def test_duplicate_evidence_keys_fail_closed():
    rows = [{"id": "x"}, {"id": "x"}]
    with pytest.raises(StagedAtlasError, match="surface_duplicate"):
        unique_index(rows, lambda row: row["id"], "surface")


def test_visual_evidence_is_full_resolution(built):
    for name, minimum in (
        ("STAGED_EXACT_SURFACE_ATLAS.png", (2048, 2048)),
        ("STAGED_CALIBRATION_BEFORE_AFTER.png", (1800, 1000)),
    ):
        with Image.open(OUT / name) as image:
            assert image.width >= minimum[0]
            assert image.height >= minimum[1]


def test_reusable_module_has_no_livery_identity_literals():
    text = (ROOT / "_forge_dlm_staged_semantic_surface_atlas.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "jason", "sex wax", "miller", "sponsor"):
        assert forbidden not in text
