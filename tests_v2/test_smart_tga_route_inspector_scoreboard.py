from pathlib import Path
from types import SimpleNamespace
import json

from PIL import Image
import pytest

import numpy as np

from scripts import smart_tga_route_layer_inspector as inspector_module
from scripts.smart_tga_route_layer_inspector import _build_scoreboard, _suspect_review_for_masks, _write_guard_visual_artifacts


def test_smart_tga_route_inspector_checkpoints_each_completed_paint(tmp_path, monkeypatch):
    monkeypatch.setattr(inspector_module, "_route_client", lambda _args: object())

    def fake_inspect(_client, paint, _args):
        if paint.name == "second.tga":
            raise RuntimeError("simulated caller timeout")
        return {"paint_label": paint.name, "success": True}

    monkeypatch.setattr(inspector_module, "inspect_paint", fake_inspect)
    args = SimpleNamespace(
        paint=["first.tga", "second.tga"], output=tmp_path,
    )
    with pytest.raises(RuntimeError, match="simulated caller timeout"):
        inspector_module.inspect(args)

    checkpoint = json.loads((tmp_path / "inspection_records.json").read_text(encoding="utf-8"))
    assert checkpoint == [{"paint_label": "first.tga", "success": True}]


def test_smart_tga_route_inspector_scoreboard_summarizes_route_contract(tmp_path):
    records_path = tmp_path / "inspection_records.json"
    records = [
        {
            "paint": "C:/1Shokker Paint Car Examples/bloomq0.tga",
            "paint_label": "1Shokker Paint Car Examples/bloomq0.tga",
            "success": True,
            "route_engine": "gpu_hybrid",
            "elapsed_sec": 12.345,
            "route_fractions": {
                "numbers": 0.028,
                "sponsors": 0.064,
                "template": 0.012,
                "brand_graphics": 0.0,
                "paint": 0.896,
            },
            "component_layer_counts": {
                "numbers": 3,
                "sponsors": 82,
                "template": 0,
                "brand_graphics": 0,
                "paint": 5,
            },
            "suspect_review_counts": {
                "remaining_text_like_paint_review": 1,
                "remaining_logo_like_paint_review": 2,
            },
            "route_number_trim_fragment_guard": {
                "status": "applied",
                "component_count": 2,
                "added_px": 846,
                "passes": ["pre_number_recovery", "post_response_badge_cleanup"],
                "components": [
                    {"bbox": [515, 863, 23, 34], "reason": "cool_number_outline_paint_fragment"},
                    {"bbox": [529, 294, 19, 31], "reason": "cool_number_outline_paint_fragment"},
                ],
            },
            "route_template_contained_paint_trim_guard": {
                "status": "empty",
                "component_count": 0,
                "components": [],
            },
        },
        {
            "paint": "C:/bad/missing.tga",
            "paint_label": "bad/missing.tga",
            "success": False,
            "error": "missing paint",
            "elapsed_sec": 0.001,
        },
    ]

    scoreboard = _build_scoreboard(records, records_path)

    assert scoreboard["schema"] == "smart_tga_route_scoreboard_v1"
    assert scoreboard["records"] == str(Path(records_path).resolve())
    assert scoreboard["samples"] == 2
    assert scoreboard["success"] == 1
    assert scoreboard["failed"] == 1
    assert scoreboard["engines"] == {"gpu_hybrid": 1}
    assert scoreboard["component_layer_totals"] == {
        "numbers": 3,
        "sponsors": 82,
        "template": 0,
        "brand_graphics": 0,
        "paint": 5,
    }
    assert scoreboard["suspect_review_totals"] == {
        "remaining_text_like_paint_review": 1,
        "remaining_logo_like_paint_review": 2,
    }
    assert scoreboard["applied_guard_totals"] == {"number_trim_fragment": 2}
    assert scoreboard["applied_guard_samples"] == {
        "number_trim_fragment": ["1Shokker Paint Car Examples/bloomq0.tga"]
    }

    bloom = scoreboard["sample_scoreboard"][0]
    assert bloom["paint_label"].endswith("bloomq0.tga")
    assert bloom["component_counts"]["sponsors"] == 82
    assert bloom["applied_guards"]["number_trim_fragment"] == {
        "components": 2,
        "added_px": 846,
        "reasons": ["cool_number_outline_paint_fragment"],
        "passes": ["pre_number_recovery", "post_response_badge_cleanup"],
    }

    failed = scoreboard["sample_scoreboard"][1]
    assert failed["success"] is False
    assert failed["component_counts"] == {
        "numbers": 0,
        "sponsors": 0,
        "template": 0,
        "brand_graphics": 0,
        "paint": 0,
    }
    assert failed["applied_guards"] == {}


def test_smart_tga_route_inspector_writes_guard_visual_artifacts(tmp_path):
    source = Image.new("RGB", (96, 96), (20, 30, 40))
    record = {
        "paint_label": "fixtures/hotwheels.tga",
        "route_number_trim_fragment_guard": {
            "status": "applied",
            "component_count": 2,
            "components": [
                {"bbox": [10, 12, 15, 18], "area": 120, "area_frac": 0.013, "reason": "cool_number_outline_paint_fragment"},
                {"bbox": [50, 42, 8, 20], "area": 90, "area_frac": 0.0098, "reason": "cool_number_outline_paint_fragment"},
            ],
        },
        "route_template_guard": {"status": "empty", "component_count": 0, "components": []},
    }

    _write_guard_visual_artifacts(source, record, tmp_path)

    records_path = Path(record["guard_component_records"])
    assert records_path.exists()
    assert record["guard_component_count"] == 2
    assert set(record["guard_component_sheets"]) == {"number_trim_fragment"}
    assert Path(record["guard_component_sheets"]["number_trim_fragment"]).exists()
    assert sorted(path.name for path in (tmp_path / "guard_crops" / "number_trim_fragment").glob("*.png")) == [
        "000_cool_number_outline_paint_fragment.png",
        "001_cool_number_outline_paint_fragment.png",
    ]


