import base64
import io

import numpy as np
from PIL import Image
import pytest


def _data_url_mask(data_url):
    _, encoded = data_url.split(",", 1)
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(encoded))).convert("L"))


def test_auto_layers_route_prefers_selected_car_folder_hint_for_loose_paint_files(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 32
    rgb_float = np.full((n, n, 3), np.array([0.2, 0.2, 0.2], np.float32), np.float32)
    empty = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    template[4:8, 4:12] = 255
    captured = {}

    paint_path = tmp_path / "loose_examples" / "1-Francis2001.tga"
    paint_path.parent.mkdir(parents=True)
    Image.fromarray(np.full((4, 4, 3), 42, np.uint8), "RGB").save(paint_path)

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
            "_ocr_regions": [{
                "id": "gpu-word-0",
                "kind": "sponsor",
                "orientation": "multi_rotation",
                "mirrored": False,
                "bbox": [8, 8, 16, 10],
            }],
        }

    def fake_hint_from_path(path):
        text = str(path).replace("\\", "/").lower()
        if "superlatemodel" in text:
            return "superlatemodel", "dirt_oval"
        if "loose_examples" in text:
            return "wrong_loose_examples", None
        return None, None

    def fake_folder_slug_from_path(path):
        text = str(path).replace("\\", "/").lower()
        if "superlatemodel" in text:
            return "superlatemodel"
        if "loose_examples" in text:
            return "loose_examples"
        return None

    def fake_separate_into_layers(*_args, **kwargs):
        captured.update(kwargs)
        use_template = kwargs.get("car_slug") == "superlatemodel"
        return {
            "success": True,
            "car": [{"slug": kwargs.get("car_slug"), "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": template.copy() if use_template else empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {
                "status": "applied" if use_template else "blocked",
                "matched_slug": kwargs.get("car_slug"),
                "source_slug": kwargs.get("source_slug_hint"),
            },
        }

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "hint_from_path", fake_hint_from_path)
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", fake_folder_slug_from_path)
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={
            "paint_file": str(paint_path),
            "paint_file_hint": str(paint_path),
            "car_folder_hint": r"C:\Users\Ricky's PC\Documents\iRacing\paint\superlatemodel",
            "preview_size": n,
        },
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert captured["car_slug"] == "superlatemodel"
    assert captured["source_slug_hint"] == "superlatemodel"
    assert body["template_guard"]["status"] == "applied"
    assert body["template_guard"]["matched_slug"] == "superlatemodel"
    assert _data_url_mask(body["layers"]["template"])[4:8, 4:12].min() == 255


@pytest.mark.parametrize("adjudicator_mode", ["off", "shadow"])
def test_auto_layers_route_keeps_blank_base_paint_as_paint_only(tmp_path, monkeypatch, adjudicator_mode):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.full((n, n, 3), np.array([0.18, 0.18, 0.19], np.float32), np.float32)
    empty = np.zeros((n, n), np.uint8)
    full_paint = np.full((n, n), 255, np.uint8)
    monkeypatch.setenv("SPB_SMART_TGA_ADJUDICATOR_MODE", adjudicator_mode)

    paint_path = tmp_path / "blank_base_contract.png"
    Image.fromarray(np.full((8, 8, 3), [46, 46, 48], np.uint8), "RGB").save(paint_path)

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
            "_ocr_regions": [{
                "id": "gpu-word-0",
                "kind": "sponsor",
                "orientation": "multi_rotation",
                "mirrored": False,
                "bbox": [8, 8, 16, 10],
            }],
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "blank_base_contract", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": full_paint.copy(),
            },
            "template_guard": {"status": "empty"},
        }

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert body["smart_tga"]["route"] == "api_auto_layers"
    assert body["smart_tga"]["build"].startswith("smart-tga-cycle")
    assert body["adjudicator_shadow"]["status"] == adjudicator_mode
    assert body["adjudicator_shadow"]["output_applied"] is False
    if adjudicator_mode == "shadow":
        assert body["adjudicator_shadow"]["ocr_member_node_count"] == 1
        assert body["adjudicator_shadow"]["ocr_membership_count"] == 1

    numbers_mask = _data_url_mask(body["layers"]["numbers"])
    sponsors_mask = _data_url_mask(body["layers"]["sponsors"])
    template_mask = _data_url_mask(body["layers"]["template"])
    brand_mask = _data_url_mask(body["layers"]["brand_graphics"])
    paint_mask = _data_url_mask(body["layers"]["paint"])

    assert numbers_mask.max() == 0
    assert sponsors_mask.max() == 0
    assert template_mask.max() == 0
    assert brand_mask.max() == 0
    assert paint_mask.min() == 255


