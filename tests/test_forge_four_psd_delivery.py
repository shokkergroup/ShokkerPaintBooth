import inspect
import json
from pathlib import Path

import pytest

import _forge_four_psd_delivery as delivery
import _forge_source_purity as source_purity


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "_forge_out/codex_four_psd_delivery/delivery_manifest_v1.json"


def test_reusable_compiler_contains_no_scheme_identity_literals():
    source = inspect.getsource(delivery).lower()
    for forbidden in ("waffle", "domino", "sex wax", "crystal lake", "miller", "mountain dew"):
        assert forbidden not in source


def test_config_has_four_unique_livery_data_cases():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cases = config["cases"]
    assert len(cases) == 4
    assert len({row["case_id"] for row in cases}) == 4
    assert len({row["slug"] for row in cases}) == 4


def test_each_case_resolves_nine_disjoint_direct_surfaces():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for case in config["cases"]:
        rows = delivery.collect_surface_layers(ROOT, config, case["case_id"])
        names = [row["surface"] for row in rows]
        assert len(rows) == 9
        assert len(names) == len(set(names))
        assert {"left_strip", "right_strip", "hood", "roof", "rear_deck_lid", "spoiler_outside", "nose"} <= set(names)


def test_inventories_have_direct_five_view_and_editable_helper_sources():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    roles = ("left_profile", "right_profile", "top_view", "front_view", "rear_view", "number_sheet", "brand_sheet")
    for case in config["cases"]:
        inventory = json.loads((ROOT / case["inventory"]).read_text(encoding="utf-8"))
        for role in roles:
            assert delivery._reference_source(inventory, role).exists()


def test_config_file_stems_are_safe_and_unique():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    stems = [row["file_stem"] for row in config["cases"]]
    assert len(stems) == len(set(stems))
    assert all(stem and stem.upper() == stem and " " not in stem for stem in stems)


def test_compiler_requires_versioned_unpromoted_candidate_label(tmp_path: Path):
    with pytest.raises(ValueError, match="snapshot_label is required"):
        delivery.compile_delivery(CONFIG, tmp_path, ROOT)
    source = inspect.getsource(delivery.compile_case)
    assert '/ "CURRENT_BEST"' not in source
    assert '"promoted": False' in source

def test_semantic_sheet_components_are_extracted_without_livery_rules():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for case in config["cases"]:
        inventory = json.loads((ROOT / case["inventory"]).read_text(encoding="utf-8"))
        for role in ("number_sheet", "brand_sheet"):
            accepted, rejected = delivery.extract_semantic_components(delivery._reference_source(inventory, role))
            assert accepted
            assert all(row["image"].mode == "RGBA" and row["image"].getchannel("A").getbbox() for row in accepted)
            assert all("image" not in row for row in rejected)


def test_same_line_component_clustering_preserves_separate_rows():
    from PIL import Image

    rows = [
        {"bbox": [10, 10, 30, 40], "area_pixels": 500, "area_fraction": 0.01, "image": Image.new("RGBA", (20, 30), "white")},
        {"bbox": [35, 12, 55, 40], "area_pixels": 450, "area_fraction": 0.01, "image": Image.new("RGBA", (20, 28), "white")},
        {"bbox": [12, 80, 54, 110], "area_pixels": 900, "area_fraction": 0.02, "image": Image.new("RGBA", (42, 30), "white")},
    ]
    clusters = delivery.cluster_semantic_components(rows, 1000)
    assert len(clusters) == 2
    assert sorted(row.get("source_component_count", 1) for row in clusters) == [1, 2]


def test_all_four_cases_pass_physical_integrity_contract():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    adapter = json.loads((ROOT / config["template_adapter"]).read_text(encoding="utf-8"))
    for case in config["cases"]:
        rows = delivery.collect_surface_layers(ROOT, config, case["case_id"])
        proof = delivery.physical_integrity_contract(rows, adapter, config["required_direct_surfaces"])
        assert proof["valid"], proof["issues"]
        assert proof["left_right_direct_sources_distinct"]
        assert proof["unique_physical_instance_count"] == 9
        assert proof["unique_visible_layer_hash_count"] == 9
        assert proof["partial_surfaces"] == ["nose"]


def test_revoked_delivery_config_fails_closed_on_assembled_vehicle_pixels():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for case in config["cases"]:
        inventory = json.loads((ROOT / case["inventory"]).read_text(encoding="utf-8"))
        proof = source_purity.evaluate_config(ROOT, config, inventory)
        assert not proof["valid"]
        codes = {issue["code"] for audit in proof["audits"] for issue in audit["issues"]}
        assert "audit_not_promoted" in codes
        assert "assembled_vehicle_pixels_forbidden" in codes


def test_paint_only_segmented_source_can_be_delivery_authority():
    digest = "a" * 64
    inventory = {"sources": [{"sha256": digest, "evidence_scope": "direct_physical_view"}]}
    audit = {
        "cases": [
            {
                "records": [
                    {
                        "surface": "surface_a",
                        "source_sha256": digest,
                        "paint_only_segmentation": {
                            "valid": True,
                            "mask_sha256": "b" * 64,
                            "foreground_scope": "paint_only",
                        },
                    }
                ]
            }
        ]
    }
    proof = source_purity.evaluate_audit(audit, inventory)
    assert proof["valid"], proof["issues"]


def test_unknown_texture_source_scope_is_rejected():
    audit = {"cases": [{"record": {"surface": "surface_a", "source_sha256": "c" * 64}}]}
    proof = source_purity.evaluate_audit(audit, {"sources": []})
    assert not proof["valid"]
    assert proof["issues"][0]["code"] == "unproved_texture_source_scope"
