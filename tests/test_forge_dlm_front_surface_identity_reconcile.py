from pathlib import Path

from _forge_dlm_front_surface_identity_reconcile import reconcile_rows


ROOT = Path(__file__).resolve().parents[1]


def test_geometry_reconciles_misnamed_front_surfaces():
    projectors = [
        {"surface_id": "alpha", "uv_bbox": [0, 0, 100, 100]},
        {"surface_id": "beta", "uv_bbox": [100, 0, 200, 100]},
    ]
    matches = reconcile_rows(projectors, {"physical_left": [0, 0, 100, 100], "physical_right": [100, 0, 200, 100]}, 0.8)
    assert {(row["staged_surface_id"], row["physical_surface_id"]) for row in matches} == {("alpha", "physical_left"), ("beta", "physical_right")}


def test_reconciliation_is_livery_neutral():
    source = (ROOT / "_forge_dlm_front_surface_identity_reconcile.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor ==", "filename =="):
        assert forbidden not in source
