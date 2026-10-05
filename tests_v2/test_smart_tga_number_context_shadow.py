from types import SimpleNamespace

from engine.spec_sculpt.number_context_shadow import number_context_shadow_telemetry


def test_context_shadow_generates_zero_authority_proposals():
    instances = [SimpleNamespace(instance_id="di:seed", bbox=(100, 100, 20, 40))]
    features = [SimpleNamespace(
        instance_id="di:seed", area_fraction=0.001, fill_ratio=0.5,
        edge_density=0.1, texture_entropy=0.2, strong_gradient_fraction=0.1,
        perceptual_lightness=0.5, perceptual_chroma=0.2,
        ocr_alpha_coverage=0.0, ocr_digit_coverage=0.0, ocr_max_coverage=0.0,
    )]
    result = number_context_shadow_telemetry(instances, features, export_full=True)
    assert result["model_version"] == "cycle696-dlm-context-envelope-v1"
    assert result["seed_count"] == 1
    assert result["proposal_count"] > 0
    assert result["casts_votes"] is False
    assert result["ownership_authority"] is False
    assert result["adds_pixels"] is False
    assert all(item["seed_instance_id"] == "di:seed" for item in result["proposal_records"])
    assert all(item["source_crop_bbox"] == item["bbox"] for item in result["proposal_records"])
