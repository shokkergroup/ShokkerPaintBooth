import json
from pathlib import Path

import pytest

from scripts.smart_tga_number_family_pair_bank import build_bank, pair_features


def _candidate(instance_id, shape, *, owner="brand_graphics"):
    return {
        "instance_id": instance_id, "shape_occupancy": shape,
        "area_fraction": 0.01, "aspect_ratio": 2.0, "mean_rgb": [200, 20, 20],
        "palette_role": "chromatic", "proposed_owners": [owner],
    }


def _rle(mask):
    flat = [value for row in mask for value in row]
    counts, current, run = [], 0, 0
    for value in flat:
        if value == current:
            run += 1
        else:
            counts.append(run)
            current = value
            run = 1
    counts.append(run)
    return {"encoding": "binary-rle-row-major-v1", "shape": [len(mask), len(mask[0])], "counts": counts}


def test_pair_features_are_rotation_and_mirror_invariant():
    shape = [1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
    mirrored = [0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0]
    features = pair_features(_candidate("a", shape), _candidate("b", mirrored))
    assert features["shape_d4_l1"] == 0.0
    assert features["shape_d4_cosine"] == pytest.approx(1.0)


def test_high_resolution_mask_descriptor_is_rotation_invariant():
    mask = [[0] * 8 for _ in range(8)]
    for y, x in ((1, 1), (1, 2), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3)):
        mask[y][x] = 1
    rotated = [list(row) for row in zip(*mask[::-1])]
    left, right = _candidate("a", [0] * 16), _candidate("b", [0] * 16)
    left["mask_rle"], right["mask_rle"] = _rle(mask), _rle(rotated)
    features = pair_features(left, right)
    assert features["mask8_d4_l1"] == pytest.approx(0.0)
    assert features["mask8_d4_cosine"] == pytest.approx(1.0)


def test_bank_builds_reviewed_positive_and_hard_negative_pairs(tmp_path: Path):
    run = tmp_path / "cycle700_demo"
    run.mkdir()
    inspections = [{
        "paint_label": "dirtlatemodel 350/car_num_1.tga",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {"features": {"records": [
            _candidate("a", [1] * 16), _candidate("b", [1] * 16),
            _candidate("n", [0] * 16, owner="template"),
        ]}}}},
    }]
    audit = {"paints": [{"paint_label": "dirtlatemodel 350/car_num_1.tga", "groups": [
        {"group_id": "g1", "instance_ids": ["n"]},
    ]}]}
    inspection_path = run / "inspection_records.json"
    audit_path = run / "audit.json"
    inspection_path.write_text(json.dumps(inspections), encoding="utf-8")
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps({
        "inspection_records": str(inspection_path), "physical_group_audit": str(audit_path),
        "paint_group_targets": {"dirtlatemodel 350/car_num_1.tga": ["template"]},
    }), encoding="utf-8")
    probe_path = run / "missed.json"
    probe_path.write_text(json.dumps({"records": [
        {"paint_label": "dirtlatemodel 350/car_num_1.tga", "family_id": "number:1", "status": "candidate_present", "best_instance_id": "a"},
        {"paint_label": "dirtlatemodel 350/car_num_1.tga", "family_id": "number:1", "status": "candidate_fragment_only", "best_instance_id": "b"},
    ]}), encoding="utf-8")

    bank = build_bank([probe_path], [labels_path])
    assert bank["summary"]["positive_pair_count"] == 2
    assert bank["summary"]["negative_pair_count"] == 2
    assert bank["summary"]["ownership_authority"] is False
