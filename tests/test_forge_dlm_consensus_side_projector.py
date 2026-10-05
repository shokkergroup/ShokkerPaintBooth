import copy
import hashlib
import json
from pathlib import Path

import pytest

from _forge_dlm_consensus_side_projector import (
    EXPECTED_SURFACE_COUNT,
    evaluate_extracted,
    evaluate_manifest,
    write_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "_forge_data"
    / "dlm_consensus_side_projector"
    / "run125_manifest.json"
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clone(extracted):
    rows = []
    for original in extracted:
        record = {
            key: copy.deepcopy(value)
            for key, value in original.items()
            if not key.startswith("_")
        }
        for key in ("_masks", "_photoshop_canvases"):
            record[key] = dict(original.get(key, {}))
        if "_embedded_rgba" in original:
            record["_embedded_rgba"] = original["_embedded_rgba"]
        rows.append(record)
    return rows


@pytest.fixture(scope="module")
def authority():
    report, extracted, manifest = evaluate_manifest(MANIFEST)
    assert report["valid"] is True, report["blockers"]
    return manifest, report, extracted


def test_real_withheld_psd_validates_eight_narrow_surfaces(authority):
    manifest, report, extracted = authority
    assert report["status"] == (
        "PASS_WITHHELD_8_OF_8_SIDE_FAMILY_PROJECTOR_NOT_IRACING_NOT_DELIVERY"
    )
    assert report["metrics"]["surfaces_passed"] == EXPECTED_SURFACE_COUNT
    assert report["metrics"]["minimum_solid_mask_coverage"] == 1.0
    assert report["metrics"]["worst_alpha_abs_max_full_canvas"] == 0
    assert report["metrics"]["worst_mean_rgb_mae_solid_mask"] <= 20.0
    assert report["metrics"]["worst_p95_rgb_abs_error_solid_mask"] > 20.0
    assert all(row["training_mask_exact"] for row in report["surface_projection"])
    assert all(row["withheld_mask_exact"] for row in report["surface_projection"])
    assert all(row["training_transform_exact"] for row in report["surface_projection"])
    assert all(row["withheld_transform_exact"] for row in report["surface_projection"])
    assert report["claims"]["withheld_historical_psd_side_family_projector"] is True
    assert all(
        value is False
        for key, value in report["claims"].items()
        if key != "withheld_historical_psd_side_family_projector"
    )
    assert len(extracted) == 3


def test_duplicate_left_side_is_recorded_but_never_selected_as_authority(authority):
    _manifest, _report, extracted = authority
    for psd_record in extracted:
        left = next(row for row in psd_record["surfaces"] if row["id"] == "left_side")
        assert left["path_candidate_count"] == 2
        assert left["authority_candidate_count"] == 1
        assert left["non_authority_candidates"] == [
            {"embedded_filename": "Left Side.psb", "source_size": [54, 15]}
        ]


def test_stale_psd_hash_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[2]["actual_sha256"] = "0" * 64
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("sha256" in blocker for blocker in report["blockers"])


def test_reflected_transform_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    surface = mutated[0]["surfaces"][0]
    points = [surface["transform"][i : i + 2] for i in range(0, 8, 2)]
    surface["transform"] = points[0] + points[3] + points[2] + points[1]
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("reflection_or_degenerate_transform" in blocker for blocker in report["blockers"])


def test_nonzero_warp_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[1]["surfaces"][2]["zero_warp"]["warp_value"] = 0.01
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("zero_warp:warp_value" in blocker for blocker in report["blockers"])


def test_duplicate_authority_candidate_fails_closed(authority):
    manifest, _report, extracted = authority
    mutated = _clone(extracted)
    mutated[0]["surfaces"][4]["authority_candidate_count"] = 2
    report = evaluate_extracted(manifest, mutated)
    assert report["valid"] is False
    assert any("candidate_count" in blocker for blocker in report["blockers"])


def test_evaluation_and_written_evidence_are_deterministic(authority, tmp_path):
    manifest, report, extracted = authority
    second = evaluate_extracted(manifest, _clone(extracted))
    stable_second = {
        key: value for key, value in second.items() if key != "report_facts_sha256"
    }
    stable_bound = {
        key: value
        for key, value in report.items()
        if key not in {"source_consensus", "report_facts_sha256"}
    }
    assert stable_second == stable_bound

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    write_outputs(MANIFEST, first_dir, report, extracted, manifest)
    write_outputs(MANIFEST, second_dir, report, extracted, manifest)
    for name in (
        "manifest_snapshot.json",
        "CONSENSUS_SIDE_PROJECTOR_REPORT.json",
        "RUN125_CONSENSUS_SIDE_PROJECTOR_CONTACT.png",
        "RUN125_SUMMARY.md",
    ):
        assert _sha(first_dir / name) == _sha(second_dir / name)

