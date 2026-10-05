from __future__ import annotations

import json
from pathlib import Path

from _forge_dlm_legacy_topology_quarantine import run, sha256_file


ROOT = Path(__file__).resolve().parents[1]
FULL_MANIFEST = ROOT / "_forge_data/dlm_legacy_topology_quarantine/run124_manifest.json"
LEGACY_SHA = "0a47ddc2fe206bf463ac9cf484764901a56298f6e14348cd844c4af542892b9d"


def _manifest(tmp_path: Path, source: Path, *, policy: str, expected: str, sha: str | None = None) -> Path:
    payload = {
        "$schema": "shokk-forge.dlm-legacy-topology-quarantine-manifest/v1",
        "quarantine_id": "test",
        "fingerprints": {
            "legacy_coverage_mask_sha256": LEGACY_SHA,
            "legacy_wire_1024_sha256": "56dff2dc571ee865e89bc730b48eebf673102d140d261cf935ae59bce1417f96",
            "legacy_component_count": 565,
            "legacy_native_mask_pixel_count": 2670216,
            "legacy_wire_1024_region_pixels": 667554,
            "legacy_lineage_tokens": ["run110", "run_110", "run113", "run_113"],
        },
        "inputs": [{
            "input_id": "fixture",
            "kind": "job",
            "policy": policy,
            "expected_disposition": expected,
            "path": str(source),
            "sha256": sha if sha is not None else (sha256_file(source) if source.exists() else "0" * 64),
        }],
    }
    path = tmp_path / f"manifest_{policy}_{expected}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_diagnostic_legacy_use_is_accepted_only_as_quarantined(tmp_path: Path):
    source = tmp_path / "diagnostic.json"
    source.write_text(json.dumps({"component_count": 565, "lineage": "run113"}), encoding="utf-8")
    report = run(_manifest(tmp_path, source, policy="diagnostic_only", expected="quarantine"), tmp_path / "out")
    assert report["status"] == "PASS_LEGACY_TOPOLOGY_QUARANTINED_NO_PROMOTION_AUTHORITY"
    assert report["inputs"][0]["disposition"] == "QUARANTINED_DIAGNOSTIC_ONLY"
    assert report["summary"]["promotion_authority_violation_count"] == 0


def test_promotion_path_with_legacy_authority_is_rejected(tmp_path: Path):
    source = tmp_path / "promotion.json"
    source.write_text(json.dumps({"authority": {"sha256": LEGACY_SHA}, "expected_pixels": 2670216}), encoding="utf-8")
    report = run(_manifest(tmp_path, source, policy="promotion_path", expected="reject"), tmp_path / "out")
    assert report["status"] == "PASS_LEGACY_TOPOLOGY_QUARANTINED_NO_PROMOTION_AUTHORITY"
    assert report["inputs"][0]["disposition"] == "REJECT_PROMOTION_PATH_LEGACY_AUTHORITY"
    assert report["summary"]["promotion_rejected_count"] == 1
    assert report["claims"]["delivery"] is False


def test_stale_hash_fails_binding_before_scan(tmp_path: Path):
    source = tmp_path / "stale.json"
    source.write_text(json.dumps({"component_count": 565}), encoding="utf-8")
    manifest = _manifest(tmp_path, source, policy="diagnostic_only", expected="quarantine", sha="f" * 64)
    report = run(manifest, tmp_path / "out")
    assert report["status"] == "REJECT_QUARANTINE_INPUT_BINDING_FAILURE"
    assert report["inputs"][0]["disposition"] == "REJECT_BINDING_STALE_HASH"


def test_missing_source_fails_closed(tmp_path: Path):
    missing = tmp_path / "run124_intentionally_absent" / "missing.json"
    assert not missing.exists()
    manifest = _manifest(tmp_path, missing, policy="promotion_path", expected="reject")
    report = run(manifest, tmp_path / "out")
    assert report["status"] == "REJECT_QUARANTINE_INPUT_BINDING_FAILURE"
    assert report["inputs"][0]["disposition"] == "REJECT_BINDING_MISSING"


def test_full_bounded_manifest_is_deterministic_and_rejects_known_promotion_jobs(tmp_path: Path):
    first = run(FULL_MANIFEST, tmp_path / "first")
    second = run(FULL_MANIFEST, tmp_path / "second")
    assert first["status"] == "PASS_LEGACY_TOPOLOGY_QUARANTINED_NO_PROMOTION_AUTHORITY"
    assert first["proof_sha256"] == second["proof_sha256"]
    assert first["summary"] == {
        "input_count": 13,
        "diagnostic_only_count": 5,
        "diagnostic_quarantined_count": 5,
        "promotion_path_count": 8,
        "promotion_rejected_count": 8,
        "promotion_clean_count": 0,
        "promotion_authority_violation_count": 0,
        "binding_error_count": 0,
        "policy_error_count": 0,
    }
    assert sha256_file(tmp_path / "first/RUN124_LEGACY_TOPOLOGY_QUARANTINE_CONTACT.png") == sha256_file(tmp_path / "second/RUN124_LEGACY_TOPOLOGY_QUARANTINE_CONTACT.png")