def test_auto_layers_route_uses_shared_number_trim_helper_after_response_cleanup(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.zeros((n, n, 3), np.float32)
    rgb_float[:, :] = np.array([0.02, 0.03, 0.04], np.float32)

    paint_path = tmp_path / "route_helper_contract.png"
    Image.fromarray(np.full((4, 4, 3), 12, np.uint8), "RGB").save(paint_path)

    empty = np.zeros((n, n), np.uint8)
    gpu_numbers = np.zeros((n, n), np.uint8)
    gpu_numbers[28:36, 28:36] = 255

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": gpu_numbers.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "route_helper_contract", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {"status": "empty"},
        }

    def empty_guard(*_args, **_kwargs):
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    helper_calls = []

    def fake_apply_number_trim(rgb, numbers, sponsors, template, brand, existing_guard=None, accum_mask=None, phase=""):
        helper_calls.append(phase)
        if accum_mask is None:
            accum_mask = np.zeros_like(numbers, dtype=np.uint8)
        if phase != "post_response_badge_cleanup":
            guard = {"status": "empty", "component_count": 0, "components": [], "phase": phase}
            return guard, accum_mask, False
        trim = np.zeros_like(numbers, dtype=np.uint8)
        trim[30:32, 40:42] = 255
        numbers[trim > 0] = 255
        sponsors[trim > 0] = 0
        template[trim > 0] = 0
        brand[trim > 0] = 0
        accum_mask = np.maximum(accum_mask, trim)
        guard = {
            "status": "applied",
            "component_count": 1,
            "candidate_count": 1,
            "added_px": int((trim > 0).sum()),
            "added_frac": round(float((trim > 0).sum()) / float(n * n), 6),
            "capped": False,
            "passes": ["post_response_badge_cleanup"],
            "components": [
                {
                    "bbox": [40, 30, 2, 2],
                    "area": int((trim > 0).sum()),
                    "phase": "post_response_badge_cleanup",
                    "reason": "route_shared_helper_contract",
                }
            ],
        }
        return guard, accum_mask, True

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    route_helper_names = [
        "_sponsor_fragment_supplement",
        "_isolated_wordmark_supplement",
        "_tiny_logotype_residual_supplement",
        "_micro_logotype_residual_supplement",
        "_colored_micro_logo_residual_supplement",
        "_bright_panel_micro_logo_residual_supplement",
        "_panel_text_residual_supplement",
        "_stacked_front_clip_template_supplement",
        "_horizontal_front_clip_template_supplement",
        "_paired_rear_lamp_template_supplement",
        "_template_contained_paint_trim_supplement",
        "_faint_number_outline_supplement",
        "_flat_livery_sponsor_to_paint",
        "_warm_edge_livery_sponsor_to_paint",
        "_vertical_livery_stripe_sponsor_to_paint",
        "_solid_warm_livery_sponsor_to_paint",
        "_diagonal_warm_livery_slash_sponsor_to_paint",
        "_decorative_livery_sponsor_to_paint",
        "_large_red_livery_sponsor_to_paint",
        "_smooth_red_body_panel_sponsor_to_paint",
        "_small_flat_red_livery_sponsor_to_paint",
        "_red_orange_livery_block_sponsor_to_paint",
        "_warm_livery_arc_sponsor_to_paint",
        "_geometric_livery_sponsor_to_paint",
        "_pale_body_panel_sponsor_to_paint",
        "_dark_body_panel_sponsor_to_paint",
        "_white_livery_sponsor_to_paint",
        "_tiny_dark_sponsor_speck_to_paint",
        "_number_logo_false_positive_to_sponsor",
        "_multicolor_logo_false_positive_to_sponsor",
        "_green_white_logo_false_positive_to_sponsor",
        "_large_green_logo_false_positive_to_sponsor",
        "_white_livery_number_panel_to_paint",
        "_small_sponsor_panel_false_positive_to_sponsor",
        "_thin_textline_number_false_positive_to_sponsor",
        "_red_single_digit_number_supplement",
        "_red_two_digit_number_supplement",
        "_number_badge_graphic_supplement",
        "_round_badge_number_supplement",
        "_yellow_panel_number_supplement",
        "_pale_sponsor_panel_number_supplement",
        "_round_number_badge_interior_to_paint",
        "_round_number_badge_number_crumb_to_paint",
        "_round_number_badge_sponsor_crumb_to_number",
    ]
    for name in route_helper_names:
        monkeypatch.setattr(car_layers_mod, name, empty_guard)
    monkeypatch.setattr(car_layers_mod, "_apply_number_trim_supplement", fake_apply_number_trim)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert "post_response_badge_cleanup" in helper_calls
    assert body["number_trim_fragment_guard"]["status"] == "applied"
    assert body["number_trim_fragment_guard"]["passes"] == ["post_response_badge_cleanup"]
    assert body["number_trim_fragment_guard"]["components"][0]["reason"] == "route_shared_helper_contract"

    numbers_mask = _data_url_mask(body["layers"]["numbers"])
    paint_mask = _data_url_mask(body["layers"]["paint"])
    assert numbers_mask[30:32, 40:42].min() == 255
    assert paint_mask[30:32, 40:42].max() == 0


