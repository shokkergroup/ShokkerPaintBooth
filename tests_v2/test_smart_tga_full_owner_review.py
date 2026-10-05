import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts.smart_tga_full_owner_review import apply_decisions, build_packet, validate_and_export


def _run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    car = run / "car"
    car.mkdir(parents=True)
    components = [{
        "layer": "numbers",
        "component_index": 0,
        "area_px": 120,
        "bbox": [10, 12, 20, 18],
        "role_guess": "number_candidate",
        "crop_file": str(car / "number.png"),
    }]
    component_path = car / "component_records.json"
    component_path.write_text(json.dumps(components), encoding="utf-8")
    number_mask = np.zeros((64, 64), np.uint8)
    number_mask[12:30, 10:30] = 255
    paint_mask = np.zeros((64, 64), np.uint8)
    Image.fromarray(number_mask).save(car / "numbers.png")
    Image.fromarray(paint_mask).save(car / "paint.png")
    (run / "inspection_records.json").write_text(json.dumps([{
        "paint_label": "family/car.tga",
        "paint": "car.tga",
        "source_1024": "source.png",
        "component_records": str(component_path),
        "mask_paths": {
            "numbers": str(car / "numbers.png"),
            "paint": str(car / "paint.png"),
        },
    }]), encoding="utf-8")
    return run


def test_draft_seeds_every_prediction_unreviewed_and_empty_unconfirmed(tmp_path):
    packet = build_packet(
        _run(tmp_path),
        owners=("numbers", "paint"),
        min_areas={"numbers": 8, "paint": 20},
    )
    record = packet["records"][0]
    assert record["owners"]["numbers"]["predictions"][0]["verdict"] == "unreviewed"
    assert record["owners"]["paint"]["predictions"] == []
    assert record["owners"]["paint"]["empty_confirmed"] is False


def test_export_rejects_unreviewed_prediction_and_unconfirmed_empty(tmp_path):
    packet = build_packet(
        _run(tmp_path),
        owners=("numbers", "paint"),
        min_areas={"numbers": 8, "paint": 20},
    )
    with pytest.raises(ValueError, match="prediction remains unreviewed"):
        validate_and_export(packet)


def test_export_emits_exact_component_review_after_all_decisions(tmp_path):
    packet = build_packet(
        _run(tmp_path),
        owners=("numbers", "paint"),
        min_areas={"numbers": 8, "paint": 20},
    )
    record = packet["records"][0]
    record["owners"]["numbers"]["predictions"][0]["verdict"] = "false"
    record["owners"]["paint"]["empty_confirmed"] = True
    entries = validate_and_export(packet)
    assert len(entries) == 1
    assert entries[0]["reviewed_owners"] == ["numbers", "paint"]
    assert entries[0]["component_reviews"]["numbers"]["false_bboxes"] == [[10, 12, 20, 18]]
    assert entries[0]["component_reviews"]["paint"]["true_bboxes"] == []
    assert "Sponsors" not in entries[0]["known_issues"][0]


def test_compact_decisions_are_explicit_and_reject_unknown_keys(tmp_path):
    packet = build_packet(
        _run(tmp_path),
        owners=("numbers", "paint"),
        min_areas={"numbers": 8, "paint": 20},
    )
    decisions = {
        "schema": "spb-smart-tga-full-owner-decisions-v1",
        "records": [{
            "paint_label": "family/car.tga",
            "owners": {
                "numbers": {"verdicts": {"numbers:0:10:12:20:18": "false"}},
                "paint": {"empty_confirmed": True},
            },
        }],
    }
    reviewed = apply_decisions(packet, decisions)
    assert validate_and_export(reviewed)[0]["component_reviews"]["numbers"]["false_bboxes"] == [[10, 12, 20, 18]]
    decisions["records"][0]["owners"]["numbers"]["verdicts"] = {"numbers:missing": "false"}
    with pytest.raises(ValueError, match="unknown decision keys"):
        apply_decisions(packet, decisions)


def test_compact_decisions_support_auditable_owner_default_with_exceptions(tmp_path):
    packet = build_packet(
        _run(tmp_path),
        owners=("numbers", "paint"),
        min_areas={"numbers": 8, "paint": 20},
    )
    decisions = {
        "schema": "spb-smart-tga-full-owner-decisions-v1",
        "records": [{
            "paint_label": "family/car.tga",
            "owners": {
                "numbers": {
                    "default_verdict": "true",
                    "verdicts": {"numbers:0:10:12:20:18": "false"},
                },
                "paint": {"default_verdict": "mixed", "empty_confirmed": True},
            },
        }],
    }
    reviewed = apply_decisions(packet, decisions)
    entry = validate_and_export(reviewed)[0]
    assert entry["component_reviews"]["numbers"]["false_bboxes"] == [[10, 12, 20, 18]]
    decisions["records"][0]["owners"]["numbers"]["default_verdict"] = "unreviewed"
    with pytest.raises(ValueError, match="default_verdict"):
        apply_decisions(packet, decisions)