def test_smart_tga_route_inspector_suppresses_red_sponsor_card_panel(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([22, 24, 27], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    card = (slice(100, 167), slice(100, 165))
    sponsors[card] = True
    rgb[card] = np.array([176, 24, 34], np.uint8)
    rgb[102:112, 102:128] = np.array([214, 222, 236], np.uint8)
    rgb[104:114, 140:158] = np.array([82, 130, 214], np.uint8)
    rgb[154:166, 103:158] = np.array([226, 232, 238], np.uint8)

    livery = (slice(220, 287), slice(100, 165))
    sponsors[livery] = True
    rgb[livery] = np.array([196, 28, 34], np.uint8)
    rgb[236:250, 108:156] = np.array([184, 24, 30], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [100, 220, 65, 67]


def test_smart_tga_route_inspector_suppresses_stacked_sponsor_card_panel(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    yy, xx = np.indices((223, 140))
    stack_mask = (xx >= 4) & (xx <= 135) & (yy >= 2) & (yy <= 220)
    voids = (
        ((yy >= 88) & (yy <= 205) & (xx >= 90) & (xx <= 132))
        | ((yy >= 138) & (yy <= 214) & (xx >= 42) & (xx <= 104))
        | ((yy >= 8) & (yy <= 64) & (xx >= 8) & (xx <= 62))
        | ((yy >= 18) & (yy <= 78) & (xx >= 66) & (xx <= 78))
        | ((yy >= 186) & (yy <= 218) & (xx >= 18) & (xx <= 40))
    )
    stack_mask &= ~voids
    stack_mask &= ((xx + 2 * yy) % 37) != 0
    stack_mask |= ((yy >= 24) & (yy <= 82) & (xx >= 82) & (xx <= 126))
    stack_mask |= ((yy >= 88) & (yy <= 134) & (xx >= 76) & (xx <= 124))
    stack_mask |= ((yy >= 118) & (yy <= 178) & (xx >= 26) & (xx <= 84))
    stack_mask |= ((yy >= 70) & (yy <= 132) & (xx >= 66) & (xx <= 83))
    stack_mask |= ((yy >= 174) & (yy <= 205) & (xx >= 24) & (xx <= 44))

    stack_y, stack_x = 100, 100
    sponsors[stack_y:stack_y + 223, stack_x:stack_x + 140] = stack_mask
    stack_rgb = np.full((223, 140, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    stack_rgb[stack_mask] = np.array([228, 88, 28], np.uint8)
    green_card = stack_mask & (yy >= 24) & (yy <= 82) & (xx >= 82) & (xx <= 126)
    stack_rgb[green_card] = np.array([26, 188, 82], np.uint8)
    for y0, x0, h, w in ((28, 86, 8, 36), (43, 91, 7, 28), (61, 88, 8, 34), (92, 81, 9, 38), (118, 88, 8, 32), (146, 34, 12, 38)):
        band = stack_mask & (yy >= y0) & (yy < y0 + h) & (xx >= x0) & (xx < x0 + w)
        stack_rgb[band] = np.array([226, 232, 224], np.uint8)
    for y0, x0, h, w in ((37, 100, 20, 4), (42, 110, 17, 4), (66, 96, 11, 20), (101, 92, 4, 28), (130, 36, 4, 34), (163, 45, 4, 25)):
        glyph = stack_mask & (yy >= y0) & (yy < y0 + h) & (xx >= x0) & (xx < x0 + w)
        stack_rgb[glyph] = np.array([28, 32, 35], np.uint8)
    rgb[stack_y:stack_y + 223, stack_x:stack_x + 140] = stack_rgb

    livery_y, livery_x = 390, 100
    sponsors[livery_y:livery_y + 223, livery_x:livery_x + 140] = stack_mask
    livery_rgb = np.full((223, 140, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    livery_rgb[stack_mask] = np.array([222, 74, 30], np.uint8)
    livery_rgb[stack_mask & (yy > 122)] = np.array([238, 126, 28], np.uint8)
    livery_rgb[stack_mask & (xx > 110) & (yy > 80) & (yy < 142)] = np.array([226, 226, 210], np.uint8)
    rgb[livery_y:livery_y + 223, livery_x:livery_x + 140] = livery_rgb

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [104, 392, 132, 219]


def test_smart_tga_route_inspector_suppresses_vertical_multicolor_sponsor_decal(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([20, 22, 28], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    decal = (slice(100, 204), slice(100, 124))
    sponsors[decal] = True
    rgb[decal] = np.array([226, 76, 22], np.uint8)
    yy, xx = np.indices((104, 24))
    sponsors[100:204, 100:124][((yy + 2 * xx) % 5) == 0] = False
    rgb[100:204:3, 100:124] = np.array([214, 230, 38], np.uint8)
    rgb[101:204:4, 102:122] = np.array([28, 150, 122], np.uint8)
    rgb[102:202, 108:111] = np.array([42, 35, 24], np.uint8)
    rgb[104:200:10, 116:121] = np.array([44, 36, 28], np.uint8)

    livery = (slice(100, 204), slice(180, 204))
    sponsors[livery] = True
    rgb[livery] = np.array([214, 42, 30], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [180, 100, 24, 104]


def test_smart_tga_route_inspector_suppresses_tiny_sponsor_wordmark_underlines(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    for x0, width in ((100, 14), (118, 9), (132, 10), (168, 14)):
        sponsors[74:77, x0:x0 + width] = True
        rgb[74:77, x0:x0 + width] = np.array([30, 30, 30], np.uint8)
        rgb[74:77, x0:x0 + max(2, int(width * 0.58))] = np.array([80, 8, 12], np.uint8)
    for x0, width in ((100, 5), (118, 4), (134, 4), (152, 5), (170, 4)):
        sponsors[44:66, x0:x0 + width] = True
        rgb[44:66, x0:x0 + width] = np.array([232, 235, 228], np.uint8)
        sponsors[56:60, x0:x0 + width + 7] = True
        rgb[56:60, x0:x0 + width + 7] = np.array([232, 235, 228], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "wordmark",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[74:77, 100:114] = True
    rgb_control[74:77, 100:114] = np.array([30, 30, 30], np.uint8)
    rgb_control[74:77, 100:108] = np.array([80, 8, 12], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "wordmark-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [100, 74, 14, 3]


def test_smart_tga_route_inspector_suppresses_vertical_sponsor_side_markers(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([12, 12, 14], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    rgb[486:542, 152:208] = np.array([104, 12, 18], np.uint8)
    rgb[486:542:5, 152:208] = np.array([12, 12, 14], np.uint8)
    rgb[486:542, 152:208:11] = np.array([12, 12, 14], np.uint8)
    for y0 in (490, 502, 514, 528):
        rgb[y0:y0 + 4, 158:202] = np.array([235, 236, 230], np.uint8)
    marker_mask = np.zeros((21, 7), bool)
    marker_yy, marker_xx = np.indices((21, 7))
    marker_mask = ((marker_yy + marker_xx) % 2) == 0
    marker_mask[:, 0] = True
    marker_mask[:, 6] = True
    sponsors[481:502, 220:227] = marker_mask
    rgb[481:502, 220:227][marker_mask] = np.array([82, 8, 12], np.uint8)
    rgb[481:502, 220:227][marker_mask & ((marker_yy + 2 * marker_xx) % 5 == 0)] = np.array([30, 30, 30], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "side-marker",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([12, 12, 14], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[481:502, 220:227] = marker_mask
    rgb_control[481:502, 220:227][marker_mask] = np.array([82, 8, 12], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "side-marker-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [220, 481, 7, 21]


def test_smart_tga_route_inspector_suppresses_long_blue_website_sponsor_strips(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([16, 18, 22], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    sponsors[62:74, 21:141] = True
    rgb[62:74, 21:141] = np.array([24, 30, 42], np.uint8)
    rgb[63:70, 26:82] = np.array([20, 154, 218], np.uint8)
    rgb[66:73, 88:126] = np.array([230, 234, 226], np.uint8)
    rgb[63:70:2, 30:120:5] = np.array([18, 20, 24], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "website-strip",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([16, 18, 22], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[62:74, 21:141] = True
    rgb_control[62:74, 21:141] = np.array([20, 154, 218], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "website-strip-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "stripe_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [21, 62, 120, 12]


def test_smart_tga_route_inspector_suppresses_grille_mesh_paint_boundary(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([238, 202, 0], np.uint8), np.uint8)
    paint = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    y0, x0 = 130, 120
    yy, xx = np.indices((26, 34))
    dark_mesh = xx < (22 - yy // 4)
    rgb[y0:y0 + 26, x0:x0 + 34][dark_mesh] = np.array([12, 15, 14], np.uint8)
    rgb[y0 + 2:y0 + 26:5, x0:x0 + 34] = np.array([54, 58, 52], np.uint8)
    rgb[y0:y0 + 26, x0 + 3:x0 + 34:7] = np.array([48, 52, 47], np.uint8)
    for row in range(26):
        col = min(32, 8 + row)
        paint[y0 + row, x0 + col:x0 + col + 2] = True
        rgb[y0 + row, x0 + col:x0 + col + 2] = np.array([222, 40, 22], np.uint8)

    logo = (slice(220, 236), slice(120, 140))
    paint[logo] = True
    rgb[logo] = np.array([224, 38, 28], np.uint8)
    rgb[224:232, 126:136] = np.array([246, 212, 24], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": empty, "template": empty, "brand_graphics": empty, "paint": paint},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "remaining_logo_like_paint_review"
    assert suspects[0]["bbox"] == [120, 220, 20, 16]


def test_smart_tga_route_inspector_suppresses_bottom_edge_flat_livery_panels(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([35, 35, 35], np.uint8), np.uint8)
    paint = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_livery_panel(x0, y0, w, h):
        paint[y0:y0 + h, x0:x0 + w] = True
        rgb[y0:y0 + h, x0:x0 + w] = np.array([246, 82, 16], np.uint8)
        rgb[y0 + 6:y0 + 9, x0:x0 + w] = np.array([38, 38, 38], np.uint8)
        rgb[y0 + 13:y0 + 17, x0:x0 + w] = np.array([38, 38, 38], np.uint8)
        rgb[y0 + 21:y0 + h, x0:x0 + w] = np.array([38, 38, 38], np.uint8)

    stamp_livery_panel(702, 998, 56, 26)
    stamp_livery_panel(646, 976, 34, 26)

    logo = (slice(970, 992), slice(802, 830))
    paint[logo] = True
    rgb[logo] = np.array([230, 42, 24], np.uint8)
    rgb[974:988, 808:824] = np.array([236, 206, 28], np.uint8)
    rgb[978:984, 812:820] = np.array([38, 170, 120], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": empty, "template": empty, "brand_graphics": empty, "paint": paint},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "remaining_logo_like_paint_review"
    assert suspects[0]["bbox"] == [802, 970, 28, 22]


def test_smart_tga_route_inspector_suppresses_cyan_template_livery_stripe_paint(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([24, 26, 29], np.uint8), np.uint8)
    paint = np.zeros((1024, 1024), bool)
    sponsors = np.zeros((1024, 1024), bool)
    template = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def shard_shape(h=14, w=23):
        yy, xx = np.indices((h, w))
        line = np.clip(10 - (xx * 5) // 11, 1, h - 2)
        return (
            (yy == line)
            | ((yy == np.maximum(0, line - 1)) & ((xx % 3) == 0))
            | ((yy == np.minimum(h - 1, line + 1)) & ((xx % 4) == 0))
            | ((yy == 9) & (xx >= 3) & (xx <= 9))
        )

    def stamp_cyan_shard(y0, x0, *, template_context):
        h, w = 14, 23
        if template_context:
            template[y0 - 12:y0 + h + 12, x0 - 18:x0 + w + 18] = True
            sponsors[y0 - 4:y0 + h + 5, x0 - 2:x0 + w + 2] = True
            rgb[y0 - 12:y0 + h + 12, x0 - 18:x0 + w + 18] = np.array([12, 13, 14], np.uint8)
            rgb[y0 + 5:y0 + h + 8, x0 - 18:x0 + w + 18] = np.array([232, 236, 238], np.uint8)
        shape = shard_shape(h, w)
        paint[y0:y0 + h, x0:x0 + w] = shape
        coords = np.argwhere(shape)
        for idx, (yy0, xx0) in enumerate(coords):
            rgb[y0 + yy0, x0 + xx0] = (
                np.array([238, 242, 244], np.uint8)
                if idx % 9 == 0
                else np.array([24, 190, 220], np.uint8)
            )

    stamp_cyan_shard(674, 717, template_context=True)
    stamp_cyan_shard(520, 720, template_context=False)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": template, "brand_graphics": empty, "paint": paint},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "remaining_logo_like_paint_review"
    assert suspects[0]["bbox"] == [720, 520, 23, 12]


def test_smart_tga_route_inspector_suppresses_template_adjacent_green_livery_edges(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([20, 22, 20], np.uint8), np.uint8)
    paint = np.zeros((1024, 1024), bool)
    sponsors = np.zeros((1024, 1024), bool)
    template = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def edge_shape():
        shape = np.zeros((24, 5), bool)
        shape[:, 2] = True
        shape[[4, 10], 0:2] = True
        shape[[16, 22], 3:5] = True
        return shape

    def stamp_green_edge(y0, x0, *, template_context):
        shape = edge_shape()
        if template_context:
            template[y0 - 12:y0 + 34, x0 - 12:x0 + 18] = True
            sponsors[y0 - 5:y0 + 30, x0 - 4:x0 + 12] = True
            rgb[y0 - 12:y0 + 34, x0 - 12:x0 + 18] = np.array([13, 15, 13], np.uint8)
            rgb[y0 - 4:y0 + 28, x0 - 12:x0 + 4] = np.array([32, 92, 45], np.uint8)
        paint[y0:y0 + 24, x0:x0 + 5] = shape
        coords = np.argwhere(shape)
        for idx, (yy0, xx0) in enumerate(coords):
            rgb[y0 + yy0, x0 + xx0] = (
                np.array([31, 118, 48], np.uint8)
                if idx % 3 == 0
                else np.array([20, 78, 35], np.uint8)
            )

    stamp_green_edge(970, 198, template_context=True)
    stamp_green_edge(520, 198, template_context=False)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": template, "brand_graphics": empty, "paint": paint},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "remaining_logo_like_paint_review"
    assert suspects[0]["bbox"] == [198, 520, 5, 24]


def test_smart_tga_route_inspector_suppresses_distressed_yellow_wordmark_sponsor_cards(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def card_mask(h=52, w=119):
        yy, xx = np.indices((h, w))
        mask = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
        mask &= ((xx + yy * 3) % 5) != 0
        mask &= ~(((xx - 7) % 29 < 4) & ((yy - 5) % 19 < 3))
        return mask

    def stamp_distressed_card(rgb, sponsors, x0, y0):
        mask = card_mask()
        h, w = mask.shape
        yy, xx = np.indices((h, w))
        local = np.full((h, w, 3), np.array([238, 214, 32], np.uint8), np.uint8)
        local[((xx + yy) % 11) <= 1] = np.array([38, 34, 28], np.uint8)
        local[:, 7:10] = np.array([34, 30, 26], np.uint8)
        local[43:48, 18:112] = np.array([34, 30, 26], np.uint8)
        local[(yy >= 18) & (yy <= 35) & (xx >= 26) & (xx <= 92)] = np.array([244, 238, 228], np.uint8)
        local[(yy >= 21) & (yy <= 32) & (xx >= 31) & (xx <= 88) & (((xx + yy) % 5) <= 2)] = np.array([132, 78, 222], np.uint8)
        local[(yy >= 8) & (yy <= 12) & (xx >= 12) & (xx <= 110)] = np.array([230, 42, 30], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]
        sponsors[y0:y0 + h, x0:x0 + w] = mask

    rgb = np.full((1024, 1024, 3), np.array([24, 24, 24], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    stamp_distressed_card(rgb, sponsors, 609, 30)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "distressed-card",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([24, 24, 24], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    mask = card_mask()
    y0, x0 = 180, 609
    local = np.full((52, 119, 3), np.array([238, 214, 32], np.uint8), np.uint8)
    local[18:35, 22:96] = np.array([228, 44, 30], np.uint8)
    rgb_control[y0:y0 + 52, x0:x0 + 119][mask] = local[mask]
    sponsors_control[y0:y0 + 52, x0:x0 + 119] = mask

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "smooth-livery-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] in {
        "decorative_livery_like_sponsor_review",
        "red_livery_like_sponsor_review",
    }


def test_smart_tga_route_inspector_suppresses_compact_multicolor_sponsor_badges(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([36, 24, 34], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    for y0, x0, base in ((100, 100, np.array([230, 54, 28], np.uint8)), (100, 180, np.array([218, 42, 82], np.uint8))):
        badge = (slice(y0, y0 + 38), slice(x0, x0 + 44))
        sponsors[badge] = True
        rgb[badge] = base
        rgb[y0 + 3:y0 + 35, x0 + 3:x0 + 41] = np.array([238, 128, 30], np.uint8)
        rgb[y0 + 5:y0 + 34, x0 + 6:x0 + 38] = np.array([228, 202, 36], np.uint8)
        rgb[y0 + 7:y0 + 34:3, x0 + 9:x0 + 34] = np.array([38, 140, 120], np.uint8)
        rgb[y0 + 8:y0 + 33:5, x0 + 12:x0 + 33] = np.array([214, 86, 36], np.uint8)
        rgb[y0 + 9:y0 + 31, x0 + 14:x0 + 17] = np.array([238, 206, 38], np.uint8)
        rgb[y0 + 11:y0 + 29, x0 + 25:x0 + 28] = np.array([238, 206, 38], np.uint8)

    livery = (slice(200, 238), slice(100, 144))
    sponsors[livery] = True
    rgb[livery] = np.array([224, 52, 32], np.uint8)
    rgb[204:235, 104:140] = np.array([226, 184, 32], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [100, 200, 44, 38]


def test_smart_tga_route_inspector_suppresses_paired_square_sponsor_badge_panels(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([22, 62, 38], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_badge(y0, x0):
        yy, xx = np.indices((66, 55))
        badge_mask = (((xx - 27) / 25.7) ** 2 + ((yy - 33) / 30.2) ** 2) <= 1.0
        sponsors[y0:y0 + 66, x0:x0 + 55] = badge_mask
        local_rgb = np.full((66, 55, 3), np.array([22, 62, 38], np.uint8), np.uint8)
        local_rgb[badge_mask] = np.array([38, 116, 206], np.uint8)
        yellow = badge_mask & (yy >= 8) & (yy <= 50) & (xx >= 4) & (xx <= 50)
        green = badge_mask & (yy >= 42) & (yy <= 54) & (xx >= 8) & (xx <= 46)
        yellow_edge = badge_mask & (yy >= 42) & (yy <= 54) & ((xx <= 10) | (xx >= 44))
        orange = badge_mask & (((xx + yy) % 8) <= 2)
        blue_detail = badge_mask & (((xx + 3 * yy) % 13) <= 1)
        pale = badge_mask & (((yy % 13) <= 1) & (xx >= 8) & (xx <= 48))
        dark = badge_mask & (((xx % 31) == 0) | ((yy % 43) == 0))
        local_rgb[yellow] = np.array([210, 205, 42], np.uint8)
        local_rgb[green] = np.array([48, 164, 82], np.uint8)
        local_rgb[yellow_edge] = np.array([210, 205, 42], np.uint8)
        local_rgb[orange] = np.array([222, 92, 32], np.uint8)
        local_rgb[blue_detail] = np.array([38, 116, 206], np.uint8)
        local_rgb[pale] = np.array([236, 232, 214], np.uint8)
        local_rgb[dark] = np.array([26, 28, 32], np.uint8)
        rgb[y0:y0 + 66, x0:x0 + 55] = local_rgb

    stamp_badge(63, 29)
    stamp_badge(63, 441)
    yy, xx = np.indices((66, 55))
    livery_mask = (((xx - 27) / 25.7) ** 2 + ((yy - 33) / 30.2) ** 2) <= 1.0
    sponsors[190:256, 240:295] = livery_mask
    livery_rgb = np.full((66, 55, 3), np.array([22, 62, 38], np.uint8), np.uint8)
    livery_rgb[livery_mask] = np.array([222, 92, 32], np.uint8)
    livery_rgb[livery_mask & (yy >= 8) & (yy <= 44) & (xx >= 5) & (xx <= 49)] = np.array([210, 205, 42], np.uint8)
    livery_rgb[livery_mask & (((xx + 2 * yy) % 19) <= 1)] = np.array([236, 156, 32], np.uint8)
    rgb[190:256, 240:295] = livery_rgb

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "decorative_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [242, 193, 51, 61]


def test_smart_tga_route_inspector_suppresses_dlm_style_decorative_sponsor_logos(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([24, 24, 24], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_wide_panel(y0, x0):
        yy, xx = np.indices((50, 106))
        mask = (
            ((yy >= 5) & (yy <= 40) & (xx >= 3) & (xx <= 96) & (((xx + yy) % 7) <= 2))
            | ((yy >= 20) & (yy <= 46) & (xx >= 20) & (xx <= 104) & (((xx - yy) % 11) <= 1))
            | ((yy <= 5) & (xx >= 8) & (xx <= 90))
        )
        sponsors[y0:y0 + 50, x0:x0 + 106] |= mask
        local = np.full((50, 106, 3), np.array([24, 24, 24], np.uint8), np.uint8)
        local[mask] = np.array([218, 24, 42], np.uint8)
        pale = mask & (xx >= 12) & (xx <= 100) & (yy >= 4) & (yy <= 46) & (((xx + 2 * yy) % 9) <= 2)
        dark = mask & (((xx % 31) == 0) | ((yy % 17) == 0))
        blue = mask & (xx >= 62) & (xx <= 82) & (yy >= 13) & (yy <= 30)
        local[pale] = np.array([238, 236, 228], np.uint8)
        local[dark] = np.array([22, 20, 22], np.uint8)
        local[blue] = np.array([38, 72, 214], np.uint8)
        rgb[y0:y0 + 50, x0:x0 + 106][mask] = local[mask]

    def stamp_compact_badge(y0, x0):
        yy, xx = np.indices((38, 38))
        mask = (((xx - 18.5) / 18.0) ** 2 + ((yy - 18.5) / 17.4) ** 2) <= 1.0
        sponsors[y0:y0 + 38, x0:x0 + 38] |= mask
        local = np.full((38, 38, 3), np.array([24, 24, 24], np.uint8), np.uint8)
        local[mask] = np.array([232, 70, 34], np.uint8)
        blue = mask & (xx >= 8) & (xx <= 32) & (yy >= 8) & (yy <= 29)
        yellow = mask & (((xx + yy) % 7) <= 2)
        pale = mask & (((xx + 2 * yy) % 11) <= 2)
        dark = mask & (((xx % 13) == 0) | ((yy % 19) == 0))
        local[blue] = np.array([54, 112, 214], np.uint8)
        local[yellow] = np.array([226, 204, 42], np.uint8)
        local[pale] = np.array([238, 236, 226], np.uint8)
        local[dark] = np.array([24, 24, 28], np.uint8)
        rgb[y0:y0 + 38, x0:x0 + 38][mask] = local[mask]

    stamp_wide_panel(120, 80)
    stamp_wide_panel(120, 210)
    stamp_compact_badge(250, 86)

    yy, xx = np.indices((44, 44))
    livery_mask = (((xx - 21.5) / 20.0) ** 2 + ((yy - 21.5) / 20.0) ** 2) <= 1.0
    sponsors[380:424, 86:130] = livery_mask
    livery_rgb = np.full((44, 44, 3), np.array([24, 24, 24], np.uint8), np.uint8)
    livery_rgb[livery_mask] = np.array([226, 92, 34], np.uint8)
    livery_rgb[livery_mask & (yy > 8) & (yy < 35) & (xx > 8) & (xx < 35)] = np.array([226, 204, 42], np.uint8)
    rgb[380:424, 86:130][livery_mask] = livery_rgb[livery_mask]

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "decorative_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [88, 382, 40, 40]


def test_smart_tga_route_inspector_suppresses_vertical_red_sponsor_card_pairs(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([22, 22, 22], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_card(y0, x0, textured=True):
        yy, xx = np.indices((48, 113))
        mask = (yy >= 2) & (yy <= 45) & (xx >= 3) & (xx <= 109)
        if textured:
            mask &= ~((xx < 31) & (yy < 24 - xx // 2))
            mask &= ~((xx > 81) & (yy > 24 + (112 - xx) // 2))
        sponsors[y0:y0 + 48, x0:x0 + 113] |= mask

        local = np.full((48, 113, 3), np.array([22, 22, 22], np.uint8), np.uint8)
        local[mask] = np.array([226, 72, 96], np.uint8)
        if textured:
            pale = mask & (
                ((xx >= 28) & (xx <= 52) & (yy >= 12) & (yy <= 17))
                | ((xx >= 58) & (xx <= 92) & (yy >= 22) & (yy <= 27))
                | ((xx >= 76) & (xx <= 78) & (yy >= 10) & (yy <= 38))
            )
            redline = mask & (
                ((xx >= 91) & (xx <= 93) & (yy >= 11) & (yy <= 36))
                | ((yy >= 34) & (yy <= 35) & (xx >= 48) & (xx <= 104))
                | ((xx >= 36) & (xx <= 38) & (yy >= 9) & (yy <= 29))
                | ((yy >= 8) & (yy <= 9) & (xx >= 32) & (xx <= 88))
            )
            dark = (
                mask
                & (
                    ((xx >= 16) & (xx <= 18) & (yy >= 10) & (yy <= 37))
                    | ((yy >= 38) & (yy <= 40) & (xx >= 36) & (xx <= 98))
                    | (((xx + yy) % 41) == 0)
                )
                & ~pale
                & ~redline
            )
            local[pale] = np.array([242, 236, 230], np.uint8)
            local[redline & ~pale] = np.array([150, 18, 34], np.uint8)
            local[dark] = np.array([45, 36, 38], np.uint8)
        rgb[y0:y0 + 48, x0:x0 + 113][mask] = local[mask]

    stamp_card(80, 260, textured=True)
    stamp_card(230, 265, textured=True)
    stamp_card(420, 80, textured=True)
    stamp_card(80, 520, textured=False)
    stamp_card(230, 520, textured=False)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    suspect_bboxes = {tuple(s["bbox"]) for s in suspects}
    assert (263, 82, 107, 44) not in suspect_bboxes
    assert (268, 232, 107, 44) not in suspect_bboxes
    assert (83, 422, 107, 44) in suspect_bboxes
    assert (523, 82, 107, 44) in suspect_bboxes
    assert (523, 232, 107, 44) in suspect_bboxes


def test_smart_tga_route_inspector_suppresses_black_panel_yellow_sponsor_text(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([18, 20, 18], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    yy, xx = np.indices((22, 122))
    text_mask = ((yy % 5) <= 2) | ((xx % 11) <= 2)
    text_mask &= ~(((xx + 2 * yy) % 13) == 0)
    text_y, text_x = 100, 100
    sponsors[text_y:text_y + 22, text_x:text_x + 122] = text_mask
    text_rgb = np.full((22, 122, 3), np.array([18, 20, 18], np.uint8), np.uint8)
    text_rgb[text_mask] = np.array([238, 204, 28], np.uint8)
    text_rgb[text_mask & (((xx + yy) % 7) <= 1)] = np.array([190, 42, 22], np.uint8)
    text_rgb[text_mask & (((xx - yy) % 9) <= 1)] = np.array([24, 25, 20], np.uint8)
    rgb[text_y:text_y + 22, text_x:text_x + 122] = text_rgb

    livery_y, livery_x = 170, 100
    livery_mask = (((yy % 6) <= 3) | ((xx % 37) <= 16))
    sponsors[livery_y:livery_y + 22, livery_x:livery_x + 122] = livery_mask
    livery_rgb = np.full((22, 122, 3), np.array([18, 20, 18], np.uint8), np.uint8)
    livery_rgb[livery_mask] = np.array([216, 48, 30], np.uint8)
    livery_rgb[livery_mask & (yy >= 11)] = np.array([236, 184, 24], np.uint8)
    rgb[livery_y:livery_y + 22, livery_x:livery_x + 122] = livery_rgb

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [100, 170, 122, 22]


def test_smart_tga_route_inspector_suppresses_edge_contingency_sponsor_panel(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([18, 19, 18], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    x0, y0, bw, bh = 955, 20, 69, 343
    panel = (slice(y0, y0 + bh), slice(x0, x0 + bw))
    sponsors[panel] = True
    rgb[panel] = np.array([238, 222, 40], np.uint8)
    rgb[y0 + 9:y0 + bh - 9, x0 + 2:x0 + 12] = np.array([188, 32, 40], np.uint8)
    rgb[y0 + 24:y0 + bh - 24:12, x0 + 17:x0 + 62] = np.array([236, 238, 226], np.uint8)
    rgb[y0 + 27:y0 + bh - 24:12, x0 + 22:x0 + 57] = np.array([236, 238, 226], np.uint8)
    rgb[y0 + 30:y0 + bh - 24:12, x0 + 28:x0 + 54] = np.array([236, 238, 226], np.uint8)
    rgb[y0 + 24:y0 + bh - 22:26, x0 + 48:x0 + 63] = np.array([224, 48, 28], np.uint8)
    rgb[y0 + 14:y0 + bh - 14:29, x0 + 14:x0 + 18] = np.array([24, 24, 20], np.uint8)

    livery_x, livery_y = 0, 450
    livery = (slice(livery_y, livery_y + bh), slice(livery_x, livery_x + bw))
    sponsors[livery] = True
    rgb[livery] = np.array([238, 208, 34], np.uint8)
    rgb[livery_y + 8:livery_y + bh - 8, livery_x + 54:livery_x + 66] = np.array([198, 38, 32], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [0, 450, 69, 343]


def test_smart_tga_route_inspector_suppresses_dark_panel_yellow_sponsor_mark(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([16, 17, 16], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    yy, xx = np.indices((150, 52))
    left_stroke = np.abs(xx - (10 + yy * 0.11)) <= 4
    right_stroke = np.abs(xx - (42 - yy * 0.11)) <= 4
    crossbar = (yy >= 74) & (yy <= 91) & (xx >= 16) & (xx <= 38)
    logo_mask = (left_stroke | right_stroke | crossbar) & (yy >= 6) & (yy <= 143)

    logo_y, logo_x = 520, 780
    sponsors[logo_y:logo_y + 150, logo_x:logo_x + 52] = logo_mask
    logo_rgb = np.full((150, 52, 3), np.array([16, 17, 16], np.uint8), np.uint8)
    logo_rgb[logo_mask] = np.array([238, 210, 28], np.uint8)
    logo_rgb[logo_mask & (((xx + yy) % 9) <= 1)] = np.array([214, 54, 26], np.uint8)
    rgb[logo_y:logo_y + 150, logo_x:logo_x + 52] = logo_rgb
    for offset in range(8, 136, 18):
        rgb[logo_y + offset:logo_y + offset + 5, logo_x + 58:logo_x + 126] = np.array([236, 204, 26], np.uint8)
        rgb[logo_y + offset + 8:logo_y + offset + 11, logo_x + 66:logo_x + 112] = np.array([236, 204, 26], np.uint8)

    livery_y, livery_x = 520, 580
    sponsors[livery_y:livery_y + 150, livery_x:livery_x + 52] = logo_mask
    livery_rgb = np.full((150, 52, 3), np.array([16, 17, 16], np.uint8), np.uint8)
    livery_rgb[logo_mask] = np.array([238, 210, 28], np.uint8)
    livery_rgb[logo_mask & (((xx + yy) % 9) <= 1)] = np.array([214, 54, 26], np.uint8)
    rgb[livery_y:livery_y + 150, livery_x:livery_x + 52] = livery_rgb

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [587, 526, 39, 138]


def test_smart_tga_route_inspector_suppresses_tiny_contingency_sponsor_mark(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([16, 18, 17], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_tiny_mark(y0, x0):
        yy, xx = np.indices((12, 11))
        mark = np.ones((12, 11), bool)
        mark &= ((xx + 2 * yy) % 7) != 0
        sponsors[y0:y0 + 12, x0:x0 + 11] = mark
        local_rgb = np.full((12, 11, 3), np.array([16, 18, 17], np.uint8), np.uint8)
        local_rgb[mark] = np.array([214, 36, 36], np.uint8)
        local_rgb[mark & (((xx + yy) % 13) <= 3)] = np.array([24, 18, 18], np.uint8)
        rgb[y0:y0 + 12, x0:x0 + 11] = local_rgb

    # Positive: tiny red/dark mark embedded in a separated contingency stack.
    rgb[860:918, 614:722] = np.array([18, 18, 16], np.uint8)
    rgb[844:866, 610:726] = np.array([236, 198, 18], np.uint8)
    rgb[914:936, 606:730] = np.array([232, 204, 22], np.uint8)
    for row in range(852, 932, 12):
        rgb[row:row + 3, 620:716] = np.array([242, 242, 232], np.uint8)
        rgb[row + 5:row + 7, 632:704] = np.array([18, 20, 22], np.uint8)
    for col in range(624, 718, 14):
        rgb[858:930, col:col + 2] = np.array([22, 24, 24], np.uint8)
    sponsors[867:881, 659:705] = True
    rgb[867:881, 659:705] = np.array([236, 236, 226], np.uint8)
    rgb[870:875, 666:700] = np.array([22, 24, 26], np.uint8)
    for col in range(662, 704, 7):
        rgb[867:881, col:col + 2] = np.array([22, 24, 26], np.uint8)
    sponsors[900:907, 664:700] = True
    rgb[900:907, 664:700] = np.array([238, 238, 230], np.uint8)
    rgb[901:905, 672:695] = np.array([22, 24, 26], np.uint8)
    for col in range(666, 700, 6):
        rgb[900:907, col:col + 2] = np.array([22, 24, 26], np.uint8)
    stamp_tiny_mark(898, 651)

    # Control: same mark isolated on a smooth dark panel must still be reviewed.
    stamp_tiny_mark(700, 580)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [580, 700, 11, 12]


def test_smart_tga_route_inspector_suppresses_tiny_horizontal_contingency_sponsor_mark(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([18, 18, 16], np.uint8), np.uint8)
    numbers = np.zeros((1024, 1024), bool)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_horizontal_mark(y0, x0):
        yy, xx = np.indices((6, 17))
        mark = np.ones((6, 17), bool)
        mark &= ((xx + yy) % 11) != 0
        sponsors[y0:y0 + 6, x0:x0 + 17] = mark
        local_rgb = np.full((6, 17, 3), np.array([18, 18, 16], np.uint8), np.uint8)
        local_rgb[mark] = np.array([214, 32, 36], np.uint8)
        local_rgb[mark & (((xx + 2 * yy) % 7) == 0)] = np.array([238, 236, 226], np.uint8)
        rgb[y0:y0 + 6, x0:x0 + 17] = local_rgb

    # Positive: a flat red contingency/logo chip embedded in sponsor textlines.
    rgb[832:898, 624:730] = np.array([22, 22, 20], np.uint8)
    numbers[820:910, 732:780] = True
    for row in (838, 852, 866, 880):
        sponsors[row:row + 5, 640:718] = True
        rgb[row:row + 5, 640:718] = np.array([238, 238, 230], np.uint8)
        rgb[row + 2:row + 4, 652:706] = np.array([24, 24, 26], np.uint8)
    rgb[872:879, 630:648] = np.array([236, 210, 32], np.uint8)
    rgb[874:877, 636:644] = np.array([24, 24, 22], np.uint8)
    stamp_horizontal_mark(862, 682)

    # Control: same red chip isolated on a smooth panel remains review-worthy.
    stamp_horizontal_mark(702, 582)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": numbers, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [582, 702, 17, 6]


def test_smart_tga_route_inspector_suppresses_top_edge_number_panel_contingency_chip(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([236, 238, 232], np.uint8), np.uint8)
    numbers = np.zeros((1024, 1024), bool)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    numbers[54:82, 92:124] = True

    def stamp_chip(y0, x0):
        sponsors[y0:y0 + 6, x0:x0 + 7] = True
        local_rgb = np.full((6, 7, 3), np.array([214, 32, 36], np.uint8), np.uint8)
        local_rgb[1, 1] = np.array([238, 236, 226], np.uint8)
        local_rgb[4, 5] = np.array([238, 236, 226], np.uint8)
        rgb[y0:y0 + 6, x0:x0 + 7] = local_rgb

    # Positive suppressor: tiny red/white sponsor chip on a top-edge number panel.
    stamp_chip(66, 104)
    numbers[66:72, 104:111] = False

    # Control: a normal lower red sponsor block must still review.
    sponsors[700:720, 580:620] = True
    rgb[700:720, 580:620] = np.array([214, 32, 36], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": numbers, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [580, 700, 40, 20]


def test_smart_tga_route_inspector_suppresses_embedded_number_panel_contingency_strip(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([236, 238, 232], np.uint8), np.uint8)
    numbers = np.zeros((1024, 1024), bool)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_strip(y0, x0):
        sponsors[y0:y0 + 5, x0:x0 + 22] = True
        yy, xx = np.indices((5, 22))
        strip = np.full((5, 22, 3), np.array([216, 32, 36], np.uint8), np.uint8)
        strip[((xx + yy) % 5) == 0] = np.array([80, 178, 78], np.uint8)
        strip[((xx + yy) % 13) == 0] = np.array([238, 236, 226], np.uint8)
        rgb[y0:y0 + 5, x0:x0 + 22] = strip

    # Positive: tiny red/green sponsor wordmark strip embedded in a number panel.
    numbers[808:842, 2:54] = True
    numbers[822:827, 17:39] = False
    stamp_strip(822, 17)

    # Control: same sponsor-colored strip away from a number panel still reviews.
    rgb[700:730, 560:630] = np.array([28, 30, 34], np.uint8)
    stamp_strip(710, 580)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": numbers, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [580, 710, 22, 5]


def test_smart_tga_route_inspector_suppresses_compact_contingency_sponsor_badges(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([20, 20, 18], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    template = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_textline(y0, x0, w=48, h=18):
        sponsors[y0:y0 + h, x0:x0 + w] = True
        rgb[y0:y0 + h, x0:x0 + w] = np.array([238, 238, 230], np.uint8)
        rgb[y0 + 4:y0 + h - 4, x0 + 5:x0 + w - 5:7] = np.array([28, 28, 30], np.uint8)
        rgb[y0 + 9:y0 + 12, x0 + 8:x0 + w - 8] = np.array([28, 28, 30], np.uint8)

    def stamp_badge(y0, x0, w=40, h=20, protected=False):
        yy, xx = np.indices((h, w))
        mask = ((xx + 2 * yy) % 4) != 0
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([20, 20, 18], np.uint8), np.uint8)
        local[mask] = np.array([214, 30, 38], np.uint8)
        local[mask & (((xx + yy) % 5) <= 2)] = np.array([228, 190, 32], np.uint8)
        local[mask & (((2 * xx + yy) % 17) <= 1)] = np.array([28, 24, 24], np.uint8)
        local[mask & (((xx % 4) == 0) | (((xx + yy) % 9) == 0))] = np.array([28, 24, 24], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w] = local
        if protected:
            template[y0:y0 + h, x0:x0 + w] = mask

    # Positives: compact red/yellow contingency/logo chunks in sponsor stacks.
    rgb[200:270, 300:430] = np.array([92, 58, 24], np.uint8)
    rgb[204:270:8, 300:430] = np.array([28, 24, 22], np.uint8)
    stamp_badge(220, 320, 40, 20)
    stamp_textline(218, 366, 48, 18)
    stamp_textline(244, 346, 34, 12)

    rgb[282:340, 100:205] = np.array([92, 58, 24], np.uint8)
    rgb[286:340:8, 100:205] = np.array([28, 24, 22], np.uint8)
    stamp_badge(300, 120, 18, 20)
    stamp_textline(302, 142, 48, 18)

    rgb[356:430, 500:640] = np.array([92, 58, 24], np.uint8)
    rgb[360:430:8, 500:640] = np.array([28, 24, 22], np.uint8)
    stamp_badge(380, 520, 35, 24)
    stamp_textline(376, 560, 61, 27)
    stamp_textline(410, 535, 37, 15)
    template[356:426, 610:638] = True
    rgb[356:426, 610:638] = np.array([210, 214, 214], np.uint8)

    # Controls: same visual mark without sponsor context, and protected art.
    stamp_badge(620, 320, 40, 20)
    stamp_badge(700, 320, 40, 20, protected=True)
    stamp_textline(696, 366, 48, 18)
    stamp_textline(724, 346, 34, 12)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": template, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    reasons_by_bbox = {tuple(s["bbox"]): s["review_reason"] for s in suspects}
    assert (320, 220, 40, 20) not in reasons_by_bbox
    assert (120, 300, 18, 20) not in reasons_by_bbox
    assert (520, 380, 35, 24) not in reasons_by_bbox
    assert reasons_by_bbox[(320, 620, 40, 20)] == "red_livery_like_sponsor_review"
    assert reasons_by_bbox[(320, 700, 40, 20)] == "red_livery_like_sponsor_review"


def test_smart_tga_route_inspector_suppresses_tiny_magenta_red_sponsor_details(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([20, 20, 20], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    template = np.zeros((1024, 1024), bool)

    def stamp_sponsor_context(y0, x0):
        rgb[y0 - 4:y0 + 72, x0 - 6:x0 + 176] = np.array([96, 94, 88], np.uint8)
        template[y0 - 2:y0 + 70, x0 + 100:x0 + 128] = True
        rgb[y0 - 2:y0 + 70, x0 + 100:x0 + 128] = np.array([210, 214, 214], np.uint8)
        for row in (0, 18, 36):
            sponsors[y0 + row:y0 + row + 6, x0:x0 + 72] = True
            rgb[y0 + row:y0 + row + 6, x0:x0 + 72] = np.array([236, 236, 228], np.uint8)
            rgb[y0 + row + 2:y0 + row + 4, x0 + 8:x0 + 64:7] = np.array([28, 28, 30], np.uint8)
        sponsors[y0 + 14:y0 + 28, x0 + 84:x0 + 114] = True
        rgb[y0 + 14:y0 + 28, x0 + 84:x0 + 114] = np.array([238, 232, 216], np.uint8)
        rgb[y0 + 18:y0 + 24, x0 + 91:x0 + 108] = np.array([30, 30, 32], np.uint8)
        sponsors[y0 + 9:y0 + 25, x0 + 128:x0 + 166] = True
        rgb[y0 + 9:y0 + 25, x0 + 128:x0 + 166] = np.array([46, 104, 206], np.uint8)
        rgb[y0 + 13:y0 + 21, x0 + 136:x0 + 158] = np.array([232, 232, 224], np.uint8)

    def stamp_red_chip(y0, x0):
        yy, xx = np.indices((5, 9))
        chip = ((xx + yy) % 13) != 0
        sponsors[y0:y0 + 5, x0:x0 + 9] = chip
        local = np.full((5, 9, 3), np.array([20, 20, 20], np.uint8), np.uint8)
        local[chip] = np.array([218, 24, 44], np.uint8)
        rgb[y0:y0 + 5, x0:x0 + 9] = local

    def stamp_magenta_vertical(y0, x0):
        yy, xx = np.indices((14, 5))
        mark = ((2 * xx + yy) % 17) != 0
        sponsors[y0:y0 + 14, x0:x0 + 5] = mark
        local = np.full((14, 5, 3), np.array([20, 20, 20], np.uint8), np.uint8)
        local[mark] = np.array([202, 18, 78], np.uint8)
        local[mark & (((xx + yy) % 6) == 0)] = np.array([58, 8, 32], np.uint8)
        rgb[y0:y0 + 14, x0:x0 + 5] = local

    def stamp_colored_trim(y0, x0):
        sponsors[y0:y0 + 34, x0:x0 + 1] = True
        rgb[y0:y0 + 34, x0:x0 + 1] = np.array([34, 8, 96], np.uint8)

    stamp_sponsor_context(286, 300)
    stamp_red_chip(304, 356)
    template[304:309, 356:359] = True
    stamp_magenta_vertical(326, 388)
    stamp_colored_trim(286, 430)

    # Dark sponsor panels can surround tiny red logo details without making
    # them livery; this mirrors dense black/white contingency panels.
    rgb[482:552, 560:720] = np.array([18, 18, 20], np.uint8)
    for row in (488, 512, 536):
        sponsors[row:row + 5, 568:640] = True
        rgb[row:row + 5, 568:640] = np.array([236, 236, 228], np.uint8)
        rgb[row + 1:row + 4, 578:628:8] = np.array([28, 28, 30], np.uint8)
    sponsors[500:516, 650:696] = True
    rgb[500:516, 650:696] = np.array([224, 224, 216], np.uint8)
    rgb[504:512, 660:686] = np.array([24, 24, 26], np.uint8)
    sponsors[528:540, 606:636] = True
    rgb[528:540, 606:636] = np.array([52, 112, 218], np.uint8)
    rgb[532:536, 614:628] = np.array([232, 232, 224], np.uint8)
    sponsors[546:552, 646:696] = True
    rgb[546:552, 646:696] = np.array([54, 96, 206], np.uint8)
    rgb[548:550, 656:686:8] = np.array([232, 232, 224], np.uint8)
    stamp_red_chip(522, 650)

    # Isolated controls keep the review queue honest.
    stamp_red_chip(700, 180)
    stamp_colored_trim(680, 260)
    sponsors[772:810, 336:466] = True
    rgb[772:810, 336:466] = np.array([214, 28, 42], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": template, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    reasons_by_bbox = {tuple(s["bbox"]): s["review_reason"] for s in suspects}
    assert (356, 304, 9, 5) not in reasons_by_bbox
    assert (388, 326, 5, 14) not in reasons_by_bbox
    assert (430, 286, 1, 34) not in reasons_by_bbox
    assert (650, 522, 9, 5) not in reasons_by_bbox
    assert reasons_by_bbox[(180, 700, 9, 5)] == "red_livery_like_sponsor_review"
    assert reasons_by_bbox[(260, 680, 1, 34)] == "stripe_like_sponsor_review"
    assert reasons_by_bbox[(336, 772, 130, 38)] == "red_livery_like_sponsor_review"


def test_smart_tga_route_inspector_suppresses_compact_red_sponsor_wordmark_panel(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([18, 18, 16], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    def stamp_wordmark_panel(y0, x0):
        sponsors[y0:y0 + 16, x0:x0 + 64] = True
        rgb[y0:y0 + 16, x0:x0 + 64] = np.array([212, 24, 36], np.uint8)
        rgb[y0 + 3:y0 + 11, x0 + 5:x0 + 24] = np.array([238, 236, 228], np.uint8)
        rgb[y0 + 2:y0 + 12, x0 + 28:x0 + 45] = np.array([236, 236, 230], np.uint8)
        rgb[y0 + 4:y0 + 14, x0 + 48:x0 + 60] = np.array([236, 236, 230], np.uint8)
        for col in (8, 16, 31, 39, 52, 58):
            rgb[y0 + 2:y0 + 14, x0 + col:x0 + col + 2] = np.array([24, 20, 22], np.uint8)
        for col in (13, 35, 55):
            rgb[y0 + 7:y0 + 10, x0 + col:x0 + col + 8] = np.array([24, 20, 22], np.uint8)

    def stamp_smooth_panel(y0, x0):
        sponsors[y0:y0 + 16, x0:x0 + 64] = True
        rgb[y0:y0 + 16, x0:x0 + 64] = np.array([212, 24, 36], np.uint8)

    stamp_wordmark_panel(240, 420)
    stamp_smooth_panel(540, 420)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [420, 540, 64, 16]


def test_smart_tga_route_inspector_suppresses_sidecar_red_logo_chip(tmp_path):
    rgb = np.full((1024, 1024, 3), np.array([232, 232, 232], np.uint8), np.uint8)
    numbers = np.zeros((1024, 1024), bool)
    sponsors = np.zeros((1024, 1024), bool)
    empty = np.zeros((1024, 1024), bool)

    chip_shape = np.ones((6, 7), bool)
    chip_shape[0, 0] = False
    chip_shape[5, 6] = False

    def stamp_chip(y0, x0):
        yy, xx = np.indices((6, 7))
        local = np.zeros((6, 7, 3), np.uint8)
        local[:] = np.array([232, 232, 232], np.uint8)
        local[chip_shape] = np.array([188, 14, 24], np.uint8)
        local[chip_shape & (((xx + 2 * yy) % 5) <= 1)] = np.array([30, 4, 8], np.uint8)
        local[chip_shape & (((xx + yy) % 21) == 0)] = np.array([214, 214, 208], np.uint8)
        sponsors[y0:y0 + 6, x0:x0 + 7] |= chip_shape
        rgb[y0:y0 + 6, x0:x0 + 7] = local

    def add_number_bleed_nameplate(y0, x0, *, with_side_sponsor):
        numbers[y0 - 30:y0 + 76, x0 - 62:x0 + 142] = True
        rgb[y0 - 30:y0 + 76, x0 - 62:x0 + 142] = np.array([232, 232, 232], np.uint8)
        if with_side_sponsor:
            sponsors[y0:y0 + 22, x0 + 10:x0 + 96] = True
            numbers[y0:y0 + 22, x0 + 10:x0 + 96] = False
            rgb[y0:y0 + 22, x0 + 10:x0 + 96] = np.array([28, 28, 30], np.uint8)
            rgb[y0 + 4:y0 + 16, x0 + 18:x0 + 88] = np.array([236, 236, 230], np.uint8)
            rgb[y0 + 1:y0 + 8, x0 + 7:x0 + 10] = np.array([178, 18, 26], np.uint8)

    # Positive: the recovered DLM-style chip is next to a separated sponsor
    # nameplate but lives inside broad Number dilation.
    add_number_bleed_nameplate(420, 407, with_side_sponsor=True)
    stamp_chip(420, 407)
    numbers[420:426, 407:414][chip_shape] = False

    # Control: same color/shape in Number bleed without the side sponsor block
    # still belongs in the review queue.
    add_number_bleed_nameplate(610, 407, with_side_sponsor=False)
    stamp_chip(610, 407)
    numbers[610:616, 407:414][chip_shape] = False

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": numbers, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path,
    )

    assert len(suspects) == 1
    assert suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert suspects[0]["bbox"] == [407, 610, 7, 6]


def test_smart_tga_route_inspector_suppresses_repeated_large_number_graphics(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def stamp_number_badge(rgb, numbers, y0, x0):
        yy, xx = np.indices((138, 196))
        core = ((xx >= 10) & (xx <= 185) & (yy >= 3) & (yy <= 134)) | ((xx >= 4) & (xx <= 191) & (yy >= 18) & (yy <= 119))
        corner_trim = ((xx < 15) & (yy < 15)) | ((xx > 180) & (yy < 15)) | ((xx < 15) & (yy > 122)) | ((xx > 180) & (yy > 122))
        texture_holes = ((xx + 2 * yy) % 43) == 0
        badge_mask = core & ~corner_trim & ~texture_holes
        numbers[y0:y0 + 138, x0:x0 + 196] = badge_mask

        badge_rgb = np.full((138, 196, 3), np.array([18, 23, 32], np.uint8), np.uint8)
        badge_rgb[badge_mask] = np.array([35, 82, 178], np.uint8)
        badge_rgb[badge_mask & (((yy // 13) % 2) == 0)] = np.array([238, 240, 232], np.uint8)
        badge_rgb[badge_mask & (((xx + yy) % 19) <= 3)] = np.array([18, 22, 30], np.uint8)
        badge_rgb[badge_mask & ((xx < 13) | (xx > 182) | (yy < 12) | (yy > 125))] = np.array([18, 22, 30], np.uint8)
        rgb[y0:y0 + 138, x0:x0 + 196] = badge_rgb

    rgb_pair = np.full((1024, 1024, 3), np.array([20, 24, 30], np.uint8), np.uint8)
    numbers_pair = np.zeros((1024, 1024), bool)
    stamp_number_badge(rgb_pair, numbers_pair, 350, 340)
    stamp_number_badge(rgb_pair, numbers_pair, 850, 350)

    paired_suspects, _paired_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_pair, "RGB"),
        {"numbers": numbers_pair, "sponsors": empty, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "paired",
    )

    assert paired_suspects == []

    rgb_single = np.full((1024, 1024, 3), np.array([20, 24, 30], np.uint8), np.uint8)
    numbers_single = np.zeros((1024, 1024), bool)
    stamp_number_badge(rgb_single, numbers_single, 350, 340)

    single_suspects, _single_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_single, "RGB"),
        {"numbers": numbers_single, "sponsors": empty, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "single",
    )

    assert len(single_suspects) == 1
    assert single_suspects[0]["review_reason"] == "large_number_badge_or_graphic_review"
    assert single_suspects[0]["bbox"] == [344, 353, 188, 132]


def test_smart_tga_route_inspector_suppresses_varied_scale_race_number_sets(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def stamp_race_number(rgb, numbers, y0, x0, h, w, warm=False):
        yy, xx = np.indices((h, w))
        stroke = max(6, w // 16)
        left_digit = (
            ((xx >= stroke) & (xx <= stroke * 3) & (yy >= stroke) & (yy <= h - stroke))
            | ((xx >= stroke * 3) & (xx <= w // 2 - stroke) & (yy >= h // 2 - stroke) & (yy <= h // 2 + stroke))
            | ((xx >= w // 2 - stroke * 2) & (xx <= w // 2 - stroke) & (yy >= stroke) & (yy <= h - stroke))
            | ((yy >= h - stroke * 2) & (yy <= h - stroke) & (xx >= stroke) & (xx <= w // 2 - stroke))
        )
        cx = int(w * 0.72)
        cy = h // 2
        outer = ((xx - cx) / max(1, w * 0.20)) ** 2 + ((yy - cy) / max(1, h * 0.38)) ** 2 <= 1.0
        inner = ((xx - cx) / max(1, w * 0.11)) ** 2 + ((yy - cy) / max(1, h * 0.22)) ** 2 <= 1.0
        connector = (yy >= h - stroke * 2) & (yy <= h - stroke) & (xx >= w // 2 - stroke) & (xx <= cx)
        mask = (left_digit | (outer & ~inner) | connector) & ~(((xx + 2 * yy) % 53) == 0)
        numbers[y0:y0 + h, x0:x0 + w] = mask

        local = np.full((h, w, 3), np.array([28, 30, 34], np.uint8), np.uint8)
        fill_a = np.array([240, 238, 222], np.uint8) if not warm else np.array([248, 190, 168], np.uint8)
        fill_b = np.array([224, 70, 92], np.uint8) if warm else np.array([76, 144, 214], np.uint8)
        local[mask] = fill_a
        local[mask & (((xx // 9 + yy // 7) % 5) <= 1)] = fill_b
        local[mask & ((xx < stroke * 2) | (yy < stroke * 2) | (yy > h - stroke * 3))] = np.array([20, 22, 28], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    rgb = np.full((1024, 1024, 3), np.array([22, 23, 26], np.uint8), np.uint8)
    numbers = np.zeros((1024, 1024), bool)
    stamp_race_number(rgb, numbers, 210, 270, 124, 330, warm=True)
    stamp_race_number(rgb, numbers, 718, 278, 100, 188, warm=True)
    stamp_race_number(rgb, numbers, 900, 828, 88, 128, warm=True)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": numbers, "sponsors": empty, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "varied-race-numbers",
    )

    assert suspects == []

    def stamp_filled_billboard(rgb, numbers, y0, x0):
        h, w = 118, 220
        yy, xx = np.indices((h, w))
        mask = np.ones((h, w), bool)
        numbers[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([192, 34, 50], np.uint8), np.uint8)
        local[((xx // 7 + yy // 5) % 3) == 0] = np.array([28, 44, 184], np.uint8)
        for band_y in (14, 34, 58, 84):
            local[band_y:band_y + 8, 18:196] = np.array([244, 244, 238], np.uint8)
            local[band_y + 9:band_y + 14, 28:186] = np.array([18, 18, 20], np.uint8)
        local[((xx + yy) % 17) < 3] = np.array([250, 238, 48], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w] = local

    rgb_control = np.full((1024, 1024, 3), np.array([22, 23, 26], np.uint8), np.uint8)
    numbers_control = np.zeros((1024, 1024), bool)
    stamp_filled_billboard(rgb_control, numbers_control, 210, 270)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": numbers_control, "sponsors": empty, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "filled-billboards",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "large_number_badge_or_graphic_review"


def test_smart_tga_route_inspector_suppresses_green_wordmark_separator_bars(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb_panel = np.full((1024, 1024, 3), np.array([24, 34, 28], np.uint8), np.uint8)
    sponsors_panel = np.zeros((1024, 1024), bool)
    rgb_panel[320:470, 80:300] = np.array([78, 184, 36], np.uint8)
    rgb_panel[398:408, 112:252] = np.array([236, 22, 204], np.uint8)
    sponsors_panel[398:408, 112:252] = True
    for i, x0 in enumerate((108, 130, 152, 176, 202, 226)):
        rgb_panel[334 + (i % 2) * 46:370 + (i % 2) * 46, x0:x0 + 12] = np.array([234, 240, 236], np.uint8)
        sponsors_panel[334 + (i % 2) * 46:370 + (i % 2) * 46, x0:x0 + 12] = True

    panel_suspects, _panel_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_panel, "RGB"),
        {"numbers": empty, "sponsors": sponsors_panel, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "panel",
    )

    assert panel_suspects == []

    rgb_livery = np.full((1024, 1024, 3), np.array([26, 28, 34], np.uint8), np.uint8)
    sponsors_livery = np.zeros((1024, 1024), bool)
    rgb_livery[398:408, 112:252] = np.array([236, 22, 204], np.uint8)
    sponsors_livery[398:408, 112:252] = True

    livery_suspects, _livery_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_livery, "RGB"),
        {"numbers": empty, "sponsors": sponsors_livery, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "livery",
    )

    assert len(livery_suspects) == 1
    assert livery_suspects[0]["review_reason"] == "stripe_like_sponsor_review"
    assert livery_suspects[0]["bbox"] == [112, 398, 140, 10]


def test_smart_tga_route_inspector_suppresses_long_sponsor_wordmark_top_strip(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([22, 23, 24], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    y0, x0, bw, bh = 706, 14, 115, 5
    sponsors[y0:y0 + bh, x0:x0 + bw] = True
    rgb[y0:y0 + bh, x0:x0 + bw] = np.array([4, 152, 172], np.uint8)
    rgb[y0:y0 + bh, x0 + 1:x0 + bw:6] = np.array([22, 26, 28], np.uint8)
    rgb[y0 + 1:y0 + bh:2, x0 + 3:x0 + bw:11] = np.array([12, 18, 20], np.uint8)

    # Dense white sponsor lettering sits immediately under the colored strip.
    rgb[y0 + bh + 2:y0 + bh + 20, x0:x0 + bw] = np.array([18, 19, 20], np.uint8)
    for offset in (5, 19, 33, 49, 66, 84, 100):
        rgb[y0 + bh + 4:y0 + bh + 18, x0 + offset:x0 + offset + 8] = np.array([238, 238, 230], np.uint8)
        rgb[y0 + bh + 8:y0 + bh + 10, x0 + offset + 1:x0 + offset + 8] = np.array([18, 19, 20], np.uint8)
        rgb[y0 + bh + 4:y0 + bh + 18:3, x0 + offset + 2:x0 + offset + 4] = np.array([18, 19, 20], np.uint8)
        rgb[y0 + bh + 11:y0 + bh + 13, x0 + offset + 1:x0 + offset + 7] = np.array([238, 238, 230], np.uint8)
    rgb[y0 + bh + 14:y0 + bh + 17, x0 + 3:x0 + bw - 5] = np.array([238, 238, 230], np.uint8)
    rgb[y0 + bh + 15, x0 + 8:x0 + bw - 8:5] = np.array([18, 19, 20], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "wordmark-top-strip",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([22, 23, 24], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[y0:y0 + bh, x0:x0 + bw] = True
    rgb_control[y0:y0 + bh, x0:x0 + bw] = np.array([4, 152, 172], np.uint8)
    rgb_control[y0:y0 + bh, x0 + 1:x0 + bw:6] = np.array([22, 26, 28], np.uint8)
    rgb_control[y0 + 1:y0 + bh:2, x0 + 3:x0 + bw:11] = np.array([12, 18, 20], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "wordmark-top-strip-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "stripe_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [x0, y0, bw, bh]


def test_smart_tga_route_inspector_suppresses_long_textlike_url_sponsor_strip(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([26, 27, 30], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    y0, x0, bw, bh = 727, 82, 186, 13
    sponsors[y0:y0 + bh, x0:x0 + bw] = True
    strip = rgb[y0:y0 + bh, x0:x0 + bw]
    strip[:, :] = np.array([236, 232, 210], np.uint8)
    for col in range(0, bw, 12):
        strip[:, col:col + 5] = np.array([210, 18, 34], np.uint8)
        strip[:, col + 5:col + 8] = np.array([34, 28, 32], np.uint8)
        strip[2:11, col + 8:col + 12] = np.array([242, 238, 226], np.uint8)
        strip[4:6, col + 1:col + 11] = np.array([34, 28, 32], np.uint8)
        strip[8:10, col + 2:col + 10] = np.array([210, 18, 34], np.uint8)
    strip[1:3, :] = np.array([238, 204, 26], np.uint8)
    strip[10:12, 4:bw - 4] = np.array([238, 204, 26], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "url-strip",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([26, 27, 30], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[y0:y0 + bh, x0:x0 + bw] = True
    rgb_control[y0:y0 + bh, x0:x0 + bw] = np.array([28, 212, 184], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "livery-strip-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "stripe_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [x0, y0, bw, bh]


def test_smart_tga_route_inspector_suppresses_long_red_white_sponsor_wordmark(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb = np.full((1024, 1024, 3), np.array([26, 24, 24], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    y0, x0, bw, bh = 710, 28, 224, 40
    word = rgb[y0:y0 + bh, x0:x0 + bw]
    local = sponsors[y0:y0 + bh, x0:x0 + bw]
    for col in range(0, bw - 12, 18):
        local[4:36, col:col + 7] = True
        word[4:36, col:col + 7] = np.array([216, 28, 42], np.uint8)
        local[8:33, col + 4:col + 9] = True
        word[8:33, col + 4:col + 9] = np.array([242, 230, 228], np.uint8)
        local[12:36, col + 8:col + 12] = True
        word[12:36, col + 8:col + 12] = np.array([34, 28, 30], np.uint8)
    local[22:27, 3:bw - 3] = True
    word[22:27, 3:bw - 3] = np.array([210, 22, 38], np.uint8)
    local[17:21, 12:bw - 12:2] = True
    word[17:21, 12:bw - 12:2] = np.array([238, 226, 224], np.uint8)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "red-white-wordmark",
    )

    assert suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([26, 24, 24], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[y0:y0 + bh, x0:x0 + bw] = True
    rgb_control[y0:y0 + bh, x0:x0 + bw] = np.array([214, 30, 36], np.uint8)
    rgb_control[y0 + 12:y0 + 18, x0 + 8:x0 + bw - 8] = np.array([242, 230, 228], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "smooth-red-white-livery-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [x0, y0, bw, bh]


def test_smart_tga_route_inspector_suppresses_sponsor_panel_wordmark_details(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    rgb_green = np.full((1024, 1024, 3), np.array([20, 24, 22], np.uint8), np.uint8)
    sponsors_green = np.zeros((1024, 1024), bool)
    rgb_green[300:382, 92:210] = np.array([62, 198, 42], np.uint8)
    for x0 in (104, 124, 166, 186):
        rgb_green[310:348, x0:x0 + 9] = np.array([238, 240, 232], np.uint8)
    mark_yy, mark_xx = np.indices((15, 9))
    mark_mask = ((mark_xx + 2 * mark_yy) % 7) != 0
    sponsors_green[336:351, 132:141] = mark_mask
    rgb_green[336:351, 132:141][mark_mask] = np.array([226, 36, 72], np.uint8)
    rgb_green[336:351, 132:141][mark_mask & (mark_xx >= 3) & (mark_xx <= 6) & (mark_yy >= 4) & (mark_yy <= 11)] = np.array([242, 238, 226], np.uint8)
    sib_yy, sib_xx = np.indices((16, 8))
    sib_mask = ((sib_xx + sib_yy) % 6) != 0
    sponsors_green[334:350, 143:151] = sib_mask
    rgb_green[334:350, 143:151][sib_mask] = np.array([192, 34, 44], np.uint8)
    rgb_green[334:350, 143:151][sib_mask & (sib_xx >= 3) & (sib_yy >= 4) & (sib_yy <= 11)] = np.array([238, 232, 218], np.uint8)

    green_suspects, _green_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_green, "RGB"),
        {"numbers": empty, "sponsors": sponsors_green, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "green",
    )

    assert green_suspects == []

    rgb_green_control = np.full((1024, 1024, 3), np.array([20, 24, 22], np.uint8), np.uint8)
    sponsors_green_control = np.zeros((1024, 1024), bool)
    sponsors_green_control[336:351, 132:141] = mark_mask
    rgb_green_control[336:351, 132:141][mark_mask] = np.array([226, 36, 72], np.uint8)
    rgb_green_control[336:351, 132:141][mark_mask & (mark_xx >= 3) & (mark_xx <= 6) & (mark_yy >= 4) & (mark_yy <= 11)] = np.array([242, 238, 226], np.uint8)

    green_control_suspects, _green_control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_green_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_green_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "green-control",
    )

    assert len(green_control_suspects) == 1
    assert green_control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert green_control_suspects[0]["bbox"] == [132, 336, 9, 15]

    def stamp_warm_badge(rgb, sponsors, y0, x0):
        yy, xx = np.indices((72, 58))
        mask = (((xx - 29) / 27.0) ** 2 + ((yy - 36) / 34.0) ** 2) <= 1.0
        sponsors[y0:y0 + 72, x0:x0 + 58] = mask
        local = np.full((72, 58, 3), np.array([206, 42, 24], np.uint8), np.uint8)
        local[mask & ((xx + 2 * yy) % 9 <= 4)] = np.array([218, 126, 30], np.uint8)
        local[mask & ((yy % 24) == 0)] = np.array([242, 232, 214], np.uint8)
        local[mask & ((xx % 19) <= 1)] = np.array([222, 164, 34], np.uint8)
        rgb[y0:y0 + 72, x0:x0 + 58][mask] = local[mask]

    rgb_warm = np.full((1024, 1024, 3), np.array([32, 28, 24], np.uint8), np.uint8)
    sponsors_warm = np.zeros((1024, 1024), bool)
    rgb_warm[176:360, 80:260] = np.array([174, 28, 20], np.uint8)
    rgb_warm[176:360:6, 80:260] = np.array([224, 166, 28], np.uint8)
    stamp_warm_badge(rgb_warm, sponsors_warm, 220, 142)
    sponsors_warm[224:258, 92:124] = True
    rgb_warm[224:258, 92:124] = np.array([242, 230, 206], np.uint8)
    rgb_warm[228:252:6, 96:120] = np.array([224, 154, 28], np.uint8)
    sponsors_warm[308:332, 128:158] = True
    rgb_warm[308:332, 128:158] = np.array([240, 226, 204], np.uint8)
    rgb_warm[312:328:5, 132:154] = np.array([220, 140, 30], np.uint8)

    warm_suspects, _warm_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_warm, "RGB"),
        {"numbers": empty, "sponsors": sponsors_warm, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "warm",
    )

    assert warm_suspects == []

    rgb_warm_control = np.full((1024, 1024, 3), np.array([32, 28, 24], np.uint8), np.uint8)
    sponsors_warm_control = np.zeros((1024, 1024), bool)
    rgb_warm_control[176:360, 80:260] = np.array([174, 28, 20], np.uint8)
    rgb_warm_control[176:360:6, 80:260] = np.array([224, 166, 28], np.uint8)
    stamp_warm_badge(rgb_warm_control, sponsors_warm_control, 220, 142)

    warm_control_suspects, _warm_control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_warm_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_warm_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "warm-control",
    )

    assert len(warm_control_suspects) == 1
    assert warm_control_suspects[0]["review_reason"] == "decorative_livery_like_sponsor_review"
    assert warm_control_suspects[0]["bbox"] == [144, 222, 55, 69]


def test_smart_tga_route_inspector_suppresses_orange_cream_sponsor_logo_clusters(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def stamp_orange_logo_panel(rgb, sponsors, x0, y0):
        h, w = 110, 130
        yy, xx = np.indices((h, w))
        mask = (
            ((yy % 4) < 2)
            | (xx < 12)
            | (xx >= w - 12)
            | ((yy > 45) & (yy < 55))
        )
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([38, 30, 24], np.uint8), np.uint8)
        orange = ((xx // 4 + yy // 4) % 10) <= 5
        local[mask & orange] = np.array([222, 82, 28], np.uint8)
        local[mask & ~orange] = np.array([38, 30, 24], np.uint8)
        cream = mask & (
            ((xx > 52) & (xx < 80) & (yy > 28) & (yy < 36))
            | ((xx > 78) & (xx < 104) & (yy > 72) & (yy < 78))
        )
        local[cream] = np.array([226, 196, 144], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    def add_tiny_fragment_context(rgb):
        yy, xx = np.indices((70, 100))
        red_context = ((xx // 4 + yy // 4) % 9) <= 2
        rgb[20:90, 910:1010][red_context] = np.array([180, 54, 24], np.uint8)
        rgb[20:90, 910:1010][~red_context] = np.array([30, 24, 22], np.uint8)

    def stamp_tiny_fragment(rgb, sponsors, x0, y0, w, h):
        yy, xx = np.indices((h, w))
        mask = (
            ((xx - (w - 1) / 2) / (w * 0.42)) ** 2
            + ((yy - (h - 1) / 2) / (h * 0.42)) ** 2
        ) <= 1.0
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([226, 86, 28], np.uint8), np.uint8)
        local[mask & (((xx + yy) % 17) == 0)] = np.array([236, 190, 118], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    rgb_cluster = np.full((1024, 1024, 3), np.array([24, 23, 22], np.uint8), np.uint8)
    sponsors_cluster = np.zeros((1024, 1024), bool)
    stamp_orange_logo_panel(rgb_cluster, sponsors_cluster, 310, 230)
    stamp_orange_logo_panel(rgb_cluster, sponsors_cluster, 810, 800)
    add_tiny_fragment_context(rgb_cluster)
    stamp_tiny_fragment(rgb_cluster, sponsors_cluster, 930, 36, 32, 39)
    stamp_tiny_fragment(rgb_cluster, sponsors_cluster, 970, 34, 27, 42)

    cluster_suspects, _cluster_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_cluster, "RGB"),
        {"numbers": empty, "sponsors": sponsors_cluster, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "cluster",
    )

    assert cluster_suspects == []

    rgb_single_panel = np.full((1024, 1024, 3), np.array([24, 23, 22], np.uint8), np.uint8)
    sponsors_single_panel = np.zeros((1024, 1024), bool)
    stamp_orange_logo_panel(rgb_single_panel, sponsors_single_panel, 310, 230)

    panel_suspects, _panel_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_single_panel, "RGB"),
        {"numbers": empty, "sponsors": sponsors_single_panel, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "single-panel",
    )

    assert len(panel_suspects) == 1
    assert panel_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert panel_suspects[0]["bbox"] == [310, 230, 130, 110]

    rgb_single_fragment = np.full((1024, 1024, 3), np.array([24, 23, 22], np.uint8), np.uint8)
    sponsors_single_fragment = np.zeros((1024, 1024), bool)
    add_tiny_fragment_context(rgb_single_fragment)
    stamp_tiny_fragment(rgb_single_fragment, sponsors_single_fragment, 930, 36, 32, 39)

    fragment_suspects, _fragment_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_single_fragment, "RGB"),
        {"numbers": empty, "sponsors": sponsors_single_fragment, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "single-fragment",
    )

    assert len(fragment_suspects) == 1
    assert fragment_suspects[0]["review_reason"] == "decorative_livery_like_sponsor_review"
    assert fragment_suspects[0]["bbox"] == [933, 39, 26, 33]


def test_smart_tga_route_inspector_suppresses_bright_orange_mascot_logo_panels(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def stamp_mascot_panel(rgb, sponsors, x0, y0, w=124, h=106):
        yy, xx = np.indices((h, w))
        mask = ((xx + 2 * yy) % 4) != 0
        rgb[y0:y0 + h, x0:x0 + w] = np.array([238, 84, 24], np.uint8)
        local = rgb[y0:y0 + h, x0:x0 + w]
        cream = (((xx - w * 0.52) / (w * 0.22)) ** 2 + ((yy - h * 0.46) / (h * 0.30)) ** 2) <= 1.0
        white = (((xx - w * 0.34) / (w * 0.14)) ** 2 + ((yy - h * 0.32) / (h * 0.12)) ** 2) <= 1.0
        dark = (
            ((yy > h * 0.18) & (yy < h * 0.23) & (xx > w * 0.12) & (xx < w * 0.86))
            | ((xx > w * 0.72) & (xx < w * 0.78) & (yy > h * 0.24) & (yy < h * 0.78))
            | ((yy % 9) <= 1)
            | ((xx % 29) <= 1)
        )
        local[cream & mask] = np.array([214, 192, 164], np.uint8)
        local[white & mask] = np.array([244, 236, 226], np.uint8)
        local[dark & mask] = np.array([40, 30, 26], np.uint8)
        sponsors[y0:y0 + h, x0:x0 + w] = mask

    def stamp_chip(rgb, sponsors, x0, y0):
        h, w = 28, 26
        yy, xx = np.indices((h, w))
        mask = ((xx + yy) % 6) != 0
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        rgb[y0:y0 + h, x0:x0 + w] = np.array([238, 84, 24], np.uint8)
        chip = rgb[y0:y0 + h, x0:x0 + w]
        chip[(yy >= 6) & (yy < 9) & (xx >= 9) & (xx < 16) & mask] = np.array([46, 32, 28], np.uint8)
        chip[(yy >= 13) & (yy < 17) & (xx >= 11) & (xx < 17) & mask] = np.array([222, 190, 154], np.uint8)
        chip[((xx % 17) == 0) & mask] = np.array([46, 32, 28], np.uint8)

    def stamp_single_mascot_decal(rgb, sponsors, x0, y0):
        h, w = 87, 123
        yy, xx = np.indices((h, w))
        body = (
            ((xx - w * 0.46) / (w * 0.38)) ** 2
            + ((yy - h * 0.50) / (h * 0.36)) ** 2
        ) <= 1.0
        head = (
            ((xx - w * 0.70) / (w * 0.20)) ** 2
            + ((yy - h * 0.38) / (h * 0.22)) ** 2
        ) <= 1.0
        mask = (body | head) & (((xx + 2 * yy) % 5) != 0)
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([212, 78, 38], np.uint8), np.uint8)
        white = (
            (((xx - w * 0.33) / (w * 0.18)) ** 2 + ((yy - h * 0.43) / (h * 0.13)) ** 2 <= 1.0)
            | (((xx - w * 0.62) / (w * 0.17)) ** 2 + ((yy - h * 0.60) / (h * 0.12)) ** 2 <= 1.0)
        )
        dark = (
            ((yy > h * 0.22) & (yy < h * 0.27) & (xx > w * 0.14) & (xx < w * 0.86))
            | ((xx > w * 0.74) & (xx < w * 0.80) & (yy > h * 0.20) & (yy < h * 0.74))
            | (((xx + yy) % 17) <= 1)
        )
        tan = (
            (((xx - w * 0.50) / (w * 0.26)) ** 2 + ((yy - h * 0.50) / (h * 0.23)) ** 2 <= 1.0)
            & ~white
            & ~dark
        )
        local[tan & mask] = np.array([210, 174, 132], np.uint8)
        local[white & mask] = np.array([244, 238, 226], np.uint8)
        local[dark & mask] = np.array([42, 32, 28], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    rgb = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    stamp_mascot_panel(rgb, sponsors, 38, 710, 138, 132)
    stamp_mascot_panel(rgb, sponsors, 720, 512, 106, 90)
    stamp_mascot_panel(rgb, sponsors, 136, 260, 172, 62)
    stamp_chip(rgb, sponsors, 744, 438)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "bright-mascot-panels",
    )

    assert suspects == []

    rgb_single = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors_single = np.zeros((1024, 1024), bool)
    stamp_single_mascot_decal(rgb_single, sponsors_single, 696, 480)

    single_suspects, _single_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_single, "RGB"),
        {"numbers": empty, "sponsors": sponsors_single, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "single-rich-mascot-panel",
    )

    assert single_suspects == []

    rgb_control = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors_control = np.zeros((1024, 1024), bool)
    sponsors_control[710:842, 38:176] = True
    rgb_control[710:842, 38:176] = np.array([238, 84, 24], np.uint8)

    control_suspects, _control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "single-smooth-orange-panel-control",
    )

    assert len(control_suspects) == 1
    assert control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert control_suspects[0]["bbox"] == [38, 710, 138, 132]


def test_smart_tga_route_inspector_suppresses_red_white_sponsor_icon_cells(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def stamp_tiny_icon(rgb, sponsors, x0, y0):
        h = w = 22
        yy, xx = np.indices((h, w))
        mask = np.ones((h, w), bool)
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([235, 35, 58], np.uint8), np.uint8)
        white = ((xx >= 7) & (xx <= 15) & (yy >= 4) & (yy <= 17)) | ((yy >= 9) & (yy <= 12))
        local[white] = np.array([246, 240, 232], np.uint8)
        local[((xx + yy) % 11) == 0] = np.array([220, 28, 48], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    def stamp_neighbor_logo(rgb, sponsors, x0, y0, w, h):
        yy, xx = np.indices((h, w))
        mask = ((xx + yy) % 5) != 0
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([38, 34, 32], np.uint8), np.uint8)
        local[mask & ((xx % 13) < 5)] = np.array([238, 236, 230], np.uint8)
        local[mask & ((yy % 17) < 4)] = np.array([190, 28, 48], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    def stamp_stacked_red_logo(rgb, sponsors, x0, y0):
        h, w = 99, 70
        yy, xx = np.indices((h, w))
        mask = np.ones((h, w), bool)
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([205, 34, 56], np.uint8), np.uint8)
        x_a = (xx - w * 0.5) + (yy - h * 0.5) * 0.52
        x_b = (xx - w * 0.5) - (yy - h * 0.5) * 0.52
        white = (np.abs(x_a) < 8) | (np.abs(x_b) < 8)
        dark = (yy < 14) | ((xx < 8) & (yy > 12) & (yy < 48))
        local[white] = np.array([244, 236, 226], np.uint8)
        local[dark] = np.array([44, 38, 38], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    def stamp_dark_sibling(rgb, sponsors, x0, y0):
        h, w = 64, 60
        yy, xx = np.indices((h, w))
        mask = ((xx + 2 * yy) % 4) != 0
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([48, 44, 54], np.uint8), np.uint8)
        local[mask & ((xx % 12) < 3)] = np.array([235, 232, 226], np.uint8)
        local[mask & ((yy % 19) < 4)] = np.array([24, 22, 25], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    rgb = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    stamp_neighbor_logo(rgb, sponsors, 308, 236, 95, 84)
    stamp_neighbor_logo(rgb, sponsors, 408, 237, 43, 82)
    stamp_tiny_icon(rgb, sponsors, 472, 227)
    stamp_neighbor_logo(rgb, sponsors, 492, 269, 115, 33)
    stamp_stacked_red_logo(rgb, sponsors, 712, 406)
    stamp_dark_sibling(rgb, sponsors, 722, 512)

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "sponsor-icon-cells",
    )

    assert suspects == []

    rgb_tiny_control = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors_tiny_control = np.zeros((1024, 1024), bool)
    sponsors_tiny_control[227:249, 472:494] = True
    rgb_tiny_control[227:249, 472:494] = np.array([235, 35, 58], np.uint8)

    tiny_control_suspects, _tiny_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_tiny_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_tiny_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "standalone-smooth-red-square-control",
    )

    assert len(tiny_control_suspects) == 1
    assert tiny_control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert tiny_control_suspects[0]["bbox"] == [472, 227, 22, 22]

    rgb_panel_control = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors_panel_control = np.zeros((1024, 1024), bool)
    sponsors_panel_control[406:505, 712:782] = True
    rgb_panel_control[406:505, 712:782] = np.array([205, 34, 56], np.uint8)

    panel_control_suspects, _panel_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_panel_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_panel_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "standalone-smooth-red-panel-control",
    )

    assert len(panel_control_suspects) == 1
    assert panel_control_suspects[0]["review_reason"] == "red_livery_like_sponsor_review"
    assert panel_control_suspects[0]["bbox"] == [712, 406, 70, 99]


def test_smart_tga_route_inspector_suppresses_clustered_red_white_sponsor_decals(tmp_path):
    empty = np.zeros((1024, 1024), bool)

    def stamp_red_wordmark(rgb, sponsors, x0, y0):
        h, w = 12, 36
        yy, xx = np.indices((h, w))
        mask = np.ones((h, w), bool)
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([218, 32, 42], np.uint8), np.uint8)
        white = (
            ((yy >= 2) & (yy <= 4) & (xx >= 4) & (xx <= 28))
            | ((yy >= 7) & (yy <= 9) & (xx >= 12) & (xx <= 34))
            | ((xx % 11) == 0)
        )
        local[white] = np.array([244, 238, 230], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w] = local

    def stamp_red_card(rgb, sponsors, x0, y0):
        h, w = 33, 69
        yy, xx = np.indices((h, w))
        mask = np.ones((h, w), bool)
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array([214, 38, 52], np.uint8), np.uint8)
        white = (
            ((yy >= 8) & (yy <= 14) & (xx >= 9) & (xx <= 58))
            | ((yy >= 18) & (yy <= 23) & (xx >= 17) & (xx <= 62))
        )
        dark = ((xx + yy) % 17) == 0
        local[white] = np.array([244, 236, 224], np.uint8)
        local[dark] = np.array([44, 34, 36], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w] = local

    def stamp_neighbor(rgb, sponsors, x0, y0, w, h, color):
        yy, xx = np.indices((h, w))
        mask = ((xx + 2 * yy) % 5) != 0
        sponsors[y0:y0 + h, x0:x0 + w] = mask
        local = np.full((h, w, 3), np.array(color, np.uint8), np.uint8)
        local[mask & ((xx % 13) <= 2)] = np.array([246, 240, 232], np.uint8)
        local[mask & ((yy % 11) <= 1)] = np.array([28, 26, 24], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][mask] = local[mask]

    rgb = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors = np.zeros((1024, 1024), bool)
    stamp_red_wordmark(rgb, sponsors, 516, 232)
    stamp_neighbor(rgb, sponsors, 471, 263, 107, 34, [42, 38, 36])
    stamp_neighbor(rgb, sponsors, 399, 300, 150, 18, [32, 30, 30])
    stamp_red_card(rgb, sponsors, 528, 744)
    stamp_neighbor(rgb, sponsors, 500, 787, 37, 14, [210, 42, 48])
    stamp_neighbor(rgb, sponsors, 451, 787, 47, 15, [52, 46, 44])
    stamp_neighbor(rgb, sponsors, 498, 821, 42, 14, [34, 74, 34])
    stamp_neighbor(rgb, sponsors, 447, 821, 51, 14, [38, 42, 40])

    suspects, _sheet = _suspect_review_for_masks(
        Image.fromarray(rgb, "RGB"),
        {"numbers": empty, "sponsors": sponsors, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "clustered-red-white-sponsor-decals",
    )

    assert suspects == []

    rgb_smooth_control = np.full((1024, 1024, 3), np.array([248, 248, 246], np.uint8), np.uint8)
    sponsors_smooth_control = np.zeros((1024, 1024), bool)
    sponsors_smooth_control[744:777, 528:597] = True
    rgb_smooth_control[744:777, 528:597] = np.array([214, 38, 52], np.uint8)
    stamp_neighbor(rgb_smooth_control, sponsors_smooth_control, 500, 787, 37, 14, [210, 42, 48])
    stamp_neighbor(rgb_smooth_control, sponsors_smooth_control, 451, 787, 47, 15, [52, 46, 44])

    smooth_control, _smooth_control_sheet = _suspect_review_for_masks(
        Image.fromarray(rgb_smooth_control, "RGB"),
        {"numbers": empty, "sponsors": sponsors_smooth_control, "template": empty, "brand_graphics": empty, "paint": empty},
        tmp_path / "smooth-red-panel-with-neighbors-control",
    )

    assert any(
        s["review_reason"] == "red_livery_like_sponsor_review" and s["bbox"] == [528, 744, 69, 33]
        for s in smooth_control
    )