def test_auto_layers_route_reruns_panel_residual_after_final_response_masks(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.zeros((n, n, 3), np.float32)
    rgb_float[:, :] = np.array([0.02, 0.03, 0.04], np.float32)

    paint_path = tmp_path / "route_panel_residual_contract.png"
    Image.fromarray(np.full((4, 4, 3), 12, np.uint8), "RGB").save(paint_path)

    empty = np.zeros((n, n), np.uint8)
    gpu_sponsors = np.zeros((n, n), np.uint8)
    gpu_sponsors[16:24, 16:32] = 255

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": gpu_sponsors.copy(),
            "logos": empty.copy(),
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "route_panel_residual_contract", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {"status": "empty"},
        }

    def empty_guard(*_args, **_kwargs):
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    def empty_trim(rgb, numbers, sponsors, template, brand, existing_guard=None, accum_mask=None, phase=""):
        if accum_mask is None:
            accum_mask = np.zeros_like(numbers, dtype=np.uint8)
        return {"status": "empty", "component_count": 0, "components": [], "phase": phase}, accum_mask, False

    panel_calls = []

    def fake_panel_text_residual(_rgb, _numbers, _sponsors, _template, _brand):
        panel_calls.append(len(panel_calls) + 1)
        mask = np.zeros((n, n), np.uint8)
        if len(panel_calls) == 1:
            mask[8:10, 8:12] = 255
            bbox = [8, 8, 4, 2]
            phase_hint = "initial_panel_residual"
        elif len(panel_calls) == 2:
            mask[30:34, 40:43] = 255
            bbox = [40, 30, 3, 4]
            phase_hint = "final_response_panel_residual"
        elif len(panel_calls) == 3:
            mask[44:46, 20:25] = 255
            bbox = [20, 44, 5, 2]
            phase_hint = "final_response_panel_residual_followup"
        elif len(panel_calls) == 4:
            mask[50:52, 20:25] = 255
            bbox = [20, 50, 5, 2]
            phase_hint = "post_white_livery_number_panel_residual"
        else:
            mask[56:58, 20:25] = 255
            bbox = [20, 56, 5, 2]
            phase_hint = "pre_response_materialization_panel_residual"
        px = int((mask > 0).sum())
        return mask, {
            "status": "applied",
            "added_frac": round(float(px) / float(n * n), 6),
            "component_count": 1,
            "candidate_count": 1,
            "bucket_counts": {"sponsor_panel_dark_logo_fill": 1},
            "capped": False,
            "max_add": 0.003,
            "anchor_radius_px": 6,
            "components": [
                {
                    "bbox": bbox,
                    "area": px,
                    "bucket": "sponsor_panel_dark_logo_fill",
                    "reason": phase_hint,
                }
            ],
        }

    white_panel_calls = []
    white_panel_emitted = []

    def fake_white_livery_number_panel(_rgb, _numbers, _sponsors, _template, _brand):
        white_panel_calls.append(len(white_panel_calls) + 1)
        mask = np.zeros((n, n), np.uint8)
        if len(panel_calls) >= 3 and not white_panel_emitted:
            mask[50:52, 20:25] = 255
            white_panel_emitted.append(True)
        if not mask.any():
            return mask, {"status": "empty", "component_count": 0, "components": []}
        return mask, {
            "status": "applied",
            "demoted_frac": round(float((mask > 0).sum()) / float(n * n), 6),
            "demoted_px": int((mask > 0).sum()),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [20, 50, 5, 2],
                    "area": int((mask > 0).sum()),
                    "reason": "final_white_panel_exposes_residual",
                }
            ],
        }

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    route_helper_names = [
        "_sponsor_fragment_supplement",
        "_isolated_wordmark_supplement",
        "_tiny_logotype_residual_supplement",
        "_micro_logotype_residual_supplement",
        "_colored_micro_logo_residual_supplement",
        "_bright_panel_micro_logo_residual_supplement",
        "_stacked_front_clip_template_supplement",
        "_horizontal_front_clip_template_supplement",
        "_paired_rear_lamp_template_supplement",
        "_template_contained_paint_trim_supplement",
        "_faint_number_outline_supplement",
        "_flat_livery_sponsor_to_paint",
        "_warm_edge_livery_sponsor_to_paint",
        "_vertical_livery_stripe_sponsor_to_paint",
        "_solid_warm_livery_sponsor_to_paint",
        "_diagonal_warm_livery_slash_sponsor_to_paint",
        "_decorative_livery_sponsor_to_paint",
        "_large_red_livery_sponsor_to_paint",
        "_smooth_red_body_panel_sponsor_to_paint",
        "_small_flat_red_livery_sponsor_to_paint",
        "_red_orange_livery_block_sponsor_to_paint",
        "_warm_livery_arc_sponsor_to_paint",
        "_geometric_livery_sponsor_to_paint",
        "_pale_body_panel_sponsor_to_paint",
        "_dark_body_panel_sponsor_to_paint",
        "_white_livery_sponsor_to_paint",
        "_tiny_dark_sponsor_speck_to_paint",
        "_number_logo_false_positive_to_sponsor",
        "_multicolor_logo_false_positive_to_sponsor",
        "_green_white_logo_false_positive_to_sponsor",
        "_large_green_logo_false_positive_to_sponsor",
        "_white_livery_number_panel_to_paint",
        "_small_sponsor_panel_false_positive_to_sponsor",
        "_thin_textline_number_false_positive_to_sponsor",
        "_red_single_digit_number_supplement",
        "_red_two_digit_number_supplement",
        "_number_badge_graphic_supplement",
        "_round_badge_number_supplement",
        "_repeated_round_badge_number_supplement",
        "_yellow_panel_number_supplement",
        "_pale_sponsor_panel_number_supplement",
        "_round_number_badge_interior_to_paint",
        "_round_number_badge_number_crumb_to_paint",
        "_round_number_badge_sponsor_crumb_to_number",
    ]
    for name in route_helper_names:
        monkeypatch.setattr(car_layers_mod, name, empty_guard)
    monkeypatch.setattr(car_layers_mod, "_panel_text_residual_supplement", fake_panel_text_residual)
    monkeypatch.setattr(car_layers_mod, "_white_livery_number_panel_to_paint", fake_white_livery_number_panel)
    monkeypatch.setattr(car_layers_mod, "_apply_number_trim_supplement", empty_trim)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert panel_calls == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert white_panel_emitted
    guard = body["panel_text_residual_guard"]
    assert guard["status"] == "applied"
    assert "post_response_final_mask_cleanup" in guard["passes"]
    assert "post_response_final_mask_cleanup_followup" in guard["passes"]
    assert "post_response_white_livery_number_panel_cleanup" in guard["passes"]
    assert "pre_response_materialization" in guard["passes"]
    assert "post_response_layer_boundary" in guard["passes"]
    assert "pre_png_emission" in guard["passes"]
    assert "post_png_number_trim" in guard["passes"]
    assert "post_png_number_logo_cleanup" in guard["passes"]
    assert "pre_png_emission_after_livery_demoters" in guard["passes"]
    assert "pre_png_final_textline_completion" in guard["passes"]
    assert guard["bucket_counts"]["sponsor_panel_dark_logo_fill"] == 11
    assert guard["components"][1]["phase"] == "post_response_final_mask_cleanup"
    assert guard["components"][2]["phase"] == "post_response_final_mask_cleanup_followup"
    assert guard["components"][3]["phase"] == "post_response_white_livery_number_panel_cleanup"
    assert guard["components"][4]["phase"] == "pre_response_materialization"
    assert guard["components"][5]["phase"] == "post_response_layer_boundary"
    assert guard["components"][6]["phase"] == "pre_png_emission"
    assert guard["components"][7]["phase"] == "post_png_number_trim"
    assert guard["components"][8]["phase"] == "post_png_number_logo_cleanup"
    assert guard["components"][9]["phase"] == "pre_png_emission_after_livery_demoters"
    assert guard["components"][10]["phase"] == "pre_png_final_textline_completion"

    sponsors_mask = _data_url_mask(body["layers"]["sponsors"])
    paint_mask = _data_url_mask(body["layers"]["paint"])
    assert sponsors_mask[30:34, 40:43].min() == 255
    assert sponsors_mask[44:46, 20:25].min() == 255
    assert sponsors_mask[50:52, 20:25].min() == 255
    assert sponsors_mask[56:58, 20:25].min() == 255
    assert paint_mask[30:34, 40:43].max() == 0
    assert paint_mask[44:46, 20:25].max() == 0
    assert paint_mask[50:52, 20:25].max() == 0
    assert paint_mask[56:58, 20:25].max() == 0


