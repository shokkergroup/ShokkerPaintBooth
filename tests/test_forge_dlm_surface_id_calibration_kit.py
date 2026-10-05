from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import _forge_dlm_surface_id_calibration_kit as kit


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_surface_id_calibration_kit" / "run110_job.json"


def _job() -> dict:
    return json.loads(JOB.read_text(encoding="utf-8"))


def _source_path(job: dict, key: str) -> Path:
    return (JOB.parent / job["sources"][key]["path"]).resolve()


def _evidence() -> tuple[dict, dict, np.ndarray, list[dict]]:
    job = _job()
    inventory = json.loads(_source_path(job, "exact_topology_inventory").read_text(encoding="utf-8"))
    atlas = json.loads(_source_path(job, "official_landmark_atlas").read_text(encoding="utf-8"))
    labels = np.asarray(Image.open(_source_path(job, "exact_topology_labels")), dtype=np.int32)
    contracts = kit._surface_contracts(job)
    return inventory, atlas, labels, contracts


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_job_sources_are_hash_bound() -> None:
    job = _job()
    for name, source in job["sources"].items():
        path = _source_path(job, name)
        assert path.is_file()
        assert _sha(path) == source["sha256"]


def test_surface_contracts_are_independent_and_unique() -> None:
    contracts = kit._surface_contracts(_job())
    assert len(contracts) == 2
    assert len({item["surface_id"] for item in contracts}) == len(contracts)
    assert len({item["physical_side"] for item in contracts}) == len(contracts)
    assert len({tuple(item["base_rgb"]) for item in contracts}) == len(contracts)


def test_exact_candidate_census_matches_bound_evidence() -> None:
    inventory, atlas, _labels, contracts = _evidence()
    candidates, conflicts = kit.derive_component_candidates(inventory, atlas, contracts)
    assert conflicts == []
    by_surface = {}
    for contract in contracts:
        surface = contract["surface_id"]
        selected = [item for item in candidates if item["surface_id"] == surface]
        by_surface[surface] = (len(selected), sum(item["declared_pixel_count"] for item in selected))
    assert by_surface == {
        "left_side": (42, 434340),
        "right_side": (247, 298880),
    }


def test_unknown_anchor_components_remain_candidate_only() -> None:
    inventory, atlas, _labels, contracts = _evidence()
    candidates, _ = kit.derive_component_candidates(inventory, atlas, contracts)
    indexed = {item["label_value"]: item for item in candidates}
    assert indexed[10]["surface_id"] == "left_side"
    assert indexed[10]["candidate_only"] is True
    assert indexed[10]["basis"] == "EXACT_TOPOLOGY_RUN99_ANCHOR_CANDIDATE_ONLY"
    assert indexed[356]["surface_id"] == "right_side"
    assert indexed[356]["candidate_only"] is True
    assert indexed[356]["basis"] == "EXACT_TOPOLOGY_RUN99_ANCHOR_CANDIDATE_ONLY"
    assert all(item["whole_component_ownership_claim"] is False for item in candidates)


def test_conflicting_anchor_nomination_fails_closed() -> None:
    inventory, atlas, _labels, contracts = _evidence()
    altered = json.loads(json.dumps(atlas))
    clone = json.loads(json.dumps(next(item for item in altered["landmarks"] if item["topology"]["label_value"] == 10)))
    clone["id"] = "synthetic.conflicting.exact.anchor"
    clone["physical_surface"] = "right_side"
    clone["physical_side"] = "right"
    altered["landmarks"].append(clone)
    candidates, conflicts = kit.derive_component_candidates(inventory, altered, contracts)
    assert any(item["label_value"] == 10 and item["status"] == "ABSTAIN_SURFACE_CONFLICT" for item in conflicts)
    assert 10 not in {item["label_value"] for item in candidates}


def test_texture_alpha_is_exact_disjoint_candidate_union() -> None:
    inventory, atlas, labels, contracts = _evidence()
    candidates, _ = kit.derive_component_candidates(inventory, atlas, contracts)
    texture, alpha, decoder = kit.render_texture(labels, candidates, contracts, _job()["policy"])
    values = [item["label_value"] for item in decoder]
    exact = np.isin(labels, values)
    assert texture.mode == "RGBA"
    assert texture.size == (2048, 2048)
    assert set(np.unique(alpha).tolist()) == {0, 255}
    assert np.array_equal(alpha == 255, exact)
    assert int(exact.sum()) == 733220
    assert int(np.logical_and(alpha == 255, labels == 0).sum()) == 0


def test_texture_is_visibly_nonsymmetric_and_tokens_are_unique() -> None:
    inventory, atlas, labels, contracts = _evidence()
    candidates, _ = kit.derive_component_candidates(inventory, atlas, contracts)
    texture, alpha, decoder = kit.render_texture(labels, candidates, contracts, _job()["policy"])
    metrics = kit._symmetry_metrics(texture, alpha)
    assert metrics["equals_horizontal_flip"] is False
    assert metrics["equals_vertical_flip"] is False
    assert metrics["equals_rotate_180"] is False
    tokens = [item["component_token"] for item in decoder]
    assert len(tokens) == len(set(tokens)) == 289


def test_capture_protocol_is_bound_to_independent_physical_sides() -> None:
    job = _job()
    ledger = json.loads(_source_path(job, "active_official_ledger").read_text(encoding="utf-8"))
    pairs = kit.validate_capture_pairs(job, ledger)
    assert len(pairs) == 3
    assert {item["left"]["physical_side"] for item in pairs} == {"left"}
    assert {item["right"]["physical_side"] for item in pairs} == {"right"}
    assert sum(len(item["capture_states"]) * 2 for item in pairs) == 12
    assert all(any("never image-mirror" in rule for rule in item["matched_camera_requirements"]) for item in pairs)


def test_build_passes_fail_closed_gates_and_is_repeatable(tmp_path: Path) -> None:
    output = tmp_path / "kit"
    first = kit.build(JOB, output)
    first_hashes = {path.name: _sha(path) for path in output.iterdir() if path.is_file()}
    second = kit.build(JOB, output)
    second_hashes = {path.name: _sha(path) for path in output.iterdir() if path.is_file()}
    assert first_hashes == second_hashes
    assert first["audit"]["status"] == "PASS_CALIBRATION_KIT_NOT_DELIVERY"
    assert second["report"]["metrics"]["encoded_pixel_count"] == 733220
    assert second["report"]["claims"]["projector"] is False
    assert second["report"]["claims"]["delivery"] is False
    assert second["report"]["claims"]["psd"] is False
    assert all(second["audit"]["gates"].values())


def test_hash_drift_is_rejected(tmp_path: Path) -> None:
    job = _job()
    for name in job["sources"]:
        job["sources"][name]["path"] = str(_source_path(job, name))
    job["sources"]["run106_report"]["sha256"] = "0" * 64
    bad_job = tmp_path / "bad_job.json"
    bad_job.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(kit.EvidenceError, match="run106_report_source_sha256_mismatch"):
        kit.build(bad_job, tmp_path / "out")
