from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_staged_front_projector_registry import FrontProjectorError, build


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_staged_front_projector" / "run144_job.json"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return build(JOB, tmp_path_factory.mktemp("front_projector"))


def test_four_physical_front_owners_are_disjoint(result):
    report = result["report"]
    assert report["metrics"] == {
        "surface_count": 4,
        "exact_mask_pixel_count": 553252,
        "ownership_overlap_pixels": 0,
        "render_validated_surface_count": 0,
    }
    assert {row["surface_id"] for row in report["surface_projectors"]} == {
        "hood", "nose", "left_front_fender", "right_front_fender"
    }


def test_front_index_has_one_owner_per_pixel(result):
    index = result["index"]
    values = set(np.unique(index).tolist())
    assert values == {0, 1, 2, 3, 4}
    assert np.count_nonzero(index) == 553252


def test_projectors_are_nondegenerate_and_fail_closed(result):
    report = result["report"]
    assert all(abs(row["homography_determinant"]) > 1e-10 for row in report["surface_projectors"])
    assert all(row["physical_readable_direction_validated"] is False for row in report["surface_projectors"])
    assert all(row["render_validated"] is False for row in report["surface_projectors"])
    assert all(report["claims"][key] is False for key in ("physical_readable_direction", "iracing", "psd", "delivery", "accuracy_95"))


def test_duplicate_component_membership_is_rejected(tmp_path):
    import json
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for row in job["sources"].values():
        path = Path(row["path"])
        if not path.is_absolute():
            row["path"] = str((JOB.parent / path).resolve())
    job["surfaces"][1]["component_labels"].append(369)
    path = tmp_path / "overlap.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(FrontProjectorError, match="surface_ownership_overlap:nose"):
        build(path, tmp_path / "out")


def test_reusable_front_registry_has_no_livery_identity_branch():
    source = (ROOT / "_forge_dlm_staged_front_projector_registry.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor", "filename =="):
        assert forbidden not in source