def test_auto_layers_route_reruns_smooth_red_before_response_materialization(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.zeros((n, n, 3), np.float32)
    rgb_float[:, :] = np.array([0.50, 0.02, 0.03], np.float32)

    paint_path = tmp_path / "route_smooth_red_materialization_contract.png"
    Image.fromarray(np.full((4, 4, 3), [128, 5, 8], np.uint8), "RGB").save(paint_path)

    empty = np.zeros((n, n), np.uint8)
    late_tile = np.zeros((n, n), np.uint8)
    late_tile[42:48, 20:30] = 255

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "route_smooth_red_materialization_contract", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {"status": "empty"},
        }

    def empty_guard(*_args, **_kwargs):
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    def empty_trim(rgb, numbers, sponsors, template, brand, existing_guard=None, accum_mask=None, phase=""):
        if accum_mask is None:
            accum_mask = np.zeros_like(numbers, dtype=np.uint8)
        return {"status": "empty", "component_count": 0, "components": [], "phase": phase}, accum_mask, False

    panel_calls = []
    panel_emitted = []

    def fake_panel_text_residual(_rgb, _numbers, _sponsors, _template, _brand):
        panel_calls.append(len(panel_calls) + 1)
        if len(panel_calls) < 3 or panel_emitted:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        panel_emitted.append(True)
        return late_tile.copy(), {
            "status": "applied",
            "added_frac": round(float((late_tile > 0).sum()) / float(n * n), 6),
            "component_count": 1,
            "candidate_count": 1,
            "bucket_counts": {"sponsor_panel_red_logo_cap": 1},
            "capped": False,
            "max_add": 0.003,
            "anchor_radius_px": 6,
            "components": [
                {
                    "bbox": [20, 42, 10, 6],
                    "area": int((late_tile > 0).sum()),
                    "bucket": "sponsor_panel_red_logo_cap",
                    "reason": "late_sponsor_recovery_exposes_red_livery_tile",
                }
            ],
        }

    smooth_calls = []

    def fake_smooth_red_body_panel(_rgb, _sponsors, _numbers, _template, _brand):
        smooth_calls.append(int((_sponsors > 0).sum()))
        if int((_sponsors > 0).sum()) == 0:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        return late_tile.copy(), {
            "status": "applied",
            "demoted_frac": round(float((late_tile > 0).sum()) / float(n * n), 6),
            "demoted_px": int((late_tile > 0).sum()),
            "component_count": 1,
            "candidate_count": 1,
            "capped": False,
            "components": [
                {
                    "bbox": [20, 42, 10, 6],
                    "area": int((late_tile > 0).sum()),
                    "reason": "late_smooth_red_materialization_contract",
                }
            ],
        }

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    route_helper_names = [
        "_sponsor_fragment_supplement",
        "_isolated_wordmark_supplement",
        "_tiny_logotype_residual_supplement",
        "_micro_logotype_residual_supplement",
        "_colored_micro_logo_residual_supplement",
        "_bright_panel_micro_logo_residual_supplement",
        "_stacked_front_clip_template_supplement",
        "_horizontal_front_clip_template_supplement",
        "_paired_rear_lamp_template_supplement",
        "_template_contained_paint_trim_supplement",
        "_faint_number_outline_supplement",
        "_flat_livery_sponsor_to_paint",
        "_warm_edge_livery_sponsor_to_paint",
        "_vertical_livery_stripe_sponsor_to_paint",
        "_solid_warm_livery_sponsor_to_paint",
        "_diagonal_warm_livery_slash_sponsor_to_paint",
        "_decorative_livery_sponsor_to_paint",
        "_large_red_livery_sponsor_to_paint",
        "_smooth_red_body_panel_sponsor_to_paint",
        "_small_flat_red_livery_sponsor_to_paint",
        "_red_orange_livery_block_sponsor_to_paint",
        "_warm_livery_arc_sponsor_to_paint",
        "_geometric_livery_sponsor_to_paint",
        "_pale_body_panel_sponsor_to_paint",
        "_dark_body_panel_sponsor_to_paint",
        "_white_livery_sponsor_to_paint",
        "_tiny_dark_sponsor_speck_to_paint",
        "_number_logo_false_positive_to_sponsor",
        "_multicolor_logo_false_positive_to_sponsor",
        "_green_white_logo_false_positive_to_sponsor",
        "_large_green_logo_false_positive_to_sponsor",
        "_white_livery_number_panel_to_paint",
        "_small_sponsor_panel_false_positive_to_sponsor",
        "_thin_textline_number_false_positive_to_sponsor",
        "_red_single_digit_number_supplement",
        "_red_two_digit_number_supplement",
        "_number_badge_graphic_supplement",
        "_round_badge_number_supplement",
        "_repeated_round_badge_number_supplement",
        "_yellow_panel_number_supplement",
        "_pale_sponsor_panel_number_supplement",
        "_round_number_badge_interior_to_paint",
        "_round_number_badge_number_crumb_to_paint",
        "_round_number_badge_sponsor_crumb_to_number",
    ]
    for name in route_helper_names:
        monkeypatch.setattr(car_layers_mod, name, empty_guard)
    monkeypatch.setattr(car_layers_mod, "_panel_text_residual_supplement", fake_panel_text_residual)
    monkeypatch.setattr(car_layers_mod, "_smooth_red_body_panel_sponsor_to_paint", fake_smooth_red_body_panel)
    monkeypatch.setattr(car_layers_mod, "_apply_number_trim_supplement", empty_trim)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert panel_emitted
    assert any(count > 0 for count in smooth_calls)

    guard = body["smooth_red_body_panel_sponsor_guard"]
    assert guard["status"] == "applied"
    assert "pre_response_materialization" in guard["passes"]
    assert guard["components"][0]["phase"] == "pre_response_materialization"

    sponsors_mask = _data_url_mask(body["layers"]["sponsors"])
    paint_mask = _data_url_mask(body["layers"]["paint"])
    assert sponsors_mask[42:48, 20:30].max() == 0
    assert paint_mask[42:48, 20:30].min() == 255


