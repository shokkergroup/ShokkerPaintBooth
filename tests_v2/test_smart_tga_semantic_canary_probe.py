from scripts.smart_tga_semantic_canary_probe import evaluate_independent_canary


def _bank(prefix, paint_count):
    rows = []
    for paint in range(paint_count):
        for index, owner in enumerate(("numbers", "sponsors", "template", "paint")):
            for sample in range(3):
                rows.append({
                    "paint_label": f"{prefix}-{paint}", "object_id": f"{prefix}-{paint}-{owner}-{sample}",
                    "review_target_layer": owner, "object_kind": "singleton",
                    "member_count": 1, "area_fraction": 0.001 + index * 0.01,
                    "bbox_fraction": 0.002 + index * 0.01, "fill_ratio": 0.2 + index * 0.2,
                    "aspect_ratio": 0.5 + index, "mean_edge_density": index * 0.2,
                    "shape_occupancy": [index / 3.0] * 16,
                })
    return {"reviewed_objects": rows}


def test_independent_canary_never_fits_canary_paints_and_has_no_authority():
    report = evaluate_independent_canary(_bank("train", 5), _bank("canary", 8), min_score=0, min_margin=0)
    assert report["train_paint_count"] == 5
    assert report["canary_paint_count"] == 8
    assert report["paint_leakage_count"] == 0
    assert report["independent_canary"] is True
    assert report["casts_votes"] is False
    assert report["ownership_authority"] is False


def test_independent_canary_rejects_paint_leakage():
    bank = _bank("same", 4)
    try:
        evaluate_independent_canary(bank, bank)
    except ValueError as exc:
        assert "canary paint leakage" in str(exc)
    else:
        raise AssertionError("paint leakage must be rejected")


def test_intrinsic_canary_rejects_mismatched_training_schema():
    canary = _bank("canary", 8)
    for row in canary["reviewed_objects"]:
        row.update({
            "mean_strong_gradient_fraction": 0.1, "max_strong_gradient_fraction": 0.2,
            "max_ocr_alpha_coverage": 0.0, "max_ocr_token_count": 0,
            "mean_perceptual_lightness": 0.5, "mean_perceptual_chroma": 0.1,
        })
    try:
        evaluate_independent_canary(_bank("train", 5), canary, feature_set="intrinsic")
    except ValueError as exc:
        assert "training bank missing requested intrinsic feature schema" in str(exc)
    else:
        raise AssertionError("canary must reject mismatched feature schemas")
