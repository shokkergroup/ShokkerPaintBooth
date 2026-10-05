import json
from pathlib import Path

from PIL import Image

import _forge_owner_render_evidence as gate


def _manifest(root: Path) -> dict:
    image = root / "driver.png"
    Image.new("RGB", (80, 40), "yellow").save(image)
    return {
        "$schema": gate.SCHEMA,
        "candidate_id": "candidate_v1",
        "decision": "reject",
        "source_root": str(root),
        "evidence": [
            {
                "filename": image.name,
                "view_role": "driver_profile",
                "sha256": gate.sha256_file(image),
                "issues": [
                    {
                        "region": "driver_side",
                        "issue_type": "surface_registration",
                        "severity": "blocker",
                        "bbox_norm": [0.1, 0.1, 0.8, 0.8],
                    }
                ],
            }
        ],
    }


def test_rejected_candidate_with_blocker_is_valid_but_not_accepted(tmp_path: Path) -> None:
    report = gate.audit_manifest(_manifest(tmp_path), manifest_dir=tmp_path)
    assert report["manifest_valid"] is True
    assert report["candidate_accepted"] is False
    assert report["severity_counts"]["blocker"] == 1
    assert report["sim_view_role_count"] == 1


def test_accept_decision_cannot_override_owner_render_blocker(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["decision"] = "accept"
    report = gate.audit_manifest(manifest, manifest_dir=tmp_path)
    assert report["manifest_valid"] is False
    assert any("conflicts" in error for error in report["errors"])


def test_hash_mismatch_is_a_manifest_error(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["evidence"][0]["sha256"] = "0" * 64
    report = gate.audit_manifest(manifest, manifest_dir=tmp_path)
    assert report["manifest_valid"] is False
    assert any("sha256 mismatch" in error for error in report["errors"])


def test_bbox_must_be_normalized_and_ordered(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["evidence"][0]["issues"][0]["bbox_norm"] = [0.8, 0.1, 0.2, 0.9]
    report = gate.audit_manifest(manifest, manifest_dir=tmp_path)
    assert report["manifest_valid"] is False
    assert any("bbox_norm" in error for error in report["errors"])


def test_report_writer_emits_machine_and_visual_evidence(tmp_path: Path) -> None:
    report = gate.audit_manifest(_manifest(tmp_path), manifest_dir=tmp_path)
    output = tmp_path / "report"
    gate.write_report(report, output)
    payload = json.loads((output / "owner_render_gate.json").read_text(encoding="utf-8"))
    assert payload["candidate_id"] == "candidate_v1"
    assert (output / "owner_render_gate.md").is_file()
    assert (output / "OWNER_RENDER_GATE_CONTACT.png").is_file()


def _accepted_manifest(root: Path) -> dict:
    evidence = []
    role_regions = {
        "driver_profile": "driver_side",
        "passenger_profile": "passenger_side",
        "front": "nose",
        "rear": "deck",
        "top": "roof",
    }
    for index, (role, region) in enumerate(role_regions.items()):
        image = root / f"{role}.png"
        Image.new("RGB", (80, 40), (20 * index, 100, 180)).save(image)
        evidence.append(
            {
                "filename": image.name,
                "view_role": role,
                "sha256": gate.sha256_file(image),
                "issues": [],
            }
        )
    return {
        "$schema": gate.SCHEMA,
        "candidate_id": "candidate_accept",
        "decision": "accept",
        "source_root": str(root),
        "visual_checks": {name: True for name in gate.REQUIRED_VISUAL_CHECKS},
        "evidence": evidence,
    }


def test_accept_requires_all_five_direct_simulator_roles(tmp_path: Path) -> None:
    manifest = _accepted_manifest(tmp_path)
    manifest["evidence"] = manifest["evidence"][:-1]
    report = gate.audit_manifest(manifest, manifest_dir=tmp_path)
    assert report["candidate_accepted"] is False
    assert report["missing_accept_roles"] == ["top"]
    assert any("requires five direct simulator roles" in error for error in report["errors"])


def test_accept_requires_every_visual_sanity_answer(tmp_path: Path) -> None:
    manifest = _accepted_manifest(tmp_path)
    manifest["visual_checks"]["no_floating_or_disconnected_artwork"] = False
    report = gate.audit_manifest(manifest, manifest_dir=tmp_path)
    assert report["candidate_accepted"] is False
    assert "no_floating_or_disconnected_artwork" in report["failed_visual_checks"]


def test_accepts_complete_five_view_visually_reviewed_evidence(tmp_path: Path) -> None:
    report = gate.audit_manifest(_accepted_manifest(tmp_path), manifest_dir=tmp_path)
    assert report["manifest_valid"] is True
    assert report["candidate_accepted"] is True
    assert report["missing_accept_roles"] == []
    assert report["failed_visual_checks"] == []