def test_auto_layers_route_reruns_decorative_livery_before_response_materialization(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.zeros((n, n, 3), np.float32)
    rgb_float[:, :] = np.array([0.26, 0.15, 0.07], np.float32)

    paint_path = tmp_path / "route_decorative_materialization_contract.png"
    Image.fromarray(np.full((4, 4, 3), [66, 38, 18], np.uint8), "RGB").save(paint_path)

    empty = np.zeros((n, n), np.uint8)
    late_fleck = np.zeros((n, n), np.uint8)
    late_fleck[42:48, 20:30] = 255

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "route_decorative_materialization_contract", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {"status": "empty"},
        }

    def empty_guard(*_args, **_kwargs):
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    def empty_trim(rgb, numbers, sponsors, template, brand, existing_guard=None, accum_mask=None, phase=""):
        if accum_mask is None:
            accum_mask = np.zeros_like(numbers, dtype=np.uint8)
        return {"status": "empty", "component_count": 0, "components": [], "phase": phase}, accum_mask, False

    panel_calls = []
    panel_emitted = []

    def fake_panel_text_residual(_rgb, _numbers, _sponsors, _template, _brand):
        panel_calls.append(len(panel_calls) + 1)
        if len(panel_calls) < 3 or panel_emitted:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        panel_emitted.append(True)
        return late_fleck.copy(), {
            "status": "applied",
            "added_frac": round(float((late_fleck > 0).sum()) / float(n * n), 6),
            "component_count": 1,
            "candidate_count": 1,
            "bucket_counts": {"materialization_sponsor_fleck": 1},
            "capped": False,
            "max_add": 0.003,
            "anchor_radius_px": 6,
            "components": [
                {
                    "bbox": [20, 42, 10, 6],
                    "area": int((late_fleck > 0).sum()),
                    "bucket": "materialization_sponsor_fleck",
                    "reason": "late_sponsor_recovery_exposes_decorative_livery_fleck",
                }
            ],
        }

    decorative_calls = []
    smooth_seen = []

    def fake_smooth_red_body_panel(_rgb, _sponsors, _numbers, _template, _brand):
        if int((_sponsors > 0).sum()) > 0:
            smooth_seen.append(True)
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    def fake_decorative_livery(_rgb, _sponsors, _numbers, _template, _brand):
        decorative_calls.append(int((_sponsors > 0).sum()))
        if int((_sponsors > 0).sum()) == 0 or not smooth_seen:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        return late_fleck.copy(), {
            "status": "applied",
            "demoted_frac": round(float((late_fleck > 0).sum()) / float(n * n), 6),
            "demoted_px": int((late_fleck > 0).sum()),
            "component_count": 1,
            "candidate_count": 1,
            "capped": False,
            "components": [
                {
                    "bbox": [20, 42, 10, 6],
                    "area": int((late_fleck > 0).sum()),
                    "reason": "late_decorative_materialization_contract",
                }
            ],
        }

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    route_helper_names = [
        "_sponsor_fragment_supplement",
        "_isolated_wordmark_supplement",
        "_tiny_logotype_residual_supplement",
        "_micro_logotype_residual_supplement",
        "_colored_micro_logo_residual_supplement",
        "_bright_panel_micro_logo_residual_supplement",
        "_stacked_front_clip_template_supplement",
        "_horizontal_front_clip_template_supplement",
        "_paired_rear_lamp_template_supplement",
        "_template_contained_paint_trim_supplement",
        "_faint_number_outline_supplement",
        "_flat_livery_sponsor_to_paint",
        "_warm_edge_livery_sponsor_to_paint",
        "_vertical_livery_stripe_sponsor_to_paint",
        "_solid_warm_livery_sponsor_to_paint",
        "_diagonal_warm_livery_slash_sponsor_to_paint",
        "_decorative_livery_sponsor_to_paint",
        "_large_red_livery_sponsor_to_paint",
        "_smooth_red_body_panel_sponsor_to_paint",
        "_small_flat_red_livery_sponsor_to_paint",
        "_red_orange_livery_block_sponsor_to_paint",
        "_warm_livery_arc_sponsor_to_paint",
        "_geometric_livery_sponsor_to_paint",
        "_pale_body_panel_sponsor_to_paint",
        "_dark_body_panel_sponsor_to_paint",
        "_white_livery_sponsor_to_paint",
        "_tiny_dark_sponsor_speck_to_paint",
        "_number_logo_false_positive_to_sponsor",
        "_multicolor_logo_false_positive_to_sponsor",
        "_green_white_logo_false_positive_to_sponsor",
        "_large_green_logo_false_positive_to_sponsor",
        "_white_livery_number_panel_to_paint",
        "_small_sponsor_panel_false_positive_to_sponsor",
        "_thin_textline_number_false_positive_to_sponsor",
        "_red_single_digit_number_supplement",
        "_red_two_digit_number_supplement",
        "_number_badge_graphic_supplement",
        "_round_badge_number_supplement",
        "_repeated_round_badge_number_supplement",
        "_yellow_panel_number_supplement",
        "_pale_sponsor_panel_number_supplement",
        "_round_number_badge_interior_to_paint",
        "_round_number_badge_number_crumb_to_paint",
        "_round_number_badge_sponsor_crumb_to_number",
    ]
    for name in route_helper_names:
        monkeypatch.setattr(car_layers_mod, name, empty_guard)
    monkeypatch.setattr(car_layers_mod, "_panel_text_residual_supplement", fake_panel_text_residual)
    monkeypatch.setattr(car_layers_mod, "_decorative_livery_sponsor_to_paint", fake_decorative_livery)
    monkeypatch.setattr(car_layers_mod, "_smooth_red_body_panel_sponsor_to_paint", fake_smooth_red_body_panel)
    monkeypatch.setattr(car_layers_mod, "_apply_number_trim_supplement", empty_trim)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert panel_emitted
    assert any(count > 0 for count in decorative_calls)

    guard = body["decorative_livery_sponsor_guard"]
    assert guard["status"] == "applied"
    assert "post_smooth_pre_response_materialization" in guard["passes"]
    assert guard["components"][0]["phase"] == "post_smooth_pre_response_materialization"

    sponsors_mask = _data_url_mask(body["layers"]["sponsors"])
    paint_mask = _data_url_mask(body["layers"]["paint"])
    assert sponsors_mask[42:48, 20:30].max() == 0
    assert paint_mask[42:48, 20:30].min() == 255


