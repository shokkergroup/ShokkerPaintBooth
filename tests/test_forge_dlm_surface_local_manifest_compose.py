import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_surface_local_manifest_compose import LAYERS, _alpha_over, _asset, _primitive, build


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "_forge_data" / "dlm_surface_local_liveries" / "waffle_front_v1.json"


def test_revoked_legacy_front_manifest_cannot_bypass_physical_identity(tmp_path):
    with pytest.raises(Exception, match="legacy_v1_manifest_evidence_only"):
        build(MANIFEST, tmp_path / "blocked_front")


def test_reusable_surface_local_composer_has_no_livery_branch():
    source = (ROOT / "_forge_dlm_surface_local_manifest_compose.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor ==", "filename =="):
        assert forbidden not in source


def test_fit_text_stretches_into_declared_local_surface_box():
    image = _primitive({
        "kind": "fit_text", "text": "LONG WORDMARK", "bbox": [50, 200, 950, 800],
        "fit": "stretch", "render_size": 240, "bold": True, "color": [10, 20, 30, 255],
    }, {})
    assert image.getchannel("A").getbbox() == (50, 200, 950, 800)


def test_contain_fit_enlarges_tight_asset_to_surface_box(tmp_path):
    path = tmp_path / "tight_panel.png"
    Image.new("RGBA", (20, 10), (220, 80, 20, 255)).save(path)
    image = _asset({"target_bbox": [100, 200, 900, 600], "fit": "contain"}, path)
    assert image.getchannel("A").getbbox() == (100, 200, 900, 600)
