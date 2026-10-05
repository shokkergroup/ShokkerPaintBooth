from pathlib import Path

from PIL import Image

import _forge_semantic as semantic


def test_surface_inference_uses_dossier_overlap_not_car_identity() -> None:
    graphic = {"bbox": [0, 722, 655, 155]}
    truth = {
        "left_strip": [0, 142.5, 655, 357.5],
        "right_strip": [0, 722.5, 655, 877.5],
    }

    surface, confidence, evidence, abstentions = semantic._infer_surface(graphic, truth)

    assert surface == "right_strip"
    assert confidence > 0.9
    assert "placement coverage" in evidence
    assert abstentions == []


def test_role_inference_prioritizes_semantics_then_generic_tokens() -> None:
    features = {"alpha_coverage": 0.02}
    assert semantic._infer_role({"semantic": {"role": "decal"}}, "band_right", features)[0] == "decal"
    assert semantic._infer_role({}, "number_door_right", features)[0] == "number"
    assert semantic._infer_role({}, "band_right", features)[0] == "paint_shape"
    assert semantic._infer_role({}, "primary_logo", features)[0] == "decal"
    assert semantic._infer_role({"zone": "spoiler_lower_sponsor_strip"}, "face", features)[0] == "decal"


def test_sparse_unknown_asset_becomes_decal_without_brand_allowlist() -> None:
    role, confidence, evidence, abstentions = semantic._infer_role(
        {}, "totally_unseen_company", {"alpha_coverage": 0.04}
    )

    assert role == "decal"
    assert confidence >= 0.7
    assert "sparse alpha" in evidence
    assert abstentions == []


def test_unmapped_region_abstains_instead_of_guessing() -> None:
    surface, confidence, _, abstentions = semantic._infer_surface(
        {"bbox": [0, 0, 20, 20]}, {"roof": [500, 500, 700, 700]}
    )

    assert surface == "unmapped_template_island"
    assert confidence < 0.5
    assert abstentions == ["surface"]


def test_asset_features_measure_real_alpha_density(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "asset.png"
    image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    for x in range(2):
        for y in range(5):
            image.putpixel((x, y), (255, 255, 255, 255))
    image.save(path)

    features = semantic._asset_features(path)

    assert features["alpha_coverage"] == 0.1
    assert features["opaque_coverage"] == 0.1


def test_mirror_policy_preserves_readable_content() -> None:
    assert semantic._mirror_policy("number", "left", True) == "preserve_readability"
    assert semantic._mirror_policy("decal", "right", True) == "preserve_readability"
    assert semantic._mirror_policy("paint_shape", "left", True) == "authored_left_right_pair"


def test_review_sheet_writes_visual_manifest(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    asset = tmp_path / "logo.png"
    Image.new("RGBA", (20, 10), (255, 255, 255, 255)).save(asset)
    manifest = {
        "source": {"brief": "demo.json"},
        "summary": {"abstaining_elements": 0},
        "elements": [
            {
                "asset": {"path": "logo.png"},
                "role": "decal",
                "surface": "right_strip",
                "side": "right",
                "psd_group": "40 SPONSORS & BRAND MARKS",
                "confidence": 0.9,
                "abstentions": [],
            }
        ],
    }
    destination = tmp_path / "sheet.png"

    semantic.build_review_sheet(manifest, root=tmp_path, destination=destination)

    assert destination.exists()
    with Image.open(destination) as result:
        assert result.width > 1000
        assert result.height > 200


def test_manifest_contract_accepts_explicit_abstention_and_rejects_silent_guess() -> None:
    base = {
        "id": "mystery",
        "asset": {},
        "role": "unknown",
        "surface": "unmapped_template_island",
        "side": "unknown",
        "mirror_policy": "none",
        "psd_group": semantic.PSD_GROUPS["unknown"],
        "placement": {},
        "abstentions": ["role", "surface", "side"],
    }

    assert semantic.validate_manifest({"elements": [base]}) == []
    invalid = {**base, "abstentions": []}
    violations = semantic.validate_manifest({"elements": [invalid]})
    assert len(violations) == 3
