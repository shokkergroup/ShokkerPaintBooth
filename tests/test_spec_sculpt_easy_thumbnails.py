"""Shipping contracts for the complete Easy Spec Sculpt named-look gallery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
THUMBS = ROOT / "thumbnails" / "spec_sculpt_presets"


def test_every_named_preset_has_a_real_shipping_thumbnail():
    manifest = json.loads((THUMBS / "_manifest.json").read_text(encoding="utf-8"))
    ids = [str(row["id"]) for row in manifest["thumbs"]]
    assert len(ids) == 175
    assert len(set(ids)) == len(ids)

    missing = [preset_id for preset_id in ids if not (THUMBS / f"{preset_id}.png").is_file()]
    assert missing == []

    manifest_ids = {str(row["id"]) for row in manifest["thumbs"]}
    assert manifest["count"] == len(ids)
    assert manifest_ids == set(ids)

    for preset_id in ids:
        path = THUMBS / f"{preset_id}.png"
        assert path.stat().st_size >= 500, preset_id
        with Image.open(path) as image:
            assert image.size == (256, 256), preset_id


def test_designer_fusion_cards_are_complete_and_not_duplicate_placeholders():
    manifest = json.loads((THUMBS / "_manifest.json").read_text(encoding="utf-8"))
    fusion_ids = [str(row["id"]) for row in manifest["thumbs"] if str(row["id"]).startswith("dz_")]
    assert len(fusion_ids) == 50
    hashes = {
        hashlib.sha256((THUMBS / f"{preset_id}.png").read_bytes()).hexdigest()
        for preset_id in fusion_ids
    }
    assert len(hashes) == len(fusion_ids)

    sync_manifest = json.loads((ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8"))
    assert "thumbnails/spec_sculpt_presets" in sync_manifest["directories"]
