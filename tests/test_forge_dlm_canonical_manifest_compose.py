import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_canonical_manifest_compose import CanonicalComposeError, _asset_image, build


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "_forge_data" / "dlm_canonical_liveries" / "waffle_side_family_v1.json"


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    output = tmp_path_factory.mktemp("canonical_compose")
    return output, build(MANIFEST, output)


def test_exact_side_family_projector_is_filled_without_ownership_overlap(compiled):
    _, result = compiled
    metrics = result["report"]["metrics"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    index_path = (MANIFEST.parent / manifest["sources"]["uv_index"]["path"]).resolve()
    expected_authority = int(np.count_nonzero(np.asarray(Image.open(index_path).convert("L"))))
    assert metrics["projected_surface_count"] == 8
    assert metrics["projector_authority_pixel_count"] == expected_authority
    assert metrics["painted_projector_pixel_count"] == expected_authority
    assert metrics["projector_fill_fraction"] == 1.0


def test_paired_readable_assets_are_distinct_physical_instances(compiled):
    _, result = compiled
    rows = result["report"]["operations"]
    number_rows = [row for row in rows if row.get("paired_family_id") == "paired_side_number"]
    wordmark_rows = [row for row in rows if row.get("paired_family_id") == "paired_side_wordmark"]
    assert len(number_rows) == 2
    assert len(wordmark_rows) == 2
    assert len({row["instance_id"] for row in number_rows + wordmark_rows}) == 4
    assert all(row["projected_canonical_pixels"] > 0 for row in number_rows + wordmark_rows)


def test_semantic_layers_remain_separate_and_visibly_populated(compiled):
    output, result = compiled
    assert result["report"]["metrics"]["semantic_nonempty_layer_count"] == 5
    for name in ("Base", "Paint", "Numbers", "Sponsors", "Rear"):
        alpha = np.asarray(Image.open(output / "uv_layers" / f"{name}.png").convert("RGBA"))[..., 3]
        assert np.count_nonzero(alpha) > 0


def test_partial_candidate_claims_fail_closed(compiled):
    _, result = compiled
    claims = result["report"]["claims"]
    assert claims["canonical_side_family_candidate"] is True
    assert all(claims[key] is False for key in ("full_dlm", "physical_readable_direction", "iracing", "psd", "delivery", "accuracy_95"))


def test_hash_bound_manifest_rejects_source_drift(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for group in ("sources", "assets"):
        for row in manifest[group].values():
            source = Path(row["path"])
            if not source.is_absolute():
                row["path"] = str((MANIFEST.parent / source).resolve())
    manifest["sources"]["wire"]["sha256"] = "0" * 64
    path = tmp_path / "bad_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CanonicalComposeError, match="source_hash_drift:wire"):
        build(path, tmp_path / "out")


def test_reusable_composer_contains_no_scheme_identity_branch():
    source = (ROOT / "_forge_dlm_canonical_manifest_compose.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor ==", "filename =="):
        assert forbidden not in source


def test_contain_fit_enlarges_tight_semantic_asset_to_canonical_slot(tmp_path):
    asset = Image.new("RGBA", (20, 10), (225, 30, 15, 255))
    path = tmp_path / "tight_panel.png"
    asset.save(path)
    fitted = _asset_image(path, None, [100, 200, 300, 300], "contain", 0, None)
    assert fitted.getchannel("A").getbbox() == (100, 200, 300, 300)


def test_report_exposes_base_independent_semantic_coverage(compiled):
    _, result = compiled
    metrics = result["report"]["metrics"]
    coverage = metrics["semantic_foreground_fraction_by_surface"]
    assert set(coverage) == {
        "left_a_post", "left_quarter_window", "left_side", "left_spoiler_side",
        "right_a_post", "right_quarter_window", "right_side", "right_spoiler_side",
    }
    assert all(0.0 <= value <= 1.0 for value in coverage.values())