def test_auto_layers_route_replays_warm_edge_after_sponsor_fragment_recovery(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.full((n, n, 3), np.array([0.9, 0.75, 0.08], np.float32), np.float32)
    empty = np.zeros((n, n), np.uint8)
    late_trim = np.zeros((n, n), np.uint8)
    late_trim[4:44, 61:64] = 255

    paint_path = tmp_path / "route_warm_edge_replay_contract.png"
    Image.fromarray(np.full((4, 4, 3), [230, 190, 20], np.uint8), "RGB").save(paint_path)

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "route_warm_edge_replay_contract", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {"status": "empty"},
        }

    def empty_guard(*_args, **_kwargs):
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    def empty_trim(rgb, numbers, sponsors, template, brand, existing_guard=None, accum_mask=None, phase=""):
        if accum_mask is None:
            accum_mask = np.zeros_like(numbers, dtype=np.uint8)
        return {"status": "empty", "component_count": 0, "components": [], "phase": phase}, accum_mask, False

    def fake_sponsor_fragment(_rgb, _numbers, _sponsors, _template, _brand):
        return late_trim.copy(), {
            "status": "applied",
            "added_frac": round(float((late_trim > 0).sum()) / float(n * n), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [61, 4, 3, 40],
                    "area": int((late_trim > 0).sum()),
                    "reason": "late_edge_trim_sponsor_fragment",
                }
            ],
        }

    warm_calls = []

    def fake_warm_edge(_rgb, _sponsors, _numbers, _template, _brand):
        warm_calls.append(int((_sponsors > 0).sum()))
        if int((_sponsors > 0).sum()) == 0:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        return late_trim.copy(), {
            "status": "applied",
            "demoted_frac": round(float((late_trim > 0).sum()) / float(n * n), 6),
            "component_count": 1,
            "candidate_count": 1,
            "capped": False,
            "max_demote": 0.021,
            "components": [
                {
                    "bbox": [61, 4, 3, 40],
                    "area": int((late_trim > 0).sum()),
                    "reason": "route_post_sponsor_fragment_tall_warm_trim",
                }
            ],
        }

    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    route_helper_names = [
        "_sponsor_fragment_supplement",
        "_isolated_wordmark_supplement",
        "_tiny_logotype_residual_supplement",
        "_micro_logotype_residual_supplement",
        "_colored_micro_logo_residual_supplement",
        "_bright_panel_micro_logo_residual_supplement",
        "_panel_text_residual_supplement",
        "_stacked_front_clip_template_supplement",
        "_horizontal_front_clip_template_supplement",
        "_paired_rear_lamp_template_supplement",
        "_template_contained_paint_trim_supplement",
        "_faint_number_outline_supplement",
        "_flat_livery_sponsor_to_paint",
        "_warm_edge_livery_sponsor_to_paint",
        "_vertical_livery_stripe_sponsor_to_paint",
        "_solid_warm_livery_sponsor_to_paint",
        "_diagonal_warm_livery_slash_sponsor_to_paint",
        "_decorative_livery_sponsor_to_paint",
        "_large_red_livery_sponsor_to_paint",
        "_smooth_red_body_panel_sponsor_to_paint",
        "_small_flat_red_livery_sponsor_to_paint",
        "_red_orange_livery_block_sponsor_to_paint",
        "_warm_livery_arc_sponsor_to_paint",
        "_geometric_livery_sponsor_to_paint",
        "_pale_body_panel_sponsor_to_paint",
        "_dark_body_panel_sponsor_to_paint",
        "_white_livery_sponsor_to_paint",
        "_tiny_dark_sponsor_speck_to_paint",
        "_number_logo_false_positive_to_sponsor",
        "_multicolor_logo_false_positive_to_sponsor",
        "_green_white_logo_false_positive_to_sponsor",
        "_large_green_logo_false_positive_to_sponsor",
        "_white_livery_number_panel_to_paint",
        "_small_sponsor_panel_false_positive_to_sponsor",
        "_thin_textline_number_false_positive_to_sponsor",
        "_red_single_digit_number_supplement",
        "_red_two_digit_number_supplement",
        "_number_badge_graphic_supplement",
        "_round_badge_number_supplement",
        "_repeated_round_badge_number_supplement",
        "_yellow_panel_number_supplement",
        "_pale_sponsor_panel_number_supplement",
        "_round_number_badge_interior_to_paint",
        "_round_number_badge_number_crumb_to_paint",
        "_round_number_badge_sponsor_crumb_to_number",
    ]
    for name in route_helper_names:
        monkeypatch.setattr(car_layers_mod, name, empty_guard)
    monkeypatch.setattr(car_layers_mod, "_sponsor_fragment_supplement", fake_sponsor_fragment)
    monkeypatch.setattr(car_layers_mod, "_warm_edge_livery_sponsor_to_paint", fake_warm_edge)
    monkeypatch.setattr(car_layers_mod, "_apply_number_trim_supplement", empty_trim)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert warm_calls[0] == 0
    assert any(count > 0 for count in warm_calls[1:])

    guard = body["warm_edge_livery_sponsor_guard"]
    assert guard["status"] == "applied"
    assert guard["passes"] == ["post_sponsor_fragment"]
    assert guard["components"][0]["reason"] == "route_post_sponsor_fragment_tall_warm_trim"

    sponsors_mask = _data_url_mask(body["layers"]["sponsors"])
    paint_mask = _data_url_mask(body["layers"]["paint"])
    assert sponsors_mask[4:44, 61:64].max() == 0
    assert paint_mask[4:44, 61:64].min() == 255


