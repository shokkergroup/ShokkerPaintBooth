"""Integrity checks for the generated owner-facing spec-overlay gallery."""

from __future__ import annotations

import json
import re
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "SPB_SPEC_OVERLAY_REVIEW.html"
MANIFEST = ROOT / "_spec_overlay_review" / "manifest.js"


def _manifest() -> dict:
    text = MANIFEST.read_text(encoding="utf-8")
    match = re.fullmatch(r"window\.SPB_SPEC_OVERLAY_REVIEW = (\{.*\});\n?", text)
    assert match, "manifest.js must remain a file://-compatible single assignment"
    return json.loads(match.group(1))


def test_gallery_catalog_and_assets_are_complete() -> None:
    from engine.spec_pattern_families.visible_overlays_2026 import PICKER_VISIBLE_SPEC_IDS

    data = _manifest()
    ids = tuple(item["id"] for item in data["items"])
    assert data["count"] == len(ids) == 181
    assert ids == PICKER_VISIBLE_SPEC_IDS
    assert len(ids) == len(set(ids))

    for item in data["items"]:
        asset = ROOT / item["asset"]
        assert asset.is_file(), item["id"]
        image = cv2.imread(str(asset), cv2.IMREAD_COLOR)
        assert image is not None, item["id"]
        assert image.shape == (data["panelSize"], data["panelSize"] * 5, 3)


def test_gallery_page_exposes_review_workflow() -> None:
    html = PAGE.read_text(encoding="utf-8")
    assert '_spec_overlay_review/manifest.js' in html
    assert "spbSpecOverlayReviewV1" in html
    for required in ("materialFilter", "grammarFilter", "verdictFilter", "exportFeedback", "openCompare"):
        assert f'id="{required}"' in html
    for view in ("Structure", "Combined M/R/CC", "Metallic", "Roughness", "Clearcoat"):
        assert view in html
