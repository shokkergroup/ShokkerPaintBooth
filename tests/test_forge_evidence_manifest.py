import hashlib
import json

from _forge_evidence_manifest import evaluate_use, validate_manifest


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path):
    paths = {}
    for name in ("left", "board", "logo", "calibration", "uv_asset"):
        path = tmp_path / f"{name}.png"
        path.write_bytes(name.encode())
        paths[name] = path
    payload = {
        "$schema": "shokk-forge.evidence-manifest/v1",
        "sources": [
            {
                "id": "left_master",
                "path": "left.png",
                "sha256": _sha(paths["left"]),
                "evidence_class": "car_view_target",
                "role": "left_profile",
                "allowed_uses": ["visual_target", "semantic_observation"],
            },
            {
                "id": "page10_panel",
                "path": "board.png",
                "sha256": _sha(paths["board"]),
                "evidence_class": "presentation_only",
                "role": "overview_board",
                "allowed_uses": ["identity_crosscheck"],
            },
            {
                "id": "hero_logo",
                "path": "logo.png",
                "sha256": _sha(paths["logo"]),
                "evidence_class": "art_asset",
                "role": "semantic_logo",
                "allowed_uses": ["delivery_art_pixels", "semantic_master"],
            },
            {
                "id": "uv_id_render",
                "path": "calibration.png",
                "sha256": _sha(paths["calibration"]),
                "evidence_class": "calibration_render",
                "role": "front_camera",
                "allowed_uses": ["correspondence_calibration"],
            },
            {
                "id": "mapped_logo",
                "path": "uv_asset.png",
                "sha256": _sha(paths["uv_asset"]),
                "evidence_class": "calibrated_uv_asset",
                "role": "hood_logo_uv",
                "allowed_uses": ["uv_projection_source"],
            },
        ],
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload))
    return path


def test_valid_manifest_separates_appearance_geometry_and_art(tmp_path):
    report = validate_manifest(_manifest(tmp_path))
    assert report["valid"]
    assert report["source_count"] == 5


def test_presentation_board_cannot_become_uv_geometry(tmp_path):
    report = evaluate_use(_manifest(tmp_path), "uv_projection_source", ["page10_panel"])
    assert report["decision"] == "reject"
    assert "not authorized" in report["blockers"][0]


def test_art_asset_can_supply_pixels_but_not_surface_geometry(tmp_path):
    manifest = _manifest(tmp_path)
    assert evaluate_use(manifest, "delivery_art_pixels", ["hero_logo"])["valid"]
    assert not evaluate_use(manifest, "correspondence_calibration", ["hero_logo"])["valid"]


def test_calibrated_uv_asset_is_required_for_uv_projection_source(tmp_path):
    manifest = _manifest(tmp_path)
    assert evaluate_use(manifest, "uv_projection_source", ["mapped_logo"])["valid"]
    assert not evaluate_use(manifest, "uv_projection_source", ["left_master"])["valid"]


def test_manifest_rejects_class_authority_escalation(tmp_path):
    manifest_path = _manifest(tmp_path)
    payload = json.loads(manifest_path.read_text())
    payload["sources"][1]["allowed_uses"].append("correspondence_calibration")
    manifest_path.write_text(json.dumps(payload))
    report = validate_manifest(manifest_path)
    assert not report["valid"]
    assert any("cannot authorize" in error for error in report["errors"])