def test_auto_layers_route_replays_white_livery_cleanup_after_final_number_shell(tmp_path, monkeypatch):
    import server
    import engine.spec_sculpt.core as core_mod
    import engine.spec_sculpt.car_layers as car_layers_mod
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    n = 64
    rgb_float = np.full((n, n, 3), np.array([0.05, 0.04, 0.03], np.float32), np.float32)
    paint_path = tmp_path / "route_final_white_livery_cleanup.png"
    Image.fromarray(np.full((4, 4, 3), 16, np.uint8), "RGB").save(paint_path)

    empty = np.zeros((n, n), np.uint8)
    crumb = np.zeros((n, n), np.uint8)
    crumb[10:14, 10:22] = 255
    white_cleanup_calls: list[int] = []

    def fake_load_paint_rgb_float01(_path, target_size=None):
        return rgb_float.copy(), None, None

    def fake_gpu_separate(_path, target_shape=None):
        return {
            "numbers": empty.copy(),
            "text": empty.copy(),
            "logos": empty.copy(),
        }

    def fake_separate_into_layers(*_args, **_kwargs):
        return {
            "success": True,
            "car": [{"slug": "route_final_white_livery_cleanup", "score": 1.0}],
            "size": (n, n),
            "brand_graphics_merge": "sponsors",
            "layers": {
                "numbers": empty.copy(),
                "sponsors": empty.copy(),
                "template": empty.copy(),
                "brand_graphics": empty.copy(),
                "paint": np.full((n, n), 255, np.uint8),
            },
            "template_guard": {"status": "empty"},
        }

    def empty_guard(*_args, **_kwargs):
        return empty.copy(), {"status": "empty", "component_count": 0, "components": []}

    def empty_trim(*_args, **_kwargs):
        return {"status": "empty", "component_count": 0, "components": []}, None, False

    def fake_large_shell(_rgb, _nm, _sp, _tm, _bg):
        return crumb.copy(), {
            "status": "applied",
            "candidate_count": 1,
            "component_count": 1,
            "added_px": int((crumb > 0).sum()),
            "components": [{"bbox": [10, 10, 12, 4], "reason": "simulated_late_number_shell"}],
        }

    def fake_white_livery_cleanup(_rgb, nm, _sp, _tm, _bg):
        if int((nm[crumb > 0] > 0).sum()) == 0:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        white_cleanup_calls.append(int((nm[crumb > 0] > 0).sum()))
        return crumb.copy(), {
            "status": "applied",
            "candidate_count": 1,
            "component_count": 1,
            "components": [{"bbox": [10, 10, 12, 4], "reason": "left_edge_warm_livery_crumb"}],
        }

    route_helper_names = [
        "_sponsor_fragment_supplement",
        "_isolated_wordmark_supplement",
        "_tiny_logotype_residual_supplement",
        "_micro_logotype_residual_supplement",
        "_colored_micro_logo_residual_supplement",
        "_bright_panel_micro_logo_residual_supplement",
        "_panel_text_residual_supplement",
        "_stacked_front_clip_template_supplement",
        "_horizontal_front_clip_template_supplement",
        "_paired_rear_lamp_template_supplement",
        "_number_template_false_positive_to_template",
        "_template_contained_paint_trim_supplement",
        "_faint_number_outline_supplement",
        "_flat_livery_sponsor_to_paint",
        "_warm_edge_livery_sponsor_to_paint",
        "_vertical_livery_stripe_sponsor_to_paint",
        "_solid_warm_livery_sponsor_to_paint",
        "_bright_warm_body_color_sponsor_to_paint",
        "_warm_tan_body_panel_sponsor_to_paint",
        "_diagonal_warm_livery_slash_sponsor_to_paint",
        "_decorative_livery_sponsor_to_paint",
        "_large_red_livery_sponsor_to_paint",
        "_smooth_red_body_panel_sponsor_to_paint",
        "_small_flat_red_livery_sponsor_to_paint",
        "_red_orange_livery_block_sponsor_to_paint",
        "_warm_livery_arc_sponsor_to_paint",
        "_geometric_livery_sponsor_to_paint",
        "_pale_body_panel_sponsor_to_paint",
        "_ornamental_neutral_livery_sponsor_to_paint",
        "_dark_body_panel_sponsor_to_paint",
        "_white_livery_sponsor_to_paint",
        "_tiny_dark_sponsor_speck_to_paint",
        "_number_logo_false_positive_to_sponsor",
        "_multicolor_logo_false_positive_to_sponsor",
        "_green_white_logo_false_positive_to_sponsor",
        "_large_green_logo_false_positive_to_sponsor",
        "_small_sponsor_panel_false_positive_to_sponsor",
        "_thin_textline_number_false_positive_to_sponsor",
        "_red_single_digit_number_supplement",
        "_red_two_digit_number_supplement",
        "_number_badge_graphic_supplement",
        "_round_badge_number_supplement",
        "_repeated_round_badge_number_supplement",
        "_yellow_panel_number_supplement",
        "_pale_sponsor_panel_number_supplement",
        "_round_number_badge_interior_to_paint",
        "_round_number_badge_number_crumb_to_paint",
        "_round_number_badge_sponsor_crumb_to_number",
        "_neutral_body_watermark_template_to_paint",
    ]
    for name in route_helper_names:
        monkeypatch.setattr(car_layers_mod, name, empty_guard)
    monkeypatch.setattr(car_layers_mod, "_apply_number_trim_supplement", empty_trim)
    monkeypatch.setattr(car_layers_mod, "_large_stylized_number_sponsor_shell_to_number", fake_large_shell)
    monkeypatch.setattr(car_layers_mod, "_white_livery_number_panel_to_paint", fake_white_livery_cleanup)
    monkeypatch.setattr(core_mod, "load_paint_rgb_float01", fake_load_paint_rgb_float01)
    monkeypatch.setattr(gpu_bridge, "separate_file_if_available", fake_gpu_separate)
    monkeypatch.setattr(gpu_bridge, "last_info", lambda: {"available": True, "cache": "test"})
    monkeypatch.setattr(car_layers_mod, "separate_into_layers", fake_separate_into_layers)
    monkeypatch.setattr(car_layers_mod, "hint_from_path", lambda _path: (None, None))
    monkeypatch.setattr(car_layers_mod, "folder_slug_from_path", lambda _path: None)

    client = server.app.test_client()
    response = client.post(
        "/api/auto-layers",
        json={"paint_file": str(paint_path), "preview_size": n},
        headers={"X-Shokker-Internal": "1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["engine"] == "gpu_hybrid"
    assert white_cleanup_calls
    assert body["white_livery_number_panel_guard"]["status"] == "applied"

    numbers_mask = _data_url_mask(body["layers"]["numbers"])
    paint_mask = _data_url_mask(body["layers"]["paint"])
    assert numbers_mask[10:14, 10:22].max() == 0
    assert paint_mask[10:14, 10:22].min() == 255
