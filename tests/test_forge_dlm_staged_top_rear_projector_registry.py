import json
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_staged_top_rear_projector_registry import TopRearProjectorError, build


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_staged_top_rear_projector" / "run149_job.json"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build(JOB, tmp_path_factory.mktemp("top_rear_projector"))


def test_five_top_rear_owners_are_nonempty_and_disjoint(built):
    report = built["report"]
    assert report["metrics"]["surface_count"] == 5
    assert report["metrics"]["ownership_overlap_pixels"] == 0
    assert all(row["exact_mask_pixels"] > 1000 for row in report["surface_projectors"])
    assert np.count_nonzero(built["index"]) == report["metrics"]["exact_mask_pixel_count"]


def test_fused_components_require_explicit_physical_partition(built):
    rows = {row["surface_id"]: row for row in built["report"]["surface_projectors"]}
    assert 27 in rows["rear_deck_lid"]["component_labels"]
    assert 27 in rows["tub"]["component_labels"]
    assert rows["rear_deck_lid"]["mask_mode"] == "components_in_landmark_polygon"
    assert rows["tub"]["mask_mode"] == "components_in_bbox"
    assert 194 in rows["spoiler_inside"]["component_labels"]
    assert 194 in rows["spoiler_outside"]["component_labels"]


def test_claims_fail_closed_before_render_holdout(built):
    claims = built["report"]["claims"]
    assert claims["top_rear_projectors_partial"] is True
    assert all(claims[key] is False for key in ("physical_readable_direction", "iracing", "psd", "delivery", "accuracy_95"))


def test_ownership_overlap_rejects(tmp_path):
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for row in job["sources"].values():
        row["path"] = str((JOB.parent / row["path"]).resolve())
    job["surfaces"][4] = dict(job["surfaces"][3], surface_id="duplicate_spoiler")
    path = tmp_path / "overlap.json"; path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(TopRearProjectorError, match="surface_ownership_overlap"):
        build(path, tmp_path / "out")


def test_reusable_projector_has_no_livery_identity():
    source = (ROOT / "_forge_dlm_staged_top_rear_projector_registry.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor ==", "filename =="):
        assert forbidden not in source
