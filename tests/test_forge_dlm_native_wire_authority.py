from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_dlm_native_wire_authority import OFFICIAL_SHA256, run, sha256_file


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "_forge_data/dlm_native_wire_authority/run121_manifest.json"
OFFICIAL = ROOT / "_dlm_dossier/psd2025_guides/wire.png"


def _write_manifest(tmp_path: Path, mutate) -> Path:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_official_native_wire_passes_exact_diagnostic_and_makes_no_delivery_claim(tmp_path: Path):
    report = run(MANIFEST, tmp_path / "official")
    assert report["status"] == "PASS_NATIVE_2048_WIRE_AUTHORITY_DIAGNOSTIC_NOT_DELIVERY"
    assert report["source"]["sha256"] == OFFICIAL_SHA256
    assert report["source"]["canvas"] == [2048, 2048]
    assert report["native_diagnostics"]["channel_pixels"] == {
        "opaque": 355449,
        "green_boundary": 73172,
        "white_mesh": 282277,
    }
    assert report["native_diagnostics"]["enclosed_regions"]["region_count"] == 4719
    assert report["native_diagnostics"]["enclosed_regions"]["region_pixels"] == 2658729
    assert report["legacy_1024"]["region_count"] == 565
    assert report["legacy_1024"]["region_pixels"] == 667554
    assert report["legacy_1024"]["authoritative"] is False
    for claim in ("physical_surface_ownership", "stored_polarity", "surface_adjacency", "projector", "psd", "app", "delivery"):
        assert report["claims"][claim] is False
    assert (tmp_path / "official/NATIVE_GREEN_BOUNDARY.png").exists()
    assert (tmp_path / "official/NATIVE_WHITE_MESH.png").exists()
    assert (tmp_path / "official/NATIVE_ENCLOSED_REGION_COVERAGE.png").exists()
    assert (tmp_path / "official/RUN121_NATIVE_WIRE_AUTHORITY_CONTACT.png").exists()


def test_downsample_is_rejected_even_when_valid_rgba(tmp_path: Path):
    with Image.open(OFFICIAL) as opened:
        down = opened.convert("RGBA").resize((1024, 1024), Image.Resampling.NEAREST)
    path = tmp_path / "downsample.png"
    down.save(path)
    report = run(MANIFEST, tmp_path / "downsample_out", source_override=path)
    assert report["status"] == "REJECT_NOT_NATIVE_HASHED_WIRE_AUTHORITY"
    assert "authoritative_source_not_native_2048" in report["errors"]
    assert "authoritative_source_sha_mismatch_or_resampled" in report["errors"]


def test_resampled_back_to_2048_is_rejected_by_hash(tmp_path: Path):
    with Image.open(OFFICIAL) as opened:
        native = opened.convert("RGBA")
        resampled = native.resize((1024, 1024), Image.Resampling.BILINEAR).resize((2048, 2048), Image.Resampling.BILINEAR)
    path = tmp_path / "resampled_2048.png"
    resampled.save(path)
    report = run(MANIFEST, tmp_path / "resampled_out", source_override=path)
    assert report["source"]["canvas"] == [2048, 2048]
    assert report["status"] == "REJECT_NOT_NATIVE_HASHED_WIRE_AUTHORITY"
    assert report["errors"] == ["authoritative_source_sha_mismatch_or_resampled"]


def test_stale_manifest_hash_is_rejected_before_authority(tmp_path: Path):
    manifest = _write_manifest(tmp_path, lambda payload: payload["authoritative_source"].update(sha256="0" * 64))
    report = run(manifest, tmp_path / "stale")
    assert report["status"] == "REJECT_NOT_NATIVE_HASHED_WIRE_AUTHORITY"
    assert "manifest_official_sha_not_immutable_authority" in report["errors"]


def test_missing_source_rejects_fail_closed(tmp_path: Path):
    missing = tmp_path / "not_here.png"
    report = run(MANIFEST, tmp_path / "missing", source_override=missing)
    assert report["status"] == "REJECT_NOT_NATIVE_HASHED_WIRE_AUTHORITY"
    assert report["errors"] == ["authoritative_source_missing"]


def test_official_result_is_deterministic(tmp_path: Path):
    first = run(MANIFEST, tmp_path / "first")
    second = run(MANIFEST, tmp_path / "second")
    assert first["proof_sha256"] == second["proof_sha256"]
    assert sha256_file(tmp_path / "first/RUN121_NATIVE_WIRE_AUTHORITY_CONTACT.png") == sha256_file(tmp_path / "second/RUN121_NATIVE_WIRE_AUTHORITY_CONTACT.png")
    assert first["sensitivity_audit"] == second["sensitivity_audit"]
