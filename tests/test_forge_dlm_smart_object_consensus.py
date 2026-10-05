import copy
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_smart_object_consensus import (
    EXPECTED_PSD_COUNT,
    EXPECTED_SURFACE_COUNT,
    evaluate_extracted,
    evaluate_manifest,
    write_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "_forge_data"
    / "dlm_smart_object_consensus"
    / "run122_manifest.json"
)


@pytest.fixture(scope="module")
def authority():
    report, extracted = evaluate_manifest(MANIFEST)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert report["valid"] is True
    return manifest, report, extracted


def _clone(extracted):
    rows = []
    for original in extracted:
        record = {
            key: copy.deepcopy(value)
            for key, value in original.items()
            if key not in {"_mask_arrays", "_raw_wire_canvas"}
        }
        record["_mask_arrays"] = dict(original.get("_mask_arrays", {}))
        if "_raw_wire_canvas" in original:
            record["_raw_wire_canvas"] = original["_raw_wire_canvas"]
        rows.append(record)
    return rows


def test_real_three_psd_consensus_is_narrow_and_hash_bound(authority):
    manifest, report, extracted = authority
    assert len(extracted) == EXPECTED_PSD_COUNT
    assert report["status"] == "PASS_3_OF_3_CONSENSUS_NOT_DELIVERY"
    assert report["metrics"]["surfaces_three_of_three"] == EXPECTED_SURFACE_COUNT
    assert report["metrics"]["solid_overlap_pixels"] == 0
    assert report["metrics"]["thresholded_ownership_overlap_pixels"] == 0
    assert report["metrics"]["mask_resampling_used"] is False
    assert (
        report["local_canonical_facts_sha256"]
        == manifest["local_canonical_facts_sha256"]
    )
    assert (
        report["external_audit"]["external_hash_comparison"]
        == "not_comparable_serialization_unknown"
    )
    assert all(value is False for value in report["claims"].values())


def test_one_bit_native_mask_change_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[1]["surfaces"][0]["mask_sha256"] = "0" * 64
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert report["status"] == "REJECT_SMART_OBJECT_CONSENSUS"
    assert any("mask_sha256" in blocker for blocker in report["blockers"])
    assert any("not_three_of_three_identical" in blocker for blocker in report["blockers"])


def test_transform_change_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[2]["surfaces"][3]["transform"][0] += 0.000001
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("transform" in blocker for blocker in report["blockers"])


def test_missing_surface_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[0]["surfaces"].pop()
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("surface_cardinality:7" in blocker for blocker in report["blockers"])


def test_duplicate_surface_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[0]["surfaces"].append(copy.deepcopy(mutated[0]["surfaces"][0]))
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("surface_cardinality:9" in blocker for blocker in report["blockers"])
    assert any("cardinality:2" in blocker for blocker in report["blockers"])


def test_psd_hash_change_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[1]["actual_sha256"] = "f" * 64
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("psd_sha256" in blocker for blocker in report["blockers"])


def test_raw_wire_identity_change_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[2]["raw_wire"]["rgba_bytes_sha256"] = "1" * 64
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("raw_wire:rgba_bytes_sha256" in blocker for blocker in report["blockers"])


def test_resampling_flag_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[0]["surfaces"][0]["mask_resampled"] = True
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("resampling_forbidden" in blocker for blocker in report["blockers"])


def test_nonzero_warp_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[0]["surfaces"][0]["zero_warp"]["warp_value"] = 0.01
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("zero_warp:warp_value" in blocker for blocker in report["blockers"])


def test_manifest_missing_or_duplicate_authority_path_fails_closed(authority):
    manifest, _report, extracted = authority
    missing = copy.deepcopy(manifest)
    missing["surfaces"].pop()
    missing_report = evaluate_extracted(missing, _clone(extracted))
    assert missing_report["valid"] is False
    assert "manifest_requires_exactly_eight_surfaces" in missing_report["blockers"]

    duplicate = copy.deepcopy(manifest)
    duplicate["surfaces"][1]["layer_path"] = duplicate["surfaces"][0]["layer_path"]
    duplicate_report = evaluate_extracted(duplicate, _clone(extracted))
    assert duplicate_report["valid"] is False
    assert "manifest_surface_paths_not_unique" in duplicate_report["blockers"]


def test_written_masks_are_native_and_thresholded_disjoint(authority, tmp_path):
    _manifest, report, extracted = authority
    write_outputs(MANIFEST, tmp_path, report, extracted)
    native_paths = sorted((tmp_path / "masks").glob("*_native_l.png"))
    ownership_paths = sorted((tmp_path / "masks").glob("*_ownership.png"))
    assert len(native_paths) == EXPECTED_SURFACE_COUNT
    assert len(ownership_paths) == EXPECTED_SURFACE_COUNT
    ownership = np.stack(
        [np.asarray(Image.open(path).convert("L"), dtype=np.uint8) > 0 for path in ownership_paths]
    )
    assert int(np.count_nonzero(ownership.sum(axis=0) > 1)) == 0
    assert (tmp_path / "SMART_OBJECT_CONSENSUS_REPORT.json").is_file()
    assert (tmp_path / "CANONICAL_FACTS.json").is_file()
    assert (tmp_path / "RUN122_SMART_OBJECT_CONSENSUS_CONTACT.png").is_file()

