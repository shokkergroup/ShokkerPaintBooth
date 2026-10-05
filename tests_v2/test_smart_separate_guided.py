"""SMART SEPARATE STUDIO guided-separation tests (2026-06-26).

Verifies the GUIDED re-sort + grow + refine pass on a synthetic livery:
  * a number_hint over a number block lands those pixels in NUMBERS (not SPONSORS),
  * an exclude_mask over part of the active layer removes those pixels,
  * it NEVER raises (all-paint input, busy input), and
  * it always returns FULL-RES uint8 masks (255 = member).
ADDITIVE — does not touch separate_livery_layers.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from engine.spec_sculpt import car_layers as car_layers_mod
from engine.spec_sculpt import smart_separate as smart_sep_mod
from engine.spec_sculpt.generate import separate_livery_layers_guided
from engine.spec_sculpt.car_layers import (
    folder_slug_from_path,
    hint_from_path,
    template_brand_compatible,
)


def test_smart_tga_ocr_poly_restore_covers_rotation_and_reflection():
    work_h, work_w = 73, 119
    source = np.array([[13, 7], [46, 7], [46, 31], [13, 31]], dtype=np.float32)

    for mirrored in (False, True):
        base = source.copy()
        if mirrored:
            base[:, 0] = work_w - 1 - base[:, 0]
        for rot in (0, 1, 2, 3):
            if rot == 0:
                observed = base.copy()
                rotated_shape = (work_h, work_w)
            elif rot == 1:
                observed = np.stack([base[:, 1], work_w - 1 - base[:, 0]], axis=1)
                rotated_shape = (work_w, work_h)
            elif rot == 2:
                observed = np.stack(
                    [work_w - 1 - base[:, 0], work_h - 1 - base[:, 1]], axis=1
                )
                rotated_shape = (work_h, work_w)
            else:
                observed = np.stack([work_h - 1 - base[:, 1], base[:, 0]], axis=1)
                rotated_shape = (work_w, work_h)

            restored = smart_sep_mod._restore_ocr_poly(
                observed, rot, rotated_shape, (work_h, work_w), mirrored=mirrored
            )
            assert np.allclose(restored, source)


def test_smart_tga_mirror_ocr_feature_gate(monkeypatch):
    monkeypatch.delenv("SPB_SMART_TGA_MIRROR_OCR", raising=False)
    assert smart_sep_mod._mirror_ocr_enabled() is True
    monkeypatch.setenv("SPB_SMART_TGA_MIRROR_OCR", "0")
    assert smart_sep_mod._mirror_ocr_enabled() is False
    assert smart_sep_mod._mirror_ocr_enabled(True) is True
    assert smart_sep_mod._mirror_ocr_enabled(False) is False


def test_smart_tga_mirror_only_numeric_starts_as_sponsor():
    poly = np.array([[10, 10], [30, 10], [30, 40], [10, 40]], dtype=np.float32)
    mirror_box = {
        "poly": poly.copy(), "text": "5", "conf": 0.91,
        "h": 30.0, "w": 20.0, "seen_mirrored": True, "seen_unmirrored": False,
    }
    normal_box = {
        "poly": poly.copy() + np.array([50, 0], dtype=np.float32),
        "text": "5", "conf": 0.88, "h": 30.0, "w": 20.0,
        "seen_mirrored": False, "seen_unmirrored": True,
    }

    numbers, sponsors = smart_sep_mod._classify([mirror_box, normal_box], 100, 100)
    assert normal_box in numbers
    assert mirror_box in sponsors
    assert mirror_box["mirror_only"] is True


def test_smart_tga_ocr_dedup_preserves_both_orientation_sources():
    poly = np.array([[10, 10], [30, 10], [30, 40], [10, 40]], dtype=np.float32)
    mirrored = {
        "poly": poly.copy(), "text": "15", "conf": 0.95,
        "seen_mirrored": True, "seen_unmirrored": False,
    }
    normal = {
        "poly": poly.copy(), "text": "15", "conf": 0.80,
        "seen_mirrored": False, "seen_unmirrored": True,
    }
    kept = smart_sep_mod._dedup([mirrored, normal])
    assert len(kept) == 1
    assert kept[0]["seen_mirrored"] is True
    assert kept[0]["seen_unmirrored"] is True


def test_smart_tga_ocr_box_overlap_uses_smaller_box_area():
    outer = {"poly": np.array([[0, 0], [40, 0], [40, 40], [0, 40]], dtype=np.float32)}
    inner = {"poly": np.array([[10, 10], [20, 10], [20, 20], [10, 20]], dtype=np.float32)}
    separate = {"poly": inner["poly"] + np.array([50, 0], dtype=np.float32)}
    assert smart_sep_mod._box_overlap_min(outer, inner) == pytest.approx(1.0)
    assert smart_sep_mod._box_overlap_min(outer, separate) == pytest.approx(0.0)


def test_smart_tga_mirror_supplement_cannot_change_initial_numbers(monkeypatch):
    normal = {
        "poly": np.array([[8, 8], [24, 8], [24, 34], [8, 34]], dtype=np.float32),
        "text": "7", "conf": 0.95, "h": 26.0, "w": 16.0,
        "rotation": 0, "mirrored": False,
        "seen_mirrored": False, "seen_unmirrored": True,
    }
    reflected_sponsor = {
        "poly": np.array([[38, 40], [62, 40], [62, 52], [38, 52]], dtype=np.float32),
        "text": "MOPAR", "conf": 0.90, "h": 12.0, "w": 24.0,
        "rotation": 0, "mirrored": True,
        "seen_mirrored": True, "seen_unmirrored": False,
    }

    def fake_boxes(_rgb, min_conf=0.30, rotations=(0, 2), mirror_ocr=None):
        result = [dict(normal)]
        if smart_sep_mod._mirror_ocr_enabled(mirror_ocr):
            result.append(dict(reflected_sponsor))
        return result

    def fake_mask(_rgb, boxes, h, w, dilate=1):
        mask = np.zeros((h, w), np.uint8)
        for box in boxes:
            x0 = int(box["poly"][:, 0].min()); x1 = int(box["poly"][:, 0].max())
            y0 = int(box["poly"][:, 1].min()); y1 = int(box["poly"][:, 1].max())
            mask[y0:y1, x0:x1] = 255
        return mask

    monkeypatch.setattr(smart_sep_mod, "_ocr_boxes", fake_boxes)
    monkeypatch.setattr(smart_sep_mod, "_reader", lambda: object())
    monkeypatch.setattr(smart_sep_mod, "_crop_reads_as_word", lambda *args, **kwargs: False)
    monkeypatch.setattr(smart_sep_mod, "_big_number_rescue", lambda *args, **kwargs: [])
    monkeypatch.setattr(smart_sep_mod, "_tight_glyph_mask", fake_mask)

    rgb = np.zeros((64, 72, 3), np.uint8)
    legacy = smart_sep_mod.separate_livery_layers_smart(rgb, mirror_ocr=False)
    mirrored = smart_sep_mod.separate_livery_layers_smart(rgb, mirror_ocr=True)
    assert np.array_equal(legacy["numbers"], mirrored["numbers"])
    assert int((legacy["sponsors"] > 0).sum()) == 0
    assert int((mirrored["sponsors"] > 0).sum()) == 24 * 12


def _synthetic_livery(n=256):
    """Gray base + a white '55'-ish number block + a colored 'sponsor' rectangle, far apart."""
    a = np.full((n, n, 3), 0.45, np.float32)            # mid-gray base paint
    # NUMBER block: bright white "55" region, upper-left
    ny0, ny1, nx0, nx1 = 40, 110, 40, 130
    a[ny0:ny1, nx0:nx1] = 0.97
    # SPONSOR rectangle: saturated orange wordmark, lower-right (well separated from the number)
    sy0, sy1, sx0, sx1 = 170, 215, 150, 230
    a[sy0:sy1, sx0:sx1] = np.array([0.92, 0.45, 0.05], np.float32)
    return a, (ny0, ny1, nx0, nx1), (sy0, sy1, sx0, sx1)


def _box_mask(n, y0, y1, x0, x1):
    m = np.zeros((n, n), np.uint8)
    m[y0:y1, x0:x1] = 255
    return m


def _all_dict_fullres(res, n):
    assert isinstance(res, dict)
    for k in ("numbers", "sponsors", "paint"):
        assert k in res, f"missing {k}"
        m = res[k]
        assert m.dtype == np.uint8, f"{k} not uint8"
        assert m.shape == (n, n), f"{k} not full-res {m.shape} != {(n, n)}"


def test_number_hint_lands_in_numbers_not_sponsors():
    n = 256
    tex, (ny0, ny1, nx0, nx1), _sp = _synthetic_livery(n)
    # hint a core square inside the number block
    hint = _box_mask(n, ny0 + 12, ny1 - 12, nx0 + 12, nx1 - 12)
    res = separate_livery_layers_guided(tex, number_hint=hint, sensitivity=1.0, number_size=1.0)
    _all_dict_fullres(res, n)
    nm, sp = res["numbers"], res["sponsors"]
    core = (slice(ny0 + 18, ny1 - 18), slice(nx0 + 18, nx1 - 18))
    # the hinted region must be NUMBERS, and NOT sponsors
    assert (nm[core] > 0).mean() > 0.6, "number_hint did not put the block into NUMBERS"
    assert (sp[core] > 0).mean() < 0.2, "hinted number block leaked into SPONSORS"


def test_exclude_mask_removes_pixels_from_active_layer():
    n = 256
    tex, (ny0, ny1, nx0, nx1), _sp = _synthetic_livery(n)
    hint = _box_mask(n, ny0 + 12, ny1 - 12, nx0 + 12, nx1 - 12)
    base = separate_livery_layers_guided(tex, number_hint=hint, sensitivity=1.0, number_size=1.0)
    _all_dict_fullres(base, n)
    # echo the result back as base_masks, then exclude the LEFT HALF of the number from NUMBERS
    ex_x1 = (nx0 + nx1) // 2
    excl = _box_mask(n, ny0, ny1, nx0, ex_x1)
    res = separate_livery_layers_guided(
        tex, number_hint=hint, exclude_mask=excl, active_layer="numbers",
        base_masks={k: base[k] for k in ("numbers", "sponsors", "paint")},
        sensitivity=1.0, number_size=1.0)
    _all_dict_fullres(res, n)
    nm = res["numbers"]
    excluded_core = (slice(ny0 + 14, ny1 - 14), slice(nx0 + 6, ex_x1 - 6))
    assert (nm[excluded_core] > 0).mean() < 0.15, "exclude_mask did not remove pixels from NUMBERS"


def test_no_exception_on_all_paint():
    n = 128
    tex = np.full((n, n, 3), 0.5, np.float32)            # featureless -> no decals
    res = separate_livery_layers_guided(tex)
    _all_dict_fullres(res, n)
    # nothing to detect -> essentially all paint
    assert (res["paint"] > 0).mean() > 0.9


def test_no_exception_on_busy_input():
    rng = np.random.default_rng(7)
    n = 192
    tex = rng.random((n, n, 3)).astype(np.float32)      # pure noise (busy base)
    h = _box_mask(n, 20, 60, 20, 60)
    res = separate_livery_layers_guided(tex, number_hint=h, sponsor_hint=h,
                                        include_mask=h, exclude_mask=h, active_layer="paint")
    _all_dict_fullres(res, n)


def test_returns_fullres_for_nonsquare():
    h, w = 200, 320
    tex = np.full((h, w, 3), 0.4, np.float32)
    tex[40:90, 40:140] = 0.95                            # a bright block
    hint = np.zeros((h, w), np.uint8); hint[55:75, 60:120] = 255
    res = separate_livery_layers_guided(tex, number_hint=hint)
    assert isinstance(res, dict)
    for k in ("numbers", "sponsors", "paint"):
        assert res[k].shape == (h, w), f"{k} not full-res {res[k].shape} != {(h, w)}"
        assert res[k].dtype == np.uint8


def test_smart_tga_known_legacy_folder_hints_resolve_to_template_slugs():
    cases = {
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\audir8gt3\car_296558.tga": "audir8lmsevo2gt3",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\dirtlatemodel 438\car_23371.tga": "dirtlatemodel_358",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\ferrari488gte\car_23371.tga": "ferrari488gt3",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\mercedesamggt3\car_team_132490.tga": "mercedesamgevogt3",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\stockcars chevycamarozl12022\car_num_23371.tga": "stockcars_camarozl12018",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\stockcars toyotacamry\car_1002478.tga": "stockcars2_camry2015",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\stockcars2 chevy cot\car_23371.tga": "stockcars2_chevy_gen4cup",
        r"C:\Users\Ricky's PC\Documents\iRacing\paint\streetstock streetstock3\car_230331.tga": "streetstock_streetstock2",
    }
    for path, expected_slug in cases.items():
        slug, family = hint_from_path(path)
        assert slug == expected_slug
        assert family is not None


def test_smart_tga_folder_hint_uses_selected_iracing_folder_slug():
    folder = r"C:\Users\Ricky's PC\Documents\iRacing\paint\superlatemodel"

    assert folder_slug_from_path(folder) == "superlatemodel"
    slug, family = hint_from_path(folder)
    assert slug == "superlatemodel"
    assert family == "dirt_late_model"


def test_smart_tga_template_brand_guard_blocks_obvious_wrong_stockcar_make():
    camaro_path = r"C:\Users\Ricky's PC\Documents\iRacing\paint\stockcars2 nwcamaro2014\car_23371.tga"
    source_slug = folder_slug_from_path(camaro_path)

    assert source_slug == "stockcars2_nwcamaro2014"
    assert not template_brand_compatible(source_slug, "stockcars2_nwford2013")
    assert not template_brand_compatible(source_slug, "stockcars2_camry2015")
    assert template_brand_compatible(source_slug, "stockcars_camarozl12018")
    assert template_brand_compatible(source_slug, "stockcars2_chevy_gen4cup")
    assert template_brand_compatible("dirtlatemodel_438", "dirtlatemodel_358")


def test_smart_tga_template_brand_guard_blocks_obvious_wrong_road_make():
    assert not template_brand_compatible("bmwm4gt4", "ferrarievogt3")
    assert not template_brand_compatible("ferrari296gt3", "c8rvettegte")
    assert not template_brand_compatible("audirs3lms", "stockcars2_chevy_gen4cup")
    assert not template_brand_compatible("porsche919", "radical_sr8")
    assert template_brand_compatible("bmwm4gt4", "bmwm4gt3")
    assert template_brand_compatible("porsche718gt4_copy", "porsche911rgt3")
    assert template_brand_compatible("unknownfolder", "ferrarievogt3")


def test_smart_tga_template_guard_reports_blocked_make_mismatch(monkeypatch):
    tex = np.zeros((32, 32, 3), np.float32)
    small_prior = np.zeros((32, 32), bool)
    small_prior[:2, :2] = True

    monkeypatch.setattr(
        car_layers_mod,
        "identify_car",
        lambda _tex, family_hint=None: [{"slug": "stockcars2_nwford2013", "score": 0.2369}],
    )
    monkeypatch.setattr(car_layers_mod, "_template_prior", lambda _slug, _h, _w: small_prior)

    blocked = car_layers_mod.separate_into_layers(
        tex, use_ocr=False, car_family_hint="nascar_stockcar",
        source_slug_hint="stockcars2_nwcamaro2014",
    )
    assert blocked["template_guard"]["status"] == "blocked"
    assert blocked["template_guard"]["reason"] == "make_mismatch"
    assert blocked["layers"]["template"].sum() == 0

    monkeypatch.setattr(
        car_layers_mod,
        "identify_car",
        lambda _tex, family_hint=None: [{"slug": "stockcars_camarozl12018", "score": 0.2369}],
    )
    applied = car_layers_mod.separate_into_layers(
        tex, use_ocr=False, car_family_hint="nascar_stockcar",
        source_slug_hint="stockcars2_nwcamaro2014",
    )
    assert applied["template_guard"]["status"] == "applied"
    assert applied["layers"]["template"].sum() > 0


def test_smart_tga_template_guard_reports_blocked_road_make_mismatch(monkeypatch):
    tex = np.zeros((32, 32, 3), np.float32)
    small_prior = np.zeros((32, 32), bool)
    small_prior[:2, :2] = True

    monkeypatch.setattr(
        car_layers_mod,
        "identify_car",
        lambda _tex, family_hint=None: [{"slug": "ferrarievogt3", "score": 0.2369}],
    )
    monkeypatch.setattr(car_layers_mod, "_template_prior", lambda _slug, _h, _w: small_prior)

    blocked = car_layers_mod.separate_into_layers(
        tex, use_ocr=False, car_family_hint="gt_road",
        source_slug_hint="bmwm4gt4",
    )
    assert blocked["template_guard"]["status"] == "blocked"
    assert blocked["template_guard"]["reason"] == "make_mismatch"
    assert blocked["template_guard"]["source_slug"] == "bmwm4gt4"
    assert blocked["template_guard"]["matched_slug"] == "ferrarievogt3"
    assert blocked["layers"]["template"].sum() == 0

    monkeypatch.setattr(
        car_layers_mod,
        "identify_car",
        lambda _tex, family_hint=None: [{"slug": "bmwm4gt3", "score": 0.2369}],
    )
    applied = car_layers_mod.separate_into_layers(
        tex, use_ocr=False, car_family_hint="gt_road",
        source_slug_hint="bmwm4gt4",
    )
    assert applied["template_guard"]["status"] == "applied"
    assert applied["layers"]["template"].sum() > 0


def test_smart_tga_unknown_source_template_prior_requires_strong_confidence(monkeypatch):
    tex = np.zeros((32, 32, 3), np.float32)
    small_prior = np.zeros((32, 32), bool)
    small_prior[:2, :2] = True
    monkeypatch.setattr(car_layers_mod, "_template_prior", lambda _slug, _h, _w: small_prior)

    monkeypatch.setattr(
        car_layers_mod,
        "identify_car",
        lambda _tex, family_hint=None: [{"slug": "dirtlatemodel_358", "score": 0.60}],
    )
    blocked = car_layers_mod.separate_into_layers(
        tex, use_ocr=False, source_slug_hint="1shokker_paint_car_examples"
    )
    assert blocked["template_guard"]["status"] == "blocked"
    assert blocked["template_guard"]["reason"] == "unknown_source_low_confidence"
    assert blocked["template_guard"]["required_score"] == 0.65
    assert blocked["layers"]["template"].sum() == 0

    monkeypatch.setattr(
        car_layers_mod,
        "identify_car",
        lambda _tex, family_hint=None: [{"slug": "dirtlatemodel_358", "score": 0.70}],
    )
    applied = car_layers_mod.separate_into_layers(
        tex, use_ocr=False, source_slug_hint="1shokker_paint_car_examples"
    )
    assert applied["template_guard"]["status"] == "applied"
    assert applied["layers"]["template"].sum() > 0


def test_smart_tga_template_prior_wins_over_sponsor_detection(monkeypatch):
    tex = np.zeros((32, 32, 3), np.float32)
    template_prior = np.zeros((32, 32), bool)
    template_prior[8:16, 8:16] = True
    sponsor_mask = np.zeros((32, 32), np.uint8)
    sponsor_mask[8:16, 8:16] = 255      # false sponsor over a fixed grille/light region
    sponsor_mask[20:24, 20:24] = 255    # true free sponsor remains

    monkeypatch.setattr(car_layers_mod, "_template_prior", lambda _slug, _h, _w: template_prior)
    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((32, 32), np.uint8),
            "sponsors": sponsor_mask.copy(),
            "paint": np.zeros((32, 32), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, car_slug="stockcars2_arcachevy25", use_ocr=True,
        source_slug_hint="stockcars2_arcachevy25",
    )
    assert (res["layers"]["template"][8:16, 8:16] > 0).all()
    assert (res["layers"]["sponsors"][8:16, 8:16] > 0).mean() == 0
    assert (res["layers"]["sponsors"][20:24, 20:24] > 0).all()


def test_smart_tga_decorative_sponsor_motif_falls_back_to_paint(monkeypatch):
    n = 1024
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.02, 0.65, 0.72], np.float32)
    sponsors = np.zeros((n, n), np.uint8)

    yy, xx = np.ogrid[:n, :n]
    motif = (((yy - 120) ** 2) / float(34 ** 2) + ((xx - 124) ** 2) / float(38 ** 2)) <= 1.0
    sponsors[motif] = 255
    tex[motif] = np.array([0.95, 0.45, 0.04], np.float32)
    stripe = motif & ((((xx + yy) // 7) % 2) == 0)
    tex[stripe] = np.array([0.62, 0.09, 0.04], np.float32)
    eye = motif & (((yy - 114) ** 2 + (xx - 114) ** 2) <= 6 ** 2)
    tex[eye] = np.array([0.04, 0.03, 0.02], np.float32)

    wordmark = (slice(352, 371), slice(78, 188))
    sponsors[wordmark] = 255
    tex[wordmark] = np.array([0.96, 0.96, 0.94], np.float32)
    tex[358:364, 98:166] = np.array([0.05, 0.05, 0.05], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    assert (res["layers"]["sponsors"][motif] > 0).mean() < 0.05
    assert (res["layers"]["paint"][motif] > 0).mean() > 0.95
    assert (res["layers"]["sponsors"][wordmark] > 0).mean() > 0.95
    assert res["decorative_livery_sponsor_guard"]["status"] == "applied"
    assert res["decorative_livery_sponsor_guard"]["component_count"] == 1


def test_smart_tga_paired_red_white_livery_endcaps_fall_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([12, 12, 12], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_endcap(y0, x0, with_pale=True, dark_text=False):
        h, w = 48, 47
        yy, xx = np.indices((h, w))
        shape = np.ones((h, w), bool)
        shape &= ~((yy < 14) & (xx < 14))
        shape &= ~((yy >= h - 14) & (xx >= w - 14))
        sponsors[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = np.array([178, 42, 28], np.uint8)
        if with_pale:
            pale = shape & (xx >= 27) & (xx <= 35) & (yy >= 7) & (yy <= h - 8)
            sub[pale] = np.array([238, 210, 198], np.uint8)
        if dark_text:
            white = shape & (((yy % 9) == 0) | ((xx % 13) == 0))
            dark = shape & (((yy + xx) % 17) == 0)
            sub[white] = np.array([245, 245, 238], np.uint8)
            sub[dark] = np.array([15, 12, 12], np.uint8)
        return np.pad(shape, ((y0, n - y0 - h), (x0, n - x0 - w)))

    endcap_a = add_endcap(760, 770)
    endcap_b = add_endcap(761, 967)
    lone_endcap = add_endcap(610, 210)
    smooth_a = add_endcap(430, 120, with_pale=False)
    smooth_b = add_endcap(430, 330, with_pale=False)
    text_a = add_endcap(235, 115, dark_text=True)
    text_b = add_endcap(236, 320, dark_text=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 2
    assert {component["reason"] for component in guard["components"]} == {
        "paired_red_white_livery_endcap"
    }
    assert (mask[endcap_a] > 0).mean() > 0.95
    assert (mask[endcap_b] > 0).mean() > 0.95
    assert (mask[lone_endcap] > 0).mean() < 0.05
    assert (mask[smooth_a] > 0).mean() < 0.05
    assert (mask[smooth_b] > 0).mean() < 0.05
    assert (mask[text_a] > 0).mean() < 0.05
    assert (mask[text_b] > 0).mean() < 0.05


def test_smart_tga_dlm_woodgrain_livery_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 18], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def paint_component(y0, x0, shape, fill_fn, *, warm_ring=False, sponsor_ring=False, protected=False):
        h, w = shape.shape
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        y_ring = slice(max(0, y0 - 14), min(n, y0 + h + 14))
        x_ring = slice(max(0, x0 - 14), min(n, x0 + w + 14))
        rgb[y_ring, x_ring] = np.array([20, 20, 20], np.uint8)
        if warm_ring:
            rgb[max(0, y0 - 14):max(0, y0 - 2), x_ring] = np.array([144, 70, 24], np.uint8)
        if sponsor_ring:
            sponsors[y_ring, x_ring] = 255
        sponsors[target][shape] = 255
        fill_fn(rgb[target], shape)
        if protected:
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target][shape] = True
        return target, shape, full

    yy, xx = np.indices((31, 74))
    center = 17.0 + 1.23 * yy
    small_shape = np.abs(xx - center) <= 24
    small_shape |= (xx == 0) & (yy < 6)
    small_shape |= (xx == 73) & (yy > 24)

    def fill_small(sub, shape):
        yy_l, xx_l = np.indices(shape.shape)
        sub[shape] = np.array([232, 74, 12], np.uint8)
        sub[shape & (xx_l < 22)] = np.array([252, 142, 12], np.uint8)
        sub[shape & (xx_l > 52)] = np.array([252, 28, 16], np.uint8)
        sub[shape & (yy_l < 10)] = np.array([252, 186, 16], np.uint8)

    yy, xx = np.indices((97, 40))
    center = 7.0 + 0.23 * yy
    vertical_shape = np.abs(xx - center) <= 10
    vertical_shape |= ((yy % 12) < 4) & (xx > center - 13) & (xx < center + 7)
    vertical_shape |= (xx == 0) & (yy < 10)
    vertical_shape |= (xx == 39) & (yy > 88)

    def fill_vertical(sub, shape):
        yy_l, xx_l = np.indices(shape.shape)
        sub[shape] = np.array([166, 34, 10], np.uint8)
        sub[shape & (xx_l < 10)] = np.array([255, 205, 8], np.uint8)
        sub[shape & (xx_l > 34)] = np.array([206, 166, 150], np.uint8)
        sub[shape & ((yy_l % 10) == 0)] = np.array([255, 42, 8], np.uint8)
        dark = shape & (((yy_l + xx_l) % 23) < 2)
        sub[dark] = np.array([50, 50, 50], np.uint8)

    yy, xx = np.indices((63, 200))
    center = 31.0 + 5.0 * np.sin(xx / 17.0)
    long_shape = np.abs(yy - center) <= 18
    long_shape |= (xx == 0)
    long_shape |= (xx == 199)

    def fill_long(sub, shape):
        yy_l, xx_l = np.indices(shape.shape)
        sub[shape] = np.array([140, 68, 24], np.uint8)
        bright = shape & (((yy_l * 2 + xx_l) % 31) < 6)
        sub[bright] = np.array([220, 110, 20], np.uint8)
        dark = shape & (((yy_l * 4 - xx_l) % 23) < 4)
        sub[dark] = np.array([42, 42, 42], np.uint8)

    small_panel = paint_component(258, 311, small_shape, fill_small, warm_ring=True)
    vertical_panel = paint_component(358, 841, vertical_shape, fill_vertical)
    long_panel = paint_component(922, 776, long_shape, fill_long)
    text_card = paint_component(120, 650, long_shape.copy(), fill_long)
    vertical_text_panel = paint_component(610, 841, vertical_shape.copy(), fill_vertical)
    sponsor_card = paint_component(520, 650, small_shape.copy(), fill_small, sponsor_ring=True)
    protected_panel = paint_component(120, 120, vertical_shape.copy(), fill_vertical, protected=True)

    yy_l, xx_l = np.indices(long_shape.shape)
    text_pixels = long_shape & (((xx_l % 18) < 4) | ((yy_l % 15) < 3))
    rgb[text_card[0]][text_pixels] = np.array([245, 244, 236], np.uint8)
    yy_v, xx_v = np.indices(vertical_shape.shape)
    vertical_text_pixels = vertical_shape & (((yy_v % 14) < 3) | ((xx_v % 11) < 2))
    rgb[vertical_text_panel[0]][vertical_text_pixels] = np.array([244, 242, 232], np.uint8)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, template, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert set(reasons) == {
        "dlm_small_warm_woodgrain_livery_panel",
        "dlm_vertical_pale_woodgrain_livery_insert",
        "dlm_long_woodgrain_livery_panel",
    }
    for target, shape, _full in (small_panel, vertical_panel, long_panel):
        assert (mask[target][shape] > 0).mean() > 0.70
    assert (mask[text_card[0]][text_card[1]] > 0).mean() < 0.05
    assert (mask[vertical_text_panel[0]][vertical_text_panel[1]] > 0).mean() < 0.05
    assert (mask[sponsor_card[2]] > 0).mean() < 0.05
    assert (mask[protected_panel[2]] > 0).mean() < 0.05


def test_smart_tga_smooth_yellow_body_insert_motif_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([236, 201, 22], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_insert(y0, x0, *, text=False, smooth=False, dark_surround=False):
        h, w = 43, 38
        if dark_surround:
            rgb[y0 - 8:y0 + h + 8, x0 - 8:x0 + w + 8] = np.array([70, 60, 48], np.uint8)
        yy, xx = np.indices((h, w))
        shape = np.ones((h, w), dtype=bool)
        shape &= ~((yy < 16) & (xx < 19 - yy))
        shape &= ~((yy > 25) & (xx > 62 - yy))
        shape &= ~((yy > 8) & (yy < 29) & (xx > 3) & (xx < 10) & (yy > xx + 5))
        shape &= ~((yy > 18) & (yy < 39) & (xx > 27) & (xx < 36) & (yy < xx + 10))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([212, 181, 30], np.uint8)
        if not smooth:
            inset = shape & (yy > 10) & (yy < 34) & (xx > 13) & (xx < 32) & (yy > xx - 9)
            rgb[target][inset] = np.array([122, 112, 68], np.uint8)
        if text:
            text_pixels = shape & (((yy % 8) < 2) | ((xx % 11) < 2))
            rgb[target][text_pixels] = np.array([245, 244, 236], np.uint8)
        return target, shape

    positive, positive_shape = add_insert(420, 760)
    text_card, text_shape = add_insert(420, 128, text=True)
    smooth_panel, smooth_shape = add_insert(610, 760, smooth=True)
    dark_panel, dark_shape = add_insert(610, 128, smooth=True, dark_surround=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("smooth_yellow_body_insert_motif") == 1
    assert (mask[positive][positive_shape] > 0).mean() > 0.95
    assert (mask[text_card][text_shape] > 0).mean() < 0.05
    assert (mask[smooth_panel][smooth_shape] > 0).mean() < 0.05
    assert (mask[dark_panel][dark_shape] > 0).mean() < 0.05


def test_smart_tga_low_fill_yellow_blue_livery_tile_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([74, 68, 62], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_tile(y0, x0, *, blue_ring=True, blue_streak=True, text=False, flat=False):
        h, w = 46, 50
        yy, xx = np.indices((h, w))
        center = 3 + (46.0 / 45.0) * yy
        shape = np.abs(xx - center) < 15
        shape |= (yy < 4) & (xx < 10 + yy * 2)
        shape |= (yy > 41) & (xx > 39 - (45 - yy) * 2)
        shape &= ~(((yy < 10) & (xx > 35)) | ((yy > 36) & (xx < 12)))

        if blue_ring:
            rgb[y0 - 14:y0 + h + 14, x0 - 14:x0 + w + 14] = np.array([140, 190, 245], np.uint8)
        else:
            rgb[y0 - 14:y0 + h + 14, x0 - 14:x0 + w + 14] = np.array([206, 178, 42], np.uint8)

        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        if flat:
            colors = np.full((h, w, 3), np.array([225, 188, 8], np.uint8), np.uint8)
        else:
            g = 0.65 * yy / float(h - 1) + 0.35 * xx / float(w - 1)
            colors = np.stack([248 - 8 * g, 222 - 62 * g, 3 + 10 * g], axis=2).clip(0, 255).astype(np.uint8)
        if blue_streak:
            colors[np.abs(xx - (6 + yy * 0.96)) < 1] = np.array([55, 150, 238], np.uint8)
        if text:
            text_pixels = shape & (((xx % 9) < 2) | ((yy % 11) < 2))
            colors[text_pixels] = np.array([246, 245, 238], np.uint8)
        rgb[target][shape] = colors[shape]
        return target, shape

    positive, positive_shape = add_tile(420, 760)
    text_card, text_shape = add_tile(420, 128, text=True)
    no_blue_tile, no_blue_shape = add_tile(610, 760, blue_ring=False, blue_streak=False, flat=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("low_fill_yellow_blue_livery_tile") == 1
    component = next(item for item in guard["components"] if item.get("reason") == "low_fill_yellow_blue_livery_tile")
    assert component["val_mean"] > 0.95
    assert (mask[positive][positive_shape] > 0).mean() > 0.95
    assert (mask[text_card][text_shape] > 0).mean() < 0.05
    assert (mask[no_blue_tile][no_blue_shape] > 0).mean() < 0.05


def test_smart_tga_low_fill_warm_body_slash_motif_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([12, 12, 12], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_slash(y0, x0, *, text=False, light_ring=False):
        h, w = 79, 62
        yy, xx = np.indices((h, w))
        center = 50 - 0.65 * yy
        shape = (np.abs(xx - center) < 9) & (yy > 4) & (yy < h - 4)
        if light_ring:
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([238, 235, 214], np.uint8)
        else:
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([12, 12, 12], np.uint8)
            rgb[y0 - 10:y0 + 20, x0 - 10:x0 + w + 10] = np.array([22, 38, 185], np.uint8)
            rgb[y0 + 58:y0 + h + 10, x0 + 20:x0 + w + 10] = np.array([232, 82, 4], np.uint8)

        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        tone = ((yy // 12) % 2).astype(np.float32)
        body_shade = np.stack([
            160 + 95 * tone,
            34 + 72 * tone,
            2 + 16 * tone,
        ], axis=-1).astype(np.uint8)
        rgb[target][shape] = body_shade[shape]
        if text:
            text_pixels = shape & (((yy % 11) < 2) | ((xx % 13) < 2))
            rgb[target][text_pixels] = np.array([244, 244, 236], np.uint8)
        return target, shape

    positive, positive_shape = add_slash(520, 700)
    text_panel, text_shape = add_slash(520, 110, text=True)
    light_panel, light_shape = add_slash(720, 700, light_ring=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("low_fill_warm_body_slash_motif") == 1
    assert (mask[positive][positive_shape] > 0).mean() > 0.95
    assert (mask[text_panel][text_shape] > 0).mean() < 0.05
    assert (mask[light_panel][light_shape] > 0).mean() < 0.05


def test_smart_tga_low_fill_multicolor_livery_stripe_falls_back_to_paint():
    sample = Path(
        "_smart_tga_runs/cycle495_dlm_batch_mixed_contingency_strip_v1_nocache/"
        "Dirt_Late_Model_car_num_1206799"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle495 DLM 1206799 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("low_fill_multicolor_livery_stripe") == 1
    component = next(item for item in guard["components"] if item.get("reason") == "low_fill_multicolor_livery_stripe")
    assert component["bbox"] == [89, 563, 137, 10]
    assert component["white_frac"] == 0
    stripe = np.zeros(sponsors.shape, bool)
    stripe[563:573, 89:226] = sponsors[563:573, 89:226] > 0
    summit_card = np.zeros(sponsors.shape, bool)
    summit_card[744:777, 528:597] = sponsors[744:777, 528:597] > 0
    assert (mask[stripe] > 0).mean() > 0.95
    assert (mask[summit_card] > 0).mean() < 0.05


def test_smart_tga_high_fill_horizontal_livery_stripes_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([11, 12, 14], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_blue_cyan_stripe(y0, x0, *, protected=False, text_like=False, blue_body=False):
        h, w = 10, 111
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        if blue_body:
            rgb[y0 - 8:y0 + h + 8, x0 - 8:x0 + w + 8] = np.array([2, 194, 238], np.uint8)
        else:
            rgb[y0 - 8:y0 + h + 8, x0 - 8:x0 + w + 8] = np.array([11, 12, 14], np.uint8)
        yy, xx = np.indices((h, w))
        shape = np.ones((h, w), bool)
        shape[((xx * 3 + yy * 7) % 37) == 0] = False
        shape[((xx * 5 + yy * 11) % 43) == 0] = False
        shape[((xx * 7 + yy * 13) % 89) == 0] = False
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([6, 176, 235], np.uint8)
        rgb[target][shape & ((xx + yy) % 17 == 0)] = np.array([18, 22, 32], np.uint8)
        if blue_body:
            rgb[target][shape & ((xx * 3 + yy) % 11 == 0)] = np.array([236, 238, 232], np.uint8)
        if text_like:
            glyph = shape & ((xx % 13 <= 2) | ((xx + yy) % 17 <= 1))
            rgb[target][glyph] = np.array([246, 246, 238], np.uint8)
            rgb[target][shape & (xx % 29 == 0)] = np.array([238, 34, 28], np.uint8)
        if protected:
            template[target][shape] = 255
        return target, shape

    def add_dark_trim(y0, x0):
        h, w = 4, 44
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[y0 - 8:y0 + h + 8, x0 - 8:x0 + w + 8] = np.array([6, 7, 8], np.uint8)
        yy, xx = np.indices((h, w))
        shape = np.ones((h, w), bool)
        shape[(xx % 17 == 0) & (yy == 0)] = False
        sponsors[target][shape] = 255
        colored = shape & (((xx * 5 + yy) % 10) < 4)
        rgb[target][shape] = np.array([32, 10, 46], np.uint8)
        rgb[target][colored] = np.array([86, 28, 126], np.uint8)
        return target, shape

    cyan_dark_ring, cyan_dark_shape = add_blue_cyan_stripe(220, 80)
    dark_trim, dark_trim_shape = add_dark_trim(390, 120)
    text_strip, text_strip_shape = add_blue_cyan_stripe(470, 90, text_like=True)
    protected_strip, protected_shape = add_blue_cyan_stripe(550, 92, protected=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("horizontal_blue_cyan_livery_stripe") == 1
    assert reasons.count("tiny_dark_horizontal_livery_trim") == 1
    assert (mask[cyan_dark_ring][cyan_dark_shape] > 0).mean() > 0.95
    assert (mask[dark_trim][dark_trim_shape] > 0).mean() > 0.95
    assert (mask[text_strip][text_strip_shape] > 0).mean() == 0
    assert (mask[protected_strip][protected_shape] > 0).mean() == 0


def test_smart_tga_lower_left_blue_cyan_dlm_livery_stripe_demotes_real_33863():
    sample = Path(
        "_smart_tga_runs/cycle574_dlm_33863_mixed_orange_wedge_partial_target_v1_nocache/"
        "Dirt_Late_Model_car_num_33863"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle574 DLM 33863 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    components = {tuple(component["bbox"]): component for component in guard["components"]}
    stripe_component = components[(0, 874, 149, 13)]
    assert stripe_component["reason"] == "lower_left_blue_cyan_dlm_livery_stripe"
    assert stripe_component["area"] == 518
    assert stripe_component["ring_sponsor_frac"] == 0
    assert stripe_component["ring_dark_frac"] >= 0.94
    assert int((mask[874:887, 0:149] > 0).sum()) == 518

    # Nearby contingency/sponsor decals above the body stripe stay editable.
    top_sponsor_stack = sponsors[792:836, 0:160] > 0
    assert int((mask[792:836, 0:160] > 0).sum()) == 0
    assert int(top_sponsor_stack.sum()) > 800


def test_smart_tga_dark_speckled_warm_livery_chip_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([13, 14, 16], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_chip(y0, x0, *, text=False, colored_ring=False, protected=False, too_clean=False):
        h = w = 33
        if colored_ring:
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([45, 95, 190], np.uint8)
        else:
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([11, 12, 14], np.uint8)
        yy, xx = np.indices((h, w))
        shape = (np.abs(xx - yy) < 4) | (np.abs(xx - (w - 1 - yy)) < 2)
        shape |= ((yy > 14) & (yy < 20) & (xx > 8) & (xx < 25))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([32, 30, 28], np.uint8)
        warm = shape & (((xx * 3 + yy) % 10) < 7)
        rgb[target][warm] = np.array([175, 62, 8], np.uint8)
        if not too_clean:
            highlight = shape & (((xx * 5 + yy * 2) % 17) < 2)
            rgb[target][highlight] = np.array([230, 98, 10], np.uint8)
        if text:
            glyph = shape & (((xx % 9) < 2) | ((yy % 11) < 2))
            rgb[target][glyph] = np.array([244, 244, 236], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    positive, positive_shape = add_chip(180, 408)
    text_card, text_shape = add_chip(260, 408, text=True)
    colored_card, colored_shape = add_chip(340, 408, colored_ring=True)
    protected_card, protected_shape = add_chip(420, 408, protected=True)
    too_clean, too_clean_shape = add_chip(500, 408, too_clean=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("dark_speckled_warm_livery_chip") == 1
    assert (mask[positive][positive_shape] > 0).mean() > 0.95
    assert (mask[text_card][text_shape] > 0).mean() < 0.05
    assert (mask[colored_card][colored_shape] > 0).mean() < 0.05
    assert (mask[protected_card][protected_shape] > 0).mean() < 0.05
    assert (mask[too_clean][too_clean_shape] > 0).mean() < 0.05


def test_smart_tga_tiny_warm_speckled_livery_fleck_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([13, 14, 16], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def fleck_shape():
        shape = np.zeros((6, 7), bool)
        shape[0, 1:5] = True
        shape[1, 0:5] = True
        shape[2, 1:7] = True
        shape[3, 0:5] = True
        shape[4, 2:4] = True
        shape[5, 3:5] = True
        return shape

    def add_fleck(y0, x0, *, speckled_ring=True, glyph_like=False, protected=False, flat=False, low_chroma=False, sponsor_ring=False):
        h, w = 6, 7
        shape = fleck_shape()
        if speckled_ring:
            ring = (slice(y0 - 28, y0 + h + 28), slice(x0 - 28, x0 + w + 28))
            rgb[ring] = np.array([12, 13, 15], np.uint8)
            yy, xx = np.indices((h + 56, w + 56))
            warm_speckles = (((xx * 3 + yy * 5) % 17) < 4)
            dark_lifts = (((xx * 7 + yy * 5) % 29) < 4)
            local = rgb[ring]
            local[warm_speckles] = np.array([126, 45, 20], np.uint8)
            local[dark_lifts] = np.array([42, 48, 56], np.uint8)
            rgb[ring] = local
            if sponsor_ring:
                sponsors[y0 - 22:y0 - 12, x0 - 22:x0 + w + 22] = 255
                rgb[y0 - 22:y0 - 12, x0 - 22:x0 + w + 22] = np.array([230, 222, 205], np.uint8)
        else:
            rgb[y0 - 28:y0 + h + 28, x0 - 28:x0 + w + 28] = np.array([22, 20, 21], np.uint8)

        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        yy, xx = np.indices((h, w))
        rgb[target][shape] = np.array([28, 28, 32], np.uint8)
        coords = np.argwhere(shape)
        bright = np.zeros_like(shape)
        bright[tuple(coords[:13].T)] = True
        rgb[target][bright] = np.array([190, 70, 20], np.uint8)
        if low_chroma:
            warm = np.zeros_like(shape)
            warm[tuple(coords[:12].T)] = True
            dark_warm = np.zeros_like(shape)
            dark_warm[tuple(coords[12:15].T)] = True
            rgb[target][shape] = np.array([20, 24, 54], np.uint8)
            rgb[target][warm] = np.array([172, 68, 36], np.uint8)
            rgb[target][dark_warm] = np.array([54, 30, 18], np.uint8)
        if flat:
            rgb[target][shape] = np.array([156, 52, 14], np.uint8)
        if glyph_like:
            glyph = shape & (((xx % 3) == 0) | ((yy % 3) == 0))
            rgb[target][glyph] = np.array([230, 222, 205], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    positive, positive_shape = add_fleck(250, 241)
    low_chroma_positive, low_chroma_shape = add_fleck(250, 432, low_chroma=True)
    plain_pair_a, plain_pair_a_shape = add_fleck(52, 811, speckled_ring=False)
    plain_pair_b, plain_pair_b_shape = add_fleck(52, 825, speckled_ring=False)
    glyph_card, glyph_shape = add_fleck(330, 241, glyph_like=True)
    protected_card, protected_shape = add_fleck(410, 241, protected=True)
    flat_card, flat_shape = add_fleck(490, 241, flat=True)
    sponsor_ring_card, sponsor_ring_shape = add_fleck(570, 241, low_chroma=True, sponsor_ring=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("tiny_warm_speckled_livery_fleck") == 2
    assert (mask[positive][positive_shape] > 0).mean() > 0.95
    assert (mask[low_chroma_positive][low_chroma_shape] > 0).mean() > 0.95
    assert (mask[plain_pair_a][plain_pair_a_shape] > 0).mean() < 0.05
    assert (mask[plain_pair_b][plain_pair_b_shape] > 0).mean() < 0.05
    assert (mask[glyph_card][glyph_shape] > 0).mean() < 0.05
    assert (mask[protected_card][protected_shape] > 0).mean() < 0.05
    assert (mask[flat_card][flat_shape] > 0).mean() < 0.05
    assert (mask[sponsor_ring_card][sponsor_ring_shape] > 0).mean() < 0.05


def test_smart_tga_red_white_dark_livery_stripe_endcap_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 18], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_endcap(y0, x0, *, ring="dark", protected=False):
        h, w = 22, 49
        if ring == "light":
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([225, 222, 212], np.uint8)
        elif ring == "colored":
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([150, 190, 235], np.uint8)
        else:
            rgb[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = np.array([14, 14, 14], np.uint8)
        yy, xx = np.indices((h, w))
        left = 3 + 0.75 * yy
        right = left + 23
        shape = (xx >= left) & (xx <= right)
        shape |= ((yy > 16) & (xx >= left - 4) & (xx <= right + 2))
        shape &= ~((yy < 4) & (xx > right - 6))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([250, 62, 22], np.uint8)
        white = shape & (yy > 16) & (xx < right - 2)
        shadow = shape & ((yy == 14) | ((xx - left) < 1))
        rgb[target][white] = np.array([244, 242, 232], np.uint8)
        rgb[target][shadow] = np.array([34, 30, 28], np.uint8)
        if protected:
            template[target][shape] = 255
        return target, shape

    positive, positive_shape = add_endcap(470, 552)
    light_card, light_shape = add_endcap(470, 120, ring="light")
    colored_card, colored_shape = add_endcap(610, 552, ring="colored")
    protected_card, protected_shape = add_endcap(610, 120, protected=True)

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, template, empty
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("red_white_dark_livery_stripe_endcap") == 1
    assert (mask[positive][positive_shape] > 0).mean() > 0.95
    assert (mask[light_card][light_shape] > 0).mean() < 0.05
    assert (mask[colored_card][colored_shape] > 0).mean() < 0.05
    assert (mask[protected_card][protected_shape] > 0).mean() < 0.05


def test_smart_tga_decorative_livery_retries_after_sponsor_fragment(monkeypatch):
    n = 96
    tex = np.full((n, n, 3), np.array([0.02, 0.02, 0.02], np.float32), np.float32)
    target = np.zeros((n, n), np.uint8)
    target[40:46, 50:58] = 255
    empty = np.zeros((n, n), np.uint8)
    decorative_phases = []

    def fake_sponsor_fragment(_rgb, _numbers, _sponsors, _template, _brand):
        return target.copy(), {
            "status": "applied",
            "added_frac": round(float((target > 0).mean()), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [50, 40, 8, 6],
                    "area": int((target > 0).sum()),
                    "reason": "fragment_recovery_contract",
                }
            ],
        }

    def fake_decorative_livery(_rgb, _sponsors, _numbers, _template, _brand):
        has_recovered_fragment = bool((_sponsors[target > 0] > 0).any())
        decorative_phases.append("post_fragment" if has_recovered_fragment else "pre_fragment")
        if not has_recovered_fragment:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        return target.copy(), {
            "status": "applied",
            "demoted_frac": round(float((target > 0).mean()), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [50, 40, 8, 6],
                    "area": int((target > 0).sum()),
                    "reason": "red_white_dark_livery_stripe_endcap",
                }
            ],
        }

    monkeypatch.setattr(car_layers_mod, "_sponsor_fragment_supplement", fake_sponsor_fragment)
    monkeypatch.setattr(car_layers_mod, "_decorative_livery_sponsor_to_paint", fake_decorative_livery)

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=False, brand_graphics_merge="sponsors"
    )

    assert decorative_phases[:2] == ["pre_fragment", "post_fragment"]
    assert decorative_phases.count("post_fragment") == 1
    assert (res["layers"]["sponsors"][target > 0] > 0).mean() == 0
    assert (res["layers"]["paint"][target > 0] > 0).mean() == 1
    assert res["decorative_livery_sponsor_guard"]["status"] == "applied"
    assert res["decorative_livery_sponsor_guard"]["passes"] == ["post_sponsor_fragment"]
    assert res["decorative_livery_sponsor_guard"]["components"][0]["reason"] == "red_white_dark_livery_stripe_endcap"


def test_smart_tga_decorative_livery_retries_before_paint_materializes(monkeypatch):
    n = 96
    tex = np.full((n, n, 3), np.array([0.02, 0.02, 0.02], np.float32), np.float32)
    target = np.zeros((n, n), np.uint8)
    target[42:48, 52:60] = 255
    empty = np.zeros((n, n), np.uint8)
    decorative_calls = []

    def fake_sponsor_fragment(_rgb, _numbers, _sponsors, _template, _brand):
        return target.copy(), {
            "status": "applied",
            "added_frac": round(float((target > 0).mean()), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [52, 42, 8, 6],
                    "area": int((target > 0).sum()),
                    "reason": "fragment_recovery_contract",
                }
            ],
        }

    def fake_decorative_livery(_rgb, _sponsors, _numbers, _template, _brand):
        call_index = len(decorative_calls) + 1
        has_recovered_fragment = bool((_sponsors[target > 0] > 0).any())
        decorative_calls.append((call_index, has_recovered_fragment))
        if call_index < 3 or not has_recovered_fragment:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        return target.copy(), {
            "status": "applied",
            "demoted_frac": round(float((target > 0).mean()), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [52, 42, 8, 6],
                    "area": int((target > 0).sum()),
                    "reason": "red_white_dark_livery_stripe_endcap",
                }
            ],
        }

    monkeypatch.setattr(car_layers_mod, "_sponsor_fragment_supplement", fake_sponsor_fragment)
    monkeypatch.setattr(car_layers_mod, "_decorative_livery_sponsor_to_paint", fake_decorative_livery)

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=False, brand_graphics_merge="sponsors"
    )

    assert decorative_calls[:3] == [(1, False), (2, True), (3, True)]
    assert all(not has_fragment for _, has_fragment in decorative_calls[3:])
    assert (res["layers"]["sponsors"][target > 0] > 0).mean() == 0
    assert (res["layers"]["paint"][target > 0] > 0).mean() == 1
    assert res["decorative_livery_sponsor_guard"]["status"] == "applied"
    assert res["decorative_livery_sponsor_guard"]["passes"] == ["post_final_false_positive_cleanup"]
    assert res["decorative_livery_sponsor_guard"]["components"][0]["phase"] == "post_final_false_positive_cleanup"


def test_smart_tga_sponsor_fragment_vetoes_number_contained_warm_chip(monkeypatch):
    if car_layers_mod.cv2 is None:
        pytest.skip("cv2 is not available")

    n = 1100
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = [24, 28, 32]
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    numbers[230:290, 180:540] = 255
    numbers[290:520, 180:240] = 255
    numbers[460:530, 180:540] = 255
    numbers[290:520, 480:540] = 255
    rgb[numbers > 0] = [235, 232, 222]

    sponsors[330:346, 455:472] = 255
    rgb[330:346, 455:472] = [240, 240, 236]
    contained_chip = np.ones((14, 30), bool)
    contained_chip[:, ::6] = False
    rgb[334:348, 449:479][contained_chip] = [218, 48, 24]

    sponsors[760:776, 620:642] = 255
    rgb[760:776, 620:642] = [238, 238, 234]
    remote_word = np.zeros((24, 84), bool)
    remote_word[4:7, 4:76] = True
    remote_word[11:14, 18:80] = True
    remote_word[18:21, 4:76] = True
    remote_word[4:21, 4:8] = True
    remote_word[4:21, 42:46] = True
    remote_word[4:21, 76:80] = True
    rgb[760:784, 680:764][remote_word] = [245, 245, 245]

    original_canny = car_layers_mod.cv2.Canny

    def high_edge_canny(gray, low, high):
        edges = original_canny(gray, low, high)
        edges[334:348, 449:479][contained_chip] = 255
        edges[760:784, 680:764][remote_word] = 255
        return edges

    monkeypatch.setattr(car_layers_mod.cv2, "Canny", high_edge_canny)

    mask, info = car_layers_mod._sponsor_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["candidate_count"] == 1
    assert info["vetoed_number_contained_count"] == 1
    assert info["vetoed_number_contained"][0]["reason"] == "number_contained_warm_sponsor_fragment"
    assert (mask[334:348, 449:479] > 0).sum() == 0
    assert (mask[760:784, 680:764] > 0).sum() > 600


def test_smart_tga_warm_livery_arc_retries_before_paint_materializes(monkeypatch):
    n = 96
    tex = np.full((n, n, 3), np.array([0.02, 0.02, 0.02], np.float32), np.float32)
    target = np.zeros((n, n), np.uint8)
    target[42:48, 52:60] = 255
    empty = np.zeros((n, n), np.uint8)
    warm_calls = []

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": np.zeros((n, n), np.uint8),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    def fake_panel_text_residual(_rgb, _numbers, _sponsors, _template, _brand):
        return target.copy(), {
            "status": "applied",
            "added_frac": round(float((target > 0).mean()), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [52, 42, 8, 6],
                    "area": int((target > 0).sum()),
                    "reason": "late_recovery_contract",
                }
            ],
        }

    def fake_warm_livery_arc(_rgb, _sponsors, _numbers, _template, _brand):
        has_late_recovery = bool((_sponsors[target > 0] > 0).any())
        warm_calls.append(has_late_recovery)
        if not has_late_recovery:
            return empty.copy(), {"status": "empty", "component_count": 0, "components": []}
        return target.copy(), {
            "status": "applied",
            "demoted_frac": round(float((target > 0).mean()), 6),
            "component_count": 1,
            "candidate_count": 1,
            "components": [
                {
                    "bbox": [52, 42, 8, 6],
                    "area": int((target > 0).sum()),
                    "reason": "dark_panel_red_white_dlm_livery_swoosh",
                }
            ],
        }

    monkeypatch.setattr(car_layers_mod, "_panel_text_residual_supplement", fake_panel_text_residual)
    monkeypatch.setattr(car_layers_mod, "_warm_livery_arc_sponsor_to_paint", fake_warm_livery_arc)

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    assert warm_calls[0] is False
    assert warm_calls[-1] is True
    assert (res["layers"]["sponsors"][target > 0] > 0).mean() == 0
    assert (res["layers"]["paint"][target > 0] > 0).mean() == 1
    assert res["warm_livery_arc_sponsor_guard"]["status"] == "applied"
    assert res["warm_livery_arc_sponsor_guard"]["passes"] == ["pre_paint_materialization"]
    assert res["warm_livery_arc_sponsor_guard"]["components"][0]["phase"] == "pre_paint_materialization"


def test_smart_tga_large_red_livery_graphic_falls_back_to_paint(monkeypatch):
    n = 1024
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.04, 0.04, 0.04], np.float32)
    sponsors = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    cy, cx = 420, 620
    graphic = (((yy - cy) / 102.0) ** 2 + ((xx - cx) / 60.0) ** 2) <= 1.0
    graphic &= ~(((xx < cx - 18) & (yy < cy - 26)) | ((xx > cx + 30) & (yy > cy + 30)))
    sponsors[graphic] = 255
    tex[graphic] = np.array([0.93, 0.20, 0.18], np.float32)
    highlight = graphic & ((((yy - (cy - 42)) / 12.0) ** 2 + ((xx - (cx + 7)) / 34.0) ** 2) <= 1.0)
    tex[highlight] = np.array([0.96, 0.92, 0.88], np.float32)

    wordmark = (slice(120, 176), slice(120, 318))
    sponsors[wordmark] = 255
    tex[wordmark] = np.array([0.91, 0.16, 0.15], np.float32)
    tex[128:172:7, 135:300] = np.array([0.96, 0.96, 0.92], np.float32)
    tex[136:170:11, 140:304] = np.array([0.04, 0.04, 0.04], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    assert (res["layers"]["sponsors"][graphic] > 0).mean() < 0.05
    assert (res["layers"]["paint"][graphic] > 0).mean() > 0.95
    assert (res["layers"]["sponsors"][wordmark] > 0).mean() > 0.95
    assert res["large_red_livery_sponsor_guard"]["status"] == "applied"
    assert res["large_red_livery_sponsor_guard"]["component_count"] == 1


def test_smart_tga_smooth_red_body_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([10, 10, 10], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    rgb[757:904, 166:283] = np.array([216, 30, 28], np.uint8)
    lower_panel = (((yy - 830) / 73.0) ** 2 + ((xx - 224) / 58.0) ** 2) <= 1.0
    sponsors[lower_panel] = 255

    right_strip_box = (yy >= 115) & (yy < 705) & (xx >= 995) & (xx < 1024)
    right_strip_y = yy - 115
    right_strip_x = xx - 995
    rgb[115:705, 995:1024] = np.array([235, 40, 34], np.uint8)
    right_strip = right_strip_box & ((right_strip_x >= 8) | (right_strip_y < 2) | (right_strip_y >= 588))
    sponsors[right_strip] = 255

    rgb[195:294, 166:261] = np.array([210, 34, 32], np.uint8)
    upper_panel = (((yy - 244) / 49.0) ** 2 + ((xx - 213) / 47.0) ** 2) <= 1.0
    sponsors[upper_panel] = 255

    text_heavy_sponsor = (slice(590, 737), slice(420, 537))
    sponsors[text_heavy_sponsor] = 255
    rgb[text_heavy_sponsor] = np.array([216, 30, 28], np.uint8)
    rgb[596:731:8, 428:529] = np.array([242, 242, 230], np.uint8)
    rgb[601:728:13, 432:525] = np.array([12, 12, 12], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert {c["reason"] for c in info["components"]} == {
        "smooth_red_body_panel",
        "smooth_saturated_red_livery_panel",
    }
    assert (mask[lower_panel] > 0).mean() > 0.95
    assert (mask[right_strip] > 0).mean() > 0.95
    assert (mask[upper_panel] > 0).mean() > 0.95
    assert (mask[text_heavy_sponsor] > 0).mean() < 0.05


def test_smart_tga_dlm_red_white_number_panel_outline_splits_from_real_artifact():
    sample = Path(
        "_smart_tga_runs/cycle444_dlm_batch05_dark_panel_red_white_swoosh_controls_v1/"
        "Dirt_Late_Model_car_num_1124938"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle444 DLM 1124938 diagnostic artifact not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    assert info["status"] == "applied"
    components = info["components"]
    assert len(components) == 1
    component = components[0]
    assert component["reason"] == "dlm_red_white_number_panel_outline_partial"
    assert component["bbox"] == [271, 225, 328, 119]
    assert component["component_area"] == 14918
    assert 7150 <= component["area"] <= 7300
    assert 0.47 <= component["partial_demote_frac"] <= 0.50
    assert component["preserved_area"] >= 7600
    assert component["preserved_white_frac"] >= 0.26
    assert component["preserved_dark_frac"] >= 0.44
    assert component["preserved_red_frac"] <= 0.22
    assert int((mask > 0).sum()) == component["area"]


def test_smart_tga_blue_panel_red_black_livery_fill_splits_from_real_artifact():
    sample = Path(
        "_smart_tga_runs/cycle452_dlm_batch05_tiny_warm_shell_sponsor_chip_controls_v1/"
        "Dirt_Late_Model_car_num_1117603"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle452 DLM 1117603 diagnostic artifact not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "blue_panel_red_black_livery_fill_partial"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [309, 392, 97, 128]
    assert component["component_area"] == 9173
    assert 5000 <= component["area"] <= 5100
    assert 0.54 <= component["partial_demote_frac"] <= 0.56
    assert component["preserved_area"] >= 4100
    assert 0.025 <= component["preserved_white_frac"] <= 0.07
    assert component["preserved_dark_frac"] >= 0.82
    assert component["preserved_red_frac"] <= 0.08
    assert 0.030 <= component["preserved_blue_frac"] <= 0.110
    assert (mask[392:520, 309:406] > 0).mean() < 0.45
    assert int((mask > 0).sum()) >= component["area"]


def test_smart_tga_upper_dark_context_yellow_livery_swoosh_splits_from_real_artifact():
    sample = Path(
        "_smart_tga_runs/cycle510_dlm_batch_distressed_yellow_wordmark_v1_nocache/"
        "Dirt_Late_Model_car_num_1256168"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle510 DLM 1256168 diagnostic artifact not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "upper_dark_context_yellow_livery_swoosh_partial"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [98, 76, 192, 75]
    assert component["component_area"] == 6639
    assert 3300 <= component["area"] <= 3400
    assert 0.49 <= component["partial_demote_frac"] <= 0.52
    assert component["preserved_area"] >= 3200
    assert component["preserved_white_frac"] <= 0.060
    assert 0.10 <= component["preserved_dark_frac"] <= 0.30
    assert component["preserved_red_frac"] <= 0.18
    assert 0.12 <= component["preserved_blue_frac"] <= 0.24
    assert (mask[76:151, 98:290] > 0).mean() < 0.25
    # The nearby distressed MBR sponsor card should remain editable Sponsor.
    assert (mask[30:82, 609:728] > 0).mean() < 0.05


def test_smart_tga_lower_body_horizontal_red_dlm_livery_panel_falls_back_to_paint():
    sample = Path(
        "_smart_tga_runs/cycle511_dlm_batch_upper_yellow_livery_swoosh_v1_nocache/"
        "Dirt_Late_Model_car_num_1244694"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle511 DLM 1244694 diagnostic artifact not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "lower_body_horizontal_red_dlm_livery_panel"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [654, 890, 121, 38]
    assert component["area"] == 2526
    assert component["component_area"] == 2526
    assert component["ring_sponsor_frac"] <= 0.025
    assert component["ring_dark_frac"] <= 0.12
    assert component["white_frac"] <= 0.010
    assert component["dark_frac"] <= 0.07
    assert component["max_row_run_frac"] >= 0.85
    assert int((mask > 0).sum()) == component["area"]


def test_smart_tga_bottom_edge_solid_red_dlm_livery_bar_falls_back_to_paint():
    sample = Path(
        "_smart_tga_runs/cycle541_dlm_next4_sparse_neutral_outline_crumb_control_v1_nocache/"
        "Dirt_Late_Model_car_num_327705"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle541 DLM 327705 diagnostic artifact not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "bottom_edge_solid_red_dlm_livery_bar"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [252, 958, 341, 41]
    assert component["area"] == 13693
    assert component["component_area"] == 13693
    assert component["white_frac"] == 0
    assert component["dark_frac"] <= 0.010
    assert component["edge_density"] <= 0.020
    assert component["ring_sponsor_frac"] == 0
    assert component["max_row_run_frac"] >= 0.98
    assert (mask[958:999, 252:593] > 0).mean() >= 0.95
    # Number/sponsor art nearby keeps its editable Sponsor pixels.
    assert (mask[717:901, 283:591] > 0).mean() < 0.05
    assert (mask[227:339, 323:471] > 0).mean() < 0.05
    assert (mask[248:291, 12:164] > 0).mean() < 0.05


def test_smart_tga_bright_orange_dlm_livery_shapes_fall_back_to_paint_after_number_cleanup():
    sample = Path(
        "_smart_tga_runs/cycle549_dlm_next4_false_number_scrap_control_v1_nocache/"
        "Dirt_Late_Model_car_num_1027044"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle549 DLM 1027044 diagnostic artifact not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    sponsors = load_mask("sponsors")
    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        sponsors,
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in info.get("components", [])
    }
    assert reasons_by_bbox[(953, 115, 45, 35)] == "right_side_bright_orange_dlm_livery_tile"
    assert reasons_by_bbox[(932, 233, 61, 16)] == "right_side_bright_orange_dlm_livery_bar"

    for x, y, w, h in [(953, 115, 45, 35), (932, 233, 61, 16)]:
        target = sponsors[y:y + h, x:x + w] > 0
        assert target.any()
        recovered = (mask[y:y + h, x:x + w] > 0) & target
        assert float(recovered.sum() / target.sum()) >= 0.92

    for x, y, w, h in [
        (311, 237, 129, 106),
        (321, 714, 120, 104),
        (813, 802, 144, 172),
        (896, 472, 20, 95),
    ]:
        assert int((mask[y:y + h, x:x + w] > 0).sum()) == 0


def test_smart_tga_low_fill_green_cyan_dlm_body_swoosh_falls_back_to_paint():
    sample = Path(
        "_smart_tga_runs/cycle512_dlm_batch_lower_body_red_panel_v1_nocache/"
        "Dirt_Late_Model_car_num_1250296"
    )
    control = Path(
        "_smart_tga_runs/cycle512_dlm_batch_lower_body_red_panel_v1_nocache/"
        "Dirt_Late_Model_car_num_1226283"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        control / "source_1024.png",
        control / "masks" / "sponsors.png",
        control / "masks" / "numbers.png",
        control / "masks" / "template.png",
        control / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle512 DLM diagnostic artifacts not present")

    def load_inputs(folder: Path):
        rgb = np.array(Image.open(folder / "source_1024.png").convert("RGB"))
        masks = {
            name: np.array(Image.open(folder / "masks" / f"{name}.png").convert("L"))
            for name in ("sponsors", "numbers", "template", "brand_graphics")
        }
        return rgb, masks

    rgb, masks = load_inputs(sample)
    mask, info = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb,
        masks["sponsors"],
        masks["numbers"],
        masks["template"],
        masks["brand_graphics"],
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "low_fill_green_cyan_dlm_body_swoosh"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [681, 822, 83, 42]
    assert component["area"] == 951
    assert component["ring_sponsor_frac"] == 0
    assert component["ring_blue_green_frac"] >= 0.88
    assert component["white_frac"] == 0
    assert component["dark_frac"] <= 0.02
    assert component["max_row_run_frac"] >= 0.54
    assert int((mask > 0).sum()) == component["area"]

    control_rgb, control_masks = load_inputs(control)
    control_mask, control_info = car_layers_mod._decorative_livery_sponsor_to_paint(
        control_rgb,
        control_masks["sponsors"],
        control_masks["numbers"],
        control_masks["template"],
        control_masks["brand_graphics"],
    )
    assert control_info["component_count"] == 0
    assert (control_mask[834:905, 880:953] > 0).mean() == 0


def test_smart_tga_textless_orange_dlm_livery_patches_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 20, 20], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_patch(y0, x0, h, w, protected=False, route_edge=False):
        yy, xx = np.indices((h, w))
        cy = (h - 1) / 2.0
        cx = (w - 1) / 2.0
        shape = (((yy - cy) / (h * 0.49)) ** 2 + ((xx - cx) / (w * 0.49)) ** 2) <= 1.0
        wave = np.abs(yy - (cy + 0.12 * h * np.sin(xx / 18.0))) < max(2, h * 0.04)
        shape |= wave & (xx > w * 0.10) & (xx < w * 0.90)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        if route_edge:
            tones = np.where(
                ((xx // 20) % 2)[..., None],
                np.array([246, 82, 2], np.uint8),
                np.array([226, 60, 1], np.uint8),
            )
        else:
            tones = np.where(
                ((xx // 16) % 2)[..., None],
                np.array([246, 82, 2], np.uint8),
                np.array([214, 52, 1], np.uint8),
            )
        rgb[target][shape] = tones[shape]
        full = np.pad(shape, ((y0, n - y0 - h), (x0, n - x0 - w)))
        if protected:
            numbers[full] = 255
        return full

    compact_body_patch = add_patch(847, 222, 56, 55)
    broad_body_patch = add_patch(905, 4, 108, 195)
    thin_body_stripe = add_patch(738, 718, 24, 104, route_edge=True)
    protected_patch = add_patch(200, 200, 56, 55, protected=True)

    sponsor_card = (slice(620, 690), slice(590, 730))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([246, 82, 2], np.uint8)
    rgb[630:682:8, 600:720] = np.array([245, 245, 232], np.uint8)
    rgb[635:678:13, 612:714] = np.array([15, 15, 15], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert {c["reason"] for c in info["components"]} == {"textless_orange_livery_patch"}
    assert (mask[compact_body_patch] > 0).mean() > 0.95
    assert (mask[broad_body_patch] > 0).mean() > 0.95
    assert (mask[thin_body_stripe] > 0).mean() > 0.95
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[protected_patch] > 0).mean() == 0


def test_smart_tga_smooth_warm_body_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([12, 12, 14], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_panel(y0, x0, h, w, kind):
        yy, xx = np.indices((h, w))
        if kind == "vertical":
            shape = xx < 28
            shape |= ((yy >= 160) & (yy <= 198) & (xx < w))
            shape |= ((yy < 7) | (yy > h - 8)) & (xx < w - 8)
        else:
            shape = xx < 38
            shape |= np.abs(yy - (52 + 18 * np.sin(xx / 34.0))) < 11
        sponsors[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        red = np.clip(238 + xx * 12 / float(max(1, w - 1)), 224, 255)
        green = np.clip(78 + yy * 22 / float(max(1, h - 1)) + ((xx % 19) - 9) * 0.4, 68, 112)
        blue = np.clip(12 + ((xx + yy) % 11) * 0.5, 10, 22)
        panel_rgb = np.stack([red, green, blue], axis=2).astype(np.uint8)
        sub[shape] = panel_rgb[shape]
        return np.pad(shape, ((y0, n - y0 - h), (x0, n - x0 - w)))

    vertical_panel = add_panel(424, 884, 360, 110, "vertical")
    compact_panel = add_panel(12, 370, 104, 127, "compact")

    sponsor_card = (slice(155, 245), slice(690, 850))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([246, 94, 14], np.uint8)
    rgb[166:238:9, 704:836] = np.array([246, 246, 234], np.uint8)
    rgb[170:236:13, 716:828] = np.array([18, 18, 18], np.uint8)

    general_tire_like = (slice(20, 365), slice(956, 1024))
    sponsors[general_tire_like] = 255
    rgb[general_tire_like] = np.array([236, 84, 14], np.uint8)
    rgb[34:348:17, 966:1014] = np.array([245, 245, 232], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {c["reason"] for c in info["components"]} == {"smooth_warm_body_panel"}
    assert (mask[vertical_panel] > 0).mean() > 0.95
    assert (mask[compact_panel] > 0).mean() > 0.95
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[general_tire_like] > 0).mean() == 0


def test_smart_tga_warm_livery_texture_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([10, 10, 12], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_wide_texture_panel(y0, x0):
        h, w = 65, 222
        yy, xx = np.indices((h, w))
        center = 8 + 0.23 * xx + 4 * np.sin(xx / 21.0)
        shape = np.abs(yy - center) <= 16
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        band = ((xx // 11) % 2).astype(bool)
        tones = np.where(band[..., None], np.array([252, 94, 4]), np.array([205, 45, 1]))
        rgb[target][shape] = tones.astype(np.uint8)[shape]
        return target, shape

    def add_compact_chip(y0, x0):
        h, w = 40, 64
        yy, xx = np.indices((h, w))
        center = 6 + 0.43 * xx + 2 * np.sin(xx / 12.0)
        shape = np.abs(yy - center) <= 11
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([247, 82, 2], np.uint8)
        return target, shape

    wide_panel, wide_shape = add_wide_texture_panel(305, 616)
    compact_chip, chip_shape = add_compact_chip(382, 541)

    sponsor_card = (slice(118, 178), slice(620, 842))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([246, 88, 4], np.uint8)
    rgb[126:170:8, 638:828] = np.array([244, 244, 232], np.uint8)
    rgb[134:168:13, 650:820] = np.array([16, 16, 16], np.uint8)

    tall_panel = (slice(527, 688), slice(779, 832))
    tall_shape = np.zeros((161, 53), bool)
    tall_shape[:, :16] = True
    tall_shape[95:125, :] = True
    sponsors[tall_panel][tall_shape] = 255
    rgb[tall_panel][tall_shape] = np.array([248, 76, 2], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = {c["reason"] for c in info["components"]}
    assert info["status"] == "applied"
    assert "wide_warm_livery_texture_panel" in reasons
    assert "compact_warm_livery_texture_chip" in reasons
    assert (mask[wide_panel][wide_shape] > 0).mean() > 0.95
    assert (mask[compact_chip][chip_shape] > 0).mean() > 0.95
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[tall_panel][tall_shape] > 0).mean() == 0


def test_smart_tga_flat_wide_red_livery_plate_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([84, 74, 68], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    flat_panel = (slice(201, 248), slice(229, 340))
    sponsors[flat_panel] = 255
    rgb[flat_panel] = np.array([184, 44, 42], np.uint8)

    text_card = (slice(318, 365), slice(232, 343))
    sponsors[text_card] = 255
    rgb[text_card] = np.array([184, 44, 42], np.uint8)
    rgb[326:340:4, 240:333] = np.array([245, 245, 232], np.uint8)
    rgb[343:358:5, 248:325] = np.array([18, 18, 18], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "flat_wide_red_body_panel"
    assert (mask[flat_panel] > 0).mean() > 0.95
    assert (mask[text_card] > 0).mean() == 0


def test_smart_tga_edge_wave_red_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([30, 28, 28], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_wave(y0, x0, protected=False):
        h, w = 43, 375
        yy, xx = np.indices((h, w))
        center = 21 + 5.0 * np.sin(xx / 43.0) + 1.5 * np.sin(xx / 17.0)
        shape = np.abs(yy - center) <= 8
        shape[:, :8] = True
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        red = np.clip(208 + 34 * np.sin(xx / 29.0) + 13 * ((xx // 37) % 2), 188, 248)
        green = np.clip(31 + 24 * np.sin(xx / 41.0 + 0.7) + 8 * ((xx // 53) % 2), 20, 74)
        blue = np.clip(38 + 10 * np.sin(xx / 35.0 + 1.5), 30, 58)
        panel_rgb = np.stack([red, green, blue], axis=2).astype(np.uint8)
        rgb[target][shape] = panel_rgb[shape]
        if protected:
            numbers[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target][shape] = True
        return target, shape, full

    wave_target, wave_shape, _wave_full = add_wave(681, 0)
    _protected_target, _protected_shape, protected_full = add_wave(500, 0, protected=True)
    non_edge_target, non_edge_shape, _non_edge_full = add_wave(620, 240)

    text_card = (slice(760, 803), slice(0, 375))
    sponsors[text_card] = 255
    rgb[text_card] = np.array([210, 32, 42], np.uint8)
    rgb[766:796:6, 16:350] = np.array([244, 244, 234], np.uint8)
    rgb[770:798:9, 30:340] = np.array([16, 16, 18], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "edge_wave_red_livery_stripe"
    assert (mask[wave_target][wave_shape] > 0).mean() > 0.95
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[non_edge_target][non_edge_shape] > 0).mean() == 0
    assert (mask[text_card] > 0).mean() == 0


def test_smart_tga_thin_red_orange_livery_stripes_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([48, 44, 40], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_stripe(y0, x0, h, w, protect=False, with_text=False):
        yy, xx = np.indices((h, w))
        if h <= 14:
            shape = ((xx + yy * 2) % 4) != 0
        else:
            shape = ((xx + yy * 3) % 10) < 5
        shape[:, :3] = True
        shape[:, -3:] = True
        shape[0, :] = True
        shape[-1, :] = True
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[target] = np.array([198, 44, 34], np.uint8)
        rgb[target][yy <= max(1, h // 8)] = np.array([28, 20, 20], np.uint8)
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([206, 48, 36], np.uint8)
        rgb[target][shape & (yy <= max(1, h // 8))] = np.array([28, 20, 20], np.uint8)
        rgb[target][shape & (((xx + yy) % 13) < 2)] = np.array([252, 128, 20], np.uint8)
        if with_text:
            text = shape & (yy >= 4) & (yy <= max(5, h - 5)) & (((xx // 10) % 2) == 0)
            rgb[target][text] = np.array([246, 246, 236], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target][shape] = True
        return target, shape, full

    stripe_target, stripe_shape, _stripe_full = add_stripe(103, 49, 14, 136)
    stripe2_target, stripe2_shape, _stripe2_full = add_stripe(317, 444, 20, 152)
    _protected_target, _protected_shape, protected_full = add_stripe(500, 49, 14, 136, protect=True)
    text_target, text_shape, _text_full = add_stripe(570, 49, 14, 136, with_text=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [c["reason"] for c in info["components"]]
    assert info["status"] == "applied"
    assert reasons.count("thin_red_orange_livery_stripe") == 2
    assert (mask[stripe_target][stripe_shape] > 0).mean() > 0.95
    assert (mask[stripe2_target][stripe2_shape] > 0).mean() > 0.95
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[text_target][text_shape] > 0).mean() == 0


def test_smart_tga_tiny_warm_red_paint_islands_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([246, 246, 242], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    island = (slice(641, 655), slice(121, 140))
    yy, xx = np.indices((14, 19))
    island_shape = np.zeros((14, 19), bool)
    for row, length in enumerate([19, 19, 19, 19, 19, 17, 15, 13, 11, 9, 7, 5, 3, 1]):
        island_shape[row, :length] = True
    pale_antialias = island_shape & ((yy == 0) | ((yy == 1) & (xx < 2)))
    sponsors[island][island_shape] = 255
    rgb[island][island_shape] = np.array([255, 0, 0], np.uint8)
    rgb[island][pale_antialias] = np.array([246, 246, 242], np.uint8)

    red_letter = (slice(676, 690), slice(121, 140))
    letter_shape = ((xx >= 2) & (xx <= 5)) | ((xx >= 13) & (xx <= 16))
    letter_shape |= (yy <= 2) | ((yy >= 6) & (yy <= 8))
    sponsors[red_letter][letter_shape] = 255
    rgb[red_letter][letter_shape] = np.array([255, 0, 0], np.uint8)

    protected_island = (slice(710, 724), slice(121, 140))
    sponsors[protected_island][island_shape] = 255
    rgb[protected_island][island_shape] = np.array([255, 0, 0], np.uint8)
    rgb[protected_island][pale_antialias] = np.array([246, 246, 242], np.uint8)
    numbers[protected_island][island_shape] = 255
    template[protected_island][island_shape] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tiny_warm_red_paint_island"
    assert (mask[island][island_shape] > 0).mean() > 0.95
    assert (mask[red_letter][letter_shape] > 0).mean() == 0
    assert (mask[protected_island][island_shape] > 0).mean() == 0


def test_smart_tga_small_dark_context_red_body_tiles_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_dark_red_context(y0, x0, h, w):
        yy, xx = np.indices((h, w))
        red_band = ((xx // 8 + yy // 8) % 2) == 0
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[target][red_band] = np.array([216, 28, 46], np.uint8)
        rgb[target][~red_band] = np.array([18, 16, 18], np.uint8)

    tile = (slice(148, 185), slice(447, 484))
    paint_dark_red_context(128, 427, 77, 77)
    sponsors[tile] = 255
    rgb[tile] = np.array([236, 4, 42], np.uint8)

    second_tile = (slice(219, 259), slice(595, 632))
    paint_dark_red_context(199, 575, 80, 77)
    sponsors[second_tile] = 255
    rgb[second_tile] = np.array([236, 4, 42], np.uint8)

    route_antialias_tile = (slice(770, 799), slice(941, 977))
    paint_dark_red_context(750, 921, 69, 76)
    sponsors[route_antialias_tile] = 255
    rgb[route_antialias_tile] = np.array([205, 2, 2], np.uint8)
    rgb[770:773, 941:947] = np.array([60, 2, 2], np.uint8)

    sponsor_card = (slice(300, 338), slice(180, 218))
    rgb[280:358, 160:238] = np.array([246, 226, 44], np.uint8)
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([236, 4, 42], np.uint8)

    glyph_card = (slice(390, 428), slice(180, 218))
    paint_dark_red_context(370, 160, 78, 78)
    sponsors[glyph_card] = 255
    rgb[glyph_card] = np.array([236, 4, 42], np.uint8)
    rgb[398:420:5, 186:212] = np.array([246, 246, 236], np.uint8)
    rgb[404:422:9, 190:208] = np.array([18, 18, 20], np.uint8)

    protected_tile = (slice(500, 537), slice(447, 484))
    paint_dark_red_context(480, 427, 77, 77)
    sponsors[protected_tile] = 255
    rgb[protected_tile] = np.array([236, 4, 42], np.uint8)
    numbers[protected_tile] = 255
    template[protected_tile] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert {c["reason"] for c in info["components"]} == {"small_dark_context_red_body_tile"}
    assert (mask[tile] > 0).mean() > 0.95
    assert (mask[second_tile] > 0).mean() > 0.95
    assert (mask[route_antialias_tile] > 0).mean() > 0.95
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[glyph_card] > 0).mean() == 0
    assert (mask[protected_tile] > 0).mean() == 0


def test_smart_tga_vertical_dark_context_red_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 16, 18], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_dark_red_context(y0, x0, h, w):
        yy, xx = np.indices((h, w))
        red_band = ((xx // 8 + yy // 8) % 2) == 0
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[target][red_band] = np.array([210, 20, 38], np.uint8)
        rgb[target][~red_band] = np.array([16, 14, 16], np.uint8)

    def paint_vertical_panel(target):
        h = target[0].stop - target[0].start
        w = target[1].stop - target[1].start
        yy, xx = np.indices((h, w))
        red = np.clip(204 + 56 * np.sin(xx / 5.0) + 16 * np.sin(yy / 17.0), 135, 245)
        green = np.clip(4 + 5 * np.sin(yy / 11.0), 2, 12)
        blue = np.clip(6 + 5 * np.sin(xx / 7.0), 2, 14)
        panel_rgb = np.stack([red, green, blue], axis=2).astype(np.uint8)
        antialias = ((yy + xx) % 32) < 3
        panel_rgb[antialias] = np.array([48, 3, 4], np.uint8)
        rgb[target] = panel_rgb
        shape = xx < 33
        shape[(yy % 16) == 0] = True
        return shape

    panel = (slice(147, 259), slice(521, 559))
    paint_dark_red_context(127, 501, 152, 78)
    panel_shape = paint_vertical_panel(panel)
    sponsors[panel][panel_shape] = 255

    glyph_card = (slice(147, 259), slice(641, 679))
    paint_dark_red_context(127, 621, 152, 78)
    glyph_shape = paint_vertical_panel(glyph_card)
    sponsors[glyph_card][glyph_shape] = 255
    rgb[162:244:12, 647:673] = np.array([246, 246, 234], np.uint8)
    rgb[167:239:16, 651:669] = np.array([12, 12, 12], np.uint8)

    sponsor_surrounded_card = (slice(147, 259), slice(761, 799))
    paint_dark_red_context(127, 741, 152, 78)
    sponsor_surrounded_shape = paint_vertical_panel(sponsor_surrounded_card)
    sponsors[sponsor_surrounded_card][sponsor_surrounded_shape] = 255
    sponsors[150:256, 752:758] = 255
    rgb[150:256, 752:758] = np.array([246, 246, 232], np.uint8)
    sponsors[150:256, 802:808] = 255
    rgb[150:256, 802:808] = np.array([246, 246, 232], np.uint8)
    sponsors[132:143, 748:812] = 255
    rgb[132:143, 748:812] = np.array([246, 246, 232], np.uint8)
    sponsors[264:275, 748:812] = 255
    rgb[264:275, 748:812] = np.array([246, 246, 232], np.uint8)

    protected_panel = (slice(147, 259), slice(881, 919))
    paint_dark_red_context(127, 861, 152, 78)
    protected_shape = paint_vertical_panel(protected_panel)
    sponsors[protected_panel][protected_shape] = 255
    numbers[protected_panel][protected_shape] = 255
    template[protected_panel][protected_shape] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "vertical_dark_context_red_livery_panel"
    assert (mask[panel][panel_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[sponsor_surrounded_card][sponsor_surrounded_shape] > 0).mean() == 0
    assert (mask[protected_panel][protected_shape] > 0).mean() == 0


def test_smart_tga_small_vertical_red_livery_insert_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([24, 10, 10], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_red_dark_body_context(y0, x0):
        h, w = 121, 82
        yy, xx = np.indices((h, w))
        red_body = ((xx // 9 + yy // 11) % 2) == 0
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[target][red_body] = np.array([128, 0, 12], np.uint8)
        rgb[target][~red_body] = np.array([26, 0, 0], np.uint8)

    def insert_shape():
        h, w = 73, 28
        yy, xx = np.indices((h, w))
        shape = yy < 33
        shape |= ((yy >= 33) & (xx < 10))
        shape |= ((yy == 40) & (xx < 18))
        return shape

    def add_insert(y0, x0, *, glyphs=False, sponsor_ring=False, protected=False, tall_decal=False):
        shape = insert_shape()
        h, w = shape.shape
        if tall_decal:
            shape = np.pad(shape, ((0, 126), (0, 0)), constant_values=True)
            h, w = shape.shape
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        yy, xx = np.indices((h, w))
        sponsors[target][shape] = 255
        panel = rgb[target]
        panel[shape] = np.array([160, 28, 42], np.uint8)
        panel[shape & ((yy + xx) % 5 == 0)] = np.array([78, 0, 0], np.uint8)
        panel[shape & ((yy * 2 + xx) % 13 == 0)] = np.array([42, 38, 38], np.uint8)
        if glyphs:
            panel[shape & (yy >= 9) & (yy <= 56) & ((yy - 9) % 13 <= 2)] = np.array([244, 244, 232], np.uint8)
            panel[shape & (yy >= 16) & (yy <= 63) & (xx >= 4) & (xx <= 22) & ((yy - 16) % 17 <= 2)] = np.array([10, 10, 12], np.uint8)
        if sponsor_ring:
            sponsors[y0 + 3:y0 + h - 3, x0 - 9:x0 - 4] = 255
            rgb[y0 + 3:y0 + h - 3, x0 - 9:x0 - 4] = np.array([246, 246, 232], np.uint8)
            sponsors[y0 + 6:y0 + h - 6, x0 + w + 4:x0 + w + 9] = 255
            rgb[y0 + 6:y0 + h - 6, x0 + w + 4:x0 + w + 9] = np.array([246, 246, 232], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    paint_red_dark_body_context(827, 0)
    good, good_shape = add_insert(851, 13)
    paint_red_dark_body_context(827, 110)
    glyph_card, glyph_shape = add_insert(851, 123, glyphs=True)
    paint_red_dark_body_context(827, 230)
    ring_card, ring_shape = add_insert(851, 243, sponsor_ring=True)
    paint_red_dark_body_context(736, 350)
    tall_card, tall_shape = add_insert(760, 363, tall_decal=True)
    paint_red_dark_body_context(827, 470)
    protected_insert, protected_shape = add_insert(851, 483, protected=True)

    crest = (slice(760, 869), slice(640, 728))
    sponsors[crest] = 255
    rgb[crest] = np.array([238, 210, 164], np.uint8)
    rgb[778:852:12, 650:716] = np.array([110, 52, 52], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "small_vertical_red_livery_insert_panel"
    assert (mask[good][good_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[ring_card][ring_shape] > 0).mean() == 0
    assert (mask[tall_card][tall_shape] > 0).mean() == 0
    assert (mask[protected_insert][protected_shape] > 0).mean() == 0
    assert (mask[crest] > 0).mean() == 0


def test_smart_tga_pale_blue_context_warm_livery_bars_fall_back_to_paint():
    n = 512
    rgb = np.full((n, n, 3), np.array([142, 204, 238], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_bar(y0, x0, h, w, *, dark_context=False, glyph_card=False, protected=False):
        shape = np.ones((h, w), bool)
        if h >= 30:
            shape[5:50, 5:6] = False
            shape[10:20, 8:9] = False
        else:
            shape[4, 3] = False
            shape[12, 5] = False
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        yy, xx = np.indices((h, w))
        if dark_context:
            rgb[y0 - 7:y0 + h + 7, x0 - 7:x0 + w + 7] = np.array([30, 42, 34], np.uint8)
        sponsors[target][shape] = 255
        panel = rgb[target]
        panel[shape] = np.array([224, 104, 42], np.uint8)
        panel[shape & ((yy + xx) % 4 == 0)] = np.array([185, 214, 50], np.uint8)
        panel[shape & ((yy * 2 + xx) % 9 == 0)] = np.array([245, 225, 110], np.uint8)
        panel[shape & ((yy + 2 * xx) % 13 == 0)] = np.array([210, 60, 150], np.uint8)
        if glyph_card:
            panel[shape & (yy >= 3) & (yy <= h - 4) & ((yy - 3) % 7 <= 1)] = np.array([20, 24, 28], np.uint8)
            panel[shape & (xx >= 2) & (xx <= w - 3) & ((xx - 2) % 5 == 0)] = np.array([246, 246, 238], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    tall_bar, tall_shape = add_bar(227, 96, 55, 12)
    small_bar, small_shape = add_bar(390, 246, 18, 8)
    dark_context_bar, dark_shape = add_bar(390, 286, 18, 8, dark_context=True)
    glyph_card, glyph_shape = add_bar(390, 326, 18, 8, glyph_card=True)
    protected_bar, protected_shape = add_bar(227, 136, 55, 12, protected=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {
        "pale_blue_context_warm_livery_bar",
    }
    assert (mask[tall_bar][tall_shape] > 0).mean() > 0.95
    assert (mask[small_bar][small_shape] > 0).mean() > 0.95
    assert (mask[dark_context_bar][dark_shape] > 0).mean() == 0
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[protected_bar][protected_shape] > 0).mean() == 0


def test_smart_tga_left_edge_low_edge_warm_livery_slab_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([58, 50, 42], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_slab(y0, x0, glyphs=False, protect=False):
        h, w = 69, 171
        yy, xx = np.indices((h, w))
        shape = xx < 118
        shape |= (yy >= 51)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([255, 226, 31], np.uint8)
        dark_patch = shape & (xx < 42) & (yy >= 8) & (yy < 58)
        rgb[target][dark_patch] = np.array([50, 42, 25], np.uint8)
        if glyphs:
            rgb[y0 + 12:y0 + 58:8, x0 + 10:x0 + 150] = np.array([246, 246, 232], np.uint8)
            rgb[y0 + 18:y0 + 56:11, x0 + 20:x0 + 142] = np.array([14, 14, 16], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    slab, slab_shape = add_slab(335, 0)
    text_card, text_shape = add_slab(430, 0, glyphs=True)
    non_edge, non_edge_shape = add_slab(525, 240)
    protected_slab, protected_shape = add_slab(620, 0, protect=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "left_edge_low_edge_warm_livery_slab"
    assert (mask[slab][slab_shape] > 0).mean() > 0.95
    assert (mask[text_card][text_shape] > 0).mean() == 0
    assert (mask[non_edge][non_edge_shape] > 0).mean() == 0
    assert (mask[protected_slab][protected_shape] > 0).mean() == 0


def test_smart_tga_low_edge_pink_lower_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([236, 112, 120], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_panel(y0, x0, glyphs=False, protect=False):
        h, w = 59, 211
        yy, xx = np.indices((h, w))
        shape = xx < (130 - yy * 0.9)
        shape |= yy >= 52
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([236, 112, 120], np.uint8)
        soft_white = shape & np.isin(yy, [32, 52]) & (xx > 20) & (xx < 190)
        rgb[target][soft_white] = np.array([244, 238, 232], np.uint8)
        if glyphs:
            rgb[y0 + 8:y0 + 50:7, x0 + 35:x0 + 186] = np.array([248, 248, 236], np.uint8)
            rgb[y0 + 12:y0 + 52:9, x0 + 44:x0 + 178] = np.array([12, 12, 16], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    panel, panel_shape = add_panel(782, 19)
    text_card, text_shape = add_panel(650, 19, glyphs=True)
    not_lower_left, not_lower_left_shape = add_panel(782, 260)
    protected_panel, protected_shape = add_panel(782, 500, protect=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "low_edge_pink_lower_livery_panel"
    assert (mask[panel][panel_shape] > 0).mean() > 0.95
    assert (mask[text_card][text_shape] > 0).mean() == 0
    assert (mask[not_lower_left][not_lower_left_shape] > 0).mean() == 0
    assert (mask[protected_panel][protected_shape] > 0).mean() == 0


def test_smart_tga_left_edge_red_white_lower_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([48, 45, 45], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 823, 0, 55, 167
    target = (slice(y0, y0 + h), slice(x0, x0 + w))
    yy, xx = np.indices((h, w))
    shape = np.ones((h, w), bool)
    shape[:10, 82:] = False
    sponsors[target][shape] = 255
    rgb[y0 - 8:y0, x0:x0 + w] = np.array([122, 32, 42], np.uint8)
    rgb[y0:y0 + h, x0 + w:x0 + w + 8] = np.array([122, 32, 42], np.uint8)
    rgb[target][shape] = np.array([222, 16, 44], np.uint8)
    stripe = shape & (yy >= 47) & (xx < 160)
    rgb[target][stripe] = np.array([244, 236, 232], np.uint8)

    sponsor_card = (slice(725, 751), slice(397, 419))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([232, 44, 64], np.uint8)
    rgb[728:748:5, 401:416] = np.array([246, 246, 236], np.uint8)
    rgb[732:746:7, 404:416] = np.array([24, 24, 28], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "left_edge_red_white_lower_livery_panel"
    assert (mask[target][shape] > 0).mean() > 0.95
    assert (mask[sponsor_card] > 0).mean() == 0


def test_smart_tga_top_right_solid_red_livery_cap_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([71, 71, 71], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_cap(y0, x0, glyphs=False, protect=False):
        h, w = 45, 27
        yy, xx = np.indices((h, w))
        shape = xx < 24
        shape[0, 24:] = True
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([144, 40, 40], np.uint8)
        if glyphs:
            rgb[y0 + 7:y0 + 39:7, x0 + 3:x0 + 24] = np.array([246, 246, 232], np.uint8)
            rgb[y0 + 11:y0 + 37:9, x0 + 6:x0 + 21] = np.array([12, 12, 16], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    cap, cap_shape = add_cap(9, 994)
    glyph_card, glyph_shape = add_cap(70, 994, glyphs=True)
    off_edge, off_edge_shape = add_cap(9, 930)
    protected_cap, protected_shape = add_cap(130, 994, protect=True)

    horizontal = (slice(90, 107), slice(953, 995))
    yy, xx = np.indices((17, 42))
    horizontal_shape = xx < 36
    horizontal_shape[:, 0] = True
    sponsors[horizontal][horizontal_shape] = 255
    rgb[horizontal][horizontal_shape] = np.array([144, 40, 40], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "top_right_solid_red_livery_cap"
    assert (mask[cap][cap_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[off_edge][off_edge_shape] > 0).mean() == 0
    assert (mask[protected_cap][protected_shape] > 0).mean() == 0
    assert (mask[horizontal][horizontal_shape] > 0).mean() == 0


def test_smart_tga_upper_right_solid_red_livery_bar_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([112, 104, 96], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_bar(y0, x0, glyphs=False, protect=False, context=True):
        h, w = 17, 42
        yy, xx = np.indices((h, w))
        shape = xx < 36
        shape[0, :] = True
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        if context:
            rgb[max(0, y0 - 18):y0 + h + 18, max(0, x0 - 18):x0 + w + 18] = np.array([118, 108, 95], np.uint8)
            rgb[max(0, y0 - 16):y0 - 4, max(0, x0 - 12):x0 + 20] = np.array([144, 40, 40], np.uint8)
            rgb[y0 + h + 4:y0 + h + 18, x0 + 8:x0 + w + 14] = np.array([64, 60, 58], np.uint8)
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([144, 40, 40], np.uint8)
        if glyphs:
            rgb[y0 + 4:y0 + 14:4, x0 + 5:x0 + 34] = np.array([246, 246, 232], np.uint8)
            rgb[y0 + 6:y0 + 15:5, x0 + 9:x0 + 31] = np.array([12, 12, 16], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    def add_realistic_bar_context(target, shape):
        comp = np.zeros((n, n), bool)
        comp[target][shape] = True
        rgb[target] = np.array([144, 40, 40], np.uint8)
        local_rgb = rgb[target]
        antialias = np.zeros_like(shape, dtype=bool)
        antialias[2:15:4, 4:10] = True
        antialias &= shape
        local_rgb[antialias] = np.array([70, 45, 42], np.uint8)
        kernel = car_layers_mod.cv2.getStructuringElement(car_layers_mod.cv2.MORPH_ELLIPSE, (17, 17))
        ring = car_layers_mod.cv2.dilate(comp.astype(np.uint8), kernel) > 0
        ring &= ~comp
        ring &= ~((numbers > 0) | (template > 0) | (brand > 0))

        near_kernel = car_layers_mod.cv2.getStructuringElement(car_layers_mod.cv2.MORPH_ELLIPSE, (7, 7))
        near_red = car_layers_mod.cv2.dilate(comp.astype(np.uint8), near_kernel) > 0
        near_red &= ring
        rgb[near_red] = np.array([144, 40, 40], np.uint8)

        far = ring & ~near_red
        ys, xs = np.where(far)
        order = np.lexsort((xs, ys))
        ys = ys[order]
        xs = xs[order]
        white_end = int(0.18 * len(ys))
        dark_end = int(0.58 * len(ys))
        rgb[ys[:white_end], xs[:white_end]] = np.array([184, 176, 164], np.uint8)
        rgb[ys[white_end:dark_end], xs[white_end:dark_end]] = np.array([64, 60, 58], np.uint8)
        rgb[ys[dark_end:], xs[dark_end:]] = np.array([118, 108, 95], np.uint8)

    glyph_card, glyph_shape = add_bar(53, 649, glyphs=True)
    off_position, off_shape = add_bar(90, 953)
    protected_bar, protected_shape = add_bar(53, 900, protect=True)
    bar, bar_shape = add_bar(53, 953, context=False)
    add_realistic_bar_context(bar, bar_shape)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "upper_right_solid_red_livery_bar"
    assert (mask[bar][bar_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[off_position][off_shape] > 0).mean() == 0
    assert (mask[protected_bar][protected_shape] > 0).mean() == 0


def test_smart_tga_yellow_panel_red_livery_border_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 34], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_border(y0, x0, glyphs=False, protect=False):
        h, w = 19, 214
        shape = np.zeros((h, w), bool)
        shape[:12, :] = True
        shape[:, 0] = True
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[max(0, y0 - 24):y0 + h + 24, max(0, x0 - 24):x0 + w + 24] = np.array([230, 216, 18], np.uint8)
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([238, 42, 38], np.uint8)
        if glyphs:
            rgb[y0 + 3:y0 + 10:3, x0 + 28:x0 + 188] = np.array([246, 246, 232], np.uint8)
            rgb[y0 + 5:y0 + 12:4, x0 + 40:x0 + 176] = np.array([12, 12, 16], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    border, border_shape = add_border(355, 518)
    glyph_card, glyph_shape = add_border(430, 518, glyphs=True)
    protected_border, protected_shape = add_border(505, 518, protect=True)

    short = (slice(585, 604), slice(518, 608))
    short_shape = np.zeros((19, 90), bool)
    short_shape[:12, :] = True
    short_shape[:, 0] = True
    sponsors[short][short_shape] = 255
    rgb[short][short_shape] = np.array([238, 42, 38], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "yellow_panel_red_livery_border"
    assert (mask[border][border_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[protected_border][protected_shape] > 0).mean() == 0
    assert (mask[short][short_shape] > 0).mean() == 0


def test_smart_tga_top_edge_solid_red_livery_bar_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([71, 71, 71], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_top_bar(y0, x0, glyphs=False, protect=False):
        h, w = 32, 83
        shape = np.ones((h, w), bool)
        shape[2:30, 10:16] = False
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([144, 40, 40], np.uint8)
        if glyphs:
            rgb[y0 + 6:y0 + 27:5, x0 + 20:x0 + 74] = np.array([246, 246, 232], np.uint8)
            rgb[y0 + 9:y0 + 28:7, x0 + 28:x0 + 69] = np.array([12, 12, 16], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    bar, bar_shape = add_top_bar(0, 941)
    glyph_card, glyph_shape = add_top_bar(60, 941, glyphs=True)
    off_position, off_shape = add_top_bar(0, 830)
    protected_bar, protected_shape = add_top_bar(120, 941, protect=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "top_edge_solid_red_livery_bar"
    assert (mask[bar][bar_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[off_position][off_shape] > 0).mean() == 0
    assert (mask[protected_bar][protected_shape] > 0).mean() == 0


def test_smart_tga_tiny_vertical_orange_livery_insert_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([38, 38, 40], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def insert_shape():
        h, w = 28, 15
        shape = np.zeros((h, w), bool)
        shape[:, :8] = True
        shape[:7, :] = True
        shape[7, 8:13] = True
        return shape

    def add_insert(y0, x0, bg=None, glyphs=False, protect=False):
        shape = insert_shape()
        h, w = shape.shape
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        if bg is not None:
            rgb[max(0, y0 - 16):y0 + h + 16, max(0, x0 - 16):x0 + w + 16] = bg
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([225, 114, 0], np.uint8)
        yy, xx = np.indices((h, w))
        antialias = shape & (yy < 2)
        rgb[target][antialias] = np.array([54, 43, 27], np.uint8)
        if glyphs:
            rgb[y0 + 4:y0 + 19:5, x0 + 2:x0 + 13] = np.array([244, 244, 235], np.uint8)
            rgb[y0 + 8:y0 + 21:6, x0 + 4:x0 + 12] = np.array([10, 10, 12], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    good, good_shape = add_insert(590, 221)
    bright_card, bright_shape = add_insert(590, 300, bg=np.array([236, 204, 26], np.uint8))
    glyph_card, glyph_shape = add_insert(650, 221, glyphs=True)
    protected, protected_shape = add_insert(710, 221, protect=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tiny_vertical_orange_livery_insert"
    assert (mask[good][good_shape] > 0).mean() > 0.95
    assert (mask[bright_card][bright_shape] > 0).mean() == 0
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[protected][protected_shape] > 0).mean() == 0


def test_smart_tga_tiny_horizontal_red_yellow_livery_tab_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([29, 29, 31], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def tab_shape():
        h, w = 12, 32
        shape = np.ones((h, w), bool)
        shape[0, 14:28] = False
        shape[1, 14:28] = False
        shape[2, 18:32] = False
        shape[3, 20:32] = False
        shape[8:12, 0:10] = False
        shape[9:12, 10:15] = False
        return shape

    def add_tab(y0, x0, *, glyphs=False, bright_ring=False, protected=False, wrong_geometry=False):
        shape = tab_shape()
        if wrong_geometry:
            shape = np.pad(shape, ((0, 0), (0, 12)), constant_values=False)
            shape[:, 32:44] = shape[:, 20:32]
        h, w = shape.shape
        if bright_ring:
            rgb[y0 - 14:y0 + h + 14, x0 - 14:x0 + w + 14] = np.array([198, 44, 34], np.uint8)
        else:
            rgb[y0 - 14:y0 + h + 14, x0 - 14:x0 + w + 14] = np.array([29, 29, 31], np.uint8)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        yy, xx = np.indices((h, w))
        dark = shape & (((xx * 3 + yy * 5) % 11) < 3)
        rgb[target][shape] = np.array([170, 35, 18], np.uint8)
        yellow = shape & (((xx + yy) % 17) < 3)
        rgb[target][yellow] = np.array([214, 157, 16], np.uint8)
        rgb[target][dark] = np.array([52, 42, 34], np.uint8)
        if glyphs:
            glyph = shape & (((xx % 8) < 2) | ((yy % 6) < 1))
            rgb[target][glyph] = np.array([244, 244, 232], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    good, good_shape = add_tab(383, 375)
    glyph_card, glyph_shape = add_tab(430, 375, glyphs=True)
    bright_card, bright_shape = add_tab(477, 375, bright_ring=True)
    protected_tab, protected_shape = add_tab(524, 375, protected=True)
    wide_tab, wide_shape = add_tab(571, 375, wrong_geometry=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tiny_horizontal_red_yellow_livery_tab"
    assert (mask[good][good_shape] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_shape] > 0).mean() == 0
    assert (mask[bright_card][bright_shape] > 0).mean() == 0
    assert (mask[protected_tab][protected_shape] > 0).mean() == 0
    assert (mask[wide_tab][wide_shape] > 0).mean() == 0


def test_smart_tga_left_edge_vertical_warm_gray_livery_strip_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([38, 38, 42], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def strip_shape():
        h, w = 144, 49
        yy, xx = np.indices((h, w))
        shape = xx < 24
        shape |= (yy % 8) == 0
        shape |= ((xx >= 39) & (yy >= 42) & (yy <= 92))
        return shape

    def add_strip(y0, x0, *, sponsor_ring=False, protected=False):
        shape = strip_shape()
        h, w = shape.shape
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        ring_x0 = min(n, x0 + w + 1)
        ring_x1 = min(n, x0 + w + 4)
        rgb[max(0, y0 - 8):y0 + h + 8, ring_x0:ring_x1] = np.array([178, 178, 170], np.uint8)
        sponsors[target][shape] = 255
        yy, xx = np.indices((h, w))
        target_rgb = rgb[target]
        target_rgb[shape] = np.array([190, 98, 75], np.uint8)
        pale = shape & ((((yy + 3) % 17) < 3) | ((xx >= 31) & (xx <= 40) & (yy >= 18) & (yy <= 88)))
        dark = shape & ~pale & (((yy * 2 + xx * 5) % 13) < 3)
        target_rgb[pale] = np.array([210, 210, 204], np.uint8)
        target_rgb[dark] = np.array([18, 16, 16], np.uint8)
        if sponsor_ring:
            ring = (slice(max(0, y0 - 3), min(n, y0 + h + 3)), slice(min(n, x0 + w + 2), min(n, x0 + w + 20)))
            sponsors[ring] = 255
            rgb[ring] = np.array([210, 52, 44], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    strip, strip_mask = add_strip(202, 0)
    off_edge, off_edge_mask = add_strip(202, 90)
    sponsor_ring, sponsor_ring_mask = add_strip(410, 0, sponsor_ring=True)
    protected_strip, protected_mask = add_strip(620, 0, protected=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "left_edge_vertical_warm_gray_livery_strip"
    assert (mask[strip][strip_mask] > 0).mean() > 0.95
    assert (mask[off_edge][off_edge_mask] > 0).mean() == 0
    assert (mask[sponsor_ring][sponsor_ring_mask] > 0).mean() == 0
    assert (mask[protected_strip][protected_mask] > 0).mean() == 0


def test_smart_tga_left_edge_broad_low_edge_red_livery_slab_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([226, 28, 46], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    slab = (slice(356, 418), slice(0, 339))
    sponsors[slab] = 255

    off_edge = (slice(446, 508), slice(40, 379))
    sponsors[off_edge] = 255

    text_card = (slice(536, 598), slice(0, 339))
    sponsors[text_card] = 255
    rgb[548:556, 18:320] = np.array([246, 246, 236], np.uint8)
    rgb[570:579, 36:302] = np.array([16, 16, 18], np.uint8)

    protected_slab = (slice(626, 688), slice(0, 339))
    sponsors[protected_slab] = 255
    numbers[protected_slab] = 255
    template[protected_slab] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "left_edge_broad_low_edge_red_livery_slab"
    assert (mask[slab] > 0).mean() > 0.95
    assert (mask[off_edge] > 0).mean() == 0
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[protected_slab] > 0).mean() == 0


def test_smart_tga_right_edge_vertical_red_livery_strip_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([80, 80, 80], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def strip_shape():
        h, w = 589, 35
        yy, xx = np.indices((h, w))
        shape = xx < 18
        shape[((yy % 17) <= 1) & (xx < 26)] = True
        shape[((yy % 43) == 0) & (xx >= 18) & (xx < 24)] = True
        shape[(yy % 89) == 0] = True
        return shape

    def add_strip(y0, x0, *, glyphs=False, protected=False):
        shape = strip_shape()
        h, w = shape.shape
        yy, xx = np.indices((h, w))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        panel = rgb[target]
        panel[shape] = np.array([230, 40, 88], np.uint8)
        panel[shape & ((yy + xx) % 19 == 0)] = np.array([252, 18, 132], np.uint8)
        panel[shape & ((yy + xx) % 13 == 0)] = np.array([80, 80, 80], np.uint8)
        panel[shape & ((yy * 3 + xx) % 71 == 0)] = np.array([188, 32, 70], np.uint8)
        if glyphs:
            panel[shape & (yy >= 22) & (yy <= 540) & ((yy - 22) % 24 <= 3)] = np.array([246, 246, 236], np.uint8)
            panel[shape & (yy >= 40) & (yy <= 535) & (xx >= 5) & (xx <= 22) & ((yy - 40) % 31 <= 4)] = np.array([12, 12, 14], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    strip, strip_mask = add_strip(116, 989)
    glyph_card, glyph_mask = add_strip(116, 944, glyphs=True)
    off_edge, off_edge_mask = add_strip(116, 890)
    protected_strip, protected_mask = add_strip(116, 854, protected=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_vertical_red_livery_strip"
    assert (mask[strip][strip_mask] > 0).mean() > 0.95
    assert (mask[glyph_card][glyph_mask] > 0).mean() == 0
    assert (mask[off_edge][off_edge_mask] > 0).mean() == 0
    assert (mask[protected_strip][protected_mask] > 0).mean() == 0


def test_smart_tga_blank_red_dlm_livery_panels_and_stripe_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    red = np.array([180, 6, 46], np.uint8)

    top_shape = np.zeros((84, 156), bool)
    top_shape[8:50, :] = True
    top_shape[:, :2] = True
    top_panel = (slice(34, 118), slice(320, 476))
    sponsors[top_panel][top_shape] = 255
    rgb[top_panel][top_shape] = red

    lower_panel = (slice(929, 965), slice(649, 720))
    sponsors[lower_panel] = 255
    rgb[lower_panel] = red

    right_strip = (slice(745, 992), slice(991, 1021))
    sponsors[right_strip] = 255
    rgb[right_strip] = red

    rgb[855:905, 680:908] = np.array([236, 234, 224], np.uint8)
    rgb[870:889, 699:896] = np.array([58, 58, 58], np.uint8)
    thin_stripe = (slice(871, 888), slice(700, 895))
    sponsors[thin_stripe] = 255
    rgb[thin_stripe] = red

    logo_shape = top_shape.copy()
    logo_panel = (slice(152, 236), slice(320, 476))
    sponsors[logo_panel][logo_shape] = 255
    rgb[logo_panel][logo_shape] = red
    yy, xx = np.indices(logo_shape.shape)
    white_logo = logo_shape & (yy >= 28) & (yy < 39) & (xx >= 22) & (xx < 134)
    dark_logo = logo_shape & (yy >= 44) & (yy < 50) & (xx >= 42) & (xx < 116)
    rgb[logo_panel][white_logo] = np.array([246, 246, 236], np.uint8)
    rgb[logo_panel][dark_logo] = np.array([16, 16, 18], np.uint8)

    protected_panel = (slice(929, 965), slice(760, 831))
    sponsors[protected_panel] = 255
    rgb[protected_panel] = red
    numbers[protected_panel] = 255
    template[protected_panel] = 255

    tiny_fragment = (slice(797, 803), slice(580, 591))
    sponsors[tiny_fragment] = 255
    rgb[tiny_fragment] = red

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [c["reason"] for c in info["components"]]
    assert info["status"] == "applied"
    assert reasons.count("solid_red_dlm_livery_block") == 2
    assert reasons.count("right_edge_solid_red_dlm_livery_strip") == 1
    assert reasons.count("thin_red_dlm_livery_stripe") == 1
    assert (mask[top_panel][top_shape] > 0).mean() > 0.95
    assert (mask[lower_panel] > 0).mean() > 0.95
    assert (mask[right_strip] > 0).mean() > 0.95
    assert (mask[thin_stripe] > 0).mean() > 0.95
    assert (mask[logo_panel][logo_shape] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0
    assert (mask[tiny_fragment] > 0).mean() == 0


def test_smart_tga_tiny_right_edge_solid_red_dlm_livery_insert_falls_back_to_paint():
    n = 1024
    y0, x0, h, w = 550, 987, 67, 8

    def run_scene(*, glyph=False, protected=False):
        rgb = np.full((n, n, 3), np.array([246, 246, 240], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)

        yy, xx = np.indices((h, w))
        insert_shape = np.zeros((h, w), bool)
        for row in range(h):
            if row in {0, 33}:
                width = 8
            elif 1 <= row <= 21:
                width = 7
            else:
                width = 6
            insert_shape[row, w - width:w] = True
        insert = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[insert] = np.array([228, 38, 24], np.uint8)
        sponsors[insert][insert_shape] = 255
        rgb[insert][insert_shape] = np.array([228, 38, 24], np.uint8)

        # Adjacent red paint context keeps this a body insert, not an isolated sponsor glyph.
        rgb[y0:y0 + h, x0 - 2:x0] = np.array([228, 38, 24], np.uint8)

        if glyph:
            rgb[insert][insert_shape & (yy >= 12) & (yy <= 48) & (xx >= 2) & (xx <= 5)] = np.array([248, 248, 240], np.uint8)
            rgb[insert][insert_shape & (yy >= 28) & (yy <= 58) & (xx >= 3) & (xx <= 6)] = np.array([18, 18, 20], np.uint8)

        if protected:
            template[insert][insert_shape] = 255

        internal = (slice(y0, y0 + h), slice(920, 920 + w))
        sponsors[internal][insert_shape] = 255
        rgb[internal][insert_shape] = np.array([228, 38, 24], np.uint8)

        mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        return mask, info, insert, insert_shape, internal

    mask, info, insert, insert_shape, internal = run_scene()
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tiny_right_edge_solid_red_dlm_livery_insert"
    assert (mask[insert][insert_shape] > 0).mean() > 0.95
    assert (mask[internal] > 0).mean() == 0

    glyph_mask, glyph_info, glyph_insert, glyph_shape, _internal = run_scene(glyph=True)
    assert glyph_info["status"] in {"empty", "filtered"}
    assert (glyph_mask[glyph_insert][glyph_shape] > 0).mean() == 0

    protected_mask, protected_info, protected_insert, protected_shape, _internal = run_scene(
        protected=True
    )
    assert protected_info["status"] in {"empty", "filtered"}
    assert (protected_mask[protected_insert][protected_shape] > 0).mean() == 0


def test_smart_tga_right_edge_red_pale_dlm_livery_strip_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([124, 122, 124], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 743, 989, 266, 35
    yy, xx = np.indices((h, w))
    strip_shape = np.ones((h, w), bool)
    strip_shape[24:89, :5] = False
    strip = (slice(y0, y0 + h), slice(x0, x0 + w))
    sponsors[strip][strip_shape] = 255
    rgb[strip][strip_shape] = np.array([255, 40, 8], np.uint8)
    pale_center = strip_shape & (yy % 12 == 0) & (xx >= 10) & (xx < 20)
    rgb[strip][pale_center] = np.array([246, 214, 214], np.uint8)

    text_strip = (slice(743, 1009), slice(920, 955))
    sponsors[text_strip] = 255
    rgb[text_strip] = np.array([255, 42, 10], np.uint8)
    rgb[780:806, 924:951] = np.array([246, 246, 236], np.uint8)
    rgb[830:862, 926:949] = np.array([24, 24, 26], np.uint8)

    protected = (slice(743, 1009), slice(870, 905))
    sponsors[protected] = 255
    rgb[protected] = np.array([255, 40, 8], np.uint8)
    rgb[protected][np.indices((266, 35))[1] == 17] = np.array([246, 214, 214], np.uint8)
    template[protected] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_red_pale_dlm_livery_strip"
    assert (mask[strip][strip_shape] > 0).mean() > 0.95
    assert (mask[text_strip] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0


def test_smart_tga_right_edge_lower_tall_red_pale_dlm_livery_strip_falls_back_to_paint():
    n = 1024
    y0, x0, h, w = 745, 989, 279, 35

    def run_scene(*, glyph=False):
        rgb = np.full((n, n, 3), np.array([250, 250, 246], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)

        strip_shape = np.ones((h, w), bool)
        strip_shape[:31, :4] = False
        strip = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[strip][strip_shape] = 255
        rgb[strip][strip_shape] = np.array([229, 34, 55], np.uint8)
        yy, xx = np.indices((h, w))
        pale_line = strip_shape & (yy % 14 == 0) & (xx >= 12) & (xx < 24)
        rgb[strip][pale_line] = np.array([248, 206, 206], np.uint8)
        if glyph:
            rgb[790:816, 998:1022] = np.array([246, 246, 236], np.uint8)
            rgb[840:872, 1000:1020] = np.array([24, 24, 26], np.uint8)

        text_strip = (slice(745, 1024), slice(920, 955))
        sponsors[text_strip] = 255
        rgb[text_strip] = np.array([238, 36, 42], np.uint8)
        rgb[790:816, 924:951] = np.array([246, 246, 236], np.uint8)
        rgb[840:872, 926:949] = np.array([24, 24, 26], np.uint8)

        protected = (slice(745, 1024), slice(870, 905))
        sponsors[protected] = 255
        rgb[protected] = np.array([238, 36, 42], np.uint8)
        rgb[protected][np.indices((279, 35))[1] == 17] = np.array([248, 206, 206], np.uint8)
        template[protected] = 255

        mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        return mask, info, strip, text_strip, protected

    mask, info, strip, text_strip, protected = run_scene()
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_red_pale_white_context_dlm_livery_strip"
    assert (mask[strip] > 0).mean() > 0.95
    assert (mask[text_strip] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0

    glyph_mask, glyph_info, glyph_strip, _text_strip, _protected = run_scene(glyph=True)
    assert glyph_info["status"] == "empty"
    assert (glyph_mask[glyph_strip] > 0).mean() == 0


def test_smart_tga_right_edge_tall_red_pink_dlm_livery_strip_falls_back_to_paint():
    n = 1024
    y0, x0, h, w = 117, 1000, 591, 24

    def run_scene(*, glyph=False, protected=False):
        rgb = np.full((n, n, 3), np.array([24, 24, 26], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)

        yy, xx = np.indices((h, w))
        widths = np.rint(16.8 + 7.2 * np.sin(np.arange(h) / 39.0)).astype(int)
        widths = np.clip(widths, 10, w)
        strip_shape = np.zeros((h, w), bool)
        for row, width in enumerate(widths):
            strip_shape[row, w - width:w] = True
        strip = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[strip][strip_shape] = 255

        rgb[strip][strip_shape] = np.array([255, 40, 8], np.uint8)
        dark_dashes = strip_shape & (yy % 9 == 0) & (xx >= 12) & (xx <= 15)
        rgb[strip][dark_dashes] = np.array([34, 8, 5], np.uint8)

        if glyph:
            rgb[170:226, 1005:1018] = np.array([246, 246, 238], np.uint8)
            rgb[308:362, 1007:1020] = np.array([12, 12, 14], np.uint8)
            rgb[470:516, 1004:1019] = np.array([246, 246, 238], np.uint8)

        if protected:
            template[strip][strip_shape] = 255

        mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        return mask, info, strip, strip_shape

    mask, info, strip, strip_shape = run_scene()
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_tall_red_pink_dlm_livery_strip"
    assert (mask[strip][strip_shape] > 0).mean() > 0.95

    glyph_mask, glyph_info, glyph_strip, glyph_shape = run_scene(glyph=True)
    assert glyph_info["status"] in {"empty", "filtered"}
    assert (glyph_mask[glyph_strip][glyph_shape] > 0).mean() == 0

    protected_mask, protected_info, protected_strip, protected_shape = run_scene(protected=True)
    assert protected_info["status"] in {"empty", "filtered"}
    assert (protected_mask[protected_strip][protected_shape] > 0).mean() == 0


def test_smart_tga_right_edge_dark_red_dlm_side_livery_strip_falls_back_to_paint():
    n = 1024
    y0, x0, h, w = 116, 989, 589, 35

    def run_scene(*, glyph=False, protected=False):
        rgb = np.full((n, n, 3), np.array([24, 24, 25], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)

        yy, xx = np.indices((h, w))
        widths = np.rint(18.5 + 8.0 * np.sin(np.arange(h) / 44.0)).astype(int)
        widths = np.clip(widths, 11, 27)
        strip_shape = np.zeros((h, w), bool)
        for row, width in enumerate(widths):
            strip_shape[row, w - width:w] = True
        strip_shape[::37, :] = True
        strip = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[strip][strip_shape] = 255
        rgb[strip][strip_shape] = np.array([234, 28, 24], np.uint8)

        dark_edge = strip_shape & (xx == (w - widths[:, None]))
        dark_dashes = strip_shape & (yy % 19 == 0) & (xx >= 13) & (xx <= 17)
        rgb[strip][dark_edge | dark_dashes] = np.array([34, 6, 5], np.uint8)

        if glyph:
            glyph_a = strip_shape & (yy >= 70) & (yy < 128) & (xx >= 17) & (xx <= 30)
            glyph_b = strip_shape & (yy >= 300) & (yy < 352) & (xx >= 15) & (xx <= 29)
            rgb[strip][glyph_a | glyph_b] = np.array([246, 246, 238], np.uint8)

        if protected:
            template[strip][strip_shape] = 255

        internal_card = (slice(116, 705), slice(910, 945))
        sponsors[internal_card] = 255
        rgb[internal_card] = np.array([234, 28, 24], np.uint8)

        mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        return mask, info, strip, strip_shape, internal_card

    mask, info, strip, strip_shape, internal_card = run_scene()
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_dark_red_dlm_side_livery_strip"
    assert (mask[strip][strip_shape] > 0).mean() > 0.95
    assert (mask[internal_card] > 0).mean() == 0

    glyph_mask, glyph_info, glyph_strip, glyph_shape, _internal_card = run_scene(glyph=True)
    assert glyph_info["status"] in {"empty", "filtered"}
    assert (glyph_mask[glyph_strip][glyph_shape] > 0).mean() == 0

    protected_mask, protected_info, protected_strip, protected_shape, _internal_card = run_scene(
        protected=True
    )
    assert protected_info["status"] in {"empty", "filtered"}
    assert (protected_mask[protected_strip][protected_shape] > 0).mean() == 0


def test_smart_tga_right_edge_neon_green_dlm_livery_strip_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([38, 38, 40], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 117, 1000, 591, 24
    yy, xx = np.indices((h, w))
    widths = np.rint(18 + 6 * np.sin(np.arange(h) / 43.0)).astype(int)
    widths = np.clip(widths, 12, w)
    strip_shape = np.zeros((h, w), bool)
    for row, width in enumerate(widths):
        strip_shape[row, w - width:w] = True
    strip = (slice(y0, y0 + h), slice(x0, x0 + w))
    sponsors[strip][strip_shape] = 255
    rgb[strip][strip_shape] = np.array([34, 238, 6], np.uint8)
    dark_edge = strip_shape & (xx == (w - widths[:, None]))
    dark_dashes = strip_shape & (yy % 17 == 0) & (xx >= 9) & (xx <= 12)
    rgb[strip][dark_edge | dark_dashes] = np.array([10, 40, 5], np.uint8)

    text_strip = (slice(117, 708), slice(960, 984))
    sponsors[text_strip] = 255
    rgb[text_strip] = np.array([34, 238, 6], np.uint8)
    rgb[180:236, 964:980] = np.array([245, 245, 238], np.uint8)
    rgb[302:344, 966:978] = np.array([18, 18, 20], np.uint8)

    protected = (slice(117, 708), slice(930, 954))
    sponsors[protected] = 255
    rgb[protected] = np.array([34, 238, 6], np.uint8)
    template[protected] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_neon_green_dlm_livery_strip"
    assert (mask[strip][strip_shape] > 0).mean() > 0.95
    assert (mask[text_strip] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0


def test_smart_tga_filled_multicolor_livery_graphic_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([62, 42, 38], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def graphic_shape():
        h, w = 96, 106
        yy, xx = np.indices((h, w))
        shape = np.ones((h, w), bool)
        shape[(yy < 8) & (xx < 18)] = False
        shape[(yy > 82) & (xx > 94)] = False
        shape[42:52, 94:102] = False
        shape[10:18, 42:54] = False
        return shape

    def paint_graphic(y0, x0, *, protected=False, text=False):
        shape = graphic_shape()
        h, w = shape.shape
        yy, xx = np.indices((h, w))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        red_region = shape & ((xx < 76) | ((yy > 58) & (xx < 96)))
        green_region = shape & ~red_region
        dark_region = shape & ((((xx - 40) / 27.0) ** 2 + ((yy - 54) / 20.0) ** 2) < 1.0)
        green_region &= ~dark_region
        red_region &= ~dark_region
        rgb[target][red_region] = np.array([172, 26, 22], np.uint8)
        rgb[target][green_region] = np.array([98, 166, 70], np.uint8)
        rgb[target][dark_region] = np.array([36, 22, 18], np.uint8)
        if text:
            rgb[y0 + 20:y0 + 28, x0 + 14:x0 + 94] = np.array([246, 246, 236], np.uint8)
            rgb[y0 + 55:y0 + 65, x0 + 20:x0 + 88] = np.array([18, 18, 20], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    graphic, graphic_mask = paint_graphic(925, 194)
    text_card, _text_mask = paint_graphic(760, 194, text=True)
    protected_graphic, protected_mask = paint_graphic(610, 194, protected=True)

    crest = (slice(450, 559), slice(15, 103))
    yy, xx = np.indices((109, 88))
    crest_shape = (((xx - 44) / 42.0) ** 2 + ((yy - 54) / 53.0) ** 2) <= 1.0
    crest_shape &= ~((yy > 88) & (xx < 22))
    sponsors[crest][crest_shape] = 255
    rgb[crest][crest_shape] = np.array([238, 210, 132], np.uint8)
    rgb[470:545:12, 30:88] = np.array([190, 32, 28], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "filled_multicolor_livery_graphic_panel"
    assert (mask[graphic][graphic_mask] > 0).mean() > 0.95
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[protected_graphic][protected_mask] > 0).mean() == 0
    assert (mask[crest] > 0).mean() == 0


def test_smart_tga_compact_dark_red_livery_block_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([36, 18, 16], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def block_shape():
        h, w = 39, 81
        yy, xx = np.indices((h, w))
        return (xx < 38) | ((yy >= 8) & (yy < 32) & (xx < w))

    def add_block(y0, x0, *, text=False, protected=False, wrong_geometry=False):
        shape = block_shape()
        if wrong_geometry:
            shape = np.pad(shape, ((0, 10), (0, 0)), constant_values=True)
        h, w = shape.shape
        yy, xx = np.indices((h, w))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        panel = rgb[target]
        panel[shape] = np.array([62, 0, 0], np.uint8)
        panel[shape & (xx < 24)] = np.array([76, 0, 0], np.uint8)
        panel[shape & (xx >= 60)] = np.array([88, 0, 0], np.uint8)
        panel[shape & (yy >= 30) & (xx < 56)] = np.array([36, 0, 0], np.uint8)
        if text:
            panel[shape & (yy >= 12) & (yy < 19) & (xx >= 10) & (xx < 72)] = np.array([246, 246, 236], np.uint8)
            panel[shape & (yy >= 24) & (yy < 30) & (xx >= 20) & (xx < 62)] = np.array([10, 10, 12], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        return target, shape

    good, good_shape = add_block(892, 133)
    text_card, _text_shape = add_block(812, 133, text=True)
    protected_block, protected_shape = add_block(732, 133, protected=True)
    tall_logo, _tall_shape = add_block(620, 133, wrong_geometry=True)

    square_badge = (slice(120, 169), slice(850, 899))
    sponsors[square_badge] = 255
    rgb[square_badge] = np.array([92, 0, 0], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "compact_dark_red_livery_block"
    assert (mask[good][good_shape] > 0).mean() > 0.95
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[protected_block][protected_shape] > 0).mean() == 0
    assert (mask[tall_logo] > 0).mean() == 0
    assert (mask[square_badge] > 0).mean() == 0


def test_smart_tga_smooth_saturated_red_livery_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([92, 84, 78], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_smooth_panel(y0, x0, h, w, kind, protect=False):
        yy, xx = np.indices((h, w))
        if kind == "long":
            shape = (yy >= 5) & (yy <= 28)
            shape[:10, 74:205] = False
            shape[24:, 248:] = False
            shape[:, :8] = True
            color = np.array([232, 92, 108], np.uint8)
        elif kind == "medium":
            shape = (xx < (w - 18 - yy * 0.15)) & (yy > 5)
            shape[18:118, :18] = True
            shape[45:100, 40:68] = False
            color = np.array([238, 88, 102], np.uint8)
        else:
            raise AssertionError(kind)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        rgb[target][shape] = color
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target][shape] = True
        return target, shape, full

    long_target, long_shape, _long_full = add_smooth_panel(972, 260, 36, 363, "long")
    medium_target, medium_shape, _medium_full = add_smooth_panel(380, 902, 144, 95, "medium")
    _protected_target, _protected_shape, protected_full = add_smooth_panel(682, 620, 144, 95, "medium", protect=True)

    sponsor_card = (slice(110, 146), slice(260, 623))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([232, 88, 104], np.uint8)
    rgb[118:136:5, 282:600] = np.array([245, 246, 234], np.uint8)
    rgb[124:140:7, 300:580] = np.array([18, 16, 18], np.uint8)

    wordmark = (slice(210, 246), slice(260, 623))
    yy, xx = np.indices((36, 363))
    glyphs = (((xx // 22) % 2) == 0) & (yy > 4) & (yy < 31)
    glyphs |= ((yy > 15) & (yy < 22) & ((xx % 57) < 30))
    sponsors[wordmark][glyphs] = 255
    rgb[wordmark][glyphs] = np.array([232, 88, 104], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [c["reason"] for c in info["components"]]
    assert info["status"] == "applied"
    assert reasons.count("smooth_saturated_red_livery_panel") == 2
    assert (mask[long_target][long_shape] > 0).mean() > 0.95
    assert (mask[medium_target][medium_shape] > 0).mean() > 0.95
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[wordmark][glyphs] > 0).mean() == 0


def test_smart_tga_sloped_saturated_red_livery_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([86, 80, 74], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_sloped_panel(y0, x0, h, w, protect=False):
        yy, xx = np.indices((h, w))
        left = yy * 2.60
        right = w - 1 - yy * 0.35
        shape = (xx >= left) & (xx <= right)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        red = np.clip(242 + ((xx // 19) % 2) * 8, 236, 252)
        green = np.clip(14 + ((yy // 11) % 2) * 4, 12, 22)
        blue = np.clip(34 + ((xx + yy) % 7), 30, 44)
        panel_rgb = np.stack([red, green, blue], axis=2).astype(np.uint8)
        rgb[target][shape] = panel_rgb[shape]
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target][shape] = True
        return target, shape, full

    wide_target, wide_shape, _wide_full = add_sloped_panel(579, 120, 55, 171)
    compact_target, compact_shape, _compact_full = add_sloped_panel(414, 222, 36, 113)
    _protected_target, _protected_shape, protected_full = add_sloped_panel(752, 121, 55, 171, protect=True)

    square_logo = (slice(170, 222), slice(702, 754))
    sponsors[square_logo] = 255
    rgb[square_logo] = np.array([244, 70, 82], np.uint8)

    text_heavy = (slice(286, 341), slice(120, 291))
    yy, xx = np.indices((55, 171))
    text_shape = (xx >= (yy * 2.60)) & (xx <= (170 - yy * 0.35))
    sponsors[text_heavy][text_shape] = 255
    rgb[text_heavy][text_shape] = np.array([244, 70, 82], np.uint8)
    rgb[294:332:7, 138:274] = np.array([246, 246, 234], np.uint8)
    rgb[300:334:11, 150:262] = np.array([18, 18, 18], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [c["reason"] for c in info["components"]]
    assert info["status"] == "applied"
    assert reasons.count("sloped_saturated_red_livery_panel") == 2
    assert (mask[wide_target][wide_shape] > 0).mean() > 0.95
    assert (mask[compact_target][compact_shape] > 0).mean() > 0.95
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[square_logo] > 0).mean() == 0
    assert (mask[text_heavy] > 0).mean() == 0


def test_smart_tga_small_smooth_red_livery_chips_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([54, 50, 47], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    chip = (slice(471, 501), slice(247, 302))
    yy, xx = np.indices((30, 55))
    chip_shape = (xx >= (yy * 0.95 - 4)) & (xx <= (54 - yy * 0.55 + 3))
    sponsors[chip][chip_shape] = 255
    rgb[chip][chip_shape] = np.array([236, 50, 74], np.uint8)
    rgb[chip][chip_shape & ((xx % 17) < 3)] = np.array([244, 62, 86], np.uint8)

    square_logo = (slice(172, 224), slice(704, 756))
    sponsors[square_logo] = 255
    rgb[square_logo] = np.array([238, 54, 76], np.uint8)

    sponsor_card = (slice(318, 348), slice(428, 483))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([236, 50, 74], np.uint8)
    rgb[324:343:5, 434:478] = np.array([244, 244, 236], np.uint8)
    rgb[328:344:7, 440:472] = np.array([14, 14, 16], np.uint8)

    text_stripe = (slice(106, 120), slice(48, 184))
    sponsors[text_stripe] = 255
    rgb[text_stripe] = np.array([220, 44, 66], np.uint8)
    rgb[109:117, 68:168:11] = np.array([22, 22, 24], np.uint8)

    protected_chip = (slice(576, 606), slice(620, 675))
    sponsors[protected_chip][chip_shape] = 255
    rgb[protected_chip][chip_shape] = np.array([236, 50, 74], np.uint8)
    numbers[protected_chip][chip_shape] = 255
    template[protected_chip][chip_shape] = 255

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "small_smooth_red_livery_chip"
    assert (mask[chip][chip_shape] > 0).mean() > 0.95
    assert (mask[square_logo] > 0).mean() == 0
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[text_stripe] > 0).mean() == 0
    assert (mask[protected_chip][chip_shape] > 0).mean() == 0


def test_smart_tga_tiny_dark_red_dlm_livery_shards_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 18], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_dark_shard(y0, x0, h, w, *, protect=False, sponsor_text=False, bright=False):
        yy, xx = np.indices((h, w))
        shape = (xx < 2) | (xx >= w - 2) | (yy < 2) | (yy >= h - 2)
        shape |= np.abs(yy - (h - 1 - xx * 0.62)) <= 1
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        sub = rgb[target]
        if bright:
            sub[shape] = np.array([236, 38, 34], np.uint8)
        else:
            sub[shape] = np.array([76, 0, 0], np.uint8)
            deep = shape & (((xx + yy * 2) % 3) == 0)
            high_period = 13 if h <= 16 and w <= 23 else 12
            high = shape & (((xx * 3 + yy) % high_period) == 0)
            sub[deep] = np.array([34, 0, 0], np.uint8)
            sub[high] = np.array([240, 0, 0], np.uint8)
        if sponsor_text:
            sub[shape & (yy >= h // 2 - 1) & (yy <= h // 2 + 1)] = np.array([246, 246, 238], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target] = shape
        return full

    targets = [
        add_dark_shard(416, 809, 24, 25),
        add_dark_shard(612, 809, 25, 25),
        add_dark_shard(650, 812, 18, 18),
        add_dark_shard(715, 480, 16, 24),
        add_dark_shard(757, 410, 16, 23),
    ]
    text_card = add_dark_shard(120, 610, 24, 25, sponsor_text=True)
    bright_card = add_dark_shard(170, 610, 24, 25, bright=True)
    protected = add_dark_shard(220, 610, 24, 25, protect=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 5
    assert {component["reason"] for component in info["components"]} == {
        "tiny_dark_red_dlm_livery_shard"
    }
    for target in targets:
        assert (mask[target] > 0).mean() > 0.95
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[bright_card] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0


def test_smart_tga_micro_dark_red_dlm_number_livery_chips_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 18], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    chip_shape = np.array(
        [
            [1, 1, 1, 0],
            [1, 1, 1, 1],
            [1, 0, 0, 1],
            [0, 1, 1, 1],
            [1, 0, 1, 1],
            [0, 1, 1, 0],
            [1, 1, 0, 1],
            [1, 0, 0, 0],
            [1, 1, 1, 1],
            [0, 1, 1, 1],
        ],
        dtype=bool,
    )

    def add_chip(y0, x0, *, text=False, sponsor_ring=False, protected=False):
        h, w = chip_shape.shape
        yy, _xx = np.indices((h, w))
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[max(0, y0 - 9):y0 + h + 9, max(0, x0 - 9):x0 + w + 9] = np.array(
            [0, 0, 0], np.uint8
        )
        sponsors[target][chip_shape] = 255
        patch = rgb[target]
        coords = np.argwhere(chip_shape)
        for idx, (y, x) in enumerate(coords):
            if idx < 18:
                patch[y, x] = np.array([72, 6, 5], np.uint8)
            elif idx < 24:
                patch[y, x] = np.array([46, 10, 10], np.uint8)
            else:
                patch[y, x] = np.array([84, 62, 62], np.uint8)
        if text:
            patch[chip_shape & (yy == h // 2)] = np.array([245, 245, 236], np.uint8)
        if sponsor_ring:
            ring = (slice(max(0, y0 - 8), y0 + h + 8), slice(max(0, x0 - 8), x0 + w + 8))
            sponsors[ring] = np.maximum(sponsors[ring], np.uint8(255))
        if protected:
            numbers[target][chip_shape] = 255
            template[target][chip_shape] = 255
        full = np.zeros((n, n), bool)
        full[target] = chip_shape
        return full

    target = add_chip(312, 155)
    text_chip = add_chip(350, 155, text=True)
    sponsor_surrounded = add_chip(390, 155, sponsor_ring=True)
    protected_chip = add_chip(430, 155, protected=True)

    underline = (slice(74, 77), slice(49, 63))
    sponsors[underline] = 255
    rgb[66:85, 41:71] = np.array([0, 0, 0], np.uint8)
    rgb[underline] = np.array([72, 6, 5], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "micro_dark_red_dlm_number_livery_chip"
    assert (mask[target] > 0).mean() > 0.95
    assert (mask[text_chip] > 0).mean() == 0
    assert (mask[sponsor_surrounded] > 0).mean() == 0
    assert (mask[protected_chip] > 0).mean() == 0
    assert (mask[underline] > 0).mean() == 0


def test_smart_tga_shallow_dark_red_dlm_livery_slivers_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([42, 42, 44], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_sliver(y0, x0, *, protect=False, text=False):
        h, w = 10, 47
        yy, xx = np.indices((h, w))
        shape = (yy >= 3) & (yy <= 6)
        shape |= ((yy <= 2) | (yy >= 7)) & (xx >= 20) & (xx <= 22)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        panel = rgb[target]
        panel[shape] = np.array([155, 34, 45], np.uint8)
        panel[shape & (((xx + yy) % 3) == 0)] = np.array([24, 14, 18], np.uint8)
        panel[shape & (((xx * 2 + yy) % 11) == 0)] = np.array([218, 60, 70], np.uint8)
        if text:
            panel[shape & (yy >= 4) & (yy <= 5)] = np.array([242, 242, 232], np.uint8)
        if protect:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target] = shape
        return target, shape, full

    _sliver_a, _shape_a, full_a = add_sliver(752, 169)
    _sliver_b, _shape_b, full_b = add_sliver(297, 157)
    _text_sliver, _text_shape, text_full = add_sliver(420, 157, text=True)
    _protected_sliver, _protected_shape, protected_full = add_sliver(540, 157, protect=True)

    sponsor_card = (slice(210, 230), slice(370, 410))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([136, 34, 52], np.uint8)
    rgb[214:224, 378:402] = np.array([242, 222, 138], np.uint8)
    rgb[218:226, 384:398] = np.array([22, 22, 24], np.uint8)

    tall_decal = (slice(578, 632), slice(637, 641))
    sponsors[tall_decal] = 255
    rgb[tall_decal] = np.array([140, 34, 52], np.uint8)
    rgb[588:622:7, 637:641] = np.array([248, 248, 238], np.uint8)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {
        "shallow_dark_red_dlm_livery_sliver"
    }
    assert (mask[full_a] > 0).mean() > 0.95
    assert (mask[full_b] > 0).mean() > 0.95
    assert (mask[text_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[tall_decal] > 0).mean() == 0


def test_smart_tga_thin_vertical_warm_dlm_livery_seam_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([28, 26, 28], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def seam_shape():
        h, w = 54, 4
        shape = np.ones((h, w), bool)
        for row in range(52):
            shape[row, (row * 2) % w] = False
        yy, xx = np.indices((h, w))
        coords = np.argwhere(shape)
        warm_bright = np.zeros((h, w), bool)
        warm_dark = np.zeros((h, w), bool)
        warm_bright[coords[:60, 0], coords[:60, 1]] = True
        warm_dark[coords[60:96, 0], coords[60:96, 1]] = True
        deep_dark = shape & ~(warm_bright | warm_dark)
        return yy, xx, shape, warm_bright, warm_dark, deep_dark

    def add_seam(y0, x0, *, glyphs=False, sponsor_ring=False, protected=False, wrong_geometry=False):
        yy, xx, shape, warm_bright, warm_dark, deep_dark = seam_shape()
        if wrong_geometry:
            shape = np.pad(shape, ((0, 0), (0, 3)), constant_values=False)
            yy, xx = np.indices(shape.shape)
            warm_dark = shape & (((yy * 3 + xx) % 5) == 0)
            warm_bright = shape & ~warm_dark & (((yy + xx) % 3) != 0)
            deep_dark = shape & ~(warm_dark | warm_bright)
        h, w = shape.shape
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[max(0, y0 - 10):y0 + h + 10, max(0, x0 - 10):x0 + w + 10] = np.array([30, 28, 30], np.uint8)
        rgb[y0 - 8:y0 + h + 8:3, max(0, x0 - 8):x0 + w + 8] = np.array([112, 32, 20], np.uint8)
        rgb[y0 - 6:y0 + h + 6:7, max(0, x0 - 8):x0 + w + 8] = np.array([218, 218, 208], np.uint8)
        sponsors[target][shape] = 255
        patch = rgb[target]
        patch[warm_bright] = np.array([180, 48, 22], np.uint8)
        patch[warm_dark] = np.array([60, 16, 10], np.uint8)
        patch[deep_dark] = np.array([8, 6, 10], np.uint8)
        if glyphs:
            patch[shape & ((yy % 7) == 0)] = np.array([245, 245, 236], np.uint8)
        if sponsor_ring:
            ring = (slice(max(0, y0 - 8), y0 + h + 8), slice(max(0, x0 - 8), x0 + w + 8))
            sponsors[ring] = np.maximum(sponsors[ring], np.uint8(255))
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target] = shape
        return full

    good = add_seam(578, 637)
    glyph_decal = add_seam(578, 690, glyphs=True)
    sponsor_surrounded = add_seam(578, 740, sponsor_ring=True)
    protected = add_seam(578, 790, protected=True)
    wrong_geometry = add_seam(578, 840, wrong_geometry=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "thin_vertical_warm_dlm_livery_seam"
    assert (mask[good] > 0).mean() > 0.95
    assert (mask[glyph_decal] > 0).mean() == 0
    assert (mask[sponsor_surrounded] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0
    assert (mask[wrong_geometry] > 0).mean() == 0


def test_smart_tga_dlm_red_logo_panel_fill_splits_from_preserved_logo():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def panel_shape():
        h, w = 92, 113
        yy, xx = np.indices((h, w))
        shape = np.ones((h, w), bool)
        shape &= ~((yy < 18) & (xx > 65 + yy * 1.8))
        shape &= ~((yy < 32) & (xx < 20 - yy * 0.35))
        shape &= ~((yy > 62) & (xx < 34 - (yy - 62) * 0.95))
        shape &= ~((yy > 66) & (xx > 102 - (yy - 66) * 0.70))
        shape &= ~((yy >= 28) & (yy <= 58) & (xx < 8))
        return yy, xx, shape

    def add_panel(y0, x0, *, bright_ring=False):
        yy, _xx, shape = panel_shape()
        target = (slice(y0, y0 + shape.shape[0]), slice(x0, x0 + shape.shape[1]))
        if bright_ring:
            rgb[
                max(0, y0 - 18):y0 + shape.shape[0] + 18,
                max(0, x0 - 18):x0 + shape.shape[1] + 18,
            ] = np.array([226, 220, 210], np.uint8)
        sponsors[target][shape] = 255
        rgb[target][shape] = np.array([190, 24, 42], np.uint8)

        white_logo = np.zeros_like(shape)
        dark_logo = np.zeros_like(shape)
        white_logo[43:47, 36:80] = True
        white_logo[53:56, 30:86] = True
        white_logo[63:66, 43:77] = True
        white_logo &= shape
        dark_logo[49:52, 38:83] = True
        dark_logo[58:61, 36:82] = True
        dark_logo[69:72, 48:76] = True
        dark_logo &= shape & ~white_logo
        rgb[target][white_logo] = np.array([246, 246, 236], np.uint8)
        rgb[target][dark_logo] = np.array([18, 18, 22], np.uint8)

        red_fill = shape & ~white_logo & ~dark_logo
        full_red = np.zeros((n, n), bool)
        full_logo = np.zeros((n, n), bool)
        full_red[target][red_fill] = True
        full_logo[target][white_logo | dark_logo] = True
        return target, full_red, full_logo

    _target, red_fill, logo = add_panel(137, 614)
    control_target, control_red_fill, control_logo = add_panel(300, 614, bright_ring=True)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "dlm_red_logo_panel_fill_partial"
    assert 0.82 <= info["components"][0]["partial_demote_frac"] <= 0.93
    assert (mask[red_fill] > 0).mean() > 0.84
    assert (mask[logo] > 0).mean() == 0
    assert (mask[control_red_fill] > 0).mean() == 0
    assert (mask[control_logo] > 0).mean() == 0
    assert (mask[control_target] > 0).mean() == 0


def test_smart_tga_large_mid_body_flat_red_dlm_livery_slab_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    yy, xx = np.indices((121, 332))
    slab_shape = (yy < 35) | ((yy >= 35) & (xx < 170))

    def add_slab(y0, x0, *, glyph=False, protected=False):
        target = (slice(y0, y0 + slab_shape.shape[0]), slice(x0, x0 + slab_shape.shape[1]))
        sponsors[target][slab_shape] = 255
        rgb[target][slab_shape] = np.array([232, 12, 28], np.uint8)
        if glyph:
            white = slab_shape & (yy >= 52) & (yy <= 60) & (xx >= 32) & (xx <= 288)
            dark = slab_shape & (yy >= 72) & (yy <= 80) & (xx >= 48) & (xx <= 274)
            rgb[target][white] = np.array([245, 245, 232], np.uint8)
            rgb[target][dark] = np.array([18, 18, 22], np.uint8)
        if protected:
            numbers[target][slab_shape] = 255
            template[target][slab_shape] = 255
        full = np.zeros((n, n), bool)
        full[target][slab_shape] = True
        return target, full

    _target, slab_full = add_slab(102, 283)
    _glyph_target, glyph_full = add_slab(390, 283, glyph=True)
    _protected_target, protected_full = add_slab(680, 283, protected=True)

    small_card = (slice(32, 81), slice(605, 728))
    sponsors[small_card] = 255
    rgb[small_card] = np.array([232, 12, 28], np.uint8)
    small_full = np.zeros((n, n), bool)
    small_full[small_card] = True

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "large_mid_body_flat_red_dlm_livery_slab"
    assert (mask[slab_full] > 0).mean() > 0.95
    assert (mask[glyph_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[small_full] > 0).mean() == 0


def test_smart_tga_medium_square_solid_red_dlm_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def panel_shape():
        h, w = 98, 87
        local = np.ones((h, w), dtype=bool)
        local[:18, :30] = False
        local[-18:, :30] = False
        local[:6, 30:50] = False
        return local

    def add_panel(y0, x0, *, text=False, protect=False, sponsor_ring=False, color=(218, 28, 32)):
        local = panel_shape()
        yy, xx = np.indices(local.shape)
        target = (slice(y0, y0 + local.shape[0]), slice(x0, x0 + local.shape[1]))
        sponsors[target][local] = 255
        rgb[target][local] = np.array(color, np.uint8)
        if text:
            glyphs = local & ((((xx % 17) < 4) & (yy > 20)) | ((yy > 44) & (yy < 53)))
            rgb[target][glyphs] = np.array([246, 246, 238], np.uint8)
        if protect:
            numbers[target][local] = 255
        if sponsor_ring:
            sponsors[max(0, y0 - 8):y0 - 3, x0 + 6:x0 + 72] = 255
            sponsors[y0 + local.shape[0] + 3:y0 + local.shape[0] + 8, x0 + 6:x0 + 72] = 255
            rgb[max(0, y0 - 8):y0 - 3, x0 + 6:x0 + 72] = np.array([246, 246, 236], np.uint8)
            rgb[y0 + local.shape[0] + 3:y0 + local.shape[0] + 8, x0 + 6:x0 + 72] = np.array([246, 246, 236], np.uint8)
        full = np.zeros((n, n), dtype=bool)
        full[target][local] = True
        return target, local, full

    panel, panel_local, _panel_full = add_panel(195, 173)
    _text_card, _text_local, text_full = add_panel(360, 173, text=True)
    _protected_panel, _protected_local, protected_full = add_panel(525, 173, protect=True)
    _sponsor_card, _sponsor_local, sponsor_full = add_panel(690, 173, sponsor_ring=True)
    _non_red_panel, _non_red_local, non_red_full = add_panel(195, 360, color=(205, 205, 190))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "medium_square_solid_red_dlm_livery_panel"
    assert (mask[panel][panel_local] > 0).mean() > 0.95
    assert (mask[text_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[sponsor_full] > 0).mean() == 0
    assert (mask[non_red_full] > 0).mean() == 0


def test_smart_tga_lower_mid_vertical_solid_red_dlm_livery_panel_falls_back_to_paint():
    n = 1024
    y0, x0, h, w = 803, 593, 63, 35

    def make_scene(*, glyph=False, protect=False, sponsor_ring=False, x_shift=0):
        rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)

        yy, xx = np.indices((h, w))
        panel = np.ones((h, w), dtype=bool)
        panel[4:20, :10] = False
        panel[26:42, :8] = False
        panel[46:60, :10] = False
        panel[10:16, 29:33] = False

        x1 = x0 + x_shift
        y1 = y0
        rgb[y1 - 10:y1 + h + 10, x1 - 10:x1 + w + 10] = np.array([42, 34, 12], np.uint8)
        context_h, context_w = h + 20, w + 20
        cyy, _cxx = np.indices((context_h, context_w))
        red_context = cyy < 54
        rgb[y1 - 10:y1 + h + 10, x1 - 10:x1 + w + 10][red_context] = np.array([138, 96, 2], np.uint8)

        target = (slice(y1, y1 + h), slice(x1, x1 + w))
        rgb[target][~panel] = np.array([138, 96, 2], np.uint8)
        sponsors[target][panel] = 255
        rgb[target][panel] = np.array([145, 105, 2], np.uint8)
        dark_flecks = panel & (((yy * 3 + xx) % 19) == 0)
        rgb[target][dark_flecks] = np.array([64, 44, 2], np.uint8)

        if glyph:
            glyphs = panel & (
                ((yy >= 12) & (yy <= 17) & (xx >= 3) & (xx <= 30))
                | ((yy >= 36) & (yy <= 42) & (xx >= 5) & (xx <= 28))
            )
            rgb[target][glyphs] = np.array([246, 246, 236], np.uint8)
        if protect:
            numbers[target][panel] = 255
            template[target][panel] = 255
        if sponsor_ring:
            sponsors[y1 - 8:y1 - 3, x1 - 4:x1 + w + 4] = 255
            sponsors[y1 + h + 3:y1 + h + 8, x1 - 4:x1 + w + 4] = 255
            rgb[y1 - 8:y1 - 3, x1 - 4:x1 + w + 4] = np.array([246, 246, 236], np.uint8)
            rgb[y1 + h + 3:y1 + h + 8, x1 - 4:x1 + w + 4] = np.array([246, 246, 236], np.uint8)

        full = np.zeros((n, n), dtype=bool)
        full[target][panel] = True
        return rgb, sponsors, numbers, template, brand, full

    rgb, sponsors, numbers, template, brand, panel_full = make_scene()
    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "lower_mid_vertical_solid_red_dlm_livery_panel"
    assert (mask[panel_full] > 0).mean() > 0.95

    for kwargs in (
        {"glyph": True},
        {"protect": True},
        {"sponsor_ring": True},
        {"x_shift": -80},
    ):
        rgb, sponsors, numbers, template, brand, panel_full = make_scene(**kwargs)
        mask, _info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        assert (mask[panel_full] > 0).mean() == 0


def test_smart_tga_upper_mid_solid_red_dlm_livery_slab_falls_back_to_paint():
    n = 1024
    y0, x0, h, w = 32, 605, 49, 123

    def make_scene(*, glyph=False, protect=False, sponsor_ring=False, x_shift=0, color=(232, 12, 28)):
        rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)

        panel = np.ones((h, w), dtype=bool)
        panel[:20, :45] = False
        panel[29:, :45] = False
        yy, xx = np.indices((h, w))

        x1 = x0 + x_shift
        target = (slice(y0, y0 + h), slice(x1, x1 + w))
        sponsors[target][panel] = 255
        rgb[target][panel] = np.array(color, np.uint8)
        rgb[y0 - 8:y0 - 3, x1 + 20:x1 + 103] = np.array([246, 246, 236], np.uint8)
        rgb[y0 + h + 3:y0 + h + 8, x1 + 20:x1 + 103] = np.array([246, 246, 236], np.uint8)

        if glyph:
            glyphs = panel & (
                ((yy >= 13) & (yy <= 18) & (xx >= 54) & (xx <= 112))
                | ((yy >= 30) & (yy <= 36) & (xx >= 50) & (xx <= 108))
            )
            rgb[target][glyphs] = np.array([246, 246, 236], np.uint8)
        if protect:
            numbers[target][panel] = 255
            template[target][panel] = 255
        if sponsor_ring:
            sponsors[y0 - 8:y0 - 3, x1 + 20:x1 + 103] = 255
            sponsors[y0 + h + 3:y0 + h + 8, x1 + 20:x1 + 103] = 255

        full = np.zeros((n, n), dtype=bool)
        full[target][panel] = True
        return rgb, sponsors, numbers, template, brand, full

    rgb, sponsors, numbers, template, brand, panel_full = make_scene()
    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "upper_mid_solid_red_dlm_livery_slab"
    assert (mask[panel_full] > 0).mean() > 0.95

    for kwargs in (
        {"glyph": True},
        {"protect": True},
        {"sponsor_ring": True},
        {"x_shift": -160},
        {"color": (72, 72, 76)},
    ):
        rgb, sponsors, numbers, template, brand, panel_full = make_scene(**kwargs)
        mask, _info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        assert (mask[panel_full] > 0).mean() == 0


def test_smart_tga_compact_red_gray_dlm_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    yy, xx = np.indices((110, 132))
    panel = np.zeros((110, 132), dtype=bool)
    panel[(yy >= 8) & (yy <= 103) & (xx >= 31) & (xx <= 100)] = True
    panel[0:4, :] = True
    panel[4:9, 0:42] = True
    panel[4:9, 88:132] = True
    panel[103:110, 0:34] = True
    panel[103:110, 98:132] = True
    panel &= ~(((yy > 36) & (yy < 92) & (xx < 18 + yy // 5)) | ((yy > 20) & (yy < 76) & (xx > 124 - yy // 8)))
    panel |= (yy >= 3) & (yy < 35) & (xx >= np.maximum(0, 40 - yy)) & (xx <= 42)
    panel |= (yy >= 60) & (yy < 107) & (xx >= 96) & (xx <= np.minimum(131, 90 + yy // 3))

    def add_panel(y0, x0, *, glyph=False, protect=False, sponsor_ring=False, color=True):
        target = (slice(y0, y0 + 110), slice(x0, x0 + 132))
        rgb[max(0, y0 - 14):y0 + 8, max(0, x0 - 14):x0 + 112] = np.array([230, 230, 220], np.uint8)
        rgb[y0 + 78:y0 + 124, max(0, x0 - 14):x0 + 42] = np.array([200, 0, 44], np.uint8)
        rgb[y0 + 90:y0 + 124, x0 + 48:x0 + 120] = np.array([200, 0, 44], np.uint8)
        rgb[y0 + 8:y0 + 96, x0 + 118:x0 + 146] = np.array([70, 70, 74], np.uint8)
        sponsors[target][panel] = 255
        rgb[target][panel] = np.array([215, 0, 44] if color else [54, 54, 58], np.uint8)
        if color:
            slash = panel & (xx > 42 + yy // 6) & (xx < 88 + yy // 6) & (yy > 12) & (yy < 96)
            slash |= panel & (xx > 76 - yy // 8) & (xx < 100 - yy // 8) & (yy > 30) & (yy < 82)
            teeth = slash & (((xx + yy) % 11) < 3)
            rgb[target][slash] = np.array([40, 45, 53], np.uint8)
            rgb[target][teeth] = np.array([120, 24, 45], np.uint8)
        if glyph:
            glyphs = panel & (((yy > 34) & (yy < 43) & (xx > 25) & (xx < 112)) | ((yy > 60) & (yy < 69) & (xx > 38) & (xx < 104)))
            rgb[target][glyphs] = np.array([245, 245, 236], np.uint8)
        if protect:
            numbers[target][panel] = 255
            template[target][panel] = 255
        if sponsor_ring:
            sponsors[max(0, y0 - 10):y0 - 3, x0 + 12:x0 + 120] = 255
            sponsors[y0 + 112:y0 + 119, x0 + 12:x0 + 118] = 255
            rgb[max(0, y0 - 10):y0 - 3, x0 + 12:x0 + 120] = np.array([245, 245, 235], np.uint8)
            rgb[y0 + 112:y0 + 119, x0 + 12:x0 + 118] = np.array([245, 245, 235], np.uint8)
        full = np.zeros((n, n), dtype=bool)
        full[target][panel] = True
        return target, full

    _target, panel_full = add_panel(234, 258)
    _glyph_target, glyph_full = add_panel(390, 258, glyph=True)
    _protected_target, protected_full = add_panel(546, 258, protect=True)
    _sponsor_target, sponsor_full = add_panel(702, 258, sponsor_ring=True)
    _non_red_target, non_red_full = add_panel(234, 470, color=False)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "compact_red_gray_dlm_livery_panel"
    assert (mask[panel_full] > 0).mean() > 0.95
    assert (mask[glyph_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[sponsor_full] > 0).mean() == 0
    assert (mask[non_red_full] > 0).mean() == 0


def test_smart_tga_lower_right_red_pale_dlm_livery_panel_falls_back_to_paint():
    n = 1024

    def make_scene(*, glyph=False, protect=False, sponsor_ring=False, x0=914, y0=680):
        rgb = np.full((n, n, 3), np.array([34, 34, 36], np.uint8), np.uint8)
        sponsors = np.zeros((n, n), np.uint8)
        numbers = np.zeros((n, n), np.uint8)
        template = np.zeros((n, n), np.uint8)
        brand = np.zeros((n, n), np.uint8)
        yy, xx = np.indices((312, 108))
        panel = np.zeros((312, 108), dtype=bool)
        panel[(yy >= 80) & (xx < 36)] = True
        panel[(yy < 80) & (xx >= 18) & (xx < 76)] = True
        panel[:, 104:108] = True
        panel[77, :] = True
        panel[77:83, 34:39] = True
        target = (slice(y0, y0 + 312), slice(x0, x0 + 108))
        sponsors[target][panel] = 255
        red_body = panel & (yy >= 80) & (xx < 36)
        pale_wrap = panel & ~red_body
        rgb[target][red_body] = np.array([226, 10, 28], np.uint8)
        rgb[target][pale_wrap] = np.array([16, 72, 246], np.uint8)
        rgb[y0 + 94:y0 + 300, max(0, x0 - 8):max(0, x0 - 2)] = np.array([226, 10, 28], np.uint8)
        if glyph:
            glyphs = panel & (yy >= 118) & (yy <= 132) & (xx >= 4) & (xx <= 96)
            glyphs |= panel & (yy >= 170) & (yy <= 184) & (xx >= 6) & (xx <= 72)
            rgb[target][glyphs] = np.array([245, 245, 236], np.uint8)
        if protect:
            numbers[target][panel] = 255
            template[target][panel] = 255
        if sponsor_ring:
            sponsors[max(0, y0 - 8):y0 - 2, x0 + 4:x0 + 102] = 255
            sponsors[y0 + 314:y0 + 320, x0 + 4:x0 + 102] = 255
            rgb[max(0, y0 - 8):y0 - 2, x0 + 4:x0 + 102] = np.array([246, 246, 236], np.uint8)
            rgb[y0 + 314:y0 + 320, x0 + 4:x0 + 102] = np.array([246, 246, 236], np.uint8)
        full = np.zeros((n, n), dtype=bool)
        full[target][panel] = True
        return rgb, sponsors, numbers, template, brand, full

    rgb, sponsors, numbers, template, brand, panel_full = make_scene()
    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "lower_right_red_pale_dlm_livery_panel"
    assert (mask[panel_full] > 0).mean() > 0.95

    for kwargs in (
        {"glyph": True},
        {"protect": True},
        {"sponsor_ring": True},
        {"x0": 760, "y0": 680},
    ):
        rgb, sponsors, numbers, template, brand, panel_full = make_scene(**kwargs)
        mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb, sponsors, numbers, template, brand
        )
        assert (mask[panel_full] > 0).mean() == 0


def test_smart_tga_edge_red_dark_livery_bands_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([42, 38, 36], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    yy, xx = np.indices((71, 316))
    band_shape = yy < 33
    band_shape |= (yy >= 33) & (xx >= 120) & (xx <= 194)

    def add_band(y0, x0, protect=False):
        target = (slice(y0, y0 + 71), slice(x0, x0 + 316))
        sponsors[target][band_shape] = 255
        rgb[target][band_shape] = np.array([236, 154, 142], np.uint8)
        dark_area = band_shape & (yy >= 33)
        rgb[target][band_shape] = np.array([236, 50, 74], np.uint8)
        rgb[target][dark_area] = np.array([62, 45, 44], np.uint8)
        if protect:
            numbers[target][band_shape] = 255
            template[target][band_shape] = 255
        full = np.zeros((n, n), bool)
        full[target][band_shape] = True
        return target, full

    band_target, band_full = add_band(0, 515)

    sponsor_target, sponsor_full = add_band(953, 50)
    rgb[sponsor_target][band_shape & (yy > 12) & (yy < 26) & (xx > 36) & (xx < 286)] = np.array([246, 246, 236], np.uint8)
    rgb[sponsor_target][band_shape & (yy > 38) & (yy < 54) & (xx > 138) & (xx < 184)] = np.array([12, 12, 14], np.uint8)

    protected_target, protected_full = add_band(953, 650, protect=True)

    non_edge_target, non_edge_full = add_band(220, 515)

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "edge_red_dark_livery_band"
    assert (mask[band_full] > 0).mean() > 0.95
    assert (mask[sponsor_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[non_edge_full] > 0).mean() == 0


def test_smart_tga_warm_edge_livery_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([244, 104, 14], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    top_edge_panel = (slice(0, 112), slice(914, 1004))
    right_edge_panel = (slice(425, 722), slice(984, 1024))
    non_edge_panel = (slice(212, 312), slice(330, 430))
    text_like_edge = (slice(760, 850), slice(0, 140))

    sponsors[top_edge_panel] = 255
    sponsors[right_edge_panel] = 255
    sponsors[non_edge_panel] = 255
    sponsors[text_like_edge] = 255
    rgb[text_like_edge] = np.array([236, 92, 16], np.uint8)
    rgb[766:846:8, 8:132] = np.array([246, 246, 232], np.uint8)
    rgb[770:844:13, 16:126] = np.array([20, 20, 22], np.uint8)

    mask, info = car_layers_mod._warm_edge_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {"warm_edge_livery_panel"}
    assert (mask[top_edge_panel] > 0).mean() > 0.95
    assert (mask[right_edge_panel] > 0).mean() > 0.95
    assert (mask[non_edge_panel] > 0).mean() == 0
    assert (mask[text_like_edge] > 0).mean() == 0


def test_smart_tga_tall_warm_edge_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([30, 28, 26], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    tall_panel = (slice(420, 785), slice(0, 35))
    sponsors[tall_panel] = 255
    rgb[tall_panel] = np.array([244, 104, 14], np.uint8)

    text_edge = (slice(420, 785), slice(989, 1024))
    sponsors[text_edge] = 255
    rgb[text_edge] = np.array([244, 104, 14], np.uint8)
    rgb[430:770:18, 994:1019] = np.array([246, 246, 236], np.uint8)
    rgb[439:770:22, 997:1016] = np.array([18, 18, 20], np.uint8)

    non_edge_panel = (slice(420, 785), slice(180, 215))
    sponsors[non_edge_panel] = 255
    rgb[non_edge_panel] = np.array([244, 104, 14], np.uint8)

    protected_panel = (slice(20, 385), slice(0, 35))
    sponsors[protected_panel] = 255
    rgb[protected_panel] = np.array([244, 104, 14], np.uint8)
    numbers[protected_panel] = 255
    template[protected_panel] = 255

    mask, info = car_layers_mod._warm_edge_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tall_warm_edge_livery_panel"
    assert (mask[tall_panel] > 0).mean() > 0.95
    assert (mask[text_edge] > 0).mean() == 0
    assert (mask[non_edge_panel] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0


def test_smart_tga_gold_edge_livery_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    gold = np.array([196, 153, 3], np.uint8)

    top_local = np.ones((42, 136), bool)
    top_local[18:42, 55:136] = False
    top_panel = (slice(0, 42), slice(0, 136))
    sponsors[top_panel][top_local] = 255
    rgb[top_panel][top_local] = gold

    bottom_local = np.ones((24, 194), bool)
    bottom_local[4:18, 40:120] = False
    bottom_panel = (slice(993, 1017), slice(773, 967))
    sponsors[bottom_panel][bottom_local] = 255
    rgb[bottom_panel][bottom_local] = gold

    text_card = (slice(118, 160), slice(0, 136))
    sponsors[text_card] = 255
    rgb[text_card] = gold
    rgb[126:154:7, 8:128] = np.array([244, 244, 232], np.uint8)
    rgb[130:154:11, 14:122] = np.array([18, 18, 20], np.uint8)

    non_edge = (slice(470, 512), slice(410, 546))
    sponsors[non_edge] = 255
    rgb[non_edge] = gold

    mask, info = car_layers_mod._warm_edge_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {"gold_edge_livery_panel"}
    assert (mask[top_panel][top_local] > 0).mean() > 0.95
    assert (mask[bottom_panel][bottom_local] > 0).mean() > 0.95
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[non_edge] > 0).mean() == 0


def test_smart_tga_tall_warm_edge_livery_trim_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    gold = np.array([246, 231, 32], np.uint8)

    def add_tall_gold_trim(y0, x0, glyph=False, protect=False):
        h, w = 300, 21
        panel = (slice(y0, y0 + h), slice(x0, x0 + w))
        local = np.ones((h, w), bool)
        local[::6, 2:20] = False
        sponsors[panel][local] = 255
        rgb[panel] = gold
        if glyph:
            rgb[y0 + 18:y0 + h - 18:20, x0 + 2:x0 + w - 2] = np.array([246, 246, 236], np.uint8)
            rgb[y0 + 27:y0 + h - 18:24, x0 + 4:x0 + w - 4] = np.array([18, 18, 20], np.uint8)
        if protect:
            numbers[panel][local] = 255
            template[panel][local] = 255

        full_mask = np.zeros((n, n), bool)
        full_mask[panel][local] = True
        return panel, full_mask

    trim_panel, trim_mask = add_tall_gold_trim(3, 1003)
    text_panel, text_mask = add_tall_gold_trim(350, 1003, glyph=True)
    non_edge_panel, non_edge_mask = add_tall_gold_trim(3, 500)
    protected_panel, protected_mask = add_tall_gold_trim(700, 0, protect=True)

    mask, info = car_layers_mod._warm_edge_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tall_warm_edge_livery_trim"
    assert (mask[trim_mask] > 0).mean() > 0.95
    assert (mask[text_mask] > 0).mean() == 0
    assert (mask[non_edge_mask] > 0).mean() == 0
    assert (mask[protected_mask] > 0).mean() == 0


def test_smart_tga_vertical_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([244, 104, 14], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_vertical_stripe(y0, x0):
        h, w = 350, 23
        local = np.zeros((h, w), bool)
        local[:, 2:8] = True
        local[:, 16:19] = True
        local[::24, 8:16] = True
        sponsors[y0:y0 + h, x0:x0 + w][local] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[local] = np.array([242, 86, 14], np.uint8)
        sub[:, 16:19][local[:, 16:19]] = np.array([248, 248, 236], np.uint8)
        return np.pad(local, ((y0, n - y0 - h), (x0, n - x0 - w)))

    stripe = add_vertical_stripe(411, 642)
    edge_stripe = add_vertical_stripe(120, 0)

    horizontal = (slice(250, 276), slice(210, 510))
    sponsors[horizontal] = 255
    rgb[horizontal] = np.array([242, 86, 14], np.uint8)
    rgb[256:262, 240:470] = np.array([248, 248, 236], np.uint8)

    dark_text_like = (slice(690, 920), slice(120, 150))
    sponsors[dark_text_like] = 255
    rgb[dark_text_like] = np.array([235, 88, 15], np.uint8)
    rgb[700:914:9, 126:146] = np.array([18, 18, 20], np.uint8)

    mask, info = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "vertical_livery_stripe"
    assert (mask[stripe] > 0).mean() > 0.95
    assert (mask[edge_stripe] > 0).mean() == 0
    assert (mask[horizontal] > 0).mean() == 0
    assert (mask[dark_text_like] > 0).mean() == 0


def test_smart_tga_smooth_vertical_red_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([16, 18, 24], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 560, 220, 128, 32
    local = np.ones((h, w), bool)
    local[:, :2] = False
    local[12:52, 26:32] = False
    local[74:90, :6] = False
    stripe = (slice(y0, y0 + h), slice(x0, x0 + w))
    sponsors[stripe][local] = 255
    stripe_rgb = rgb[stripe]
    sy, sx = np.indices((h, w))
    red = np.clip(218 + sx * 30 / float(w - 1) + ((sy % 17) == 0) * 12, 206, 255)
    green = np.clip(10 + sy * 24 / float(h - 1) + ((sx % 9) == 0) * 10, 8, 48)
    blue = np.clip(12 + ((sx + sy * 2) % 17) * 2, 8, 54)
    stripe_color = np.stack([red, green, blue], axis=2).astype(np.uint8)
    stripe_rgb[local] = stripe_color[local]
    target = np.pad(local, ((y0, n - y0 - h), (x0, n - x0 - w)))

    word_y, word_x, word_h, word_w = 610, 160, 101, 28
    wordmark = (slice(word_y, word_y + word_h), slice(word_x, word_x + word_w))
    sponsors[wordmark] = 255
    rgb[wordmark] = np.array([205, 50, 56], np.uint8)
    rgb[word_y + 8:word_y + word_h - 8:11, word_x + 5:word_x + word_w - 4] = np.array([246, 246, 238], np.uint8)
    rgb[word_y + 14:word_y + word_h - 14:19, word_x + 10:word_x + word_w - 8] = np.array([24, 20, 20], np.uint8)

    sponsor_card = (slice(180, 247), slice(470, 535))
    sponsors[sponsor_card] = 255
    rgb[sponsor_card] = np.array([216, 30, 28], np.uint8)
    rgb[188:238:8, 478:527] = np.array([242, 242, 230], np.uint8)
    rgb[193:234:13, 482:522] = np.array([12, 12, 12], np.uint8)

    edge_text_strip = (slice(0, 355), slice(760, 830))
    sponsors[edge_text_strip] = 255
    rgb[edge_text_strip] = np.array([232, 42, 34], np.uint8)
    rgb[18:334:17, 775:815] = np.array([246, 246, 236], np.uint8)

    tiny_line = (slice(880, 884), slice(210, 232))
    sponsors[tiny_line] = 255
    rgb[tiny_line] = np.array([218, 32, 28], np.uint8)
    rgb[tiny_line][xx[tiny_line] % 2 == 0] = np.array([28, 24, 22], np.uint8)

    mask, info = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "smooth_vertical_red_livery_stripe"
    assert (mask[target] > 0).mean() > 0.95
    assert (mask[wordmark] > 0).mean() == 0
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[edge_text_strip] > 0).mean() == 0
    assert (mask[tiny_line] > 0).mean() == 0


def test_smart_tga_edge_green_cyan_side_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 22], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    h, w = 593, 22
    yy, xx = np.indices((h, w))

    def add_side_stripe(y0, x0, *, protected=False, glyphs=False):
        local = np.ones((h, w), bool)
        local[:, :2] = False
        local[80:180, 2:7] = False
        local[320:410, 18:22] = False
        local[500:560, 2:10] = False
        stripe = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[stripe][local] = 255
        if protected:
            numbers[stripe][local] = 255
        stripe_rgb = rgb[stripe]
        green = np.clip(178 + (yy % 79), 0, 255)
        red = np.clip(54 + (xx * 78 / float(w - 1)) + (yy % 23), 0, 255)
        blue = np.clip(6 + ((yy + xx * 3) % 45), 0, 255)
        stripe_color = np.stack([red, green, blue], axis=2).astype(np.uint8)
        stripe_rgb[local] = stripe_color[local]
        if glyphs:
            glyph = local & (yy % 33 < 5) & (xx >= 5) & (xx <= 18)
            stripe_rgb[glyph] = np.array([246, 246, 236], np.uint8)
        return np.pad(local, ((y0, n - y0 - h), (x0, n - x0 - w)))

    target = add_side_stripe(116, 1002)
    text_edge = add_side_stripe(116, 0, glyphs=True)
    protected_edge = add_side_stripe(116, 970, protected=True)

    internal_card = (slice(116, 116 + h), slice(860, 860 + w))
    sponsors[internal_card] = 255
    rgb[internal_card] = np.array([95, 224, 14], np.uint8)

    mask, info = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb, sponsors, numbers, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "edge_green_cyan_side_livery_stripe"
    assert (mask[target] > 0).mean() > 0.95
    assert (mask[text_edge] > 0).mean() == 0
    assert (mask[protected_edge] > 0).mean() == 0
    assert (mask[internal_card] > 0).mean() == 0


def test_smart_tga_edge_blue_cyan_side_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([248, 248, 244], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    h, w = 592, 26
    yy, xx = np.indices((h, w))

    target = (slice(115, 115 + h), slice(998, 998 + w))
    target_mask = np.ones((h, w), bool)
    target_mask[80:170, :8] = False
    target_mask[318:402, 18:] = False
    sponsors[target][target_mask] = 255
    target_rgb = rgb[target]
    blue = np.clip(214 + (yy % 32), 0, 255)
    green = np.clip(176 + (xx * 34 / float(w - 1)), 0, 255)
    red = np.clip(24 + (yy % 14), 0, 255)
    stripe_color = np.stack([red, green, blue], axis=2).astype(np.uint8)
    target_rgb[target_mask] = stripe_color[target_mask]

    text_edge = (slice(116, 116 + h), slice(36, 36 + w))
    text_mask = np.ones((h, w), bool)
    sponsors[text_edge][text_mask] = 255
    text_rgb = rgb[text_edge]
    text_rgb[text_mask] = np.array([48, 184, 226], np.uint8)
    glyph = text_mask & (yy % 38 < 6) & (xx >= 5) & (xx <= 20)
    text_rgb[glyph] = np.array([246, 246, 238], np.uint8)

    mask, info = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb, sponsors, numbers, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert {item["reason"] for item in info["components"]} == {"edge_blue_cyan_side_livery_stripe"}
    assert (mask[target][target_mask] > 0).mean() > 0.95
    assert (mask[text_edge][text_mask] > 0).mean() == 0

    rgb2 = np.full((n, n, 3), np.array([248, 248, 244], np.uint8), np.uint8)
    sponsors2 = np.zeros((n, n), np.uint8)
    smooth_target = (slice(116, 116 + h), slice(0, w))
    smooth_mask = np.ones((h, w), bool)
    smooth_mask[80:170, :8] = False
    smooth_mask[318:402, 18:] = False
    sponsors2[smooth_target][smooth_mask] = 255
    smooth_rgb = rgb2[smooth_target]
    smooth_color = np.stack([
        np.clip(44 + (yy % 5), 0, 255),
        np.clip(184 + (xx % 21), 0, 255),
        np.clip(218 + (yy % 11), 0, 255),
    ], axis=2).astype(np.uint8)
    smooth_rgb[smooth_mask] = smooth_color[smooth_mask]

    mask2, info2 = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb2, sponsors2, numbers, template, empty
    )

    assert info2["status"] == "applied"
    assert info2["component_count"] == 1
    assert info2["components"][0]["reason"] == "edge_blue_cyan_side_livery_stripe"
    assert (mask2[smooth_target][smooth_mask] > 0).mean() > 0.95

    rgb3 = np.full((n, n, 3), np.array([248, 248, 244], np.uint8), np.uint8)
    sponsors3 = np.zeros((n, n), np.uint8)
    low_edge_target = (slice(115, 115 + h), slice(0, w))
    low_edge_mask = np.ones((h, w), bool)
    low_edge_mask[80:170, :8] = False
    low_edge_mask[318:402, 18:] = False
    sponsors3[low_edge_target][low_edge_mask] = 255
    low_edge_rgb = rgb3[low_edge_target]
    low_edge_color = np.stack([
        np.clip(yy % 2, 0, 255),
        np.clip(85 + ((xx * 12 / float(w - 1)) % 12) + (yy % 3), 0, 255),
        np.clip(184 + ((yy * 12 / float(h - 1)) % 12) + (xx % 3), 0, 255),
    ], axis=2).astype(np.uint8)
    low_edge_rgb[low_edge_mask] = low_edge_color[low_edge_mask]

    mask3, info3 = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb3, sponsors3, numbers, template, empty
    )

    assert info3["status"] == "applied"
    assert info3["component_count"] == 1
    assert info3["components"][0]["reason"] == "edge_blue_cyan_side_livery_stripe"
    assert 0.010 <= info3["components"][0]["edge_density"] < 0.015
    assert (mask3[low_edge_target][low_edge_mask] > 0).mean() > 0.95


def test_smart_tga_curved_dark_warm_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([22, 185, 215], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    h, w = 154, 12
    y0, x0 = 520, 840
    local = np.zeros((h, w), bool)
    yy, xx = np.indices((h, w))
    center = 1 + np.round((yy[:, 0] / float(h - 1)) * 8).astype(int)
    for row, cx in enumerate(center):
        local[row, cx:cx + 3] = True
    stripe = (slice(y0, y0 + h), slice(x0, x0 + w))
    sponsors[stripe][local] = 255
    stripe_rgb = rgb[stripe]
    dark_part = local & (xx == (center[:, None] + 2))
    stripe_rgb[local & ~dark_part] = np.array([235, 198, 18], np.uint8)
    stripe_rgb[dark_part] = np.array([22, 24, 16], np.uint8)

    horizontal_sponsor_bar = (slice(190, 197), slice(835, 900))
    sponsors[horizontal_sponsor_bar] = 255
    rgb[horizontal_sponsor_bar] = np.array([230, 52, 190], np.uint8)

    white_text_strip = (slice(550, 704), slice(700, 712))
    sponsors[white_text_strip] = 255
    rgb[white_text_strip] = np.array([228, 190, 20], np.uint8)
    rgb[560:696:12, 703:709] = np.array([244, 244, 238], np.uint8)

    mask, info = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "curved_dark_warm_livery_stripe"
    assert (mask[stripe][local] > 0).mean() > 0.95
    assert (mask[horizontal_sponsor_bar] > 0).mean() == 0
    assert (mask[white_text_strip] > 0).mean() == 0


def test_smart_tga_short_stacked_livery_accent_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([15, 91, 145], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    h, w = 80, 29
    local = np.ones((h, w), bool)
    local[:, :3] = False
    local[0:18, 3:14] = False
    local[32:48, 17:29] = False
    local[62:80, 3:13] = False
    yy, xx = np.indices((h, w))

    y0, x0 = 238, 986
    stripe = (slice(y0, y0 + h), slice(x0, x0 + w))
    sponsors[stripe][local] = 255
    stripe_rgb = rgb[stripe]
    stripe_rgb[local] = np.array([237, 39, 48], np.uint8)
    stripe_rgb[local & (xx >= 18)] = np.array([19, 94, 173], np.uint8)
    stripe_rgb[local & (yy < 24)] = np.array([247, 225, 60], np.uint8)

    text_y, text_x = 330, 740
    text_strip = (slice(text_y, text_y + h), slice(text_x, text_x + w))
    sponsors[text_strip][local] = 255
    text_rgb = rgb[text_strip]
    text_rgb[local] = np.array([237, 39, 48], np.uint8)
    text_rgb[local & (xx >= 18)] = np.array([19, 94, 173], np.uint8)
    text_rgb[local & (yy < 24)] = np.array([246, 246, 238], np.uint8)

    prot_y, prot_x = 470, 650
    protected_strip = (slice(prot_y, prot_y + h), slice(prot_x, prot_x + w))
    sponsors[protected_strip][local] = 255
    numbers[protected_strip][local] = 255
    prot_rgb = rgb[protected_strip]
    prot_rgb[local] = np.array([237, 39, 48], np.uint8)
    prot_rgb[local & (xx >= 18)] = np.array([19, 94, 173], np.uint8)
    prot_rgb[local & (yy < 24)] = np.array([247, 225, 60], np.uint8)

    tiny_badge = (slice(650, 690), slice(720, 735))
    sponsors[tiny_badge] = 255
    rgb[tiny_badge] = np.array([237, 39, 48], np.uint8)

    mask, info = car_layers_mod._vertical_livery_stripe_sponsor_to_paint(
        rgb, sponsors, numbers, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "short_stacked_livery_accent"
    assert (mask[stripe][local] > 0).mean() > 0.95
    assert (mask[text_strip] > 0).mean() == 0
    assert (mask[protected_strip] > 0).mean() == 0
    assert (mask[tiny_badge] > 0).mean() == 0


def test_smart_tga_solid_warm_livery_panels_fall_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([244, 104, 14], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    solid_panel = (slice(322, 442), slice(359, 447))
    solid_stripe = (slice(818, 852), slice(341, 446))
    edge_panel = (slice(340, 460), slice(0, 88))
    wordmark = (slice(620, 700), slice(520, 710))

    sponsors[solid_panel] = 255
    sponsors[solid_stripe] = 255
    sponsors[edge_panel] = 255
    sponsors[wordmark] = 255

    yy, xx = np.indices((120, 88))
    solid_panel_mask = (xx < 70) | (yy > 88)
    sponsors[solid_panel] = 0
    sponsors[322:442, 359:447][solid_panel_mask] = 255

    yy, xx = np.indices((34, 105))
    solid_stripe_mask = np.ones((34, 105), dtype=bool)
    solid_stripe_mask[(yy % 6 == 0) & (xx % 3 == 0)] = False
    sponsors[solid_stripe] = 0
    sponsors[818:852, 341:446][solid_stripe_mask] = 255
    stripe_rgb = rgb[818:852, 341:446]
    stripe_rgb[solid_stripe_mask] = np.array([242, 120, 18], np.uint8)
    stripe_rgb[solid_stripe_mask & (xx > 70)] = np.array([247, 96, 14], np.uint8)

    rgb[wordmark] = np.array([242, 112, 17], np.uint8)
    rgb[628:692:7, 530:700] = np.array([245, 245, 230], np.uint8)
    rgb[636:684:11, 540:690] = np.array([20, 20, 22], np.uint8)

    mask, info = car_layers_mod._solid_warm_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {"solid_warm_livery_panel"}
    assert (mask[solid_panel] > 0).mean() > 0.70
    assert (mask[solid_stripe] > 0).mean() > 0.85
    assert (mask[edge_panel] > 0).mean() == 0
    assert (mask[wordmark] > 0).mean() == 0


def test_smart_tga_bright_warm_body_color_sponsor_panels_fall_back_to_paint():
    n = 512
    body_yellow = np.array([236, 201, 22], np.uint8)
    rgb = np.full((n, n, 3), body_yellow, np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_irregular_panel(y0, x0, h, w, color):
        yy, xx = np.indices((h, w))
        panel = (
            ((yy > 8) & (xx > 6) & (yy < h - 8) & (xx < w - 6))
            & ~((yy < h * 0.42) & (xx > w * 0.58))
            & ~((yy > h * 0.70) & (xx < w * 0.22))
        )
        sponsors[y0:y0 + h, x0:x0 + w][panel] = 255
        rgb[y0:y0 + h, x0:x0 + w][panel] = np.array(color, np.uint8)
        return (slice(y0, y0 + h), slice(x0, x0 + w)), panel

    large_panel, _ = add_irregular_panel(70, 38, 108, 132, body_yellow)
    matching_panel, _ = add_irregular_panel(235, 300, 108, 128, body_yellow)

    text_panel, text_mask = add_irregular_panel(350, 38, 95, 132, body_yellow)
    _yy, xx = np.indices(text_mask.shape)
    text_pixels = text_mask & ((xx % 18) < 5)
    rgb[text_panel][text_pixels] = np.array([245, 245, 235], np.uint8)

    orange_card, _ = add_irregular_panel(54, 310, 96, 118, np.array([255, 92, 8], np.uint8))
    dark_logo, _ = add_irregular_panel(360, 310, 86, 98, np.array([28, 26, 24], np.uint8))

    mask, info = car_layers_mod._bright_warm_body_color_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {
        "bright_warm_body_color_livery_panel"
    }
    assert info["dominant_body_hue"] in range(20, 31)
    assert (mask[large_panel] > 0).mean() > 0.45
    assert (mask[matching_panel] > 0).mean() > 0.45
    assert (mask[text_panel] > 0).mean() == 0
    assert (mask[orange_card] > 0).mean() == 0
    assert (mask[dark_logo] > 0).mean() == 0


def test_smart_tga_muted_yellow_body_color_insets_fall_back_to_paint(monkeypatch):
    monkeypatch.setattr(car_layers_mod, "_BRIGHT_WARM_BODY_COLOR_SPONSOR_MAX_DEMOTE", 0.001)
    monkeypatch.setattr(car_layers_mod, "_BRIGHT_WARM_BODY_COLOR_MUTED_YELLOW_EXTRA_MAX_DEMOTE", 0.040)

    n = 512
    body_yellow = np.array([236, 201, 22], np.uint8)
    muted_yellow = np.array([199, 170, 36], np.uint8)
    muted_gray = np.array([140, 134, 112], np.uint8)
    rgb = np.full((n, n, 3), body_yellow, np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_muted_panel(y0, x0, h, w, *, surround=None, text=False):
        if surround is not None:
            rgb[max(0, y0 - 9):min(n, y0 + h + 9), max(0, x0 - 9):min(n, x0 + w + 9)] = np.array(surround, np.uint8)
        yy, xx = np.indices((h, w))
        panel = (yy > 5) & (yy < h - 5) & (xx > 5) & (xx < w - 5)
        panel &= ~((yy < h * 0.42) & (xx > w * 0.56))
        panel &= ~((yy > h * 0.62) & (xx < w * 0.32))
        muted_patch = panel & (
            ((yy > h * 0.40) & (xx < w * 0.45))
            | ((yy < h * 0.40) & (xx > w * 0.55))
        )
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][panel] = 255
        rgb[target][panel] = muted_yellow
        rgb[target][muted_patch] = muted_gray
        if text:
            text_pixels = panel & ((xx % 14) < 4)
            rgb[target][text_pixels] = np.array([246, 246, 236], np.uint8)
        return target

    panel_a = add_muted_panel(76, 56, 80, 84)
    panel_b = add_muted_panel(228, 284, 80, 84)
    text_card = add_muted_panel(350, 56, 72, 82, text=True)
    vertical_text_panel = add_muted_panel(88, 436, 178, 35, text=True)
    isolated_panel = add_muted_panel(350, 310, 72, 80, surround=np.array([74, 64, 52], np.uint8))

    mask, info = car_layers_mod._bright_warm_body_color_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = [component["reason"] for component in info["components"]]
    assert info["status"] == "applied"
    assert info["capped"] is True
    assert info["muted_yellow_extra_demoted_frac"] > 0
    assert info["muted_yellow_extra_capped"] is False
    assert reasons.count("muted_yellow_body_color_livery_panel") == 2
    assert (mask[panel_a] > 0).mean() > 0.45
    assert (mask[panel_b] > 0).mean() > 0.45
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[vertical_text_panel] > 0).mean() == 0
    assert (mask[isolated_panel] > 0).mean() == 0


def test_smart_tga_small_bright_warm_body_color_panels_survive_main_cap(monkeypatch):
    monkeypatch.setattr(car_layers_mod, "_BRIGHT_WARM_BODY_COLOR_SPONSOR_MAX_DEMOTE", 0.030)

    n = 512
    body_yellow = np.array([236, 201, 22], np.uint8)
    rgb = np.full((n, n, 3), body_yellow, np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_panel(y0, x0, h, w, color, notch=True):
        yy, xx = np.indices((h, w))
        panel = (yy > 6) & (yy < h - 6) & (xx > 5) & (xx < w - 5)
        if notch:
            panel &= ~((yy < h * 0.34) & (xx > w * 0.62))
            panel &= ~((yy > h * 0.68) & (xx < w * 0.24))
        sponsors[y0:y0 + h, x0:x0 + w][panel] = 255
        rgb[y0:y0 + h, x0:x0 + w][panel] = np.array(color, np.uint8)
        return (slice(y0, y0 + h), slice(x0, x0 + w)), panel

    broad_panel, _ = add_panel(36, 36, 104, 104, body_yellow)
    capped_broad_panel, _ = add_panel(36, 310, 104, 104, body_yellow)
    small_panel_a, _ = add_panel(250, 50, 52, 48, body_yellow)
    small_panel_b, _ = add_panel(250, 160, 50, 50, body_yellow)
    text_panel, text_mask = add_panel(360, 50, 50, 50, body_yellow)
    dark_cut_panel, _ = add_panel(360, 160, 50, 50, np.array([80, 65, 20], np.uint8))

    _yy, xx = np.indices(text_mask.shape)
    text_pixels = text_mask & ((xx % 12) < 4)
    rgb[text_panel][text_pixels] = np.array([246, 246, 236], np.uint8)

    mask, info = car_layers_mod._bright_warm_body_color_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = [component["reason"] for component in info["components"]]
    assert info["status"] == "applied"
    assert "bright_warm_body_color_livery_panel" in reasons
    assert reasons.count("small_bright_warm_body_color_livery_panel") == 2
    assert info["capped"] is True
    assert info["small_panel_extra_demoted_frac"] > 0
    assert (mask[broad_panel] > 0).mean() > 0.45
    assert (mask[capped_broad_panel] > 0).mean() == 0
    assert (mask[small_panel_a] > 0).mean() > 0.45
    assert (mask[small_panel_b] > 0).mean() > 0.45
    assert (mask[text_panel] > 0).mean() == 0
    assert (mask[dark_cut_panel] > 0).mean() == 0


def test_smart_tga_paired_warm_tan_body_panels_fall_back_to_paint():
    n = 512
    tan = np.array([154, 132, 90], np.uint8)
    rgb = np.full((n, n, 3), np.array([28, 36, 44], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_panel(y0, x0, h, w, color):
        yy, xx = np.indices((h, w))
        panel = (
            ((yy > 4) & (yy < h - 4) & (xx > 3) & (xx < w - 3))
            & ~((yy < h * 0.34) & (xx > w * 0.62))
            & ~((yy > h * 0.66) & (xx < w * 0.24))
        )
        sponsors[y0:y0 + h, x0:x0 + w][panel] = 255
        rgb[y0:y0 + h, x0:x0 + w][panel] = np.array(color, np.uint8)
        return (slice(y0, y0 + h), slice(x0, x0 + w)), panel

    upper_panel, _ = add_panel(54, 82, 42, 52, tan)
    lower_panel, _ = add_panel(398, 83, 42, 52, tan)
    isolated_tan, _ = add_panel(226, 325, 42, 52, tan)
    text_card, card_mask = add_panel(54, 326, 42, 52, tan)
    dark_logo, _ = add_panel(398, 326, 42, 52, np.array([40, 35, 28], np.uint8))

    _yy, xx = np.indices(card_mask.shape)
    text_pixels = card_mask & ((xx % 14) < 5)
    rgb[text_card][text_pixels] = np.array([245, 245, 238], np.uint8)

    mask, info = car_layers_mod._warm_tan_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert info["paired_candidate_count"] == 2
    assert {component["reason"] for component in info["components"]} == {
        "paired_warm_tan_body_panel"
    }
    assert (mask[upper_panel] > 0).mean() > 0.50
    assert (mask[lower_panel] > 0).mean() > 0.50
    assert (mask[isolated_tan] > 0).mean() == 0
    assert (mask[text_card] > 0).mean() == 0
    assert (mask[dark_logo] > 0).mean() == 0


def test_smart_tga_round_warm_tan_access_panel_falls_back_to_paint():
    n = 512
    tan = np.array([220, 198, 136], np.uint8)
    body = np.array([24, 36, 54], np.uint8)
    rgb = np.full((n, n, 3), body, np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_round_panel(y0, x0, background=body, add_text=False):
        h = w = 24
        yy, xx = np.indices((h, w))
        panel = ((yy - 11.5) ** 2 + (xx - 11.5) ** 2) <= (12.0 ** 2)
        rgb[y0 - 8:y0 + h + 8, max(0, x0 - 8):x0 + w + 8] = background
        sponsors[y0:y0 + h, x0:x0 + w][panel] = 255
        rgb[y0:y0 + h, x0:x0 + w][panel] = tan
        shade_a = panel & (xx < 10)
        shade_b = panel & (xx > 15)
        rgb[y0:y0 + h, x0:x0 + w][shade_a] = np.array([190, 166, 112], np.uint8)
        rgb[y0:y0 + h, x0:x0 + w][shade_b] = np.array([220, 200, 138], np.uint8)
        rivets = panel & (
            (((yy - 5) ** 2 + (xx - 6) ** 2) <= 2)
            | (((yy - 5) ** 2 + (xx - 17) ** 2) <= 2)
            | (((yy - 18) ** 2 + (xx - 6) ** 2) <= 2)
            | (((yy - 18) ** 2 + (xx - 17) ** 2) <= 2)
        )
        rgb[y0:y0 + h, x0:x0 + w][rivets] = np.array([164, 146, 106], np.uint8)
        if add_text:
            text = panel & (yy > 8) & (yy < 15) & ((xx % 7) < 3)
            rgb[y0:y0 + h, x0:x0 + w][text] = np.array([246, 246, 238], np.uint8)
        return (slice(y0, y0 + h), slice(x0, x0 + w)), panel

    edge_panel, _ = add_round_panel(238, 2)
    center_panel, _ = add_round_panel(180, 244)
    white_card_panel, _ = add_round_panel(296, 2, background=np.array([238, 238, 232], np.uint8))
    text_panel, _ = add_round_panel(354, 2, add_text=True)

    # Keep the dark body ring colored enough to prove this is a body/access panel,
    # not an isolated tan logo card.
    rgb[246:255, 30:40] = np.array([205, 78, 28], np.uint8)

    mask, info = car_layers_mod._warm_tan_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    reasons = [component["reason"] for component in info["components"]]
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["single_access_candidate_count"] == 1
    assert reasons == ["round_warm_tan_access_panel"]
    assert (mask[edge_panel] > 0).mean() > 0.65
    assert (mask[center_panel] > 0).mean() == 0
    assert (mask[white_card_panel] > 0).mean() == 0
    assert (mask[text_panel] > 0).mean() == 0


def test_smart_tga_round_pale_tan_access_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([92, 82, 72], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_pale_panel(y0, x0, ring_kind="neutral", protected=False, saturated=False):
        h, w = 47, 48
        y_ring = slice(max(0, y0 - 14), min(n, y0 + h + 14))
        x_ring = slice(max(0, x0 - 14), min(n, x0 + w + 14))
        if ring_kind == "white_card":
            rgb[y_ring, x_ring] = np.array([236, 234, 222], np.uint8)
        else:
            rgb[y_ring, x_ring] = np.array([88, 78, 68], np.uint8)
            rgb[max(0, y0 - 10):y0 + h + 10:5, x_ring] = np.array([38, 34, 30], np.uint8)
            rgb[y0 + h + 4:y0 + h + 10, x_ring] = np.array([226, 222, 204], np.uint8)
            rgb[max(0, y0 + 5):min(n, y0 + 25), min(n, x0 + w + 3):min(n, x0 + w + 15)] = np.array([156, 82, 42], np.uint8)

        yy, xx = np.indices((h, w))
        disk = ((yy - 23.0) ** 2 + (xx - 23.5) ** 2) <= 25.0 ** 2
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][disk] = 255
        if saturated:
            rgb[target][disk] = np.array([230, 34, 24], np.uint8)
        else:
            rgb[target][disk] = np.array([210, 190, 130], np.uint8)
            shade = disk & (xx < 9)
            rgb[target][shade] = np.array([182, 162, 110], np.uint8)
            dist = np.sqrt((yy - 23.0) ** 2 + (xx - 23.5) ** 2)
            rim = disk & (np.abs(dist - 24.5) <= 0.8)
            line = disk & ((xx == 23) | (yy == 23))
            rivets = disk & (
                (((yy - 8) ** 2 + (xx - 9) ** 2) <= 3)
                | (((yy - 8) ** 2 + (xx - 38) ** 2) <= 3)
                | (((yy - 38) ** 2 + (xx - 9) ** 2) <= 3)
                | (((yy - 38) ** 2 + (xx - 38) ** 2) <= 3)
            )
            rgb[target][rim | line | rivets] = np.array([38, 35, 28], np.uint8)
            tan_detail = disk & (
                ((((xx == 12) | (xx == 35)) & (yy > 8) & (yy < 39))
                | (((yy == 12) | (yy == 35)) & (xx > 8) & (xx < 40)))
            )
            rgb[target][tan_detail] = np.array([142, 122, 82], np.uint8)
        if protected:
            template[target][disk] = 255
        full = np.zeros((n, n), bool)
        full[target][disk] = True
        return target, disk, full

    access_panel, access_disk, _access_full = add_pale_panel(942, 233)
    white_card_panel, white_card_disk, _white_full = add_pale_panel(120, 233, ring_kind="white_card")
    protected_panel, protected_disk, protected_full = add_pale_panel(230, 233, protected=True)
    saturated_panel, saturated_disk, _saturated_full = add_pale_panel(340, 233, saturated=True)

    mask, info = car_layers_mod._warm_tan_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, template, empty
    )

    reasons = [component["reason"] for component in info["components"]]
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert reasons == ["round_pale_tan_access_panel"]
    assert (mask[access_panel][access_disk] > 0).mean() > 0.65
    assert (mask[white_card_panel][white_card_disk] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[saturated_panel][saturated_disk] > 0).mean() == 0


def test_smart_tga_diagonal_warm_livery_slash_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([220, 84, 14], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    slash_box = (slice(348, 417), slice(0, 128))
    yy, xx = np.indices((69, 128))
    diagonal_slash = np.abs(yy - (60 - (xx * 0.54))) <= 12
    sponsors[slash_box][diagonal_slash] = 255
    slash_rgb = rgb[slash_box]
    slash_rgb[diagonal_slash] = np.array([255, 170, 70], np.uint8)
    slash_rgb[diagonal_slash & (xx % 5 == 0)] = np.array([255, 132, 32], np.uint8)

    straight_edge_panel = (slice(825, 875), slice(0, 170))
    sponsors[straight_edge_panel] = 255
    rgb[straight_edge_panel] = np.array([250, 245, 235], np.uint8)

    vertical_edge_panel = (slice(790, 1000), slice(860, 928))
    sponsors[vertical_edge_panel] = 255
    rgb[vertical_edge_panel] = np.array([255, 168, 70], np.uint8)

    mask, info = car_layers_mod._diagonal_warm_livery_slash_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "diagonal_warm_livery_slash"
    assert (mask[slash_box] > 0).mean() > 0.25
    assert (mask[straight_edge_panel] > 0).mean() == 0
    assert (mask[vertical_edge_panel] > 0).mean() == 0


def test_smart_tga_small_flat_red_livery_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([10, 10, 10], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_flat_component(y0, x0, color):
        h, w = 16, 72
        yy, xx = np.indices((h, w))
        mask = ((yy >= 3) & (yy <= 12)) | (xx < 2)
        rgb[y0:y0 + h, x0:x0 + w] = np.array([185, 20, 24], np.uint8)
        sponsors[y0:y0 + h, x0:x0 + w][mask] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        red = np.clip(color[0] - 36 + (xx * 68 / float(w - 1)) + ((yy - 8) * 2), 170, 255)
        green = np.clip(color[1] - 8 + (xx * 28 / float(w - 1)) + ((yy % 3) * 5), 8, 55)
        blue = np.clip(color[2] - 10 + (xx * 22 / float(w - 1)) + ((yy % 4) * 4), 8, 60)
        component_rgb = np.stack([red, green, blue], axis=2).astype(np.uint8)
        sub[mask] = component_rgb[mask]
        return np.zeros((n, n), bool) | np.pad(mask, ((y0, n - y0 - h), (x0, n - x0 - w)))

    stripe = add_flat_component(210, 120, np.array([224, 20, 28], np.uint8))

    wordmark = add_flat_component(300, 120, np.array([224, 20, 28], np.uint8))
    rgb[304:312, 132:182][sponsors[304:312, 132:182] > 0] = np.array([248, 248, 238], np.uint8)

    mixed_logo = add_flat_component(390, 120, np.array([218, 78, 24], np.uint8))
    rgb[394:402, 136:178][sponsors[394:402, 136:178] > 0] = np.array([245, 210, 34], np.uint8)

    mask, guard = car_layers_mod._small_flat_red_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert (mask[stripe] > 0).mean() > 0.95
    assert (mask[wordmark] > 0).mean() < 0.05
    assert (mask[mixed_logo] > 0).mean() < 0.05
    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["components"][0]["reason"] == "small_flat_red_livery_stripe"


def test_smart_tga_dark_red_lower_edge_livery_slashes_fall_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([6, 5, 6], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_dark_slash(y0, x0, h, w, *, ring="dark", protect=False, dense=False):
        if ring == "light":
            rgb[y0 - 12:y0 + h + 12, x0 - 12:x0 + w + 12] = np.array([222, 220, 214], np.uint8)
        else:
            rgb[y0 - 12:y0 + h + 12, x0 - 12:x0 + w + 12] = np.array([6, 5, 6], np.uint8)
        yy, xx = np.indices((h, w))
        slash = np.zeros((h, w), bool)
        if dense:
            slash[2:7, :] = True
            slash |= np.abs(xx - (2 + yy * 1.9)) <= 1
        else:
            slash[3:8, :] = True
            slash |= np.abs(xx - (2 + yy * 1.7)) <= 1
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][slash] = 255
        sub = rgb[target]
        red = np.where((xx + yy) % 5 == 0, 30, 78).astype(np.uint8)
        green = np.where((xx + yy) % 5 == 0, 2, 4).astype(np.uint8)
        blue = np.where((xx + yy) % 5 == 0, 42, 5).astype(np.uint8)
        slash_rgb = np.stack([red, green, blue], axis=2)
        bright_edge = slash & (((xx + yy) % 7) == 0)
        slash_rgb[bright_edge] = np.array([138, 3, 5], np.uint8)
        sub[slash] = slash_rgb[slash]
        if protect:
            template[target][slash] = 255
        return np.pad(slash, ((y0, n - y0 - h), (x0, n - x0 - w)))

    slash_a = add_dark_slash(991, 376, 10, 22)
    slash_b = add_dark_slash(992, 419, 8, 21, dense=True)
    light_card = add_dark_slash(991, 120, 10, 22, ring="light")
    remote_slash = add_dark_slash(870, 376, 10, 22)
    protected_slash = add_dark_slash(991, 520, 10, 22, protect=True)

    mask, guard = car_layers_mod._small_flat_red_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("dark_red_lower_edge_livery_slash") == 2
    assert (mask[slash_a] > 0).mean() > 0.95
    assert (mask[slash_b] > 0).mean() > 0.95
    assert (mask[light_card] > 0).mean() == 0
    assert (mask[remote_slash] > 0).mean() == 0
    assert (mask[protected_slash] > 0).mean() == 0

    mask, guard = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    reasons = [component.get("reason") for component in guard["components"]]
    assert guard["status"] == "applied"
    assert reasons.count("dark_red_lower_edge_livery_slash") == 2
    assert (mask[slash_a] > 0).mean() > 0.95
    assert (mask[slash_b] > 0).mean() > 0.95
    assert (mask[light_card] > 0).mean() == 0
    assert (mask[remote_slash] > 0).mean() == 0
    assert (mask[protected_slash] > 0).mean() == 0


def test_smart_tga_long_warm_texture_stripe_falls_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([18, 18, 20], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_texture_stripe(y0, x0, mark_ink=False, protect=False):
        h, w = 13, 124
        yy, xx = np.indices((h, w))
        stripe = ((yy >= 4) & (yy <= 7)) | ((xx % 5) == 0)
        sponsors[y0:y0 + h, x0:x0 + w][stripe] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        red = np.clip(214 + ((xx % 9) - 4) * 3 + (yy - 6), 196, 232)
        green = np.clip(172 + ((xx % 7) - 3) * 5, 148, 196)
        blue = np.clip(108 + ((yy % 4) - 2) * 6, 88, 130)
        warm = np.stack([red, green, blue], axis=2).astype(np.uint8)
        sub[stripe] = warm[stripe]
        if mark_ink:
            ink = stripe & (((xx % 11) < 2) | ((yy == 5) & (xx % 17 < 8)))
            sub[ink] = np.array([244, 244, 236], np.uint8)
            dark_ink = stripe & ((xx % 19) == 0)
            sub[dark_ink] = np.array([28, 26, 22], np.uint8)
        if protect:
            numbers[y0:y0 + h, x0:x0 + w][stripe] = 255
            template[y0:y0 + h, x0:x0 + w][stripe] = 255
        return np.pad(stripe, ((y0, n - y0 - h), (x0, n - x0 - w)))

    texture_stripe = add_texture_stripe(96, 700)
    wordmark = add_texture_stripe(140, 700, mark_ink=True)
    protected_stripe = add_texture_stripe(184, 700, protect=True)

    mask, guard = car_layers_mod._small_flat_red_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["components"][0]["reason"] == "long_warm_texture_livery_stripe"
    assert (mask[texture_stripe] > 0).mean() > 0.95
    assert (mask[wordmark] > 0).mean() == 0
    assert (mask[protected_stripe] > 0).mean() == 0


def test_smart_tga_red_orange_livery_blocks_fall_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([12, 12, 12], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_livery_block(y0, x0, h, w, shape_kind):
        yy, xx = np.indices((h, w))
        if shape_kind == "left":
            shape = (xx < 23) | ((yy % 9) == 0)
        elif shape_kind == "slash":
            shape = np.abs(yy - (58 - xx * 0.88)) <= 13
            shape |= (yy == 0) | (yy == h - 1) | (xx == 0) | (xx == w - 1)
        else:
            shape = (yy > 16) | ((xx % 10) == 0)

        sponsors[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = np.array([248, 38, 18], np.uint8)
        orange = shape & ((((xx + yy) % 6) < 2) | ((xx % 13) == 0))
        sub[orange] = np.array([255, 116, 20], np.uint8)
        yellow_orange = shape & (((xx * 2 + yy) % 17) == 0)
        sub[yellow_orange] = np.array([255, 160, 40], np.uint8)
        return np.pad(shape, ((y0, n - y0 - h), (x0, n - x0 - w)))

    block_a = add_livery_block(170, 0, 68, 36, "left")
    block_b = add_livery_block(239, 177, 67, 60, "slash")
    block_c = add_livery_block(828, 0, 49, 60, "bottom")

    sponsor_like = add_livery_block(610, 120, 58, 58, "slash")
    rgb[620:626, 130:166][sponsors[620:626, 130:166] > 0] = np.array([246, 246, 236], np.uint8)
    rgb[636:642, 128:168][sponsors[636:642, 128:168] > 0] = np.array([18, 18, 20], np.uint8)

    tiny_red_chip = (slice(724, 738), slice(224, 242))
    sponsors[tiny_red_chip] = 255
    rgb[tiny_red_chip] = np.array([250, 40, 18], np.uint8)

    mask, guard = car_layers_mod._red_orange_livery_block_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 3
    assert {component["reason"] for component in guard["components"]} == {"red_orange_livery_block"}
    assert (mask[block_a] > 0).mean() > 0.95
    assert (mask[block_b] > 0).mean() > 0.95
    assert (mask[block_c] > 0).mean() > 0.95
    assert (mask[sponsor_like] > 0).mean() < 0.05
    assert (mask[tiny_red_chip] > 0).mean() == 0


def test_smart_tga_long_multicolor_livery_swoosh_falls_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([18, 18, 20], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_swoosh(y0, x0, with_text=False, pale=False):
        h, w = 30, 133
        yy, xx = np.indices((h, w))
        center = 15 + 4 * np.sin(xx / 18.0)
        shape = np.abs(yy - center) <= 8
        shape |= ((xx > 6) & (xx < 44) & (yy > center + 3) & (yy < center + 12))
        sponsors[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        if pale:
            component_rgb = np.zeros((h, w, 3), np.uint8)
            component_rgb[:, :, :] = np.array([224, 214, 172], np.uint8)
        else:
            red = np.clip(236 + xx * 15 / float(w - 1), 0, 255)
            green = np.clip(26 + xx * 180 / float(w - 1), 0, 255)
            blue = np.clip(18 + (yy % 5) * 3, 0, 255)
            component_rgb = np.stack([red, green, blue], axis=2).astype(np.uint8)
            cyan_tail = shape & (xx >= 104) & (xx <= 124)
            component_rgb[cyan_tail] = np.array([22, 190, 230], np.uint8)
        sub[shape] = component_rgb[shape]
        if with_text:
            text = shape & (yy >= 10) & (yy <= 14) & (xx >= 18) & (xx <= 110)
            sub[text] = np.array([246, 246, 236], np.uint8)
        return np.pad(shape, ((y0, n - y0 - h), (x0, n - x0 - w)))

    swoosh = add_swoosh(250, 500)
    sponsor_card = add_swoosh(350, 500, with_text=True)
    pale_decal = add_swoosh(450, 500, pale=True)

    mask, guard = car_layers_mod._red_orange_livery_block_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["components"][0]["reason"] == "long_multicolor_livery_swoosh"
    assert (mask[swoosh] > 0).mean() > 0.95
    assert (mask[sponsor_card] > 0).mean() < 0.05
    assert (mask[pale_decal] > 0).mean() < 0.05


def test_smart_tga_micro_logotype_default_budget_recovers_extra_dark_sponsor_crumbs():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([12, 12, 12], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    targets = []

    def add_micro_wordmark(y0, x0, anchored=True):
        h, w = 11, 38
        glyph = np.zeros((h, w), bool)
        glyph[2, 2:34] = True
        glyph[6, 3:36] = True
        glyph[9, 5:32] = True
        glyph[:, 2] = True
        glyph[:, 29] = True
        rgb[y0:y0 + h, x0:x0 + w][glyph] = np.array([224, 224, 220], np.uint8)
        if anchored:
            sponsors[y0 + 22:y0 + 26, x0:x0 + 40] = 255
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = glyph
        return full

    for x0 in range(100, 520, 70):
        targets.append(add_micro_wordmark(160, x0))
    far_decoy = add_micro_wordmark(300, 700, anchored=False)

    mask, info = car_layers_mod._micro_logotype_residual_supplement(
        rgb, empty, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["max_add"] == 0.0009
    assert info["broad_max_add"] == 0.00078
    assert info["thin_max_add"] == 0.00016
    assert info["component_count"] == 2
    assert info["candidate_count"] == 6
    assert info["capped"] is True
    assert all(component["bucket"] == "broad" for component in info["components"])
    assert (mask[targets[0]] > 0).mean() > 0.95
    assert (mask[targets[1]] > 0).mean() > 0.95
    assert (mask[targets[2]] > 0).mean() == 0
    assert (mask[far_decoy] > 0).mean() == 0


def test_smart_tga_micro_logotype_recovers_dark_sponsor_logo_interior():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([172, 172, 168], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    # White sponsor strokes have already been recovered, but the dark interior
    # of the same tiny tilted wordmark is still unclaimed Paint.
    sponsors[214:219, 222:246] = 255
    sponsors[236:241, 220:247] = 255
    sponsors[214:241, 220:225] = 255
    sponsors[216:240, 242:247] = 255
    rgb[sponsors > 0] = np.array([238, 238, 230], np.uint8)

    hole = np.zeros((n, n), bool)
    for offset in range(8):
        hole[222 + offset:225 + offset, 229 + offset:235 + offset] = True
    hole[228:234, 234:241] = True
    sponsors[hole] = 0
    rgb[hole] = np.array([22, 23, 25], np.uint8)

    far_dark_chip = np.zeros((n, n), bool)
    far_dark_chip[720:730, 720:734] = True
    rgb[far_dark_chip] = np.array([22, 23, 25], np.uint8)

    mask, info = car_layers_mod._micro_logotype_residual_supplement(
        rgb, empty, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["bucket_counts"]["dark"] >= 1
    assert info["dark_candidate_count"] >= 1
    assert (mask[hole] > 0).mean() > 0.20
    assert (mask[far_dark_chip] > 0).mean() == 0


def test_smart_tga_isolated_wordmark_recovers_paired_warm_dark_sponsor_segments():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([12, 12, 12], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    brand[24:34, 24:104] = 255

    def add_segment(y0, x0):
        import math

        h, w = 21, 57
        glyph = np.zeros((h, w), bool)
        for gx in range(2, w - 2):
            top = 5 + round(2.5 * math.sin(gx / 4.0))
            bottom = 15 + round(2.5 * math.sin((gx + 3) / 4.6))
            glyph[max(0, top - 1):min(h, top + 2), gx] = True
            glyph[max(0, bottom - 1):min(h, bottom + 2), gx] = True
        for gx in range(4, w - 3, 7):
            top = 5 + round(2.5 * math.sin(gx / 4.0))
            bottom = 15 + round(2.5 * math.sin((gx + 3) / 4.6))
            glyph[min(top, bottom):max(top, bottom) + 1, gx:gx + 2] = True
        yy, xx = np.indices((h, w))
        sub = rgb[y0:y0 + h, x0:x0 + w]
        bright = glyph & (((xx + yy * 2) % 10) < 5)
        dark = glyph & (((xx + yy * 2) % 10) >= 5) & (((xx + yy * 2) % 10) < 8)
        neutral = glyph & ~(bright | dark)
        sub[bright] = np.array([178, 138, 22], np.uint8)
        sub[dark] = np.array([75, 48, 16], np.uint8)
        sub[neutral] = np.array([114, 112, 106], np.uint8)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = glyph
        return full

    target_a = add_segment(64, 664)
    target_b = add_segment(64, 727)
    single_decoy = add_segment(220, 650)

    def add_shadow(y0, x0, h, w):
        shadow = np.zeros((n, n), bool)
        shadow[y0:y0 + h, x0:x0 + w] = True
        rgb[shadow] = np.array([32, 28, 12], np.uint8)
        return shadow

    target_shadow_a = add_shadow(66, 697, 5, 13)
    target_shadow_b = add_shadow(66, 760, 5, 13)
    single_shadow = add_shadow(222, 683, 5, 13)

    neutral_gap = np.zeros((n, n), bool)
    neutral_gap[66:84, 721:727] = True
    rgb[neutral_gap] = np.array([36, 35, 32], np.uint8)

    numbers[488:536, 210:310] = 255
    near_number_a = add_segment(500, 316)
    near_number_b = add_segment(500, 379)
    near_number_shadow = add_shadow(502, 349, 5, 13)

    mask, info = car_layers_mod._isolated_wordmark_supplement(
        rgb, numbers, empty, empty, brand
    )

    assert info["status"] == "applied"
    assert info["warm_segment_candidates"] == 4
    assert info["warm_segment_paired_count"] == 2
    assert info["warm_shadow_component_count"] >= 1
    assert info["component_count"] >= 3
    assert {component["reason"] for component in info["components"]} >= {
        "warm_dark_wordmark_segment",
        "warm_dark_wordmark_shadow_fill",
    }
    assert (mask[target_a] > 0).mean() > 0.70
    assert (mask[target_b] > 0).mean() > 0.70
    assert (mask[target_shadow_a | target_shadow_b] > 0).mean() > 0.70
    assert (mask[neutral_gap] > 0).mean() == 0
    assert (mask[single_decoy] > 0).mean() == 0
    assert (mask[single_shadow] > 0).mean() == 0
    assert (mask[near_number_a] > 0).mean() == 0
    assert (mask[near_number_b] > 0).mean() == 0
    assert (mask[near_number_shadow] > 0).mean() == 0


def test_smart_tga_grouped_warm_livery_arcs_fall_back_to_paint(monkeypatch):
    n = 1024
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.035, 0.035, 0.038], np.float32)
    sponsors = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    arc_masks = []
    for cy, cx, rx, ry, side in ((560, 90, 26, 52, -1), (562, 178, 26, 52, 1)):
        outer = (((yy - cy) / float(ry)) ** 2 + ((xx - cx) / float(rx)) ** 2) <= 1.0
        inner = (((yy - cy) / float(max(1, ry - 11))) ** 2 + ((xx - cx) / float(max(1, rx - 8))) ** 2) <= 1.0
        arc = outer & ~inner
        arc &= (xx <= cx + 12) if side < 0 else (xx >= cx - 12)
        sponsors[arc] = 255
        tex[arc] = np.array([0.96, 0.28, 0.05], np.float32)
        shadow = arc & ((((yy * 3) + (xx * 2)) % 17) < 4)
        tex[shadow] = np.array([0.28, 0.05, 0.02], np.float32)
        arc_masks.append(arc)

    lozenge = (((yy - 612) / 16.0) ** 2 + ((xx - 134) / 24.0) ** 2) <= 1.0
    sponsors[lozenge] = 255
    tex[lozenge] = np.array([0.94, 0.33, 0.08], np.float32)
    lozenge_shadow = lozenge & (((yy + xx) % 13) < 3)
    tex[lozenge_shadow] = np.array([0.30, 0.06, 0.03], np.float32)
    arc_masks.append(lozenge)

    wordmark = (slice(118, 156), slice(516, 676))
    sponsors[wordmark] = 255
    tex[wordmark] = np.array([0.90, 0.12, 0.10], np.float32)
    tex[124:150:7, 528:664] = np.array([0.96, 0.96, 0.92], np.float32)
    tex[130:150:11, 536:660] = np.array([0.05, 0.05, 0.05], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    for arc in arc_masks:
        assert (res["layers"]["sponsors"][arc] > 0).mean() < 0.05
        assert (res["layers"]["paint"][arc] > 0).mean() > 0.95
    assert (res["layers"]["sponsors"][wordmark] > 0).mean() > 0.95
    assert (res["layers"]["paint"][wordmark] > 0).mean() < 0.05
    assert res["warm_livery_arc_sponsor_guard"]["status"] == "applied"
    assert res["warm_livery_arc_sponsor_guard"]["component_count"] == 2


def test_smart_tga_dark_panel_red_white_dlm_livery_swoosh_falls_back_to_paint():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([14, 14, 16], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_swoosh(y0, x0, *, red_ring=False, number=False, templ=False, sponsor_card=False):
        yy, xx = np.indices((52, 62))
        center = 9 + (yy * 0.82) + 4.2 * np.sin(yy / 7.0)
        dist = np.abs(xx - center)
        band = dist <= 8
        band |= np.abs(xx - center - 12) <= 2
        band &= xx >= 2
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 52), slice(x0, x0 + 62)] = band

        if red_ring:
            rgb[y0 - 8:y0 + 60, x0 - 8:x0 + 70] = np.array([212, 28, 20], np.uint8)
        if sponsor_card:
            card = (slice(y0 - 8, y0 + 60), slice(x0 - 8, x0 + 70))
            sponsors[card] = 255
            rgb[card] = np.array([224, 224, 218], np.uint8)

        sponsors[full] = 255
        sub = rgb[y0:y0 + 52, x0:x0 + 62]
        sub[band] = np.array([185, 44, 18], np.uint8)
        sub[band & (dist <= 1.7)] = np.array([222, 210, 202], np.uint8)
        dark_band = band & ((dist >= 7.7) | (((yy + xx) % 17) == 0))
        sub[dark_band] = np.array([58, 18, 12], np.uint8)
        if number:
            numbers[full] = 255
        if templ:
            template[full] = 255
        return full

    positive = paint_swoosh(220, 780)
    red_ring = paint_swoosh(360, 780, red_ring=True)
    number = paint_swoosh(500, 780, number=True)
    templ = paint_swoosh(640, 780, templ=True)
    sponsor_card = paint_swoosh(780, 780, sponsor_card=True)

    mask, guard = car_layers_mod._warm_livery_arc_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["components"][0]["reason"] == "dark_panel_red_white_dlm_livery_swoosh"
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[red_ring] > 0).mean() == 0
    assert (mask[number] > 0).mean() == 0
    assert (mask[templ] > 0).mean() == 0
    assert (mask[sponsor_card] > 0).mean() == 0


def test_smart_tga_white_context_red_orange_dlm_livery_arc_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([248, 248, 244], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def add_arc(y0, x0, *, glyphs=False, sponsor_ring=False, protected=False, square_logo=False):
        h, w = (90, 106) if square_logo else (30, 102)
        yy, xx = np.indices((h, w))
        if square_logo:
            shape = (((yy - 45) / 39.0) ** 2 + ((xx - 53) / 47.0) ** 2) <= 1.0
            shape &= ~((((yy - 45) / 21.0) ** 2 + ((xx - 53) / 24.0) ** 2) <= 1.0)
            shape |= ((yy >= 14) & (yy <= 76) & (xx >= 43) & (xx <= 63))
        else:
            center = 18.0 - 0.055 * xx + 8.0 * np.sin(xx / 18.0)
            dist = np.abs(yy - center)
            shape = dist <= 5.4
            shape |= (np.abs(yy - center - 6.5) <= 0.75) & (xx > 8) & (xx < 93)
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[target][shape] = 255
        panel = rgb[target]
        panel[shape] = np.array([210, 82, 58], np.uint8)
        dark = shape & (
            ((dist >= 4.4) | (((xx * 3 + yy * 5) % 31) == 0))
            if not square_logo else ((yy + xx) % 5 == 0)
        )
        panel[dark] = np.array([42, 18, 12], np.uint8)
        if not square_logo:
            highlight = shape & (dist <= 0.65) & (((xx + yy) % 17) == 0)
            panel[highlight] = np.array([234, 210, 198], np.uint8)
        if glyphs:
            panel[shape & (xx >= 12) & (xx <= w - 12) & ((xx - 12) % 16 <= 3)] = np.array([246, 246, 238], np.uint8)
            panel[shape & (xx >= 20) & (xx <= w - 20) & ((xx - 20) % 23 <= 3)] = np.array([18, 18, 18], np.uint8)
        if sponsor_ring:
            sponsors[y0 - 6:y0 + h + 6, x0 - 9:x0 - 3] = 255
            sponsors[y0 - 6:y0 + h + 6, x0 + w + 3:x0 + w + 9] = 255
            rgb[y0 - 6:y0 + h + 6, x0 - 9:x0 - 3] = np.array([246, 92, 18], np.uint8)
            rgb[y0 - 6:y0 + h + 6, x0 + w + 3:x0 + w + 9] = np.array([246, 92, 18], np.uint8)
        if protected:
            numbers[target][shape] = 255
            template[target][shape] = 255
        full = np.zeros((n, n), bool)
        full[target] = shape
        return full

    positive = add_arc(229, 819)
    glyph_arc = add_arc(305, 819, glyphs=True)
    sponsor_ring_arc = add_arc(381, 819, sponsor_ring=True)
    protected_arc = add_arc(457, 819, protected=True)
    square_logo = add_arc(515, 733, square_logo=True)

    mask, guard = car_layers_mod._warm_livery_arc_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["components"][0]["reason"] == "white_context_red_orange_dlm_livery_arc"
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[glyph_arc] > 0).mean() == 0
    assert (mask[sponsor_ring_arc] > 0).mean() == 0
    assert (mask[protected_arc] > 0).mean() == 0
    assert (mask[square_logo] > 0).mean() == 0


def test_smart_tga_geometric_livery_panel_falls_back_to_paint(monkeypatch):
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.03, 0.04, 0.05], np.float32)
    sponsors = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 252, 520, 82, 82
    yy, xx = np.indices((h, w))
    panel = (xx > 4) & (yy > 4) & (xx < w - 4) & (yy < h - 4) & (xx < yy + 10)
    sponsors[y0:y0 + h, x0:x0 + w][panel] = 255
    sub = tex[y0:y0 + h, x0:x0 + w]
    sub[panel] = np.array([0.10, 0.48, 0.99], np.float32)
    stripe = panel & (np.abs(xx - yy - 4) <= 1)
    sub[stripe] = np.array([0.90, 0.94, 0.98], np.float32)

    logo = (slice(94, 158), slice(110, 262))
    sponsors[logo] = 255
    tex[logo] = np.array([0.96, 0.96, 0.94], np.float32)
    tex[102:150:6, 122:250] = np.array([0.08, 0.08, 0.08], np.float32)
    tex[110:148:9, 128:248] = np.array([0.84, 0.04, 0.05], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    out_sponsors = res["layers"]["sponsors"]
    out_paint = res["layers"]["paint"]
    assert (out_sponsors[y0:y0 + h, x0:x0 + w][panel] > 0).mean() < 0.05
    assert (out_paint[y0:y0 + h, x0:x0 + w][panel] > 0).mean() > 0.95
    assert (out_sponsors[logo] > 0).mean() > 0.95
    assert (out_paint[logo] > 0).mean() < 0.05
    assert res["geometric_livery_sponsor_guard"]["status"] == "applied"
    assert res["geometric_livery_sponsor_guard"]["component_count"] == 1


def test_smart_tga_large_angular_warm_livery_panels_fall_back_to_paint():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    protected = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    cv2 = car_layers_mod.cv2

    def add_poly(x, y, w, h, points, base, accents):
        local = np.zeros((h, w), np.uint8)
        cv2.fillPoly(local, [np.array(points, np.int32)], 255)
        mask = local > 0
        sponsors[y:y + h, x:x + w][mask] = 255
        sub = rgb[y:y + h, x:x + w]
        sub[mask] = np.array(base, np.uint8)
        yy, xx = np.indices((h, w))
        for selector, color in accents:
            accent = mask & selector(yy, xx)
            sub[accent] = np.array(color, np.uint8)
        return (slice(y, y + h), slice(x, x + w), mask)

    tall_panel = add_poly(
        70,
        350,
        105,
        165,
        [(0, 0), (104, 0), (68, 30), (40, 164), (0, 164), (26, 90)],
        [226, 138, 28],
        [
            (lambda yy, xx: ((xx + yy) % 43) < 4, [198, 116, 24]),
            (lambda yy, xx: ((yy - xx) % 59) < 4, [246, 174, 54]),
        ],
    )
    wide_panel = add_poly(
        555,
        570,
        146,
        96,
        [(0, 52), (145, 0), (145, 20), (72, 95), (0, 85)],
        [128, 70, 12],
        [
            (lambda yy, xx: ((xx * 2 + yy) % 50) < 5, [190, 104, 18]),
            (lambda yy, xx: ((yy + xx) % 67) < 4, [38, 34, 28]),
        ],
    )

    text_card = (slice(88, 210), slice(385, 564))
    sponsors[text_card] = 255
    rgb[text_card] = np.array([224, 135, 24], np.uint8)
    rgb[104:196:12, 405:548] = np.array([245, 245, 235], np.uint8)
    rgb[116:194:18, 420:550] = np.array([34, 28, 20], np.uint8)

    protected_panel = (slice(470, 590), slice(335, 500))
    sponsors[protected_panel] = 255
    protected[protected_panel] = 255
    rgb[protected_panel] = np.array([220, 128, 20], np.uint8)

    mask, info = car_layers_mod._geometric_livery_sponsor_to_paint(
        rgb, sponsors, empty, protected, empty
    )

    assert info["status"] == "applied"
    assert {component["reason"] for component in info["components"]} == {
        "large_angular_warm_livery_panel"
    }
    for y_slice, x_slice, panel_mask in (tall_panel, wide_panel):
        assert (mask[y_slice, x_slice][panel_mask] > 0).mean() > 0.95
    assert (mask[text_card] > 0).mean() < 0.05
    assert (mask[protected_panel] > 0).mean() < 0.05


def test_smart_tga_blank_white_livery_panel_falls_back_to_paint(monkeypatch):
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.03, 0.04, 0.05], np.float32)
    sponsors = np.zeros((n, n), np.uint8)

    panel = (slice(168, 232), slice(72, 184))
    sponsors[panel] = 255
    tex[panel] = np.array([0.985, 0.988, 0.982], np.float32)

    logo_mask = np.zeros((n, n), bool)
    logo_mask[432:490:8, 82:258] = True
    logo_mask[438:496:13, 90:250] = True
    sponsors[logo_mask] = 255
    tex[logo_mask] = np.array([0.96, 0.96, 0.94], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    assert (res["layers"]["sponsors"][panel] > 0).mean() < 0.05
    assert (res["layers"]["paint"][panel] > 0).mean() > 0.95
    assert (res["layers"]["sponsors"][logo_mask] > 0).mean() > 0.95
    assert (res["layers"]["paint"][logo_mask] > 0).mean() < 0.05
    assert res["white_livery_sponsor_guard"]["status"] == "applied"
    assert res["white_livery_sponsor_guard"]["component_count"] == 1


def test_smart_tga_skinny_white_livery_panel_tolerates_runtime_edge():
    n = 512
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([8, 9, 10], np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    blank_panel = (slice(96, 146), slice(132, 150))
    sponsors[blank_panel] = 255
    rgb[blank_panel] = np.array([255, 255, 254], np.uint8)

    wordmark = np.zeros((n, n), bool)
    wordmark[286:291, 80:260] = True
    wordmark[302:307, 94:250] = True
    sponsors[wordmark] = 255
    rgb[wordmark] = np.array([250, 250, 248], np.uint8)

    empty = np.zeros((n, n), np.uint8)
    mask, info = car_layers_mod._white_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[blank_panel] > 0).mean() > 0.95
    assert (mask[wordmark] > 0).mean() < 0.05


def test_smart_tga_ornamental_neutral_livery_panel_falls_back_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([218, 218, 214], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    yy, xx = np.ogrid[:n, :n]
    y0, y1, x0, x1 = 156, 286, 118, 348
    ornamental = (
        ((yy >= y0) & (yy < y0 + 22) & (xx >= x0) & (xx < x1))
        | ((yy >= y1 - 36) & (yy < y1) & (xx >= x0) & (xx < x1))
        | ((xx >= x0) & (xx < x0 + 32) & (yy >= y0) & (yy < y1))
        | ((xx >= x1 - 14) & (xx < x1) & (yy >= y0) & (yy < y1))
    )
    sponsors[ornamental] = 255
    rgb[ornamental] = np.array([83, 74, 69], np.uint8)
    rgb[ornamental & (yy < y0 + 30)] = np.array([130, 118, 109], np.uint8)
    rgb[ornamental & (yy > y1 - 44)] = np.array([76, 68, 64], np.uint8)
    rgb[ornamental & (xx < x0 + 32)] = np.array([168, 160, 154], np.uint8)

    sponsor_plate = (slice(512, 572), slice(90, 326))
    sponsors[sponsor_plate] = 255
    rgb[sponsor_plate] = np.array([226, 224, 218], np.uint8)
    rgb[530:537, 122:294] = np.array([24, 24, 24], np.uint8)
    rgb[552:559, 112:284] = np.array([24, 24, 24], np.uint8)

    protected_panel = (slice(170, 284), slice(474, 660))
    sponsors[protected_panel] = 255
    brand[protected_panel] = 255
    rgb[protected_panel] = np.array([126, 114, 106], np.uint8)

    mask, info = car_layers_mod._ornamental_neutral_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "ornamental_neutral_livery_panel"
    assert (mask[ornamental] > 0).mean() > 0.95
    assert (mask[sponsor_plate] > 0).mean() < 0.05
    assert (mask[protected_panel] > 0).mean() < 0.05


def test_smart_tga_pale_body_panel_sponsor_falls_back_to_paint(monkeypatch):
    n = 512
    tex = np.full((n, n, 3), np.array([0.035, 0.038, 0.04], np.float32), np.float32)
    sponsors = np.zeros((n, n), np.uint8)

    long_panel = (slice(92, 132), slice(74, 242))
    sponsors[long_panel] = 255
    tex[long_panel] = np.array([0.985, 0.988, 0.982], np.float32)

    block_panel = (slice(156, 241), slice(358, 418))
    sponsors[block_panel] = 255
    tex[block_panel] = np.array([0.965, 0.965, 0.960], np.float32)
    tex[178:184, 368:388] = np.array([0.78, 0.78, 0.77], np.float32)
    tex[205:211, 390:410] = np.array([0.82, 0.82, 0.81], np.float32)
    tex[220:225, 368:420] = np.array([0.55, 0.55, 0.54], np.float32)

    sponsor_plate = (slice(330, 370), slice(70, 260))
    sponsors[sponsor_plate] = 255
    tex[sponsor_plate] = np.array([0.965, 0.965, 0.950], np.float32)
    tex[338:344, 92:240] = np.array([0.035, 0.035, 0.035], np.float32)
    tex[356:362, 106:230] = np.array([0.035, 0.035, 0.035], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    assert (res["layers"]["sponsors"][long_panel] > 0).mean() < 0.05
    assert (res["layers"]["paint"][long_panel] > 0).mean() > 0.95
    assert (res["layers"]["sponsors"][block_panel] > 0).mean() < 0.05
    assert (res["layers"]["paint"][block_panel] > 0).mean() > 0.95
    assert (res["layers"]["sponsors"][sponsor_plate] > 0).mean() > 0.95
    assert (res["layers"]["paint"][sponsor_plate] > 0).mean() < 0.05
    assert res["pale_body_panel_sponsor_guard"]["status"] == "applied"
    assert res["pale_body_panel_sponsor_guard"]["component_count"] == 2


def test_smart_tga_dark_body_panel_sponsor_falls_back_to_paint():
    n = 768
    rgb = np.full((n, n, 3), np.array([9, 10, 11], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    wide_panel = (slice(146, 206), slice(88, 238))
    sponsors[wide_panel] = 255
    sponsors[166:172, 108:198] = 0
    rgb[wide_panel] = np.array([29, 29, 29], np.uint8)

    block_panel = (slice(316, 376), slice(520, 595))
    sponsors[block_panel] = 255
    sponsors[340:346, 535:585] = 0
    rgb[block_panel] = np.array([37, 37, 37], np.uint8)
    rgb[338:344, 540:584] = np.array([44, 44, 44], np.uint8)

    red_sponsor = (slice(500, 540), slice(90, 250))
    sponsors[red_sponsor] = 255
    rgb[red_sponsor] = np.array([205, 22, 18], np.uint8)

    pale_sponsor = (slice(555, 595), slice(300, 470))
    sponsors[pale_sponsor] = 255
    rgb[pale_sponsor] = np.array([236, 236, 232], np.uint8)

    mask, info = car_layers_mod._dark_body_panel_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert info["capped"] is False
    assert (mask[wide_panel] > 0).mean() > 0.85
    assert (mask[block_panel] > 0).mean() > 0.85
    assert (mask[red_sponsor] > 0).mean() < 0.05
    assert (mask[pale_sponsor] > 0).mean() < 0.05


def test_smart_tga_tiny_dark_sponsor_speck_falls_back_to_paint():
    n = 512
    rgb = np.full((n, n, 3), np.array([10, 11, 12], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    speck = (slice(120, 123), slice(160, 163))
    sponsors[speck] = 255
    rgb[speck] = np.array([2, 2, 4], np.uint8)

    bright_tiny_sponsor = (slice(220, 223), slice(220, 223))
    sponsors[bright_tiny_sponsor] = 255
    rgb[bright_tiny_sponsor] = np.array([220, 28, 22], np.uint8)

    larger_dark_logo = (slice(304, 308), slice(112, 124))
    sponsors[larger_dark_logo] = 255
    rgb[larger_dark_logo] = np.array([3, 4, 8], np.uint8)

    mask, info = car_layers_mod._tiny_dark_sponsor_speck_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[speck] > 0).mean() > 0.95
    assert (mask[bright_tiny_sponsor] > 0).mean() == 0
    assert (mask[larger_dark_logo] > 0).mean() == 0


def test_smart_tga_multicolor_graphic_logo_demotes_from_numbers_to_sponsors():
    n = 512
    rgb = np.full((n, n, 3), np.array([8, 10, 12], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    logo = (((yy - 140) / 27.0) ** 2 + ((xx - 158) / 40.0) ** 2) <= 1.0
    numbers[logo] = 255
    rgb[logo] = np.array([235, 46, 42], np.uint8)
    green = logo & (xx < 145)
    rgb[green] = np.array([115, 178, 70], np.uint8)
    white = logo & (yy > 128) & (yy < 141) & (xx > 150) & (xx < 190)
    rgb[white] = np.array([242, 242, 230], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[278:350, 284:330] = True
    digit[278:294, 284:356] = True
    digit[334:350, 284:356] = True
    digit[294:334, 330:356] = True
    numbers[digit] = 255
    rgb[digit] = np.array([230, 42, 40], np.uint8)
    rgb[digit & (xx > 336)] = np.array([245, 245, 232], np.uint8)

    mask, info = car_layers_mod._multicolor_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[logo] > 0).mean() > 0.95
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_green_white_logo_false_positive_demotes_to_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    cy, cx = 300, 400
    logo = (((yy - cy) / 35.0) ** 2 + ((xx - cx) / 50.0) ** 2) <= 1.0
    logo &= ~(((xx > cx + 7) & (yy < cy - 12)) | ((xx < cx - 7) & (yy > cy + 12)))
    numbers[logo] = 255
    rgb[logo] = np.array([94, 176, 68], np.uint8)
    white_stroke = logo & (yy > cy - 9) & (yy < cy + 9) & (xx > cx - 34) & (xx < cx + 38)
    rgb[white_stroke] = np.array([242, 242, 230], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[558:698, 568:656] = True
    digit[558:590, 568:712] = True
    digit[666:698, 568:712] = True
    digit[590:666, 656:712] = True
    numbers[digit] = 255
    rgb[digit] = np.array([230, 42, 40], np.uint8)

    mask, info = car_layers_mod._green_white_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[logo] > 0).mean() > 0.95
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_large_green_logo_false_positive_demotes_to_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 15, 16], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    cy, cx = 300, 260
    logo = (((yy - cy) / 80.0) ** 2 + ((xx - cx) / 96.0) ** 2) <= 1.0
    logo &= ~(((yy - cy) / 31.0) ** 2 + ((xx - cx) / 39.0) ** 2 <= 1.0)
    numbers[logo] = 255
    rgb[logo] = np.array([82, 168, 2], np.uint8)
    stripe = logo & ((((xx + yy) % 29) < 2) | (((xx - yy) % 31) < 2))
    rgb[stripe] = np.array([38, 118, 1], np.uint8)

    small_cy, small_cx = 520, 720
    small_outer = ((yy - small_cy) ** 2 + (xx - small_cx) ** 2) <= 56 ** 2
    small_inner = ((yy - small_cy) ** 2 + (xx - small_cx) ** 2) <= 38 ** 2
    small_badge = small_outer & ~small_inner
    sponsor_context = ((yy - small_cy) ** 2 + (xx - small_cx) ** 2) <= 72 ** 2
    sponsors[sponsor_context] = 255
    sponsors[small_badge] = 0
    numbers[small_badge] = 255
    pattern = (xx + yy) % 10
    rgb[small_badge & (pattern < 4)] = np.array([24, 136, 16], np.uint8)
    rgb[small_badge & (pattern >= 4) & (pattern < 7)] = np.array([160, 38, 22], np.uint8)
    rgb[small_badge & (pattern >= 7) & (pattern < 9)] = np.array([178, 150, 20], np.uint8)
    rgb[small_badge & (pattern >= 9)] = np.array([38, 35, 8], np.uint8)

    true_green_number = (((yy - 710) / 78.0) ** 2 + ((xx - 320) / 92.0) ** 2) <= 1.0
    true_green_number &= ~(((yy - 710) / 30.0) ** 2 + ((xx - 320) / 36.0) ** 2 <= 1.0)
    numbers[true_green_number] = 255
    rgb[true_green_number] = np.array([85, 255, 0], np.uint8)
    bright_edges = true_green_number & ((((xx + yy) % 29) < 2) | (((xx - yy) % 31) < 2))
    rgb[bright_edges] = np.array([160, 255, 60], np.uint8)

    mask, info = car_layers_mod._large_green_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {
        "large_green_sponsor_logo",
        "round_green_sponsor_badge",
    }
    assert (mask[logo] > 0).mean() > 0.95
    assert (mask[small_badge] > 0).mean() > 0.95
    assert (mask[true_green_number] > 0).mean() < 0.05


def test_smart_tga_wide_white_livery_panel_demotes_from_numbers_to_paint():
    n = 512
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    panel = (slice(82, 111), slice(82, 282))
    numbers[panel] = 255
    rgb[panel] = np.array([244, 244, 238], np.uint8)
    rgb[90:93, 100:140] = np.array([106, 106, 104], np.uint8)
    rgb[98:102, 188:226] = np.array([128, 128, 124], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[258:342, 302:338] = True
    digit[258:276, 302:372] = True
    digit[324:342, 302:372] = True
    digit[276:324, 338:372] = True
    numbers[digit] = 255
    yy, xx = np.ogrid[:n, :n]
    rgb[digit] = np.array([232, 40, 38], np.uint8)
    rgb[digit & (xx > 344)] = np.array([246, 246, 234], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_large_white_body_fields_demote_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([7, 8, 9], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    side_panel = np.zeros((n, n), bool)
    side_panel[130:249, 264:617] = True
    side_panel[130:190, 264:300] = False
    side_panel[210:249, 540:617] = False
    side_panel[230:249, 300:366] = False
    numbers[side_panel] = 255
    rgb[side_panel] = np.array([249, 249, 247], np.uint8)

    roof_panel = np.zeros((n, n), bool)
    roof_panel[155:307, 0:184] = True
    roof_panel[155:210, 0:30] = False
    roof_panel[220:307, 126:184] = False
    roof_panel[250:307, 54:94] = False
    numbers[roof_panel] = 255
    rgb[roof_panel] = np.array([248, 247, 245], np.uint8)

    white_digit = np.zeros((n, n), bool)
    white_digit[700:840, 760:815] = True
    white_digit[700:736, 760:900] = True
    white_digit[804:840, 760:900] = True
    white_digit[736:804, 845:900] = True
    numbers[white_digit] = 255
    rgb[white_digit] = np.array([245, 245, 238], np.uint8)
    outline = np.zeros((n, n), bool)
    outline[692:848, 752:908] = True
    outline[704:836, 768:892] = False
    numbers[outline] = 255
    rgb[outline] = np.array([220, 34, 30], np.uint8)
    rgb[outline & ((np.indices((n, n))[0] % 19) < 2)] = np.array([4, 4, 4], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"large_white_body_number_panel"}
    assert (mask[side_panel] > 0).mean() > 0.95
    assert (mask[roof_panel] > 0).mean() > 0.95
    assert (mask[white_digit] > 0).mean() < 0.05
    assert (mask[outline] > 0).mean() < 0.05


def test_smart_tga_flat_dark_body_panel_demotes_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 120, 160, 39, 68
    panel = np.zeros((n, n), bool)
    panel[y0:y0 + h, x0:x0 + w] = True
    panel[y0:y0 + 9, x0:x0 + 17] = False
    panel[y0 + h - 11:y0 + h, x0 + w - 18:x0 + w] = False
    panel[y0:y0 + 6, x0 + w - 12:x0 + w] = False
    panel[y0 + h - 6:y0 + h, x0:x0 + 12] = False
    numbers[panel] = 255
    rgb[panel] = np.array([8, 8, 8], np.uint8)

    saturated_panel = (slice(248, 287), slice(160, 228))
    numbers[saturated_panel] = 255
    rgb[saturated_panel] = np.array([42, 112, 220], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[410:500, 454:501] = True
    digit[410:433, 454:548] = True
    digit[477:500, 454:548] = True
    digit[433:477, 501:548] = True
    numbers[digit] = 255
    rgb[digit] = np.array([44, 204, 230], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "flat_dark_body_number_panel"
    assert info["components"][0]["edge_density"] == 0
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[saturated_panel] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_dark_neutral_body_panels_demote_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 34], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    tall_panel = np.zeros((n, n), bool)
    tall_local = np.ones((240, 81), bool)
    tall_local[38:96, 24:58] = False
    tall_local[130:184, 8:44] = False
    tall_local[190:232, 42:72] = False
    tall_panel[650:890, 10:91][tall_local] = True
    numbers[tall_panel] = 255
    rgb[tall_panel] = np.array([46, 46, 46], np.uint8)

    wide_panel = np.zeros((n, n), bool)
    wide_local = np.ones((47, 156), bool)
    wide_local[5:15, 10:60] = False
    wide_local[30:42, 96:146] = False
    wide_panel[888:935, 313:469][wide_local] = True
    numbers[wide_panel] = 255
    rgb[wide_panel] = np.array([36, 36, 36], np.uint8)

    white_plate = (slice(286, 442), slice(616, 792))
    rgb[white_plate] = np.array([238, 238, 232], np.uint8)
    black_digit_on_white = np.zeros((n, n), bool)
    black_digit_on_white[320:418, 652:708] = True
    black_digit_on_white[320:346, 652:760] = True
    black_digit_on_white[392:418, 652:760] = True
    black_digit_on_white[346:392, 720:760] = True
    numbers[black_digit_on_white] = 255
    rgb[black_digit_on_white] = np.array([28, 28, 28], np.uint8)

    saturated_plate = (slice(480, 636), slice(616, 792))
    rgb[saturated_plate] = np.array([38, 78, 210], np.uint8)
    black_digit_on_blue = np.zeros((n, n), bool)
    black_digit_on_blue[514:612, 652:708] = True
    black_digit_on_blue[514:540, 652:760] = True
    black_digit_on_blue[586:612, 652:760] = True
    black_digit_on_blue[540:586, 720:760] = True
    numbers[black_digit_on_blue] = 255
    rgb[black_digit_on_blue] = np.array([30, 30, 30], np.uint8)

    striped_logo = np.zeros((n, n), bool)
    striped_logo[720:820, 620:760] = True
    numbers[striped_logo] = 255
    rgb[striped_logo] = np.array([42, 42, 42], np.uint8)
    yy, xx = np.indices((100, 140))
    stripe = ((xx + yy) % 18) < 4
    rgb[720:820, 620:760][stripe] = np.array([212, 212, 205], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"dark_neutral_body_number_panel"}
    assert (mask[tall_panel] > 0).mean() > 0.95
    assert (mask[wide_panel] > 0).mean() > 0.95
    assert (mask[black_digit_on_white] > 0).mean() < 0.05
    assert (mask[black_digit_on_blue] > 0).mean() < 0.05
    assert (mask[striped_logo] > 0).mean() == 0


def test_smart_tga_uv_edge_dark_neutral_body_panels_demote_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([92, 92, 88], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    yy, xx = np.indices((74, 220))
    top_local = (yy > 8 + (xx % 39) * 0.10) & (yy < 66 - (xx % 47) * 0.08)
    top_local[18:46, 76:126] = False
    top_panel = np.zeros((n, n), bool)
    top_panel[8:82, 270:490][top_local] = True
    numbers[top_panel] = 255
    rgb[top_panel] = np.array([35, 35, 35], np.uint8)
    top_patch = np.zeros((n, n), bool)
    top_patch[8:82, 270:382][top_local[:, :112]] = True
    rgb[top_patch] = np.array([49, 49, 49], np.uint8)
    rgb[82:94, 270:490] = np.array([46, 46, 46], np.uint8)

    bottom_local = np.ones((55, 126), bool)
    bottom_local[4:14, 12:48] = False
    bottom_local[34:48, 74:118] = False
    bottom_local[18:32, 20:62] = False
    bottom_panel = np.zeros((n, n), bool)
    bottom_panel[914:969, 858:984][bottom_local] = True
    numbers[bottom_panel] = 255
    rgb[bottom_panel] = np.array([36, 36, 36], np.uint8)
    bottom_patch = np.zeros((n, n), bool)
    bottom_patch[914:969, 858:918][bottom_local[:, :60]] = True
    rgb[bottom_patch] = np.array([51, 51, 51], np.uint8)
    rgb[900:914, 858:984] = np.array([44, 44, 44], np.uint8)

    central_same_shape = np.zeros((n, n), bool)
    central_same_shape[410:484, 270:490][top_local] = True
    numbers[central_same_shape] = 255
    rgb[central_same_shape] = np.array([35, 35, 35], np.uint8)
    central_patch = np.zeros((n, n), bool)
    central_patch[410:484, 270:382][top_local[:, :112]] = True
    rgb[central_patch] = np.array([49, 49, 49], np.uint8)

    edge_digit = np.zeros((n, n), bool)
    edge_digit[12:102, 760:814] = True
    edge_digit[12:36, 760:876] = True
    edge_digit[78:102, 760:876] = True
    edge_digit[36:78, 832:876] = True
    numbers[edge_digit] = 255
    rgb[edge_digit] = np.array([34, 34, 34], np.uint8)

    cream_strip = (slice(132, 153), slice(330, 481))
    numbers[cream_strip] = 255
    rgb[cream_strip] = np.array([246, 218, 150], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"uv_edge_dark_neutral_body_panel"}
    assert (mask[top_panel] > 0).mean() > 0.95
    assert (mask[bottom_panel] > 0).mean() > 0.95
    assert (mask[central_same_shape] > 0).mean() == 0
    assert (mask[edge_digit] > 0).mean() < 0.05
    assert (mask[cream_strip] > 0).mean() == 0


def test_smart_tga_medium_context_dark_neutral_body_panels_demote_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([112, 110, 104], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    tall_local = np.ones((111, 70), bool)
    tall_local[8:28, 10:36] = False
    tall_local[46:68, 32:63] = False
    tall_local[82:102, 6:29] = False
    tall_panel = np.zeros((n, n), bool)
    tall_panel[386:497, 580:650][tall_local] = True
    numbers[tall_panel] = 255
    rgb[tall_panel] = np.array([35, 35, 35], np.uint8)
    tall_patch = np.zeros((n, n), bool)
    tall_patch[386:497, 580:616][tall_local[:, :36]] = True
    rgb[tall_patch] = np.array([47, 47, 47], np.uint8)
    rgb[374:386, 582:648] = np.array([46, 46, 46], np.uint8)

    compact_local = np.ones((77, 60), bool)
    compact_local[10:25, 8:28] = False
    compact_local[46:66, 30:55] = False
    compact_panel = np.zeros((n, n), bool)
    compact_panel[556:633, 248:308][compact_local] = True
    numbers[compact_panel] = 255
    rgb[compact_panel] = np.array([34, 34, 34], np.uint8)
    compact_patch = np.zeros((n, n), bool)
    compact_patch[556:633, 248:280][compact_local[:, :32]] = True
    rgb[compact_patch] = np.array([44, 44, 44], np.uint8)
    rgb[633:646, 250:306] = np.array([46, 46, 46], np.uint8)

    saturated_ring_digit_bg = (slice(120, 230), slice(620, 750))
    rgb[saturated_ring_digit_bg] = np.array([210, 40, 32], np.uint8)
    black_digit_on_red = np.zeros((n, n), bool)
    black_digit_on_red[140:220, 648:702] = True
    black_digit_on_red[140:162, 648:738] = True
    black_digit_on_red[198:220, 648:738] = True
    black_digit_on_red[162:198, 714:738] = True
    numbers[black_digit_on_red] = 255
    rgb[black_digit_on_red] = np.array([34, 34, 34], np.uint8)

    solid_digit = np.zeros((n, n), bool)
    solid_digit[372:488, 780:824] = True
    solid_digit[372:402, 780:884] = True
    solid_digit[458:488, 780:884] = True
    solid_digit[402:458, 840:884] = True
    numbers[solid_digit] = 255
    rgb[solid_digit] = np.array([34, 34, 34], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"medium_context_dark_neutral_body_panel"}
    assert (mask[tall_panel] > 0).mean() > 0.95
    assert (mask[compact_panel] > 0).mean() > 0.95
    assert (mask[black_digit_on_red] > 0).mean() < 0.05
    assert (mask[solid_digit] > 0).mean() < 0.05


def test_smart_tga_paired_saturated_context_dark_body_panels_demote_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([104, 100, 94], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    rgb[109:117, 197:263] = np.array([42, 42, 40], np.uint8)
    rgb[121:164, 263:280] = np.array([194, 22, 26], np.uint8)
    rgb[164:176, 197:263] = np.array([194, 22, 26], np.uint8)
    rgb[153:221, 246:341] = np.array([142, 136, 128], np.uint8)
    rgb[121:164, 263:280] = np.array([194, 22, 26], np.uint8)
    rgb[164:176, 197:263] = np.array([194, 22, 26], np.uint8)
    rgb[157:165, 258:324] = np.array([42, 42, 40], np.uint8)
    rgb[165:209, 324:332] = np.array([128, 15, 19], np.uint8)
    rgb[209:217, 258:324] = np.array([128, 15, 19], np.uint8)
    rgb[121:164, 197:263] = np.array([34, 34, 34], np.uint8)
    rgb[165:209, 258:324] = np.array([35, 35, 35], np.uint8)

    paired_a = np.zeros((n, n), bool)
    paired_a_local = np.ones((43, 66), bool)
    paired_a_local[5:10, 10:28] = False
    paired_a[121:164, 197:263][paired_a_local] = True
    paired_b = np.zeros((n, n), bool)
    paired_b_local = np.ones((44, 66), bool)
    paired_b_local[30:35, 38:58] = False
    paired_b[165:209, 258:324][paired_b_local] = True
    numbers[paired_a] = 255
    numbers[paired_b] = 255

    red_lone_bg = (slice(300, 368), slice(178, 280))
    rgb[red_lone_bg] = np.array([194, 22, 26], np.uint8)
    lone_blank = (slice(311, 354), slice(197, 263))
    numbers[lone_blank] = 255
    rgb[lone_blank] = np.array([34, 34, 34], np.uint8)

    red_digit_bg = (slice(458, 556), slice(588, 752))
    rgb[red_digit_bg] = np.array([205, 24, 30], np.uint8)
    digit_a = (slice(478, 536), slice(612, 632))
    digit_b = (slice(478, 536), slice(652, 672))
    numbers[digit_a] = 255
    numbers[digit_b] = 255
    rgb[digit_a] = np.array([34, 34, 34], np.uint8)
    rgb[digit_b] = np.array([34, 34, 34], np.uint8)

    gray_medium_pair = (slice(700, 780), slice(620, 690))
    rgb[gray_medium_pair] = np.array([112, 110, 104], np.uint8)
    medium_context_panel = (slice(713, 756), slice(632, 698))
    numbers[medium_context_panel] = 255
    rgb[medium_context_panel] = np.array([34, 34, 34], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"paired_saturated_context_dark_neutral_body_panel"}
    assert (mask[paired_a] > 0).mean() > 0.95
    assert (mask[paired_b] > 0).mean() > 0.95
    assert (mask[lone_blank] > 0).mean() == 0
    assert (mask[digit_a] > 0).mean() == 0
    assert (mask[digit_b] > 0).mean() == 0
    assert (mask[medium_context_panel] > 0).mean() == 0


def test_smart_tga_flat_neutral_livery_slabs_demote_from_numbers_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([26, 24, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    pale_bbox = (slice(110, 170), slice(110, 321))
    yy, xx = np.indices((60, 211))
    pale_local = (yy >= 6 + xx * 0.18) & (yy <= 30 + xx * 0.18)
    pale = np.zeros((n, n), bool)
    pale[pale_bbox][pale_local] = True
    numbers[pale] = 255
    rgb[pale] = np.array([246, 244, 236], np.uint8)

    dark_bbox = (slice(174, 264), slice(200, 326))
    dark = np.zeros((90, 126), bool)
    dark[:, :] = True
    dark[25:70, 0:58] = False
    dark[52:82, 84:121] = False
    dark_panel = np.zeros((n, n), bool)
    dark_panel[dark_bbox][dark] = True
    numbers[dark_panel] = 255
    rgb[dark_panel] = np.array([4, 4, 4], np.uint8)

    small_bbox = (slice(205, 237), slice(160, 221))
    small = np.zeros((32, 61), bool)
    small[:, :] = True
    small[3:20, 6:26] = False
    small_panel = np.zeros((n, n), bool)
    small_panel[small_bbox][small] = True
    numbers[small_panel] = 255
    rgb[small_panel] = np.array([4, 4, 4], np.uint8)

    remote_small = np.zeros((n, n), bool)
    remote_small[520:552, 160:221][small] = True
    numbers[remote_small] = 255
    rgb[remote_small] = np.array([4, 4, 4], np.uint8)

    blue_number = np.zeros((n, n), bool)
    blue_number[600:710, 560:610] = True
    blue_number[600:630, 560:690] = True
    blue_number[680:710, 560:690] = True
    blue_number[630:680, 640:690] = True
    numbers[blue_number] = 255
    rgb[blue_number] = np.array([72, 154, 202], np.uint8)
    rgb[blue_number & ((np.indices((n, n))[1] % 13) < 2)] = np.array([238, 238, 236], np.uint8)

    black_number = np.zeros((n, n), bool)
    black_number[750:890, 560:625] = True
    black_number[750:790, 560:720] = True
    black_number[850:890, 560:720] = True
    black_number[790:850, 655:720] = True
    numbers[black_number] = 255
    rgb[black_number] = np.array([6, 6, 6], np.uint8)
    rgb[black_number & ((np.indices((n, n))[0] % 17) < 2)] = np.array([220, 220, 214], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert reasons == {
        "flat_neutral_livery_number_slab",
        "flat_neutral_livery_number_slab_companion",
    }
    assert (mask[pale] > 0).mean() > 0.95
    assert (mask[dark_panel] > 0).mean() > 0.95
    assert (mask[small_panel] > 0).mean() > 0.95
    assert (mask[remote_small] > 0).mean() == 0
    assert (mask[blue_number] > 0).mean() < 0.05
    assert (mask[black_number] > 0).mean() < 0.05


def test_smart_tga_solid_warm_livery_panel_in_numbers_demotes_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 32, 29], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    panel_bbox = (slice(329, 437), slice(457, 581))
    panel_local = np.ones((108, 124), bool)
    panel_local[0:24, 0:42] = False
    panel_local[84:108, 84:124] = False
    panel = np.zeros((n, n), bool)
    panel[panel_bbox][panel_local] = True
    numbers[panel] = 255
    rgb[panel_bbox] = np.array([255, 152, 46], np.uint8)

    outlined_number = np.zeros((n, n), bool)
    outlined_number[610:754, 650:705] = True
    outlined_number[610:644, 650:800] = True
    outlined_number[720:754, 650:800] = True
    outlined_number[644:720, 745:800] = True
    numbers[outlined_number] = 255
    rgb[outlined_number] = np.array([255, 150, 46], np.uint8)
    yy, xx = np.indices((n, n))
    rgb[outlined_number & ((xx % 17) < 3)] = np.array([244, 244, 236], np.uint8)
    rgb[outlined_number & ((yy % 23) < 3)] = np.array([12, 12, 12], np.uint8)

    tiny_orange_tag = (slice(120, 146), slice(700, 752))
    numbers[tiny_orange_tag] = 255
    rgb[tiny_orange_tag] = np.array([255, 152, 46], np.uint8)

    smooth_full_block = (slice(238, 308), slice(700, 794))
    numbers[smooth_full_block] = 255
    rgb[smooth_full_block] = np.array([255, 152, 46], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "solid_warm_livery_number_panel"
    assert info["components"][0]["warm_orange_frac"] >= 0.96
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[outlined_number] > 0).mean() < 0.05
    assert (mask[tiny_orange_tag] > 0).mean() == 0
    assert (mask[smooth_full_block] > 0).mean() == 0


def test_smart_tga_pale_saturated_context_number_panel_demotes_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([255, 125, 30], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    panel_bbox = (slice(229, 314), slice(923, 986))
    panel_local = np.ones((85, 63), bool)
    panel_local[0:28, 0:18] = False
    panel_local[54:85, 41:63] = False
    panel = np.zeros((n, n), bool)
    panel[panel_bbox][panel_local] = True
    numbers[panel] = 255
    rgb[panel] = np.array([183, 179, 177], np.uint8)
    rgb[panel & ((np.indices((n, n))[0] % 29) < 2)] = np.array([168, 166, 188], np.uint8)

    tall_digit_piece = np.zeros((n, n), bool)
    tall_digit_piece[460:606, 120:185] = True
    tall_digit_piece[460:494, 120:152] = False
    tall_digit_piece[558:606, 152:185] = False
    numbers[tall_digit_piece] = 255
    rgb[tall_digit_piece] = np.array([214, 212, 210], np.uint8)

    text_panel = (slice(650, 735), slice(760, 823))
    numbers[text_panel] = 255
    rgb[text_panel] = np.array([184, 180, 176], np.uint8)
    rgb[674:681, 770:813] = np.array([16, 16, 16], np.uint8)
    rgb[700:707, 772:812] = np.array([230, 230, 222], np.uint8)

    full_block = (slice(760, 828), slice(120, 184))
    numbers[full_block] = 255
    rgb[full_block] = np.array([183, 179, 177], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "pale_saturated_context_livery_number_panel"
    assert info["components"][0]["saturated_ring_frac"] >= 0.82
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[tall_digit_piece] > 0).mean() == 0
    assert (mask[text_panel] > 0).mean() == 0
    assert (mask[full_block] > 0).mean() == 0


def test_smart_tga_saturated_cool_livery_number_panels_demote_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([214, 16, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    panel_a_local = np.ones((50, 92), bool)
    panel_a_local[0:8, 0:18] = False
    panel_a_local[42:50, 74:92] = False
    panel_a_local[0:5, 70:92] = False
    panel_a_local[45:50, 0:22] = False
    panel_a_local[18:32, 0:8] = False
    panel_a = np.zeros((n, n), bool)
    panel_a[188:238, 626:718][panel_a_local] = True
    numbers[panel_a] = 255
    rgb[panel_a] = np.array([12, 36, 162], np.uint8)

    panel_b_local = np.ones((51, 186), bool)
    for row in range(18, panel_b_local.shape[0]):
        notch = min(17, 2 + row // 3)
        panel_b_local[row, 93 - notch:93 + notch] = False
    panel_b_local[0:7, 0:18] = False
    panel_b_local[44:51, 168:186] = False
    panel_b_local[0:5, 148:186] = False
    panel_b_local[46:51, 0:38] = False
    panel_b = np.zeros((n, n), bool)
    panel_b[240:291, 629:815][panel_b_local] = True
    numbers[panel_b] = 255
    rgb[panel_b] = np.array([14, 36, 160], np.uint8)
    rgb[panel_b & (((xx + yy) % 41) == 0)] = np.array([22, 43, 174], np.uint8)

    blue_digit = np.zeros((n, n), bool)
    blue_digit[585:700, 160:210] = True
    blue_digit[585:615, 160:292] = True
    blue_digit[670:700, 160:292] = True
    blue_digit[615:670, 242:292] = True
    numbers[blue_digit] = 255
    rgb[blue_digit] = np.array([16, 58, 178], np.uint8)
    rgb[blue_digit & ((xx % 17) < 3)] = np.array([238, 238, 232], np.uint8)

    full_block = (slice(340, 394), slice(626, 776))
    numbers[full_block] = 255
    rgb[full_block] = np.array([12, 36, 162], np.uint8)

    sponsor_card_local = np.ones((52, 140), bool)
    sponsor_card_local[10:16, 18:122] = False
    sponsor_card_local[24:30, 28:130] = False
    sponsor_card_local[38:44, 34:118] = False
    sponsor_card = np.zeros((n, n), bool)
    sponsor_card[438:490, 620:760][sponsor_card_local] = True
    numbers[sponsor_card] = 255
    rgb[sponsor_card] = np.array([12, 36, 162], np.uint8)
    rgb[448:454, 638:742] = np.array([238, 238, 232], np.uint8)
    rgb[462:468, 648:750] = np.array([20, 20, 22], np.uint8)
    rgb[476:482, 654:738] = np.array([238, 238, 232], np.uint8)

    vertical_local = np.ones((92, 50), bool)
    vertical_local[0:18, 0:8] = False
    vertical_local[74:92, 42:50] = False
    vertical_local[18:32, 0:8] = False
    vertical_panel = np.zeros((n, n), bool)
    vertical_panel[598:690, 420:470][vertical_local] = True
    numbers[vertical_panel] = 255
    rgb[vertical_panel] = np.array([12, 36, 162], np.uint8)

    protected_panel = np.zeros((n, n), bool)
    protected_panel[120:170, 820:912][panel_a_local] = True
    numbers[protected_panel] = 255
    template[protected_panel] = 255
    rgb[protected_panel] = np.array([12, 36, 162], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {
        "saturated_cool_livery_number_panel",
    }
    assert all(component["cool_blue_frac"] >= 0.94 for component in info["components"])
    assert (mask[panel_a] > 0).mean() > 0.95
    assert (mask[panel_b] > 0).mean() > 0.95
    assert (mask[blue_digit] > 0).mean() < 0.05
    assert (mask[full_block] > 0).mean() == 0
    assert (mask[sponsor_card] > 0).mean() == 0
    assert (mask[vertical_panel] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0


def test_smart_tga_lower_uv_medium_blue_livery_number_panels_demote_real_dlm_1168248():
    sample = Path(
        "_smart_tga_runs/cycle554_dlm_next8_after_1144819_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1168248"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle554 DLM 1168248 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "lower_uv_medium_blue_livery_number_panel"
    ]
    assert len(components) == 7
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [
        [604, 938, 37, 40],
        [606, 999, 80, 25],
        [617, 863, 18, 62],
        [647, 927, 115, 66],
        [648, 975, 31, 26],
        [673, 847, 91, 75],
        [703, 998, 53, 23],
    ]
    assert all(component["cool_blue_frac"] >= 0.92 for component in components)
    assert all(component["color_std"] <= 0.105 for component in components)

    for x, y, w, h in bboxes:
        target = numbers[y:y + h, x:x + w] > 0
        demoted = mask[y:y + h, x:x + w] > 0
        assert float((demoted & target).sum()) / float(max(1, target.sum())) > 0.96

    true_side_number = numbers[236:343, 260:426] > 0
    true_side_demoted = mask[236:343, 260:426] > 0
    assert int((true_side_demoted & true_side_number).sum()) == 0

    small_logo_or_sponsor = numbers[217:238, 288:359] > 0
    small_logo_demoted = mask[217:238, 288:359] > 0
    assert int((small_logo_demoted & small_logo_or_sponsor).sum()) == 0

    gray_wordmark = numbers[815:831, 485:522] > 0
    gray_wordmark_demoted = mask[815:831, 485:522] > 0
    assert int((gray_wordmark_demoted & gray_wordmark).sum()) == 0


def test_smart_tga_clustered_monochrome_dlm_livery_panels_demote_real_1078322():
    sample = Path(
        "_smart_tga_runs/cycle602_dlm_next4_after_1070087_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1078322"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle602 DLM 1078322 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "clustered_monochrome_dlm_livery_panel"
    ]
    assert info["status"] == "applied"
    assert sorted(component["bbox"] for component in components) == [
        [134, 7, 154, 68],
        [321, 35, 154, 80],
        [487, 31, 112, 93],
        [636, 225, 126, 57],
        [696, 704, 53, 26],
        [719, 739, 100, 22],
    ]
    assert all(component["same_family_count"] >= 3 for component in components)
    assert all(component["sat_mean"] <= 0.025 for component in components)
    assert all(component["color_std"] <= 0.078 for component in components)

    for x, y, w, h in (component["bbox"] for component in components):
        target = numbers[y:y + h, x:x + w] > 0
        demoted = mask[y:y + h, x:x + w] > 0
        assert float((demoted & target).sum()) / float(max(1, target.sum())) > 0.95

    true_upper_10 = numbers[254:339, 296:440] > 0
    true_lower_10 = numbers[721:799, 282:433] > 0
    assert int(((mask[254:339, 296:440] > 0) & true_upper_10).sum()) == 0
    assert int(((mask[721:799, 282:433] > 0) & true_lower_10).sum()) == 0


def test_smart_tga_blank_dark_dlm_livery_plates_demote_real_1004124():
    sample = Path(
        "_smart_tga_runs/cycle595_dlm_next4_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1004124"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle595 DLM 1004124 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] in {
            "top_edge_dark_saturated_context_livery_plate",
            "lower_dark_context_livery_plate",
        }
    ]
    assert info["status"] == "applied"
    assert sorted(component["bbox"] for component in components) == [
        [169, 37, 77, 26],
        [695, 703, 55, 28],
        [718, 738, 102, 23],
        [783, 704, 57, 29],
    ]
    assert {component["reason"] for component in components} == {
        "top_edge_dark_saturated_context_livery_plate",
        "lower_dark_context_livery_plate",
    }
    assert all(component["white_frac"] == 0 for component in components)
    assert all(component["red_frac"] == 0 for component in components)
    assert all(component["color_std"] <= 0.05 for component in components)

    for x, y, w, h in [component["bbox"] for component in components]:
        target = numbers[y:y + h, x:x + w] > 0
        demoted = mask[y:y + h, x:x + w] > 0
        assert float((demoted & target).sum()) / float(max(1, target.sum())) > 0.96


def test_smart_tga_right_edge_red_livery_number_sliver_demotes_to_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([128, 128, 128], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def curved_sliver(top: int, left: int) -> np.ndarray:
        local = np.zeros((350, 32), bool)
        for row in range(local.shape[0]):
            start = int(round(10 + 10 * np.sin(row / 60.0)))
            local[row, start:start + 12] = True
        panel = np.zeros((n, n), bool)
        panel[top:top + 350, left:left + 32][local] = True
        return panel

    sliver = curved_sliver(425, 992)
    numbers[sliver] = 255
    yy, xx = np.indices((n, n))
    rgb[sliver] = np.array([184, 45, 45], np.uint8)
    rgb[sliver & ((xx % 7) < 2)] = np.array([228, 28, 40], np.uint8)
    rgb[sliver & ((xx % 11) < 2)] = np.array([126, 72, 72], np.uint8)
    rgb[sliver & ((yy % 17) < 2)] = np.array([255, 90, 90], np.uint8)

    red_digit = np.zeros((n, n), bool)
    red_digit[520:770, 120:164] = True
    red_digit[520:565, 120:250] = True
    red_digit[725:770, 120:250] = True
    red_digit[565:725, 206:250] = True
    numbers[red_digit] = 255
    rgb[red_digit] = np.array([190, 44, 44], np.uint8)

    text_sliver = curved_sliver(62, 992)
    numbers[text_sliver] = 255
    rgb[text_sliver] = np.array([184, 45, 45], np.uint8)
    rgb[text_sliver & ((yy % 29) < 5)] = np.array([236, 236, 226], np.uint8)
    rgb[text_sliver & ((yy % 41) < 4)] = np.array([20, 20, 20], np.uint8)

    protected_sliver = curved_sliver(62, 880)
    numbers[protected_sliver] = 255
    template[protected_sliver] = 255
    rgb[protected_sliver] = np.array([184, 45, 45], np.uint8)
    rgb[protected_sliver & ((xx % 7) < 2)] = np.array([218, 38, 42], np.uint8)
    rgb[protected_sliver & ((xx % 11) < 2)] = np.array([146, 68, 68], np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "right_edge_red_livery_number_sliver"
    assert (mask[sliver] > 0).mean() > 0.95
    assert (mask[red_digit] > 0).mean() == 0
    assert (mask[text_sliver] > 0).mean() == 0
    assert (mask[protected_sliver] > 0).mean() == 0


def test_smart_tga_dark_panel_angular_white_livery_graphic_demotes_to_paint_from_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle485_dlm_batch_left_edge_neutral_sponsor_logo_v1_nocache/"
        "Dirt_Late_Model_car_num_1167712"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle485 DLM 1167712 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "dark_panel_angular_white_livery_graphic"
    ]
    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (834, 816, 99, 160),
    }
    component = components[0]
    assert component["dark_ring_frac"] >= 0.96
    assert component["ring_sponsor_frac"] <= 0.01
    assert component["ring_number_frac"] <= 0.01
    assert component["ring_template_frac"] <= 0.01
    assert float((mask[816:976, 834:933] > 0).mean()) > 0.50
    assert float((mask[28:282, 875:1024] > 0).mean()) == 0.0
    assert float((mask[239:342, 271:455] > 0).mean()) == 0.0


def test_smart_tga_small_neutral_sponsor_panel_demotes_from_numbers_to_sponsors():
    n = 512
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    panel = (slice(118, 130), slice(154, 180))
    numbers[panel] = 255
    rgb[panel] = np.array([116, 116, 112], np.uint8)
    rgb[121:123, 158:176] = np.array([228, 228, 218], np.uint8)
    rgb[125:127, 160:176] = np.array([36, 36, 38], np.uint8)
    rgb[119:128:3, 157:178] = np.array([42, 42, 44], np.uint8)
    rgb[120:129:4, 159:177] = np.array([224, 224, 216], np.uint8)

    saturated_small_panel = (slice(188, 202), slice(156, 188))
    numbers[saturated_small_panel] = 255
    rgb[saturated_small_panel] = np.array([38, 92, 214], np.uint8)
    rgb[193:196, 160:184] = np.array([230, 230, 238], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[274:342, 292:328] = True
    digit[274:290, 292:356] = True
    digit[326:342, 292:356] = True
    digit[290:326, 328:356] = True
    numbers[digit] = 255
    rgb[digit] = np.array([230, 42, 40], np.uint8)

    mask, info = car_layers_mod._small_sponsor_panel_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[saturated_small_panel] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_warm_orange_sponsor_tag_demotes_from_numbers_to_sponsors():
    n = 512
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    orange_tag = (slice(76, 86), slice(68, 102))
    numbers[orange_tag] = 255
    rgb[orange_tag] = np.array([218, 91, 48], np.uint8)
    rgb[78:79, 72:96] = np.array([245, 236, 226], np.uint8)

    red_number_bar = (slice(128, 138), slice(68, 102))
    numbers[red_number_bar] = 255
    rgb[red_number_bar] = np.array([230, 42, 40], np.uint8)

    blue_panel = (slice(188, 202), slice(156, 188))
    numbers[blue_panel] = 255
    rgb[blue_panel] = np.array([38, 92, 214], np.uint8)

    mask, info = car_layers_mod._small_sponsor_panel_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "warm_orange_sponsor_tag"
    assert (mask[orange_tag] > 0).mean() > 0.95
    assert (mask[red_number_bar] > 0).mean() == 0
    assert (mask[blue_panel] > 0).mean() == 0


def test_smart_tga_pale_label_sponsor_panel_demotes_from_numbers_to_sponsors():
    n = 512
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 118, 152, 12, 28
    pale_label = np.zeros((n, n), bool)
    pale_label[y0:y0 + 2, x0:x0 + w] = True
    pale_label[y0 + 5:y0 + 7, x0 + 2:x0 + w - 1] = True
    pale_label[y0 + 10:y0 + h, x0 + 4:x0 + w] = True
    pale_label[y0:y0 + h, x0 + 2:x0 + 5] = True
    pale_label[y0 + 2:y0 + 10, x0 + 14:x0 + 16] = True
    pale_label[y0 + 2:y0 + 10, x0 + 24:x0 + 26] = True
    numbers[pale_label] = 255
    rgb[pale_label] = np.array([204, 176, 202], np.uint8)
    rgb[pale_label & (((xx - x0) % 5) == 0)] = np.array([246, 235, 242], np.uint8)
    rgb[pale_label & (((yy - y0) % 4) == 0)] = np.array([80, 50, 84], np.uint8)

    gray_decoy = np.zeros((n, n), bool)
    gy, gx = 178, 152
    gray_decoy[gy:gy + 2, gx:gx + w] = True
    gray_decoy[gy + 5:gy + 7, gx + 2:gx + w - 1] = True
    gray_decoy[gy + 10:gy + h, gx + 4:gx + w] = True
    gray_decoy[gy:gy + h, gx + 2:gx + 5] = True
    gray_decoy[gy + 2:gy + 10, gx + 14:gx + 16] = True
    gray_decoy[gy + 2:gy + 10, gx + 24:gx + 26] = True
    numbers[gray_decoy] = 255
    rgb[gray_decoy] = np.array([122, 122, 122], np.uint8)
    rgb[gray_decoy & (((xx - gx) % 5) == 0)] = np.array([194, 194, 194], np.uint8)
    rgb[gray_decoy & (((yy - gy) % 4) == 0)] = np.array([42, 42, 42], np.uint8)

    red_digit = np.zeros((n, n), bool)
    red_digit[292:360, 286:324] = True
    red_digit[292:308, 286:354] = True
    red_digit[344:360, 286:354] = True
    red_digit[308:344, 324:354] = True
    numbers[red_digit] = 255
    rgb[red_digit] = np.array([230, 42, 40], np.uint8)

    mask, info = car_layers_mod._small_sponsor_panel_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "pale_label_sponsor_panel"
    assert (mask[pale_label] > 0).mean() > 0.95
    assert (mask[gray_decoy] > 0).mean() == 0
    assert (mask[red_digit] > 0).mean() < 0.05


def test_smart_tga_dark_text_logo_sponsor_panel_demotes_from_numbers_to_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([8, 9, 10], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 50, 510, 40, 72
    panel = np.zeros((n, n), bool)
    panel[y0:y0 + h, x0:x0 + w] = True
    interior = np.zeros((n, n), bool)
    interior[y0 + 3:y0 + h - 3, x0 + 3:x0 + w - 3] = True
    holes = interior & (((xx - x0) % 4) < 2) & (((yy - y0) % 5) < 3)
    panel &= ~holes
    numbers[panel] = 255
    rgb[panel] = np.array([91, 102, 57], np.uint8)
    rgb[panel & ((((xx - x0) + (yy - y0)) % 17) < 2)] = np.array([130, 145, 70], np.uint8)
    rgb[panel & (((yy - y0) % 7) < 3)] = np.array([34, 40, 28], np.uint8)
    rgb[panel & (((xx - x0) % 11) < 1)] = np.array([214, 222, 198], np.uint8)

    muted_number_block = np.zeros((n, n), bool)
    by, bx = 140, 510
    muted_number_block[by:by + h, bx:bx + w] = True
    muted_number_block[by + 6:by + h - 6, bx + 12:bx + w - 12] = False
    numbers[muted_number_block] = 255
    rgb[muted_number_block] = np.array([92, 104, 58], np.uint8)

    true_digit = np.zeros((n, n), bool)
    true_digit[520:680, 300:355] = True
    true_digit[520:555, 300:425] = True
    true_digit[645:680, 300:425] = True
    true_digit[555:645, 390:425] = True
    numbers[true_digit] = 255
    rgb[true_digit] = np.array([230, 228, 212], np.uint8)

    mask, info = car_layers_mod._small_sponsor_panel_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "dark_text_logo_sponsor_panel"
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[muted_number_block] > 0).mean() == 0
    assert (mask[true_digit] > 0).mean() < 0.05


def test_smart_tga_darker_thin_textline_demotes_to_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([12, 16, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 118, 152, 19, 72
    textline = np.zeros((n, n), bool)
    for yoff, thickness in ((0, 4), (7, 5), (15, 4)):
        textline[y0 + yoff:y0 + yoff + thickness, x0:x0 + w] = True
    for xoff in range(0, w, 14):
        textline[y0:y0 + h, x0 + xoff:x0 + xoff + 2] = True
    numbers[textline] = 255
    brand[textline] = 255
    rgb[textline] = np.array([0, 74, 94], np.uint8)
    rgb[textline & ((xx - x0) % 9 < 4)] = np.array([0, 138, 178], np.uint8)
    rgb[textline & ((yy - y0) % 7 < 3)] = np.array([0, 26, 36], np.uint8)
    rgb[textline & ((xx - x0) % 23 > 16)] = np.array([14, 190, 220], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[384:474, 392:438] = True
    digit[384:407, 392:486] = True
    digit[451:474, 392:486] = True
    digit[407:451, 438:486] = True
    numbers[digit] = 255
    rgb[digit] = np.array([238, 44, 40], np.uint8)

    mask, info = car_layers_mod._thin_textline_number_false_positive_to_sponsor(
        rgb, numbers, empty, empty, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["dark_frac"] > 0.43
    assert info["components"][0]["dark_limit"] == 0.48
    assert (mask[textline] > 0).mean() > 0.90
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_thin_textline_number_false_positive_demotes_to_sponsors():
    n = 512
    rgb = np.full((n, n, 3), np.array([12, 16, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    textline = (slice(118, 126), slice(152, 188))
    numbers[textline] = 255
    numbers[119:125:2, 156:185:5] = 0
    numbers[118:126:2, 154:186:4] = 0
    rgb[textline] = np.array([42, 86, 206], np.uint8)
    rgb[119:125:2, 155:185] = np.array([236, 238, 242], np.uint8)
    rgb[120:126:3, 158:186] = np.array([30, 34, 44], np.uint8)
    rgb[121:125, 166:170] = np.array([232, 80, 180], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[262:342, 292:332] = True
    digit[262:282, 292:372] = True
    digit[322:342, 292:372] = True
    digit[282:322, 332:372] = True
    numbers[digit] = 255
    rgb[digit] = np.array([238, 44, 40], np.uint8)
    rgb[digit & (np.indices((n, n))[1] > 344)] = np.array([246, 246, 232], np.uint8)

    wider_digit_like = (slice(392, 430), slice(96, 164))
    numbers[wider_digit_like] = 255
    rgb[wider_digit_like] = np.array([236, 38, 34], np.uint8)

    mask, info = car_layers_mod._thin_textline_number_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert (mask[textline] > 0).mean() > 0.80
    assert (mask[digit] > 0).mean() < 0.05
    assert (mask[wider_digit_like] > 0).mean() == 0


def test_smart_tga_shallow_wordmark_number_false_positive_demotes_to_sponsor():
    n = 512
    rgb = np.full((n, n, 3), np.array([12, 15, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    shallow_wordmark = (slice(120, 143), slice(150, 240))
    numbers[shallow_wordmark] = 255
    rgb[shallow_wordmark] = np.array([220, 78, 64], np.uint8)
    for x in range(154, 236, 6):
        rgb[121:142, x:x + 2] = np.array([242, 242, 230], np.uint8)
        rgb[122:141, x + 3:x + 5] = np.array([30, 54, 178], np.uint8)

    smooth_wide_number_bar = (slice(200, 223), slice(150, 240))
    numbers[smooth_wide_number_bar] = 255
    rgb[smooth_wide_number_bar] = np.array([224, 48, 40], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[294:374, 292:332] = True
    digit[294:314, 292:372] = True
    digit[354:374, 292:372] = True
    digit[314:354, 332:372] = True
    numbers[digit] = 255
    rgb[digit] = np.array([238, 44, 40], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "wide_wordmark_logo_strip"
    assert info["components"][0]["aspect"] < 4.25
    assert (mask[shallow_wordmark] > 0).mean() > 0.95
    assert (mask[smooth_wide_number_bar] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_wide_script_sponsor_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 18, 35], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 324, 73, 59, 212
    script_wordmark = np.zeros((n, n), bool)
    for yoff in (3, 17, 31, 45):
        script_wordmark[y0 + yoff:y0 + yoff + 8, x0:x0 + w] = True
    for xoff in (18, 52, 88, 126, 162, 194):
        script_wordmark[y0:y0 + h, x0 + xoff:x0 + xoff + 6] = True
    numbers[script_wordmark] = 255
    rgb[script_wordmark] = np.array([222, 35, 44], np.uint8)
    rgb[script_wordmark & ((xx - x0) % 9 < 4)] = np.array([240, 236, 230], np.uint8)

    smooth_wide_number_bar = (slice(470, 529), slice(73, 285))
    numbers[smooth_wide_number_bar] = 255
    rgb[smooth_wide_number_bar] = np.array([225, 45, 42], np.uint8)
    rgb[470:529, 73:91] = np.array([246, 246, 238], np.uint8)

    true_number = np.zeros((n, n), bool)
    true_number[660:778, 395:454] = True
    true_number[660:684, 395:500] = True
    true_number[754:778, 395:500] = True
    true_number[684:754, 454:500] = True
    numbers[true_number] = 255
    rgb[true_number] = np.array([235, 42, 45], np.uint8)
    rgb[true_number & ((xx - 395) % 13 < 4)] = np.array([244, 242, 235], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "wide_script_sponsor_wordmark"
    assert (mask[script_wordmark] > 0).mean() > 0.90
    assert (mask[smooth_wide_number_bar] > 0).mean() == 0
    assert (mask[true_number] > 0).mean() < 0.05


def test_smart_tga_shallow_green_white_script_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([12, 16, 14], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_script_wordmark(y0, x0, protect=False, textured=True):
        h, w = 31, 288
        ly, lx = np.indices((h, w))
        local = np.ones((h, w), bool)
        local &= ~(((lx % 31) >= 15) & (ly > 4) & (ly < h - 5))
        local &= ~((((lx + 2 * ly) % 53) < 2) & (ly > 3) & (ly < h - 4))
        patch = np.zeros((n, n), bool)
        patch[y0:y0 + h, x0:x0 + w] = local
        numbers[patch] = 255
        if protect:
            template[patch] = 255

        roi = rgb[y0:y0 + h, x0:x0 + w]
        roi[local] = np.array([110, 116, 110], np.uint8)
        if textured:
            white = local & ((lx % 24) < 6)
            dark = local & ~white & (((lx + 11) % 18) < 5)
            green = local & ~white & ~dark & (((lx + ly) % 5) < 3)
            roi[white] = np.array([238, 238, 230], np.uint8)
            roi[dark] = np.array([30, 34, 30], np.uint8)
            roi[green] = np.array([38, 178, 42], np.uint8)
        return patch

    wordmark = add_script_wordmark(128, 100)
    smooth_low_fill_bar = add_script_wordmark(230, 100, textured=False)
    protected_wordmark = add_script_wordmark(332, 100, protect=True)

    true_number = np.zeros((n, n), bool)
    true_number[560:654, 420:486] = True
    true_number[560:584, 420:542] = True
    true_number[630:654, 420:542] = True
    true_number[584:630, 486:542] = True
    numbers[true_number] = 255
    rgb[true_number] = np.array([238, 238, 232], np.uint8)
    rgb[true_number & ((np.indices((n, n))[1] - 420) % 15 < 4)] = np.array([42, 178, 44], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert any(
        component["reason"] == "shallow_green_white_script_sponsor_wordmark"
        for component in info["components"]
    )
    assert (mask[wordmark] > 0).mean() > 0.92
    assert (mask[smooth_low_fill_bar] > 0).mean() == 0
    assert (mask[protected_wordmark] > 0).mean() == 0
    assert (mask[true_number] > 0).mean() < 0.05


def test_smart_tga_large_red_white_sponsor_billboard_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([16, 20, 34], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 104, 45, 63, 283
    billboard = (slice(y0, y0 + h), slice(x0, x0 + w))
    numbers[billboard] = 255
    rgb[billboard] = np.array([208, 45, 52], np.uint8)
    rgb[y0:y0 + 2, x0:x0 + w] = np.array([58, 36, 45], np.uint8)
    rgb[y0 + h - 2:y0 + h, x0:x0 + w] = np.array([58, 36, 45], np.uint8)
    rgb[y0:y0 + h, x0:x0 + 2] = np.array([58, 36, 45], np.uint8)
    rgb[y0:y0 + h, x0 + w - 2:x0 + w] = np.array([58, 36, 45], np.uint8)
    for row_y in (10, 36):
        for xoff in range(28, 246, 22):
            rgb[y0 + row_y:y0 + row_y + 18, x0 + xoff:x0 + xoff + 15] = np.array([246, 242, 232], np.uint8)
            rgb[y0 + row_y + 3:y0 + row_y + 15, x0 + xoff + 6:x0 + xoff + 8] = np.array([208, 45, 52], np.uint8)
            rgb[y0 + row_y + 5:y0 + row_y + 13, x0 + xoff + 11:x0 + xoff + 12] = np.array([208, 45, 52], np.uint8)
            rgb[y0 + row_y + 9:y0 + row_y + 10, x0 + xoff + 1:x0 + xoff + 14] = np.array([208, 45, 52], np.uint8)

    smooth_number_plate = (slice(260, 323), slice(45, 328))
    numbers[smooth_number_plate] = 255
    rgb[smooth_number_plate] = np.array([210, 44, 50], np.uint8)
    rgb[270:313, 88:132] = np.array([244, 242, 235], np.uint8)
    rgb[270:313, 206:250] = np.array([244, 242, 235], np.uint8)

    pale_panel = (slice(430, 493), slice(45, 328))
    numbers[pale_panel] = 255
    rgb[pale_panel] = np.array([236, 232, 214], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "large_red_white_sponsor_billboard"
    assert info["components"][0]["white_text_components"] >= 10
    assert (mask[billboard] > 0).mean() > 0.95
    assert (mask[smooth_number_plate] > 0).mean() == 0
    assert (mask[pale_panel] > 0).mean() == 0


def test_smart_tga_large_multicolor_sponsor_billboard_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([16, 20, 34], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 216, 33, 95, 127
    billboard = (slice(y0, y0 + h), slice(x0, x0 + w))
    ly, lx = np.indices((h, w))
    local = np.ones((h, w), bool)
    holes = ((lx * 7 + ly * 11) % 17 < 5) & (lx > 4) & (lx < w - 5) & (ly > 4) & (ly < h - 5)
    local &= ~holes
    local[:2, :] = True
    local[-2:, :] = True
    local[:, :2] = True
    local[:, -2:] = True
    numbers_roi = numbers[billboard]
    rgb_roi = rgb[billboard]
    numbers_roi[local] = 255

    palette = (
        np.array([205, 44, 42], np.uint8),
        np.array([188, 86, 44], np.uint8),
        np.array([58, 158, 64], np.uint8),
        np.array([226, 160, 42], np.uint8),
    )
    for cy in range(0, h, 12):
        for cx in range(0, w, 13):
            block = local & (ly >= cy) & (ly < cy + 12) & (lx >= cx) & (lx < cx + 13)
            rgb_roi[block] = palette[((cy // 12) + (cx // 13)) % len(palette)]
    separator = local & (((lx % 13) < 2) | ((ly % 12) < 2))
    rgb_roi[separator] = np.array([160, 154, 144], np.uint8)
    for cy, cx in ((10, 14), (10, 72), (35, 30), (35, 88), (63, 18), (63, 76)):
        block = local & (ly >= cy) & (ly < cy + 16) & (lx >= cx) & (lx < cx + 25)
        rgb_roi[block] = np.array([244, 238, 222], np.uint8)
    for cy in (25, 52, 78):
        for cx in (12, 40, 68, 96):
            block = local & (ly >= cy) & (ly < cy + 7) & (lx >= cx) & (lx < cx + 9)
            rgb_roi[block] = np.array([106, 98, 88], np.uint8)

    smooth_number_plate = (slice(360, 455), slice(40, 167))
    numbers[smooth_number_plate] = 255
    rgb[smooth_number_plate] = np.array([176, 86, 50], np.uint8)
    rgb[382:430, 70:96] = np.array([244, 238, 222], np.uint8)
    rgb[382:430, 112:138] = np.array([244, 238, 222], np.uint8)

    true_number = (slice(560, 655), slice(40, 167))
    yy, xx = np.indices((95, 127))
    digit_pair = (
        ((xx - 41) ** 2 / float(18 ** 2) + (yy - 48) ** 2 / float(39 ** 2) < 1.0)
        | ((xx - 86) ** 2 / float(18 ** 2) + (yy - 48) ** 2 / float(39 ** 2) < 1.0)
    )
    numbers[true_number][digit_pair] = 255
    rgb[true_number][digit_pair] = np.array([244, 238, 222], np.uint8)
    rgb[true_number][digit_pair & ((xx % 9) < 3)] = np.array([205, 44, 42], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "large_multicolor_sponsor_billboard"
    assert info["components"][0]["colored_text_components"] >= 14
    assert (mask[billboard][local] > 0).mean() > 0.95
    assert (mask[smooth_number_plate] > 0).mean() == 0
    assert (mask[true_number] > 0).mean() < 0.05


def test_smart_tga_left_edge_pale_purple_product_panel_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([30, 31, 35], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_product_panel(y0, x0, *, protected=False, colored=True):
        h, w = 145, 179
        ly, lx = np.indices((h, w))
        local = np.ones((h, w), bool)
        local &= ~(((lx % 31) > 28) & (ly > 8) & (ly < h - 8))
        local &= ~(((lx % 43) > 38) & (ly > 12) & (ly < h - 12))
        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w] = local
        numbers[panel] = 255
        if protected:
            template[panel] = 255

        roi = rgb[y0:y0 + h, x0:x0 + w]
        base = np.array([92, 48, 150], np.uint8) if colored else np.array([220, 220, 216], np.uint8)
        roi[local] = base
        if colored:
            for row_y in (12, 43, 74, 105):
                for col_x in (8, 48, 88, 128):
                    block = local & (ly >= row_y) & (ly < row_y + 26) & (lx >= col_x) & (lx < col_x + 38)
                    roi[block] = np.array([242, 240, 232], np.uint8)
                    dark = block & (ly == row_y + 10) & (lx >= col_x + 6) & (lx < col_x + 24)
                    roi[dark] = np.array([34, 30, 42], np.uint8)
        return panel

    product_panel = add_product_panel(158, 0)
    centered_panel = add_product_panel(158, 250)
    grayscale_panel = add_product_panel(520, 0, colored=False)
    protected_panel = add_product_panel(330, 0, protected=True)

    yy, xx = np.indices((n, n))
    red_number = np.zeros((n, n), bool)
    outer_left = ((xx - 142) / 63.0) ** 2 + ((yy - 762) / 71.0) ** 2 <= 1.0
    outer_right = ((xx - 222) / 55.0) ** 2 + ((yy - 762) / 70.0) ** 2 <= 1.0
    inner_left = ((xx - 142) / 40.0) ** 2 + ((yy - 762) / 45.0) ** 2 <= 1.0
    inner_right = ((xx - 222) / 34.0) ** 2 + ((yy - 762) / 45.0) ** 2 <= 1.0
    red_number |= (outer_left & ~inner_left) | (outer_right & ~inner_right)
    numbers[red_number] = 255
    rgb[red_number] = np.array([236, 42, 52], np.uint8)
    rgb[red_number & (xx % 13 < 5)] = np.array([246, 242, 236], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert sum(
        component["reason"] == "left_edge_pale_purple_sponsor_product_panel"
        for component in info["components"]
    ) == 1
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "left_edge_pale_purple_sponsor_product_panel"
    )
    assert component["colored_frac"] >= 0.25
    assert component["red_frac"] <= 0.035
    assert (mask[product_panel] > 0).mean() > 0.92
    assert (mask[centered_panel] > 0).mean() == 0
    assert (mask[grayscale_panel] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0
    assert (mask[red_number] > 0).mean() == 0


def test_smart_tga_top_right_white_contingency_logo_stack_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([24, 24, 28], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_contingency_stack(y0, x0, *, with_sponsor_context=True, protected=False):
        h, w = 155, 163
        ly, lx = np.indices((h, w))
        local = np.zeros((h, w), bool)
        scaffold = ((lx % 34) == 0) | ((ly % 37) == 0)
        scaffold |= ((lx > 8) & (lx < w - 8) & ((ly == 8) | (ly == h - 9)))
        scaffold |= ((ly > 8) & (ly < h - 8) & ((lx == 8) | (lx == w - 9)))
        local |= scaffold
        roi = rgb[y0:y0 + h, x0:x0 + w]
        roi[scaffold] = np.array([154, 154, 158], np.uint8)

        for row_y in (13, 44, 75, 106):
            for col_x in (14, 52, 90, 126):
                logo = (ly >= row_y) & (ly < row_y + 24) & (lx >= col_x) & (lx < col_x + 24)
                local |= logo
                roi[logo] = np.array([244, 244, 240], np.uint8)
                cut = (
                    (ly >= row_y + 7)
                    & (ly < row_y + 11)
                    & (lx >= col_x + 5)
                    & (lx < col_x + 19)
                )
                local |= cut
                roi[cut] = np.array([42, 42, 46], np.uint8)

        for row_y, col_x in ((23, 42), (54, 118), (88, 42), (119, 118)):
            mark = (ly >= row_y) & (ly < row_y + 14) & (lx >= col_x) & (lx < col_x + 30)
            local |= mark
            roi[mark] = np.array([244, 244, 240], np.uint8)
            slit = mark & (ly >= row_y + 5) & (ly < row_y + 8)
            roi[slit] = np.array([42, 42, 46], np.uint8)
        for row_y, col_x in ((3, 3), (3, 132), (142, 3), (142, 132)):
            mark = (ly >= row_y) & (ly < row_y + 10) & (lx >= col_x) & (lx < col_x + 28)
            local |= mark
            roi[mark] = np.array([244, 244, 240], np.uint8)
        for row_y, col_x in ((5, 3), (146, 140)):
            mark = (ly >= row_y) & (ly < row_y + 2) & (lx >= col_x) & (lx < col_x + 20)
            local |= mark
            roi[mark] = np.array([42, 42, 46], np.uint8)

        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w] = local
        numbers[panel] = 255
        if protected:
            template[panel] = 255
        if with_sponsor_context:
            sponsors[max(0, y0 - 24):max(0, y0 - 8), x0 + 34:x0 + 130] = 255
            sponsors[y0 + 82:y0 + h, x0 - 18:x0 - 11] = 255
            sponsors[y0 + 74:y0 + h, x0 - 3:x0] = 255
            sponsors[y0 + h + 1:y0 + h + 24, x0 + 24:x0 + 146] = 255
        return panel

    target_panel = add_contingency_stack(28, 861)
    no_context_panel = add_contingency_stack(28, 610, with_sponsor_context=False)
    protected_panel = add_contingency_stack(220, 861, protected=True)

    yy, xx = np.indices((n, n))
    smooth_number = (
        ((xx - 930) / 70.0) ** 2 + ((yy - 520) / 68.0) ** 2 <= 1.0
    ) | (
        ((xx - 930) / 42.0) ** 2 + ((yy - 520) / 40.0) ** 2 <= 1.0
    )
    smooth_number &= ~(((xx - 930) / 38.0) ** 2 + ((yy - 520) / 35.0) ** 2 <= 1.0)
    numbers[smooth_number] = 255
    rgb[smooth_number] = np.array([236, 236, 232], np.uint8)
    rgb[smooth_number & (xx % 29 < 6)] = np.array([82, 82, 86], np.uint8)
    sponsors[608:635, 816:840] = 255

    red_number = (
        (((xx - 170) / 62.0) ** 2 + ((yy - 172) / 68.0) ** 2 <= 1.0)
        | (((xx - 260) / 58.0) ** 2 + ((yy - 172) / 68.0) ** 2 <= 1.0)
    )
    red_number &= ~(
        (((xx - 170) / 38.0) ** 2 + ((yy - 172) / 42.0) ** 2 <= 1.0)
        | (((xx - 260) / 35.0) ** 2 + ((yy - 172) / 42.0) ** 2 <= 1.0)
    )
    numbers[red_number] = 255
    rgb[red_number] = np.array([238, 46, 60], np.uint8)
    rgb[red_number & (xx % 15 < 5)] = np.array([246, 244, 236], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert sum(
        component["reason"] == "top_right_white_contingency_logo_stack"
        for component in info["components"]
    ) == 1
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "top_right_white_contingency_logo_stack"
    )
    assert component["broad_near_sponsor"] >= 0.55
    assert component["white_text_components"] >= 10
    assert component["colored_text_components"] == 0
    assert (mask[target_panel] > 0).mean() > 0.82
    assert (mask[no_context_panel] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0
    assert (mask[smooth_number] > 0).mean() == 0
    assert (mask[red_number] > 0).mean() == 0


def test_smart_tga_top_right_dense_white_contingency_logo_stack_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([26, 26, 30], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_dense_stack(y0, x0, *, with_sponsor_context=True, protected=False):
        h, w = 155, 159
        ly, lx = np.indices((h, w))
        local = np.zeros((h, w), bool)
        roi = rgb[y0:y0 + h, x0:x0 + w]

        scaffold = (
            ((lx % 32) == 0)
            | ((ly % 31) == 0)
            | ((lx == 7) | (lx == w - 8))
            | ((ly == 7) | (ly == h - 8))
            | (lx == 0)
            | (lx == w - 1)
            | (ly == 0)
            | (ly == h - 1)
        )
        local |= scaffold
        roi[scaffold] = np.array([156, 156, 156], np.uint8)

        for row_y in (12, 43, 74, 105):
            for col_x in (12, 49, 86, 123):
                white = (
                    (ly >= row_y)
                    & (ly < row_y + 24)
                    & (lx >= col_x)
                    & (lx < col_x + 25)
                )
                dark = (
                    (ly >= row_y + 8)
                    & (ly < row_y + 12)
                    & (lx >= col_x + 5)
                    & (lx < col_x + 21)
                )
                local |= white | dark
                roi[white] = np.array([244, 244, 244], np.uint8)
                roi[dark] = np.array([84, 84, 84], np.uint8)

        for row_y, col_x in (
            (132, 12), (132, 49), (132, 86), (132, 123),
            (22, 31), (53, 68), (84, 31), (115, 68),
            (24, 101), (55, 18), (86, 101), (117, 18),
        ):
            mark = (
                (ly >= row_y)
                & (ly < row_y + 10)
                & (lx >= col_x)
                & (lx < min(w - 3, col_x + 31))
            )
            dark = mark & (ly >= row_y + 4) & (ly < row_y + 6)
            local |= mark | dark
            roi[mark] = np.array([244, 244, 244], np.uint8)
            roi[dark] = np.array([84, 84, 84], np.uint8)

        for row_y, col_x in ((0, 4), (0, 132), (145, 4), (145, 132)):
            mark = (
                (ly >= row_y)
                & (ly < row_y + 10)
                & (lx >= col_x)
                & (lx < min(w, col_x + 23))
            )
            local |= mark
            roi[mark] = np.array([244, 244, 244], np.uint8)

        for row_y, col_x in (
            (3, 3), (3, 31), (3, 101), (3, 133),
            (148, 3), (148, 31), (148, 101), (148, 133),
        ):
            dark = (
                (ly >= row_y)
                & (ly < row_y + 4)
                & (lx >= col_x)
                & (lx < min(w, col_x + 23))
            )
            local |= dark
            roi[dark] = np.array([42, 42, 42], np.uint8)

        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w] = local
        numbers[panel] = 255
        if protected:
            template[panel] = 255
        if with_sponsor_context:
            sponsors[y0 + 26:y0 + h, x0 - 14:x0 - 6] = 255
            sponsors[y0 + 40:y0 + h, x0 - 4:x0 - 1] = 255
            sponsors[y0 + 24:y0 + h - 8, x0:x0 + 10] = 255
            sponsors[y0 + h + 1:y0 + h + 20, x0 + 14:x0 + 148] = 255
            sponsors[max(0, y0 - 18):max(0, y0 - 7), x0 + 42:x0 + 130] = 255
        return panel

    target_panel = add_dense_stack(28, 865)
    no_context_panel = add_dense_stack(28, 610, with_sponsor_context=False)
    protected_panel = add_dense_stack(222, 865, protected=True)

    yy, xx = np.indices((n, n))
    smooth_number = (
        ((xx - 930) / 70.0) ** 2 + ((yy - 526) / 69.0) ** 2 <= 1.0
    ) | (
        ((xx - 930) / 44.0) ** 2 + ((yy - 526) / 41.0) ** 2 <= 1.0
    )
    smooth_number &= ~(((xx - 930) / 38.0) ** 2 + ((yy - 526) / 35.0) ** 2 <= 1.0)
    numbers[smooth_number] = 255
    rgb[smooth_number] = np.array([236, 236, 232], np.uint8)
    rgb[smooth_number & (xx % 31 < 5)] = np.array([82, 82, 86], np.uint8)
    sponsors[612:634, 812:840] = 255

    red_number = (
        (((xx - 172) / 62.0) ** 2 + ((yy - 172) / 68.0) ** 2 <= 1.0)
        | (((xx - 262) / 58.0) ** 2 + ((yy - 172) / 68.0) ** 2 <= 1.0)
    )
    red_number &= ~(
        (((xx - 172) / 38.0) ** 2 + ((yy - 172) / 42.0) ** 2 <= 1.0)
        | (((xx - 262) / 35.0) ** 2 + ((yy - 172) / 42.0) ** 2 <= 1.0)
    )
    numbers[red_number] = 255
    rgb[red_number] = np.array([238, 46, 60], np.uint8)
    rgb[red_number & (xx % 15 < 5)] = np.array([246, 244, 236], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert sum(
        component["reason"] == "top_right_dense_white_contingency_logo_stack"
        for component in info["components"]
    ) == 1
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "top_right_dense_white_contingency_logo_stack"
    )
    assert component["near_sponsor"] >= 0.12
    assert component["broad_near_sponsor"] >= 0.72
    assert component["white_text_components"] >= 14
    assert component["dark_text_components"] >= 18
    assert component["colored_text_components"] == 0
    assert (mask[target_panel] > 0).mean() > 0.82
    assert (mask[no_context_panel] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0
    assert (mask[smooth_number] > 0).mean() == 0
    assert (mask[red_number] > 0).mean() == 0


def test_smart_tga_stacked_white_sponsor_logo_panel_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 34, 38], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_logo_stack(y0, x0, *, with_sponsor_context=True, protected=False):
        h, w = 106, 161
        ly, lx = np.indices((h, w))
        local = np.zeros((h, w), bool)
        scaffold = ((lx % 23) == 0) | ((ly % 19) == 0)
        scaffold |= ((lx % 31) == 1) & (ly > 10) & (ly < h - 10)
        scaffold |= ((lx % 17) == 3) & (ly > 8) & (ly < h - 8)
        scaffold |= ((ly % 29) == 3) & (lx > 8) & (lx < w - 8)
        scaffold |= ((ly > 8) & (ly < h - 8) & ((lx == 8) | (lx == w - 9)))
        scaffold |= ((lx > 8) & (lx < w - 8) & ((ly == 8) | (ly == h - 9)))
        local |= scaffold
        roi = rgb[y0:y0 + h, x0:x0 + w]
        roi[scaffold] = np.array([154, 154, 160], np.uint8)

        for row_y in (10, 31, 52, 73, 92):
            for col_x in (12, 38, 64, 90, 116, 138):
                white = (ly >= row_y) & (ly < row_y + 13) & (lx >= col_x) & (lx < col_x + 17)
                dark = (ly >= row_y + 4) & (ly < row_y + 7) & (lx >= col_x + 5) & (lx < col_x + 13)
                local |= white | dark
                roi[white] = np.array([244, 242, 236], np.uint8)
                roi[dark] = np.array([42, 42, 48], np.uint8)
        for row_y, col_x in ((4, 70), (100, 70)):
            dark = (ly >= row_y) & (ly < row_y + 5) & (lx >= col_x) & (lx < col_x + 21)
            local |= dark
            roi[dark] = np.array([42, 42, 48], np.uint8)
        for row_y, col_x in (
            (14, 4), (14, 136),
            (26, 18), (26, 108), (47, 34), (47, 96),
            (68, 18), (68, 110), (90, 42), (90, 102),
            (94, 4), (94, 136),
        ):
            accent = (ly >= row_y) & (ly < row_y + 6) & (lx >= col_x) & (lx < col_x + 17)
            local |= accent
            roi[accent] = np.array([196, 62, 88], np.uint8)

        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w] = local
        numbers[panel] = 255
        if protected:
            template[panel] = 255
        if with_sponsor_context:
            sponsor_roi = sponsors[y0:y0 + h, x0:x0 + w]
            sponsor_roi[~local] = 255
            sponsors[y0 - 12:y0 + h + 12, x0 - 20:x0 - 7] = 255
            sponsors[y0 - 10:y0 + h + 10, x0 + w + 7:x0 + w + 20] = 255
        return panel

    target_panel = add_logo_stack(720, 445)
    no_context_panel = add_logo_stack(720, 70, with_sponsor_context=False)
    protected_panel = add_logo_stack(510, 445, protected=True)

    red_number = np.zeros((n, n), bool)
    yy, xx = np.indices((n, n))
    outer_left = ((xx - 188) / 56.0) ** 2 + ((yy - 248) / 64.0) ** 2 <= 1.0
    outer_right = ((xx - 278) / 54.0) ** 2 + ((yy - 248) / 64.0) ** 2 <= 1.0
    inner_left = ((xx - 188) / 34.0) ** 2 + ((yy - 248) / 39.0) ** 2 <= 1.0
    inner_right = ((xx - 278) / 33.0) ** 2 + ((yy - 248) / 39.0) ** 2 <= 1.0
    red_number |= (outer_left & ~inner_left) | (outer_right & ~inner_right)
    numbers[red_number] = 255
    rgb[red_number] = np.array([234, 42, 58], np.uint8)
    rgb[red_number & (xx % 17 < 5)] = np.array([246, 242, 236], np.uint8)

    smooth_gray_number = (slice(318, 424), slice(70, 231))
    numbers[smooth_gray_number] = 255
    rgb[smooth_gray_number] = np.array([218, 220, 220], np.uint8)
    rgb[352:394, 94:130] = np.array([54, 54, 58], np.uint8)
    rgb[352:394, 170:206] = np.array([54, 54, 58], np.uint8)
    sponsors[315:427, 45:62] = 255
    sponsors[315:427, 240:258] = 255

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert sum(
        component["reason"] == "stacked_white_sponsor_logo_panel"
        for component in info["components"]
    ) == 1
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "stacked_white_sponsor_logo_panel"
    )
    assert component["near_sponsor"] >= 0.55
    assert component["white_text_components"] >= 22
    assert component["dark_text_components"] >= 15
    assert (mask[target_panel] > 0).mean() > 0.80
    assert (mask[no_context_panel] > 0).mean() == 0
    assert (mask[protected_panel] > 0).mean() == 0
    assert (mask[red_number] > 0).mean() == 0
    assert (mask[smooth_gray_number] > 0).mean() == 0


def test_smart_tga_green_red_sponsor_logo_panel_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 24, 28], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_panel(y0, x0, h, w, vertical=False, protected=False):
        local = np.zeros((h, w), bool)
        ly, lx = np.indices((h, w))
        roi = rgb[y0:y0 + h, x0:x0 + w]
        grid = (((lx * 3 + ly * 5) % 11) < 5) | ((lx % 19) < 1) | ((ly % 23) < 1)
        local |= grid
        if vertical:
            green_region = (ly < h * 0.38) | (ly > h * 0.68)
            red_region = (ly >= h * 0.38) & (ly <= h * 0.60)
            yellow_region = (ly > h * 0.60) & (ly <= h * 0.68)
        else:
            green_region = (lx < w * 0.42) | (lx > w * 0.70)
            red_region = (lx >= w * 0.42) & (lx <= w * 0.60)
            yellow_region = (lx > w * 0.60) & (lx <= w * 0.70)
        roi[local & green_region] = np.array([82, 168, 45], np.uint8)
        roi[local & red_region] = np.array([226, 42, 48], np.uint8)
        roi[local & yellow_region] = np.array([220, 178, 38], np.uint8)
        roi[local & ~(green_region | red_region | yellow_region)] = np.array([124, 210, 64], np.uint8)
        glyphs = (
            (12, 10), (24, 22), (38, 12), (15, 58), (34, 70),
            (56, 114), (27, 121), (48, 130), (61, 24), (8, 96),
        )
        for k, (gy, gx) in enumerate(glyphs):
            gy = min(h - 12, gy)
            gx = min(w - 12, gx)
            glyph = (ly >= gy) & (ly < gy + 8) & (lx >= gx) & (lx < gx + 11)
            roi[glyph] = np.array([246, 244, 236], np.uint8)
            local |= glyph
            stroke = (ly >= gy + 3) & (ly < gy + 9) & (lx >= gx + 13) & (lx < gx + 15)
            if gx + 15 < w:
                roi[stroke] = np.array([50, 82, 48], np.uint8)
                local |= stroke
        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w] = local
        numbers[panel] = 255
        if protected:
            template[panel] = 255
        return panel

    wide_panel = add_panel(112, 60, 84, 152)
    protected_panel = add_panel(424, 60, 84, 152, protected=True)

    smooth_color_number = (slice(650, 734), slice(60, 212))
    numbers[smooth_color_number] = 255
    rgb[smooth_color_number] = np.array([42, 192, 40], np.uint8)
    rgb[650:734, 112:160] = np.array([226, 42, 48], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert {component["reason"] for component in info["components"]} == {
        "green_red_sponsor_logo_panel",
    }
    assert (mask[wide_panel] > 0).mean() > 0.92
    assert (mask[protected_panel] > 0).mean() == 0
    assert (mask[smooth_color_number] > 0).mean() == 0


def test_smart_tga_large_warm_flame_script_sponsor_logo_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 22, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_flame_logo(y0, x0, h, w):
        ly, lx = np.indices((h, w))
        center = h * 0.52 + np.sin(lx / max(6.0, w * 0.090)) * h * 0.10
        local = np.abs(ly - center) <= h * 0.30
        local[:, :2] = True
        local[:, w - 2:] = True
        patch = np.zeros((n, n), bool)
        patch[y0:y0 + h, x0:x0 + w][local] = True
        numbers[patch] = 255

        warm_rgb = np.zeros((h, w, 3), np.uint8)
        warm_rgb[local] = np.array([216, 58, 42], np.uint8)
        warm_rgb[local & (lx < w * 0.45) & (ly < center + h * 0.04)] = np.array([246, 186, 50], np.uint8)
        warm_rgb[local & (lx > w * 0.72)] = np.array([224, 98, 48], np.uint8)
        warm_rgb[local & (lx < w * 0.58) & (ly < center + h * 0.12)] = np.array([248, 188, 42], np.uint8)

        split = local & (np.abs(lx - w * 0.52) <= max(2, int(round(w * 0.010))))
        warm_rgb[split] = np.array([246, 242, 228], np.uint8)
        cols = np.linspace(max(6, int(w * 0.07)), min(w - 12, int(w * 0.88)), 6, dtype=int)
        rows = np.linspace(max(3, int(h * 0.08)), min(h - 12, int(h * 0.82)), 4, dtype=int)
        for cy in rows:
            for cx in cols:
                block = local & (lx >= cx) & (lx < cx + max(10, int(w * 0.085))) & (ly >= cy) & (ly < cy + max(9, int(h * 0.190)))
                warm_rgb[block] = np.array([246, 242, 228], np.uint8)
                warm_rgb[
                    block
                    & (lx >= cx + max(2, int(w * 0.018)))
                    & (lx < cx + max(4, int(w * 0.026)))
                ] = np.array([126, 72, 28], np.uint8)
                warm_rgb[
                    block
                    & (ly >= cy + max(3, int(h * 0.060)))
                    & (ly < cy + max(4, int(h * 0.075)))
                ] = np.array([126, 72, 28], np.uint8)
        for xline in np.linspace(max(4, int(w * 0.12)), min(w - 5, int(w * 0.92)), 9, dtype=int):
            vein = local & (np.abs(lx - xline) <= max(1, int(round(w * 0.006))))
            vein &= (ly > center - h * 0.24) & (ly < center + h * 0.24)
            warm_rgb[vein] = np.array([118, 60, 24], np.uint8)
        if h > w:
            narrow_red = local & (lx > w * 0.56) & (ly > center - h * 0.20) & (ly < center + h * 0.22)
            narrow_yellow = local & (lx < w * 0.48) & (ly > center - h * 0.22) & (ly < center + h * 0.18)
            warm_rgb[narrow_red] = np.array([224, 70, 42], np.uint8)
            warm_rgb[narrow_yellow] = np.array([248, 188, 42], np.uint8)
            for cy in np.linspace(max(4, int(h * 0.12)), min(h - 8, int(h * 0.82)), 5, dtype=int):
                left_glyph = local & (lx >= int(w * 0.12)) & (lx < int(w * 0.32)) & (ly >= cy) & (ly < cy + max(5, int(h * 0.060)))
                right_glyph = local & (lx >= int(w * 0.66)) & (lx < int(w * 0.84)) & (ly >= cy) & (ly < cy + max(5, int(h * 0.060)))
                warm_rgb[left_glyph | right_glyph] = np.array([246, 242, 228], np.uint8)
            for cy in np.linspace(max(5, int(h * 0.18)), min(h - 6, int(h * 0.78)), 6, dtype=int):
                shadow = local & (lx >= int(w * 0.14)) & (lx < int(w * 0.86)) & (ly >= cy) & (ly < cy + 1)
                warm_rgb[shadow] = np.array([78, 54, 30], np.uint8)
        split = local & (np.abs(lx - w * 0.52) <= max(3, int(round(w * 0.014))))
        warm_rgb[split] = np.array([246, 242, 228], np.uint8)

        roi = rgb[y0:y0 + h, x0:x0 + w]
        roi[local] = warm_rgb[local]
        return patch

    wide_logo = add_flame_logo(120, 255, 88, 339)
    tall_logo = add_flame_logo(456, 388, 112, 87)
    mid_logo = add_flame_logo(554, 696, 63, 235)

    smooth_plate = (slice(730, 818), slice(255, 594))
    numbers[smooth_plate] = 255
    rgb[smooth_plate] = np.array([226, 62, 36], np.uint8)
    rgb[730:770, 255:414] = np.array([246, 188, 54], np.uint8)
    rgb[778:798, 302:522] = np.array([246, 242, 228], np.uint8)

    true_number = np.zeros((n, n), bool)
    true_number[270:386, 120:172] = True
    true_number[270:296, 120:228] = True
    true_number[360:386, 120:228] = True
    true_number[296:360, 176:228] = True
    numbers[true_number] = 255
    rgb[true_number] = np.array([230, 52, 42], np.uint8)
    rgb[true_number & ((np.indices((n, n))[1] - 120) % 16 < 5)] = np.array([245, 242, 230], np.uint8)

    dark_badge = (slice(860, 948), slice(80, 260))
    numbers[dark_badge] = 255
    rgb[dark_badge] = np.array([48, 45, 42], np.uint8)
    rgb[878:930, 118:220] = np.array([112, 70, 48], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert {component["reason"] for component in info["components"]} == {
        "large_warm_flame_script_sponsor_logo",
    }
    assert all(component["yellow_frac"] >= 0.18 for component in info["components"])
    assert all(component["white_text_components"] >= 12 for component in info["components"])
    assert (mask[wide_logo] > 0).mean() > 0.90
    assert (mask[tall_logo] > 0).mean() > 0.90
    assert (mask[mid_logo] > 0).mean() > 0.90
    assert (mask[smooth_plate] > 0).mean() == 0
    assert (mask[true_number] > 0).mean() < 0.05
    assert (mask[dark_badge] > 0).mean() == 0


def test_smart_tga_large_cool_event_badge_sponsor_logo_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 323, 519, 141, 246
    ly, lx = np.indices((h, w))
    center = 70 + 0.23 * (lx - (w / 2.0))
    local = np.abs(ly - center) <= 44
    event_badge = np.zeros((n, n), bool)
    event_badge[y0:y0 + h, x0:x0 + w][local] = True
    numbers[event_badge] = 255
    roi = rgb[y0:y0 + h, x0:x0 + w]
    roi[local] = np.array([110, 76, 158], np.uint8)

    for row in range(6):
        for col in range(10):
            yy = 3 + row * 22
            xx = 3 + col * 23
            block = (ly >= yy) & (ly < yy + 18) & (lx >= xx) & (lx < xx + 20) & local
            roi[block] = np.array([30, 24, 54], np.uint8)

    for row in range(5):
        for col in range(9):
            yy = 15 + row * 24
            xx = 14 + col * 25
            block = (ly >= yy) & (ly < yy + 11) & (lx >= xx) & (lx < xx + 13) & local
            roi[block] = np.array([238, 238, 232], np.uint8)

    for row in range(4):
        for col in range(7):
            yy = 30 + row * 24
            xx = 28 + col * 31
            block = (ly >= yy) & (ly < yy + 9) & (lx >= xx) & (lx < xx + 10) & local
            roi[block] = np.array([62, 78, 160], np.uint8)

    smooth_number_plate = (slice(120, 261), slice(519, 765))
    numbers[smooth_number_plate] = 255
    rgb[smooth_number_plate] = np.array([112, 100, 136], np.uint8)
    rgb[154:226, 594:645] = np.array([236, 236, 230], np.uint8)
    rgb[154:226, 662:712] = np.array([236, 236, 230], np.uint8)

    warm_script_like = (slice(560, 701), slice(519, 765))
    numbers[warm_script_like] = 255
    rgb[warm_script_like] = np.array([218, 64, 42], np.uint8)
    rgb[584:646, 560:720:12] = np.array([246, 190, 50], np.uint8)
    rgb[594:666:18, 552:730] = np.array([246, 242, 228], np.uint8)

    true_digit = np.zeros((n, n), bool)
    true_digit[780:910, 170:230] = True
    true_digit[780:808, 170:308] = True
    true_digit[882:910, 170:308] = True
    true_digit[808:882, 248:308] = True
    numbers[true_digit] = 255
    rgb[true_digit] = np.array([224, 224, 218], np.uint8)
    rgb[true_digit & ((np.indices((n, n))[1] - 170) % 18 < 5)] = np.array([44, 48, 60], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "large_cool_event_badge_sponsor_logo"
    assert info["components"][0]["white_text_components"] >= 20
    assert info["components"][0]["dark_text_components"] >= 4
    assert info["components"][0]["colored_text_components"] >= 8
    assert (mask[event_badge] > 0).mean() > 0.90
    assert (mask[smooth_number_plate] > 0).mean() == 0
    assert (mask[warm_script_like] > 0).mean() == 0
    assert (mask[true_digit] > 0).mean() < 0.05


def test_smart_tga_wide_pale_sponsor_text_billboard_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([16, 18, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 2, 0, 86, 376
    billboard = (slice(y0, y0 + h), slice(x0, x0 + w))
    numbers[billboard] = 255
    rgb[billboard] = np.array([228, 225, 218], np.uint8)
    rgb[y0 + 3:y0 + h - 5, x0 + 3:x0 + w - 3] = np.array([240, 238, 229], np.uint8)
    rgb[y0 + h - 5:y0 + h, x0:x0 + w] = np.array([58, 50, 58], np.uint8)

    for xoff, color in (
        (18, [190, 72, 88]),
        (58, [184, 154, 58]),
        (98, [86, 122, 174]),
    ):
        rgb[y0 + 14:y0 + 72, x0 + xoff:x0 + xoff + 5] = np.array(color, np.uint8)
        rgb[y0 + 16:y0 + 21, x0 + xoff:x0 + xoff + 32] = np.array(color, np.uint8)
        rgb[y0 + 62:y0 + 68, x0 + xoff + 4:x0 + xoff + 32] = np.array(color, np.uint8)
        rgb[y0 + 28:y0 + 35, x0 + xoff + 14:x0 + xoff + 29] = np.array([116, 110, 112], np.uint8)

    for xoff in range(168, 346, 30):
        rgb[y0 + 20:y0 + 56, x0 + xoff:x0 + xoff + 22] = np.array([138, 136, 132], np.uint8)
        rgb[y0 + 25:y0 + 31, x0 + xoff + 4:x0 + xoff + 19] = np.array([235, 233, 224], np.uint8)
        rgb[y0 + 42:y0 + 48, x0 + xoff + 4:x0 + xoff + 19] = np.array([235, 233, 224], np.uint8)
        rgb[y0 + 23:y0 + 54, x0 + xoff + 10:x0 + xoff + 13] = np.array([235, 233, 224], np.uint8)
        rgb[y0 + 18:y0 + 23, x0 + xoff + 2:x0 + xoff + 9] = np.array([92, 128, 178], np.uint8)
        rgb[y0 + 55:y0 + 60, x0 + xoff + 12:x0 + xoff + 20] = np.array([182, 80, 104], np.uint8)

    smooth_pale_panel = (slice(160, 246), slice(0, 376))
    numbers[smooth_pale_panel] = 255
    rgb[smooth_pale_panel] = np.array([236, 233, 224], np.uint8)

    two_digit_plate = (slice(300, 386), slice(0, 376))
    numbers[two_digit_plate] = 255
    rgb[two_digit_plate] = np.array([238, 236, 228], np.uint8)
    rgb[315:372, 88:138] = np.array([118, 120, 124], np.uint8)
    rgb[315:372, 230:280] = np.array([118, 120, 124], np.uint8)
    rgb[330:358, 100:126] = np.array([238, 236, 228], np.uint8)
    rgb[330:358, 242:268] = np.array([238, 236, 228], np.uint8)

    true_number = np.zeros((n, n), bool)
    true_number[520:638, 90:148] = True
    true_number[520:545, 90:204] = True
    true_number[613:638, 90:204] = True
    true_number[545:613, 148:204] = True
    numbers[true_number] = 255
    rgb[true_number] = np.array([232, 230, 220], np.uint8)
    rgb[true_number & ((xx - 90) % 15 < 4)] = np.array([120, 124, 130], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "wide_pale_sponsor_text_billboard"
    assert info["components"][0]["nonwhite_text_components"] >= 5
    assert (mask[billboard] > 0).mean() > 0.95
    assert (mask[smooth_pale_panel] > 0).mean() == 0
    assert (mask[two_digit_plate] > 0).mean() == 0
    assert (mask[true_number] > 0).mean() < 0.05


def test_smart_tga_pale_blue_sponsor_wordmark_row_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([16, 20, 28], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    def add_panel(y0, x0):
        h, w = 67, 151
        ly, lx = np.indices((h, w))
        local = np.abs(ly - (18 + lx * 0.20)) <= 16
        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w][local] = True
        numbers[panel] = 255
        rgb[panel] = np.array([192, 198, 201], np.uint8)
        rgb[panel & (((xx - x0) % 23) < 2)] = np.array([138, 154, 166], np.uint8)
        return panel

    upper_panel = add_panel(118, 740)
    lower_panel = add_panel(380, 740)

    letter_masks = []
    for idx, x0 in enumerate((58, 136, 236, 532)):
        y0, h, w = 732, 37, 33
        ly, lx = np.indices((h, w))
        local = (
            (lx < 7)
            | (lx >= w - 7)
            | ((ly < 7) & (lx < w - 3))
            | ((ly >= h - 7) & (lx > 3))
        )
        if idx % 2:
            local &= ~((ly >= 15) & (ly < 22) & (lx >= 12) & (lx < 24))
        letter = np.zeros((n, n), bool)
        letter[y0:y0 + h, x0:x0 + w][local] = True
        numbers[letter] = 255
        rgb[letter] = np.array([224, 224, 224], np.uint8)
        shadow = letter & (xx >= x0 + 2 + idx % 2) & (xx < x0 + 7 + idx % 2)
        rgb[shadow] = np.array([120, 120, 120], np.uint8)
        letter_masks.append(letter)

    sponsors[724:780, 36:300] = 255
    sponsors[numbers > 0] = 0

    isolated_digit = np.zeros((n, n), bool)
    isolated_digit[220:257, 130:163] = True
    isolated_digit[229:248, 140:153] = False
    numbers[isolated_digit] = 255
    rgb[isolated_digit] = np.array([226, 226, 226], np.uint8)
    rgb[isolated_digit & (xx % 11 == 0)] = np.array([56, 56, 56], np.uint8)

    true_number = np.zeros((n, n), bool)
    true_number[560:662, 434:474] = True
    true_number[560:584, 434:594] = True
    true_number[638:662, 434:594] = True
    true_number[584:638, 530:594] = True
    numbers[true_number] = 255
    rgb[true_number] = np.array([238, 238, 238], np.uint8)
    rgb[true_number & (xx % 9 < 2)] = np.array([228, 52, 42], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert reasons == {
        "pale_blue_sponsor_wordmark_panel",
        "pale_neutral_sponsor_wordmark_letter",
    }
    assert info["component_count"] == 6
    assert (mask[upper_panel] > 0).mean() > 0.90
    assert (mask[lower_panel] > 0).mean() > 0.90
    for letter in letter_masks:
        assert (mask[letter] > 0).mean() > 0.90
    assert (mask[isolated_digit] > 0).mean() == 0
    assert (mask[true_number] > 0).mean() < 0.05


def test_smart_tga_vertical_red_white_sponsor_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 18, 35], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 621, 167, 101, 28
    vertical_wordmark = (slice(y0, y0 + h), slice(x0, x0 + w))
    numbers[vertical_wordmark] = 255
    rgb[vertical_wordmark] = np.array([206, 48, 54], np.uint8)
    for row_y in range(5, 94, 7):
        for xoff in (2, 8, 14, 20):
            rgb[y0 + row_y:y0 + row_y + 5, x0 + xoff:x0 + xoff + 3] = np.array([246, 242, 232], np.uint8)

    smooth_vertical_strip = (slice(118, 219), slice(64, 92))
    numbers[smooth_vertical_strip] = 255
    rgb[smooth_vertical_strip] = np.array([206, 48, 54], np.uint8)

    gray_number_strip = (slice(320, 408), slice(184, 201))
    numbers[gray_number_strip] = 255
    rgb[gray_number_strip] = np.array([162, 162, 164], np.uint8)
    rgb[324:404, 189:196] = np.array([236, 236, 238], np.uint8)
    rgb[352:365, 184:201] = np.array([44, 44, 48], np.uint8)

    true_digit = np.zeros((n, n), bool)
    true_digit[680:781, 580:608] = True
    true_digit[680:700, 580:655] = True
    true_digit[761:781, 580:655] = True
    numbers[true_digit] = 255
    rgb[true_digit] = np.array([214, 42, 48], np.uint8)
    rgb[true_digit & (np.indices((n, n))[1] % 17 < 5)] = np.array([246, 242, 232], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "vertical_red_white_sponsor_wordmark"
    assert info["components"][0]["white_text_components"] >= 8
    assert (mask[vertical_wordmark] > 0).mean() > 0.95
    assert (mask[smooth_vertical_strip] > 0).mean() == 0
    assert (mask[gray_number_strip] > 0).mean() == 0
    assert (mask[true_digit] > 0).mean() < 0.05


def test_smart_tga_compact_vertical_warm_sponsor_wordmark_demotes_from_numbers():
    n = 512
    rgb = np.full((n, n, 3), np.array([84, 18, 18], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def paint_big_wordmark(y0, x0):
        shape = np.zeros((50, 34), bool)
        shape[:, 0:7] = True
        shape[0:7, 7:27] = True
        shape[21:28, 7:27] = True
        shape[43:50, 7:27] = True
        shape[8:20, 24:32] = True
        shape[30:42, 24:32] = True
        shape[:, 24:27] = True
        full = np.zeros((n, n), bool)
        full[y0:y0 + 50, x0:x0 + 34] = shape
        yy, xx = np.indices((n, n))
        local_y = yy - y0
        local_x = xx - x0
        rgb[full] = np.array([245, 210, 30], np.uint8)
        red_ink = full & (((local_x + local_y) % 4) == 0)
        rgb[red_ink] = np.array([190, 30, 80], np.uint8)
        for yoff in (2, 11, 20, 29, 38, 46):
            stroke = full & (local_y >= yoff) & (local_y < yoff + 2) & (local_x >= 2) & (local_x < 32)
            rgb[stroke] = np.array([80, 40, 80], np.uint8)
        return full

    positive = paint_big_wordmark(244, 117)
    numbers[positive] = 255

    smooth_digit = np.zeros((n, n), bool)
    smooth_digit[104:154, 270:304] = True
    numbers[smooth_digit] = 255
    rgb[smooth_digit] = np.array([218, 164, 18], np.uint8)
    rgb[smooth_digit & (np.indices((n, n))[0] % 11 < 4)] = np.array([206, 34, 22], np.uint8)

    wide_warm_mark = np.zeros((n, n), bool)
    wide_warm_mark[330:356, 90:170] = True
    numbers[wide_warm_mark] = 255
    rgb[wide_warm_mark] = np.array([218, 164, 18], np.uint8)
    rgb[wide_warm_mark & (np.indices((n, n))[1] % 9 < 3)] = np.array([206, 34, 22], np.uint8)

    protected = paint_big_wordmark(380, 270)
    numbers[protected] = 255
    template[protected] = 255

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "compact_vertical_warm_sponsor_wordmark"
    assert info["components"][0]["dark_text_components"] >= 4
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[smooth_digit] > 0).mean() == 0
    assert (mask[wide_warm_mark] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0


def test_smart_tga_decorative_livery_preserves_compact_vertical_warm_sponsor_wordmark():
    n = 512
    rgb = np.full((n, n, 3), np.array([84, 18, 18], np.uint8), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def paint_big_wordmark(y0, x0):
        shape = np.zeros((50, 34), bool)
        shape[:, 0:7] = True
        shape[0:7, 7:27] = True
        shape[21:28, 7:27] = True
        shape[43:50, 7:27] = True
        shape[8:20, 24:32] = True
        shape[30:42, 24:32] = True
        shape[:, 24:27] = True
        full = np.zeros((n, n), bool)
        full[y0:y0 + 50, x0:x0 + 34] = shape
        yy, xx = np.indices((n, n))
        local_y = yy - y0
        local_x = xx - x0
        rgb[full] = np.array([245, 210, 30], np.uint8)
        rgb[full & (((local_x + local_y) % 4) == 0)] = np.array([190, 30, 80], np.uint8)
        for yoff in (2, 11, 20, 29, 38, 46):
            stroke = full & (local_y >= yoff) & (local_y < yoff + 2) & (local_x >= 2) & (local_x < 32)
            rgb[stroke] = np.array([80, 40, 80], np.uint8)
        return full

    positive = paint_big_wordmark(244, 117)
    sponsors[positive] = 255

    mask, info = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, empty, empty, empty
    )

    assert info["status"] == "empty"
    assert info["wordmark_veto_count"] == 1
    assert (mask[positive] > 0).mean() == 0


def test_smart_tga_orange_white_dlm_body_flourish_splits_mixed_contingency_wedge():
    sample = Path(
        "_smart_tga_runs/cycle573_dlm_33863_post572_probe_v1_nocache/"
        "Dirt_Late_Model_car_num_33863"
    )
    paint_path = Path(
        r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing"
        r"\SPB Smart TGA Examples\Dirt Late Model\car_num_33863.tga"
    )
    required = [
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        paint_path,
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle573 DLM 33863 diagnostic artifacts are not present")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    rgb_float, _alpha, _meta = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(rgb_float[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(required[0]).convert("L"))
    sponsors = np.array(Image.open(required[1]).convert("L"))
    template = np.array(Image.open(required[2]).convert("L"))
    brand = np.array(Image.open(required[3]).convert("L"))

    mask, info = car_layers_mod._decorative_livery_sponsor_to_paint(
        rgb, sponsors, numbers, template, brand
    )
    components = {tuple(component["bbox"]): component for component in info.get("components", [])}

    assert info["status"] == "applied"
    assert components[(0, 297, 110, 72)]["reason"] == "left_mid_orange_white_dlm_body_flourish"
    assert components[(662, 187, 33, 26)]["reason"] == "tiny_orange_white_dlm_body_flourish_shard"
    assert components[(9, 735, 56, 96)]["reason"] == "lower_left_mixed_orange_dlm_wedge_fill_partial"
    assert components[(0, 874, 149, 13)]["reason"] == "lower_left_blue_cyan_dlm_livery_stripe"
    assert components[(9, 735, 56, 96)]["component_area"] == 3098
    assert components[(9, 735, 56, 96)]["area"] == 905
    assert int((mask[297:369, 0:110] > 0).sum()) == 2361
    assert int((mask[187:213, 662:695] > 0).sum()) == 574
    assert int((mask[735:831, 9:65] > 0).sum()) == 905
    assert int((mask[874:887, 0:149] > 0).sum()) == 518

    # This nearby component contains real contingency/sponsor decal ink inside
    # the orange body shape, so only smooth saturated orange fill can move.
    wedge_rgb = rgb[735:831, 9:65]
    wedge_mask = mask[735:831, 9:65] > 0
    wedge_hsv = car_layers_mod.cv2.cvtColor(wedge_rgb, car_layers_mod.cv2.COLOR_RGB2HSV)
    assert int((wedge_mask & (wedge_hsv[:, :, 1] < 65) & (wedge_hsv[:, :, 2] > 150)).sum()) == 0
    assert int((wedge_mask & (wedge_hsv[:, :, 1] < 65) & (wedge_hsv[:, :, 2] < 76)).sum()) == 0


def test_smart_tga_tall_cool_script_wordmark_demotes_from_numbers():
    cv2 = car_layers_mod.cv2
    assert cv2 is not None
    n = 1024
    rgb = np.full((n, n, 3), np.array([142, 238, 190], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 578, 30, 195, 71
    shape = np.zeros((h, w), np.uint8)
    cv2.line(shape, (42, 0), (58, 48), 1, 9, cv2.LINE_AA)
    cv2.line(shape, (58, 48), (18, 58), 1, 10, cv2.LINE_AA)
    cv2.line(shape, (18, 58), (54, 86), 1, 10, cv2.LINE_AA)
    cv2.line(shape, (54, 86), (19, 122), 1, 12, cv2.LINE_AA)
    cv2.line(shape, (19, 122), (42, 194), 1, 8, cv2.LINE_AA)
    cv2.ellipse(shape, (28, 126), (22, 44), -8, 0, 360, 1, 8, cv2.LINE_AA)
    cv2.ellipse(shape, (34, 55), (25, 24), 12, 0, 320, 1, 8, cv2.LINE_AA)
    cv2.line(shape, (8, 110), (62, 112), 1, 9, cv2.LINE_AA)
    shape = shape > 0

    wordmark = (slice(y0, y0 + h), slice(x0, x0 + w))
    numbers[wordmark][shape] = 255
    yy, xx = np.indices((n, n))
    wordmark_pixels = numbers > 0
    rgb[wordmark_pixels] = np.array([28, 125, 68], np.uint8)
    rgb[wordmark_pixels & ((yy % 13) < 4)] = np.array([8, 42, 22], np.uint8)
    rgb[wordmark_pixels & ((xx % 11) < 3)] = np.array([96, 220, 146], np.uint8)
    rgb[wordmark_pixels & (((yy + xx) % 17) < 3)] = np.array([14, 54, 30], np.uint8)

    smooth_tall_digit = (slice(90, 285), slice(160, 231))
    numbers[smooth_tall_digit] = 255
    rgb[smooth_tall_digit] = np.array([22, 152, 82], np.uint8)

    true_99_left = (slice(360, 500), slice(350, 440))
    true_99_right = (slice(360, 500), slice(452, 542))
    for digit in (true_99_left, true_99_right):
        numbers[digit] = 255
        rgb[digit] = np.array([78, 190, 135], np.uint8)
        rgb[digit][8:122, 10:80] = np.array([238, 238, 232], np.uint8)
        rgb[digit][28:102, 28:62] = np.array([142, 238, 190], np.uint8)
        rgb[digit][::9, :] = np.array([32, 70, 48], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tall_cool_script_sponsor_wordmark"
    assert (mask[wordmark][shape] > 0).mean() > 0.95
    assert (mask[smooth_tall_digit] > 0).mean() < 0.05
    assert (mask[true_99_left] > 0).mean() < 0.05
    assert (mask[true_99_right] > 0).mean() < 0.05


def test_smart_tga_tall_cool_green_blue_vertical_wordmark_demotes_real_dlm_1250296():
    sample = Path(
        "_smart_tga_runs/cycle514_dlm_batch_red44_mixed_color_sibling_v1_nocache/"
        "Dirt_Late_Model_car_num_1250296"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    assert all(path.exists() for path in required)

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "tall_cool_green_blue_vertical_sponsor_wordmark"
    ]
    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (25, 406, 82, 210),
    }
    component = components[0]
    assert component["fill"] >= 0.68
    assert component["green_frac"] >= 0.28
    assert component["blue_frac"] >= 0.48
    assert component["colored_text_components"] >= 18
    assert component["dark_span_y"] >= 0.90
    assert float((mask[406:616, 25:107] > 0).mean()) > 0.70
    assert float((mask[28:183, 865:1024] > 0).mean()) == 0.0
    assert float((mask[598:680, 835:873] > 0).mean()) == 0.0
    assert float((mask[908:935, 934:971] > 0).mean()) == 0.0


def test_smart_tga_sparse_sponsor_logo_fragment_demotes_from_numbers():
    n = 768
    rgb = np.full((n, n, 3), np.array([20, 24, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 122, 148, 18, 52
    false_fragment = np.zeros((n, n), bool)
    false_fragment[y0:y0 + 2, x0:x0 + w] = True
    false_fragment[y0 + h - 2:y0 + h, x0:x0 + w] = True
    false_fragment[y0:y0 + h, x0:x0 + 2] = True
    false_fragment[y0:y0 + h, x0 + w - 2:x0 + w] = True
    numbers[false_fragment] = 255
    sponsors[y0 - 4:y0 + h + 4, x0 + 6:x0 + w + 8] = 255
    rgb[false_fragment] = np.array([220, 56, 48], np.uint8)
    rgb[false_fragment & (np.indices((n, n))[1] % 5 < 2)] = np.array([46, 88, 222], np.uint8)
    rgb[false_fragment & (np.indices((n, n))[1] % 11 == 0)] = np.array([242, 242, 230], np.uint8)

    remote_livery_fragment = np.zeros((n, n), bool)
    ry0, rx0 = 208, 148
    remote_livery_fragment[ry0:ry0 + 2, rx0:rx0 + w] = True
    remote_livery_fragment[ry0 + h - 2:ry0 + h, rx0:rx0 + w] = True
    remote_livery_fragment[ry0:ry0 + h, rx0:rx0 + 2] = True
    remote_livery_fragment[ry0:ry0 + h, rx0 + w - 2:rx0 + w] = True
    numbers[remote_livery_fragment] = 255
    rgb[remote_livery_fragment] = np.array([218, 58, 48], np.uint8)
    rgb[remote_livery_fragment & (np.indices((n, n))[1] % 5 < 2)] = np.array([46, 88, 222], np.uint8)
    rgb[remote_livery_fragment & (np.indices((n, n))[1] % 11 == 0)] = np.array([242, 242, 230], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[304:384, 292:332] = True
    digit[304:324, 292:372] = True
    digit[364:384, 292:372] = True
    digit[324:364, 332:372] = True
    numbers[digit] = 255
    rgb[digit] = np.array([238, 44, 40], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "sparse_sponsor_logo_fragment"
    assert info["components"][0]["near_sponsor"] >= 0.18
    assert (mask[false_fragment] > 0).mean() > 0.90
    assert (mask[remote_livery_fragment] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_dark_sponsor_wordmark_fragments_demote_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 16, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 270, 620, 18, 48
    wordmark = np.zeros((n, n), bool)
    wordmark[y0, x0 + 2:x0 + w - 2] = True
    wordmark[y0 + 7, x0:x0 + w] = True
    wordmark[y0 + 14, x0 + 4:x0 + w - 4] = True
    wordmark[y0 + 17, x0 + 2:x0 + w - 2] = True
    for xoff in (5, 16, 27, 39):
        wordmark[y0 + 1:y0 + h, x0 + xoff] = True
    numbers[wordmark] = 255
    sponsors[y0 - 8:y0 + h + 8, x0 - 8:x0 + w + 8] = 255
    sponsors[wordmark] = 0
    rgb[y0 - 2:y0 + h + 2, x0 - 2:x0 + w + 2] = np.array([132, 104, 98], np.uint8)
    rgb[wordmark] = np.array([34, 26, 26], np.uint8)
    rgb[wordmark & (((xx - x0) + (yy - y0)) % 2 == 0)] = np.array([118, 70, 66], np.uint8)

    by0, bx0, bh, bw = 920, 620, 81, 62
    local_y, local_x = np.indices((bh, bw))
    badge = np.zeros((n, n), bool)
    local = (
        ((local_x >= 8) & (local_x <= 10) & (local_y >= 7) & (local_y <= 73))
        | ((local_x >= 51) & (local_x <= 53) & (local_y >= 7) & (local_y <= 73))
        | ((local_y >= 9) & (local_y <= 11) & (local_x >= 9) & (local_x <= 53))
        | ((local_y >= 39) & (local_y <= 41) & (local_x >= 9) & (local_x <= 53))
        | ((local_y >= 71) & (local_y <= 73) & (local_x >= 9) & (local_x <= 53))
        | ((local_x >= 16) & (local_x <= 46) & (np.abs((local_y - 14) - (local_x - 16) * 1.7) <= 1))
    )
    badge[by0:by0 + bh, bx0:bx0 + bw][local] = True
    numbers[badge] = 255
    sponsors[by0 - 9:by0 + bh + 9, bx0 - 9:bx0 + bw + 9] = 255
    sponsors[badge] = 0
    rgb[badge] = np.array([54, 38, 38], np.uint8)
    rgb[badge & (((xx - bx0) + (yy - by0)) % 17 < 3)] = np.array([84, 50, 48], np.uint8)

    remote_wordmark = np.zeros((n, n), bool)
    ry0, rx0 = 382, 620
    remote_wordmark[ry0, rx0 + 2:rx0 + w - 2] = True
    remote_wordmark[ry0 + 7, rx0:rx0 + w] = True
    remote_wordmark[ry0 + 14, rx0 + 4:rx0 + w - 4] = True
    remote_wordmark[ry0 + 17, rx0 + 2:rx0 + w - 2] = True
    for xoff in (5, 16, 27, 39):
        remote_wordmark[ry0 + 1:ry0 + h, rx0 + xoff] = True
    numbers[remote_wordmark] = 255
    rgb[remote_wordmark] = np.array([34, 26, 26], np.uint8)

    pale_digit = np.zeros((n, n), bool)
    pale_digit[500:640, 390:450] = True
    pale_digit[500:540, 390:530] = True
    pale_digit[600:640, 390:530] = True
    pale_digit[540:600, 485:530] = True
    numbers[pale_digit] = 255
    sponsors[490:650, 380:540] = 255
    sponsors[pale_digit] = 0
    rgb[pale_digit] = np.array([218, 210, 204], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] >= 1
    assert reasons == {"dark_sponsor_wordmark_fragment"}
    assert min(component["near_sponsor"] for component in info["components"]) >= 0.36
    assert (mask[badge] > 0).mean() > 0.90
    assert (mask[remote_wordmark] > 0).mean() == 0
    assert (mask[pale_digit] > 0).mean() < 0.05


def test_smart_tga_dense_sponsor_badge_fragments_demote_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([252, 122, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 720, 620, 81, 62
    local_y, local_x = np.indices((h, w))
    badge_local = (
        ((local_x >= 8) & (local_x <= 11) & (local_y >= 7) & (local_y <= 73))
        | ((local_x >= 50) & (local_x <= 53) & (local_y >= 7) & (local_y <= 73))
        | ((local_y >= 10) & (local_y <= 12) & (local_x >= 9) & (local_x <= 53))
        | ((local_y >= 39) & (local_y <= 42) & (local_x >= 9) & (local_x <= 53))
        | ((local_y >= 70) & (local_y <= 73) & (local_x >= 9) & (local_x <= 53))
        | ((local_y >= 16) & (local_y <= 65) & (np.abs((local_x - 15) - (local_y - 16) * 0.62) <= 2))
    )
    badge = np.zeros((n, n), bool)
    badge[y0:y0 + h, x0:x0 + w][badge_local] = True
    numbers[badge] = 255
    sponsors[y0 - 10:y0 + h + 10, x0 - 10:x0 + w + 10] = 255
    sponsors[badge] = 0
    rgb[badge] = np.array([86, 72, 70], np.uint8)
    rgb[badge & (((xx - x0) + (yy - y0)) % 11 < 5)] = np.array([42, 32, 32], np.uint8)
    rgb[badge & (((xx - x0) * 3 + (yy - y0)) % 29 < 3)] = np.array([118, 72, 70], np.uint8)

    remote_badge = np.zeros((n, n), bool)
    ry0, rx0 = 720, 820
    remote_badge[ry0:ry0 + h, rx0:rx0 + w][badge_local] = True
    numbers[remote_badge] = 255
    rgb[remote_badge] = np.array([86, 44, 42], np.uint8)

    bright_number = np.zeros((n, n), bool)
    bright_number[300:430, 200:260] = True
    bright_number[300:340, 200:340] = True
    bright_number[390:430, 200:340] = True
    bright_number[340:390, 300:340] = True
    numbers[bright_number] = 255
    sponsors[290:440, 190:350] = 255
    sponsors[bright_number] = 0
    rgb[bright_number] = np.array([226, 218, 210], np.uint8)
    rgb[bright_number & ((xx % 17) < 3)] = np.array([52, 52, 52], np.uint8)

    low_edge_panel = (slice(520, 552), slice(730, 800))
    numbers[low_edge_panel] = 255
    sponsors[512:560, 720:810] = 255
    sponsors[low_edge_panel] = 0
    rgb[low_edge_panel] = np.array([84, 44, 42], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert reasons == {"dense_sponsor_badge_fragment"}
    assert info["components"][0]["near_sponsor"] >= 0.48
    assert (mask[badge] > 0).mean() > 0.90
    assert (mask[remote_badge] > 0).mean() == 0
    assert (mask[bright_number] > 0).mean() < 0.05
    assert (mask[low_edge_panel] > 0).mean() == 0


def test_smart_tga_green_waveform_logo_glyph_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_waveform(y0, x0):
        h, w = 32, 35
        local = np.zeros((h, w), bool)
        yy, xx = np.indices((h, w))
        for y in range(h):
            cx = int(round(17 + 12 * np.sin(y / 3.2)))
            local[y, max(0, cx - 3):min(w, cx + 4)] = True
        for y in (6, 15, 24):
            local[y:y + 3, 2:33] = True
        numbers[y0:y0 + h, x0:x0 + w][local] = 255
        patch = rgb[y0:y0 + h, x0:x0 + w]
        patch[local] = np.array([45, 150, 38], np.uint8)
        dark_strokes = local & ((xx % 2) == 0)
        patch[dark_strokes] = np.array([10, 45, 8], np.uint8)
        return (slice(y0, y0 + h), slice(x0, x0 + w)), local

    glyph1, glyph1_mask = add_waveform(476, 722)
    glyph2, glyph2_mask = add_waveform(517, 723)

    yy, xx = np.indices((160, 170))
    badge = ((xx - 84) ** 2 + (yy - 78) ** 2) < 78 ** 2
    hole = ((xx - 84) ** 2 + (yy - 78) ** 2) < 54 ** 2
    ring = badge & ~hole
    sponsors[432:592, 675:845][ring] = 255
    rgb[432:592, 675:845][ring] = np.array([10, 160, 20], np.uint8)
    sponsors[468:556, 758:786] = 255
    sponsors[470:554, 760:784] = 0
    rgb[468:556, 758:786][sponsors[468:556, 758:786] > 0] = np.array([10, 160, 20], np.uint8)
    for glyph, glyph_mask in ((glyph1, glyph1_mask), (glyph2, glyph2_mask)):
        y0, y1 = glyph[0].start, glyph[0].stop
        x0, x1 = glyph[1].start, glyph[1].stop
        sponsors[y0 - 7:y1 + 7, x0 - 7:x1 + 7] = 255
        sponsors[glyph][glyph_mask] = 0

    remote_glyph, remote_mask = add_waveform(112, 722)

    digit = np.zeros((n, n), bool)
    digit[710:790, 250:290] = True
    digit[710:730, 250:330] = True
    digit[770:790, 250:330] = True
    digit[730:770, 290:330] = True
    numbers[digit] = 255
    rgb[digit] = np.array([18, 210, 24], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {"green_waveform_logo_glyph"}
    assert min(component["near_sponsor"] for component in info["components"]) >= 0.55
    assert (mask[glyph1][glyph1_mask] > 0).mean() > 0.90
    assert (mask[glyph2][glyph2_mask] > 0).mean() > 0.90
    assert (mask[remote_glyph][remote_mask] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_muted_red_dense_sponsor_tag_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 100, 120, 16, 45
    tag = np.zeros((n, n), bool)
    tag[y0:y0 + h, x0:x0 + w] = True
    tag[y0 + 3:y0 + 10, x0 + 7:x0 + 14] = False
    tag[y0 + 4:y0 + 9, x0 + 29:x0 + 35] = False
    numbers[tag] = 255
    rgb[tag] = np.array([190, 146, 154], np.uint8)
    rgb[tag & (xx < x0 + 25)] = np.array([238, 232, 232], np.uint8)
    rgb[tag & (xx >= x0 + 24) & (xx < x0 + 41)] = np.array([222, 72, 84], np.uint8)
    printed_strokes = tag & ((((xx - x0) % 11) == 0) | (((yy - y0) % 8) == 0))
    rgb[printed_strokes] = np.array([128, 136, 165], np.uint8)
    logo_bar = tag & (yy >= y0 + 10) & (yy < y0 + 13) & (xx >= x0 + 25) & (xx < x0 + 41)
    rgb[logo_bar] = np.array([222, 72, 84], np.uint8)

    smooth_bar = np.zeros((n, n), bool)
    smooth_bar[170:186, 120:165] = True
    smooth_bar[173:180, 127:134] = False
    smooth_bar[174:179, 149:155] = False
    numbers[smooth_bar] = 255
    rgb[smooth_bar] = np.array([214, 154, 164], np.uint8)

    number = np.zeros((n, n), bool)
    number[430:531, 434:474] = True
    number[430:454, 434:594] = True
    number[507:531, 434:594] = True
    number[454:507, 530:594] = True
    numbers[number] = 255
    rgb[number] = np.array([238, 238, 238], np.uint8)
    rgb[number & (xx % 9 < 2)] = np.array([228, 52, 42], np.uint8)
    rgb[number & (yy % 13 < 3)] = np.array([246, 164, 34], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "muted_red_dense_sponsor_tag"
    assert 0.25 <= info["components"][0]["sat_mean"] <= 0.33
    assert 0.35 <= info["components"][0]["white_frac"] <= 0.58
    assert 0.30 <= info["components"][0]["red_frac"] <= 0.45
    assert (mask[tag] > 0).mean() > 0.95
    assert (mask[smooth_bar] > 0).mean() == 0
    assert (mask[number] > 0).mean() < 0.05


def test_smart_tga_stacked_yellow_logo_fragments_demote_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    frag1 = np.zeros((n, n), bool)
    y0, x0, h, w = 100, 650, 47, 69
    rgb[y0:y0 + h, x0:x0 + w] = np.array([255, 245, 32], np.uint8)
    frag1[y0:y0 + h, x0:x0 + 10] = True
    frag1[y0:y0 + 4, x0:x0 + w] = True
    frag1[y0 + h - 4:y0 + h, x0:x0 + w] = True
    frag1[y0 + 20:y0 + 24, x0 + 8:x0 + 57] = True
    numbers[frag1] = 255
    rgb[frag1] = np.array([255, 245, 32], np.uint8)

    frag2 = np.zeros((n, n), bool)
    y1, x1, h1, w1 = 155, 676, 32, 55
    rgb[y1:y1 + h1, x1:x1 + w1] = np.array([255, 219, 30], np.uint8)
    frag2[y1:y1 + h1, x1:x1 + w1] = True
    frag2[y1 + 7:y1 + 24, x1 + 17:x1 + 37] = False
    numbers[frag2] = 255
    rgb[frag2] = np.array([255, 219, 30], np.uint8)

    single_roof_digit = np.zeros((n, n), bool)
    single_roof_digit[250:295, 650:710] = True
    single_roof_digit[260:285, 672:692] = False
    numbers[single_roof_digit] = 255
    rgb[single_roof_digit] = np.array([255, 224, 32], np.uint8)

    large_yellow_number = np.zeros((n, n), bool)
    large_yellow_number[470:650, 250:310] = True
    large_yellow_number[470:520, 250:420] = True
    large_yellow_number[600:650, 250:420] = True
    large_yellow_number[520:600, 360:420] = True
    numbers[large_yellow_number] = 255
    rgb[large_yellow_number] = np.array([244, 172, 22], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {component["reason"] for component in info["components"]} == {"yellow_stacked_logo_fragment"}
    assert (mask[frag1] > 0).mean() > 0.90
    assert (mask[frag2] > 0).mean() > 0.90
    assert (mask[single_roof_digit] > 0).mean() == 0
    assert (mask[large_yellow_number] > 0).mean() < 0.05


def test_smart_tga_yellow_logo_outline_false_number_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([22, 24, 30], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 888, 816, 73, 132
    yy, xx = np.indices((h, w))
    logo = np.zeros((h, w), bool)
    upper = 4 + xx * 0.20
    lower = 68 - xx * 0.20
    logo |= np.abs(yy - upper) <= 4
    logo |= np.abs(yy - lower) <= 4
    logo |= ((xx >= 58) & (xx <= 66) & (yy >= upper) & (yy <= lower))
    logo |= ((xx >= 96) & (xx <= 105) & (yy >= upper + 4) & (yy <= lower - 2))
    numbers[y0:y0 + h, x0:x0 + w][logo] = 255
    patch = rgb[y0:y0 + h, x0:x0 + w]
    patch[logo] = np.array([225, 174, 0], np.uint8)
    patch[logo & ((xx + yy) % 7 < 2)] = np.array([196, 144, 0], np.uint8)

    roof_like = np.zeros((h, w), bool)
    roof_upper = 4 + xx * 0.20
    roof_lower = 68 - xx * 0.20
    roof_like |= np.abs(yy - roof_upper) <= 4
    roof_like |= np.abs(yy - roof_lower) <= 4
    roof_like |= ((xx >= 58) & (xx <= 66) & (yy >= roof_upper) & (yy <= roof_lower))
    roof_like |= ((xx >= 96) & (xx <= 105) & (yy >= roof_upper + 4) & (yy <= roof_lower - 2))
    ry, rx = 650, 760
    numbers[ry:ry + h, rx:rx + w][roof_like] = 255
    roof_patch = rgb[ry:ry + h, rx:rx + w]
    roof_patch[roof_like] = np.array([224, 164, 12], np.uint8)
    roof_patch[roof_like & ((xx % 9) < 2)] = np.array([248, 248, 236], np.uint8)
    roof_patch[roof_like & ((yy % 11) == 0)] = np.array([24, 24, 24], np.uint8)

    large_yellow_number = np.zeros((n, n), bool)
    large_yellow_number[210:390, 220:280] = True
    large_yellow_number[210:260, 220:390] = True
    large_yellow_number[340:390, 220:390] = True
    large_yellow_number[260:340, 340:390] = True
    numbers[large_yellow_number] = 255
    rgb[large_yellow_number] = np.array([236, 166, 18], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "yellow_logo_outline_false_number"
    assert (mask[y0:y0 + h, x0:x0 + w][logo] > 0).mean() > 0.90
    assert (mask[ry:ry + h, rx:rx + w][roof_like] > 0).mean() == 0
    assert (mask[large_yellow_number] > 0).mean() < 0.05


def test_smart_tga_low_sat_gray_wordmark_demotes_from_numbers():
    n = 768
    rgb = np.full((n, n, 3), np.array([20, 24, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 120, 180, 48, 128
    wordmark = np.zeros((n, n), bool)
    for yoff in (0, 16, 32, 40):
        wordmark[y0 + yoff:y0 + yoff + 6, x0:x0 + w] = True
    for xoff in range(0, w, 18):
        wordmark[y0:y0 + h, x0 + xoff:x0 + xoff + 3] = True
    numbers[wordmark] = 255
    rgb[wordmark] = np.array([116, 118, 118], np.uint8)
    rgb[wordmark & ((xx - x0) % 9 < 4)] = np.array([216, 216, 210], np.uint8)
    rgb[wordmark & ((yy - y0) % 11 > 7)] = np.array([62, 72, 78], np.uint8)

    flat_panel = (slice(232, 272), slice(168, 238))
    numbers[flat_panel] = 255
    rgb[flat_panel] = np.array([80, 82, 82], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[304:384, 292:332] = True
    digit[304:324, 292:372] = True
    digit[364:384, 292:372] = True
    digit[324:364, 332:372] = True
    numbers[digit] = 255
    rgb[digit] = np.array([36, 210, 232], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "low_sat_large_sponsor_wordmark"
    assert 2.35 <= info["components"][0]["aspect"] <= 3.20
    assert info["components"][0]["sat_mean"] <= 0.18
    assert (mask[wordmark] > 0).mean() > 0.90
    assert (mask[flat_panel] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_broad_low_sat_wordmark_near_sponsors_demotes_from_numbers():
    n = 512
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 126, 77, 25, 98
    wordmark = np.zeros((n, n), bool)
    for yoff in (1, 8, 16):
        wordmark[y0 + yoff:y0 + yoff + 3, x0:x0 + w] = True
    for xoff in (4, 18, 31, 46, 61, 77, 90):
        wordmark[y0:y0 + h, x0 + xoff:x0 + xoff + 2] = True
    numbers[wordmark] = 255
    rgb[wordmark] = np.array([170, 170, 168], np.uint8)
    rgb[wordmark & ((xx - x0) % 14 < 8)] = np.array([234, 234, 228], np.uint8)
    rgb[wordmark & ((yy - y0) % 9 > 6)] = np.array([48, 50, 54], np.uint8)

    sponsor_sibling = (slice(96, 122), slice(55, 180))
    sponsors[sponsor_sibling] = 255
    rgb[sponsor_sibling] = np.array([230, 170, 38], np.uint8)
    rgb[104:114, 78:155] = np.array([246, 244, 232], np.uint8)

    smooth_number_panel = (slice(236, 261), slice(77, 175))
    numbers[smooth_number_panel] = 255
    rgb[smooth_number_panel] = np.array([226, 226, 222], np.uint8)
    rgb[242:255, 93:107] = np.array([52, 52, 56], np.uint8)
    rgb[242:255, 128:142] = np.array([52, 52, 56], np.uint8)

    separated_digits = np.zeros((n, n), bool)
    for xoff in (258, 291, 324):
        separated_digits[320:397, xoff:xoff + 15] = True
        separated_digits[320:337, xoff:xoff + 31] = True
        separated_digits[380:397, xoff:xoff + 31] = True
    numbers[separated_digits] = 255
    rgb[separated_digits] = np.array([238, 238, 232], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "broad_low_sat_sponsor_wordmark"
    assert info["components"][0]["broad_near_sponsor"] >= 0.45
    assert info["components"][0]["white_text_components"] >= 5
    assert (mask[wordmark] > 0).mean() > 0.90
    assert (mask[smooth_number_panel] > 0).mean() == 0
    assert (mask[separated_digits] > 0).mean() < 0.05


def test_smart_tga_dark_backed_horizontal_sponsor_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_dark_wordmark(y0, x0, *, with_sponsor_context=True, protected=False, dense_text=True):
        h, w = 47, 142
        ly, lx = np.indices((h, w))
        local = np.ones((h, w), bool)
        local &= ~(((lx % 24) >= 18) & (ly > 4) & (ly < h - 4))
        panel = np.zeros((n, n), bool)
        panel[y0:y0 + h, x0:x0 + w] = local
        numbers[panel] = 255
        if protected:
            template[panel] = 255

        roi = rgb[y0:y0 + h, x0:x0 + w]
        roi[local] = np.array([38, 38, 42], np.uint8)
        if dense_text:
            for xoff in range(8, w - 8, 10):
                glyph = local & (ly >= 6) & (ly < 40) & (lx >= xoff) & (lx < xoff + 6)
                roi[glyph] = np.array([238, 238, 232], np.uint8)
                notch = glyph & (ly >= 19) & (ly < 22)
                roi[notch] = np.array([38, 38, 42], np.uint8)
        else:
            for xoff in (24, 84):
                glyph = local & (ly >= 9) & (ly < 35) & (lx >= xoff) & (lx < xoff + 20)
                roi[glyph] = np.array([238, 238, 232], np.uint8)

        if with_sponsor_context:
            top = (slice(max(0, y0 - 52), max(0, y0 - 18)), slice(max(0, x0 - 12), min(n, x0 + w + 12)))
            bottom = (slice(min(n, y0 + h + 18), min(n, y0 + h + 42)), slice(max(0, x0 - 12), min(n, x0 + w + 12)))
            sponsors[top] = 255
            sponsors[bottom] = 255
            rgb[top] = np.array([190, 40, 72], np.uint8)
            rgb[bottom] = np.array([190, 40, 72], np.uint8)
        return panel

    target_wordmark = add_dark_wordmark(281, 457)
    no_context_wordmark = add_dark_wordmark(408, 457, with_sponsor_context=False)
    protected_wordmark = add_dark_wordmark(535, 457, protected=True)
    smooth_dark_number_panel = add_dark_wordmark(662, 457, dense_text=False)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert sum(
        component["reason"] == "dark_backed_horizontal_sponsor_wordmark"
        for component in info["components"]
    ) == 1
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "dark_backed_horizontal_sponsor_wordmark"
    )
    assert component["broad_near_sponsor"] >= 0.62
    assert component["white_text_components"] >= 10
    assert component["dark_frac"] >= 0.42
    assert (mask[target_wordmark] > 0).mean() > 0.86
    assert (mask[no_context_wordmark] > 0).mean() == 0
    assert (mask[protected_wordmark] > 0).mean() == 0
    assert (mask[smooth_dark_number_panel] > 0).mean() == 0


def test_smart_tga_mid_fill_logo_blob_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 24, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 160, 260, 85, 68
    logo = np.zeros((n, n), bool)
    for base in (8, 28, 48):
        center = x0 + base + ((yy - y0) // 5)
        logo |= ((yy >= y0) & (yy < y0 + h) & (xx >= center) & (xx < center + 11))
    logo[y0 + 4:y0 + 10, x0 + 4:x0 + w - 4] = True
    logo[y0 + h - 10:y0 + h - 5, x0 + 9:x0 + w - 3] = True
    numbers[logo] = 255
    rgb[logo] = np.array([70, 155, 170], np.uint8)
    rgb[logo & ((xx - x0) % 17 < 7)] = np.array([196, 204, 202], np.uint8)
    rgb[logo & ((yy - y0) % 7 < 3)] = np.array([42, 58, 72], np.uint8)
    rgb[logo & (((xx - x0) + (yy - y0)) % 11 < 3)] = np.array([142, 196, 210], np.uint8)

    smooth_logo_sized_panel = (slice(300, 385), slice(260, 328))
    numbers[smooth_logo_sized_panel] = 255
    rgb[smooth_logo_sized_panel] = np.array([92, 118, 128], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[450:540, 454:501] = True
    digit[450:473, 454:548] = True
    digit[517:540, 454:548] = True
    digit[473:517, 501:548] = True
    numbers[digit] = 255
    rgb[digit] = np.array([44, 204, 230], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "mid_fill_sponsor_logo_blob"
    assert 1.05 <= info["components"][0]["aspect"] <= 1.45
    assert 0.30 <= info["components"][0]["sat_mean"] <= 0.58
    assert (mask[logo] > 0).mean() > 0.90
    assert (mask[smooth_logo_sized_panel] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_pink_script_logo_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 24, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    logo = np.zeros((n, n), bool)
    y0, x0, h, w = 160, 260, 72, 41
    logo[y0:y0 + h, x0 + 18:x0 + 28] = True
    logo[y0 + 18:y0 + 56, x0:x0 + 10] = True
    logo[y0 + 30:y0 + 36, x0 + 10:x0 + 18] = True
    logo[y0 + 24:y0 + 58, x0 + 37:x0 + w] = True
    logo[y0 + 42:y0 + 48, x0 + 28:x0 + 37] = True
    numbers[logo] = 255
    rgb[logo] = np.array([221, 33, 68], np.uint8)

    red_script_like_digit = np.zeros((n, n), bool)
    ry0, rx0 = 300, 260
    red_script_like_digit[ry0:ry0 + h, rx0 + 18:rx0 + 28] = True
    red_script_like_digit[ry0 + 18:ry0 + 56, rx0:rx0 + 10] = True
    red_script_like_digit[ry0 + 30:ry0 + 36, rx0 + 10:rx0 + 18] = True
    red_script_like_digit[ry0 + 24:ry0 + 58, rx0 + 37:rx0 + w] = True
    red_script_like_digit[ry0 + 42:ry0 + 48, rx0 + 28:rx0 + 37] = True
    numbers[red_script_like_digit] = 255
    rgb[red_script_like_digit] = np.array([230, 42, 40], np.uint8)

    blue_digit = np.zeros((n, n), bool)
    blue_digit[450:540, 454:501] = True
    blue_digit[450:473, 454:548] = True
    blue_digit[517:540, 454:548] = True
    blue_digit[473:517, 501:548] = True
    numbers[blue_digit] = 255
    rgb[blue_digit] = np.array([44, 204, 230], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "pink_script_sponsor_logo"
    assert (mask[logo] > 0).mean() > 0.90
    assert (mask[red_script_like_digit] > 0).mean() == 0
    assert (mask[blue_digit] > 0).mean() < 0.05


def test_smart_tga_vertical_brand_strip_demotes_with_pink_script_budget():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 24, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 240, 480, 248, 47
    vertical_strip = np.zeros((n, n), bool)
    vertical_strip[y0:y0 + h, x0:x0 + w] = True
    vertical_strip[y0 + 16:y0 + h - 16, x0 + 4:x0 + 8] = False
    vertical_strip[y0 + 150:y0 + 180, x0 + 10:x0 + 23] = True
    vertical_strip[y0 + 190:y0 + 235, x0 + 10:x0 + 23] = True
    vertical_strip[y0 + 215:y0 + 227, x0 + 17:x0 + 38] = True
    numbers[vertical_strip] = 255
    rgb[vertical_strip] = np.array([16, 16, 16], np.uint8)
    rgb[y0 + 150:y0 + 180, x0 + 10:x0 + 23][vertical_strip[y0 + 150:y0 + 180, x0 + 10:x0 + 23]] = np.array([238, 238, 232], np.uint8)
    rgb[y0 + 190:y0 + 235, x0 + 10:x0 + 23][vertical_strip[y0 + 190:y0 + 235, x0 + 10:x0 + 23]] = np.array([238, 238, 232], np.uint8)
    rgb[y0 + 218:y0 + 225, x0 + 15:x0 + 39][vertical_strip[y0 + 218:y0 + 225, x0 + 15:x0 + 39]] = np.array([214, 190, 118], np.uint8)

    pink_logo = np.zeros((n, n), bool)
    py0, px0, ph, pw = 160, 260, 72, 41
    pink_logo[py0:py0 + ph, px0 + 18:px0 + 28] = True
    pink_logo[py0 + 18:py0 + 56, px0:px0 + 10] = True
    pink_logo[py0 + 30:py0 + 36, px0 + 10:px0 + 18] = True
    pink_logo[py0 + 24:py0 + 58, px0 + 37:px0 + pw] = True
    pink_logo[py0 + 42:py0 + 48, px0 + 28:px0 + 37] = True
    numbers[pink_logo] = 255
    rgb[pink_logo] = np.array([221, 33, 68], np.uint8)

    narrow_digit = np.zeros((n, n), bool)
    narrow_digit[580:760, 470:512] = True
    narrow_digit[580:602, 444:534] = True
    narrow_digit[738:760, 444:534] = True
    numbers[narrow_digit] = 255
    rgb[narrow_digit] = np.array([34, 34, 34], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert "vertical_low_sat_brand_strip" in reasons
    assert "pink_script_sponsor_logo" in reasons
    assert (mask[vertical_strip] > 0).mean() > 0.90
    assert (mask[pink_logo] > 0).mean() > 0.90
    assert (mask[narrow_digit] > 0).mean() < 0.05


def test_smart_tga_pale_vertical_wordmark_strip_demotes_without_digit_loss():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 24, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 176, 860, 201, 34
    wordmark = np.zeros((n, n), bool)
    wordmark[y0:y0 + h, x0:x0 + w] = True
    wordmark[y0 + 15:y0 + h - 15, x0 + 5:x0 + 6] = False
    wordmark[y0 + 25:y0 + h - 25, x0 + 14:x0 + 15] = False
    wordmark[y0 + 35:y0 + h - 35, x0 + 23:x0 + 24] = False
    numbers[wordmark] = 255
    rgb[wordmark] = np.array([22, 22, 22], np.uint8)
    letter_bars = wordmark & (xx >= x0 + 8) & (xx < x0 + 31) & (
        ((yy >= y0 + 10) & (yy < y0 + 29))
        | ((yy >= y0 + 47) & (yy < y0 + 66))
        | ((yy >= y0 + 84) & (yy < y0 + 103))
        | ((yy >= y0 + 121) & (yy < y0 + 140))
        | ((yy >= y0 + 158) & (yy < y0 + 177))
    )
    mid_strokes = wordmark & (xx >= x0 + 10) & (xx < x0 + 26) & (
        ((yy >= y0 + 32) & (yy < y0 + 42))
        | ((yy >= y0 + 122) & (yy < y0 + 132))
    )
    rgb[mid_strokes] = np.array([180, 180, 180], np.uint8)
    rgb[letter_bars] = np.array([230, 230, 230], np.uint8)

    saturated_digit = np.zeros((n, n), bool)
    saturated_digit[520:721, 220:254] = True
    saturated_digit[536:706, 225:226] = False
    saturated_digit[546:696, 234:235] = False
    numbers[saturated_digit] = 255
    rgb[saturated_digit] = np.array([210, 34, 38], np.uint8)

    smooth_gray_digit = np.zeros((n, n), bool)
    smooth_gray_digit[520:721, 360:394] = True
    numbers[smooth_gray_digit] = 255
    rgb[smooth_gray_digit] = np.array([64, 64, 66], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "pale_vertical_wordmark_strip"
    assert 5.40 <= info["components"][0]["aspect"] <= 6.35
    assert info["components"][0]["sat_mean"] <= 0.055
    assert 0.18 <= info["components"][0]["white_frac"] <= 0.36
    assert 0.52 <= info["components"][0]["dark_frac"] <= 0.72
    assert (mask[wordmark] > 0).mean() > 0.90
    assert (mask[saturated_digit] > 0).mean() < 0.05
    assert (mask[smooth_gray_digit] > 0).mean() == 0


def test_smart_tga_tall_pale_vertical_brand_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_brand_strip(y0, x0, protected=False):
        h, w = 206, 41
        local = np.ones((h, w), bool)
        for xoff in (7, 19, 31):
            local[18:h - 18, xoff:xoff + 3] = False
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = local
        numbers[full] = 255
        if protected:
            template[full] = 255
        rgb[full] = np.array([224, 224, 224], np.uint8)
        roi = rgb[y0:y0 + h, x0:x0 + w]
        for yy0 in (14, 46, 82, 118, 154, 188):
            stroke = np.zeros_like(local)
            stroke[yy0:yy0 + 6, 2:w - 2] = True
            roi[local & stroke] = np.array([8, 8, 12], np.uint8)
        for yy0 in (62, 134):
            accent = np.zeros_like(local)
            accent[yy0:yy0 + 5, 5:w - 5] = True
            roi[local & accent] = np.array([184, 24, 44], np.uint8)
        return full

    wordmark = add_brand_strip(180, 650)
    protected_wordmark = add_brand_strip(180, 760, protected=True)

    digit = np.zeros((n, n), bool)
    digit[520:728, 220:252] = True
    digit[520:546, 194:278] = True
    digit[702:728, 194:278] = True
    numbers[digit] = 255
    rgb[digit] = np.array([224, 224, 222], np.uint8)
    rgb[digit & (np.indices((n, n))[1] % 15 < 2)] = np.array([68, 68, 70], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tall_pale_vertical_brand_wordmark"
    assert 3.60 <= info["components"][0]["aspect"] <= 5.35
    assert info["components"][0]["dark_text_components"] >= 3
    assert info["components"][0]["nonwhite_text_components"] >= 3
    assert (mask[wordmark] > 0).mean() > 0.90
    assert (mask[protected_wordmark] > 0).mean() == 0
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_tall_dark_backed_pale_vertical_sponsor_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_vertical_wordmark(y0, x0, protected=False):
        h, w = 179, 65
        yy, xx = np.indices((h, w))
        local = np.ones((h, w), bool)
        for xoff in (11, 25, 39, 53):
            local[12:h - 12, xoff:xoff + 1] = False
        for idx, yy0 in enumerate((16, 34, 52, 70, 88, 106, 124, 142, 160)):
            x1, x2 = (13, 27) if idx % 2 == 0 else (38, 52)
            local[yy0:yy0 + 12, x1:x2] = False

        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = local
        numbers[full] = 255
        if protected:
            template[full] = 255

        roi = rgb[y0:y0 + h, x0:x0 + w]
        dark_rows = (yy % 10) < 5
        pale_rows = (yy % 10 == 5) | (yy % 10 == 6)
        white_rows = (yy % 10) >= 7
        roi[local & dark_rows] = np.array([34, 34, 34], np.uint8)
        roi[local & pale_rows] = np.array([132, 138, 122], np.uint8)
        roi[local & white_rows] = np.array([238, 238, 232], np.uint8)
        green_marks = local & dark_rows & (xx >= 4) & (xx < 12)
        roi[green_marks] = np.array([74, 128, 70], np.uint8)
        return full

    wordmark = add_vertical_wordmark(428, 761)
    no_context = add_vertical_wordmark(142, 610)
    protected_wordmark = add_vertical_wordmark(428, 875, protected=True)

    sponsors[390:646, 688:730] = 255
    sponsors[382:654, 842:895] = 255
    sponsors[455:520, 828:838] = 255
    sponsors[numbers > 0] = 0

    true_digit = np.zeros((n, n), bool)
    true_digit[548:720, 430:466] = True
    true_digit[548:575, 408:500] = True
    true_digit[693:720, 408:500] = True
    true_digit[575:693, 474:500] = True
    numbers[true_digit] = 255
    rgb[true_digit] = np.array([226, 226, 220], np.uint8)
    rgb[true_digit & (np.indices((n, n))[1] % 17 < 3)] = np.array([50, 50, 52], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "tall_dark_backed_pale_vertical_sponsor_wordmark"
    assert 2.45 <= info["components"][0]["aspect"] <= 3.10
    assert info["components"][0]["white_text_components"] >= 12
    assert info["components"][0]["dark_text_components"] >= 6
    assert info["components"][0]["colored_text_components"] >= 8
    assert (mask[wordmark] > 0).mean() > 0.90
    assert (mask[no_context] > 0).mean() == 0
    assert (mask[protected_wordmark] > 0).mean() == 0
    assert (mask[true_digit] > 0).mean() < 0.05


def test_smart_tga_lower_right_mixed_red_white_sponsor_badge_demotes_from_numbers():
    n = 1024

    def add_mixed_badge(rgb, numbers, template=None, protected=False):
        y0, x0, h, w = 826, 809, 110, 151
        yy, xx = np.indices((h, w))
        left = np.rint(50.0 - (50.0 * yy / float(h - 1))).astype(int)
        right = left + 100
        local = (xx >= left) & (xx <= right)
        for yy0 in (12, 26, 40, 54, 68, 82, 96):
            row_left = int(left[yy0, 0])
            local[yy0:yy0 + 2, row_left + 25:row_left + 75] = False

        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = local
        numbers[full] = 255
        if protected and template is not None:
            template[full] = 255

        roi = rgb[y0:y0 + h, x0:x0 + w]
        cycle = yy % 14
        white_rows = cycle < 5
        red_rows = (cycle >= 5) & (cycle < 8)
        dark_rows = (cycle >= 8) & (cycle < 12)
        gray_rows = cycle >= 12
        roi[local & white_rows] = np.array([226, 226, 220], np.uint8)
        roi[local & red_rows] = np.array([188, 84, 98], np.uint8)
        roi[local & dark_rows] = np.array([42, 42, 44], np.uint8)
        roi[local & gray_rows] = np.array([122, 118, 116], np.uint8)
        return full

    rgb = np.full((n, n, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    badge = add_mixed_badge(rgb, numbers)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "lower_right_mixed_red_white_sponsor_badge"
    assert info["components"][0]["colored_text_components"] >= 8
    assert info["components"][0]["nonwhite_text_components"] >= 8
    assert (mask[badge] > 0).mean() > 0.90

    rgb_protected = np.full((n, n, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    numbers_protected = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    protected_badge = add_mixed_badge(rgb_protected, numbers_protected, template, protected=True)
    protected_mask, protected_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_protected, numbers_protected, empty, template, empty
    )
    assert protected_info["status"] == "empty"
    assert (protected_mask[protected_badge] > 0).mean() == 0

    rgb_number = np.full((n, n, 3), np.array([20, 22, 26], np.uint8), np.uint8)
    numbers_number = np.zeros((n, n), np.uint8)
    y0, x0, h, w = 826, 809, 110, 151
    yy, xx = np.indices((h, w))
    true_number = np.zeros((n, n), bool)
    local = ((xx - 75) / 70.0) ** 2 + ((yy - 55) / 50.0) ** 2 <= 1.0
    local[28:82, 60:92] = False
    true_number[y0:y0 + h, x0:x0 + w] = local
    numbers_number[true_number] = 255
    rgb_number[true_number] = np.array([232, 232, 226], np.uint8)
    rgb_number[true_number & (np.indices((n, n))[1] % 17 < 3)] = np.array([82, 82, 86], np.uint8)
    number_mask, number_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_number, numbers_number, empty, empty, empty
    )
    assert number_info["status"] == "empty"
    assert (number_mask[true_number] > 0).mean() == 0


def test_smart_tga_mixed_white_red_dark_sponsor_monogram_demotes_from_numbers():
    n = 1024
    fixture = Path(
        "_smart_tga_runs/cycle453_dlm_batch05_blue_panel_red_black_livery_fill_controls_v1/"
        "Dirt_Late_Model_car_num_1133016"
    )
    required = [
        fixture / "source_1024.png",
        fixture / "masks" / "numbers.png",
        fixture / "masks" / "sponsors.png",
        fixture / "masks" / "template.png",
        fixture / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle453 DLM 1133016 artifact fixture is not available")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    monogram = np.zeros(numbers.shape, bool)
    monogram[542:632, 693:799] = numbers[542:632, 693:799] > 0

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "mixed_white_red_dark_sponsor_monogram"
    )
    assert component["bbox"] == [693, 542, 106, 90]
    assert component["dark_text_components"] >= 4
    assert component["colored_text_components"] >= 3
    assert (mask[monogram] > 0).mean() > 0.90

    rgb_protected = np.full((n, n, 3), np.array([210, 20, 18], np.uint8), np.uint8)
    numbers_protected = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    protected_monogram = np.zeros((n, n), bool)
    protected_monogram[542:632, 693:799] = True
    numbers_protected[protected_monogram] = 255
    template[protected_monogram] = 255
    rgb_protected[protected_monogram] = np.array([226, 226, 222], np.uint8)
    protected_mask, protected_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_protected, numbers_protected, np.zeros((n, n), np.uint8), template, np.zeros((n, n), np.uint8)
    )
    assert protected_info["status"] == "empty"
    assert (protected_mask[protected_monogram] > 0).mean() == 0

    rgb_number = np.full((n, n, 3), np.array([210, 20, 18], np.uint8), np.uint8)
    numbers_number = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))
    true_digit = np.zeros((n, n), bool)
    y0, x0 = 542, 693
    outer = ((xx - (x0 + 54)) / 47.0) ** 2 + ((yy - (y0 + 45)) / 41.0) ** 2 <= 1.0
    inner = ((xx - (x0 + 54)) / 26.0) ** 2 + ((yy - (y0 + 45)) / 22.0) ** 2 <= 1.0
    true_digit |= outer & ~inner
    numbers_number[true_digit] = 255
    rgb_number[true_digit] = np.array([236, 236, 232], np.uint8)
    red_trim = true_digit & ((xx - x0) % 19 < 3)
    rgb_number[red_trim] = np.array([206, 52, 48], np.uint8)
    number_mask, number_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_number,
        numbers_number,
        np.zeros((n, n), np.uint8),
        np.zeros((n, n), np.uint8),
        np.zeros((n, n), np.uint8),
    )
    assert number_info["status"] == "empty"
    assert (number_mask[true_digit] > 0).mean() == 0


def test_smart_tga_large_pale_sponsor_panel_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    y0, x0, h, w = 184, 0, 107, 199
    panel = np.zeros((n, n), bool)
    panel[y0:y0 + h, x0:x0 + w] = True
    panel[y0 + 6:y0 + h - 6, x0 + 70:x0 + 154] = False
    panel[y0 + 44:y0 + 58, x0 + 130:x0 + 178] = True
    numbers[panel] = 255
    rgb[panel] = np.array([247, 247, 248], np.uint8)
    rgb[y0 + 22:y0 + 35, x0 + 18:x0 + 68][panel[y0 + 22:y0 + 35, x0 + 18:x0 + 68]] = np.array([226, 226, 230], np.uint8)

    mirror = np.zeros((n, n), bool)
    my0, mx0 = 896, 0
    mirror[my0:my0 + 106, mx0:mx0 + 177] = True
    mirror[my0 + 7:my0 + 99, mx0 + 61:mx0 + 137] = False
    mirror[my0 + 42:my0 + 56, mx0 + 116:mx0 + 160] = True
    numbers[mirror] = 255
    rgb[mirror] = np.array([246, 246, 247], np.uint8)

    mark_y, mark_x, mark_h, mark_w = 240, 450, 94, 150
    pale_mark = np.zeros((n, n), bool)
    pale_mark[mark_y:mark_y + mark_h, mark_x:mark_x + mark_w] = True
    pale_mark[mark_y + 7:mark_y + mark_h - 7, mark_x + 38:mark_x + 110] = False
    pale_mark[mark_y + 38:mark_y + 52, mark_x + 98:mark_x + 142] = True
    numbers[pale_mark] = 255
    rgb[pale_mark] = np.array([250, 246, 246], np.uint8)
    yy, xx = np.indices((n, n))
    red_tint = pale_mark & (yy >= mark_y + 38) & (yy < mark_y + 52) & (xx >= mark_x + 98) & (xx < mark_x + 142)
    rgb[red_tint] = np.array([248, 170, 170], np.uint8)

    digit = np.zeros((n, n), bool)
    digit[430:531, 434:474] = True
    digit[430:454, 434:594] = True
    digit[507:531, 434:594] = True
    digit[454:507, 530:594] = True
    numbers[digit] = 255
    rgb[digit] = np.array([238, 238, 238], np.uint8)
    rgb[digit & (np.indices((n, n))[1] % 9 < 2)] = np.array([228, 52, 42], np.uint8)
    rgb[digit & (np.indices((n, n))[0] % 13 < 3)] = np.array([246, 164, 34], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert {component["reason"] for component in info["components"]} == {
        "large_pale_sponsor_mark",
        "large_pale_sponsor_panel",
    }
    assert info["max_large_pale_panel_demote"] == 0.034
    assert (mask[panel] > 0).mean() > 0.95
    assert (mask[mirror] > 0).mean() > 0.95
    assert (mask[pale_mark] > 0).mean() > 0.95
    assert (mask[digit] > 0).mean() < 0.05


def test_smart_tga_large_pale_oval_sponsor_badge_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 32, 30], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def oval_badge_shape():
        h, w = 91, 130
        yy, xx = np.indices((h, w))
        left_outer = ((xx - 43) / 43.0) ** 2 + ((yy - 45) / 40.0) ** 2 <= 1.0
        left_inner = ((xx - 43) / 31.0) ** 2 + ((yy - 45) / 28.0) ** 2 <= 1.0
        right_fill = ((xx - 95) / 32.0) ** 2 + ((yy - 45) / 42.0) ** 2 <= 1.0
        return (left_outer & ~left_inner) | right_fill

    def add_badge(y0, x0, layer, protected=False):
        shape = oval_badge_shape()
        h, w = shape.shape
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        layer[full] = 255
        if protected:
            template[full] = 255
        local = rgb[y0:y0 + h, x0:x0 + w]
        local[shape] = np.array([210, 210, 204], np.uint8)

        dark = np.zeros_like(shape)
        for yy0, xx0, hh, ww in (
            (10, 28, 4, 34),
            (37, 8, 4, 26),
            (52, 8, 4, 26),
            (78, 28, 4, 34),
            (24, 82, 5, 26),
            (52, 84, 5, 24),
            (72, 88, 4, 18),
        ):
            dark[yy0:yy0 + hh, xx0:xx0 + ww] = True
        gray = np.zeros_like(shape)
        for yy0, xx0, hh, ww in (
            (18, 74, 5, 42),
            (31, 72, 5, 45),
            (64, 75, 5, 40),
            (83, 78, 4, 34),
        ):
            gray[yy0:yy0 + hh, xx0:xx0 + ww] = True
        local[shape & gray] = np.array([150, 150, 146], np.uint8)
        local[shape & dark] = np.array([36, 36, 36], np.uint8)
        return full

    badge = add_badge(180, 480, numbers)
    protected_badge = add_badge(340, 480, numbers, protected=True)

    yy, xx = np.indices((n, n))
    zero_digit = np.zeros((n, n), bool)
    z_y, z_x = 560, 488
    outer = ((xx - (z_x + 65)) / 48.0) ** 2 + ((yy - (z_y + 45)) / 42.0) ** 2 <= 1.0
    inner = ((xx - (z_x + 65)) / 31.0) ** 2 + ((yy - (z_y + 45)) / 27.0) ** 2 <= 1.0
    zero_digit |= outer & ~inner
    numbers[zero_digit] = 255
    rgb[zero_digit] = np.array([212, 212, 206], np.uint8)

    bright_digit = np.zeros((n, n), bool)
    bright_digit[716:807, 488:542] = True
    bright_digit[716:737, 488:610] = True
    bright_digit[786:807, 488:610] = True
    bright_digit[737:786, 576:610] = True
    numbers[bright_digit] = 255
    rgb[bright_digit] = np.array([246, 246, 244], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "large_pale_oval_sponsor_badge"
    assert info["components"][0]["dark_text_components"] >= 5
    assert (mask[badge] > 0).mean() > 0.95
    assert (mask[protected_badge] > 0).mean() == 0
    assert (mask[zero_digit] > 0).mean() == 0
    assert (mask[bright_digit] > 0).mean() < 0.05


def test_smart_tga_tall_red_white_oval_sponsor_badge_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([36, 72, 190], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_oval_badge(y0, x0, protected=False):
        h, w = 160, 72
        yy, xx = np.indices((h, w))
        oval = ((xx - 35.5) / 35.5) ** 2 + ((yy - 79.5) / 79.5) ** 2 <= 1.0
        target = (slice(y0, y0 + h), slice(x0, x0 + w))
        numbers[target][oval] = 255
        if protected:
            template[target][oval] = 255

        local = rgb[target]
        local[oval] = np.array([214, 214, 208], np.uint8)

        red = oval & (
            ((yy >= 8) & (yy <= 28) & (xx >= 14) & (xx <= 58))
            | ((yy >= 66) & (yy <= 84) & (xx >= 7) & (xx <= 65))
            | ((yy >= 118) & (yy <= 146) & (xx >= 16) & (xx <= 56))
        )
        dark = oval & (
            ((yy >= 36) & (yy <= 45) & (xx >= 11) & (xx <= 61))
            | ((yy >= 92) & (yy <= 104) & (xx >= 13) & (xx <= 59))
            | ((xx >= 29) & (xx <= 36) & (yy >= 18) & (yy <= 140))
        )
        white = oval & (
            ((yy >= 12) & (yy <= 18) & (xx >= 20) & (xx <= 52))
            | ((yy >= 72) & (yy <= 78) & (xx >= 13) & (xx <= 59))
            | ((yy >= 127) & (yy <= 134) & (xx >= 21) & (xx <= 51))
            | ((xx >= 18) & (xx <= 24) & (yy >= 50) & (yy <= 112))
            | ((xx >= 48) & (xx <= 54) & (yy >= 50) & (yy <= 112))
        )
        local[red] = np.array([214, 34, 38], np.uint8)
        local[dark] = np.array([34, 34, 36], np.uint8)
        local[white] = np.array([246, 246, 238], np.uint8)

        full = np.zeros((n, n), bool)
        full[target][oval] = True
        return full

    badge = add_oval_badge(450, 44)
    protected_badge = add_oval_badge(450, 160, protected=True)

    yy, xx = np.indices((n, n))
    smooth_zero = np.zeros((n, n), bool)
    z_y, z_x = 430, 720
    outer = ((xx - (z_x + 36)) / 31.0) ** 2 + ((yy - (z_y + 80)) / 76.0) ** 2 <= 1.0
    inner = ((xx - (z_x + 36)) / 18.0) ** 2 + ((yy - (z_y + 80)) / 53.0) ** 2 <= 1.0
    smooth_zero |= outer & ~inner
    numbers[smooth_zero] = 255
    rgb[smooth_zero] = np.array([238, 238, 230], np.uint8)

    horizontal_wordmark = np.zeros((n, n), bool)
    horizontal_wordmark[180:232, 460:600] = True
    numbers[horizontal_wordmark] = 255
    rgb[horizontal_wordmark] = np.array([210, 34, 38], np.uint8)
    rgb[190:199, 474:586] = np.array([246, 246, 238], np.uint8)
    rgb[210:218, 474:586] = np.array([34, 34, 36], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, template, empty
    )

    reasons = [component["reason"] for component in info["components"]]
    assert info["status"] == "applied"
    assert "tall_red_white_oval_sponsor_badge" in reasons
    target_components = [
        component for component in info["components"]
        if component["reason"] == "tall_red_white_oval_sponsor_badge"
    ]
    assert target_components[0]["white_text_components"] >= 5
    assert (mask[badge] > 0).mean() > 0.95
    assert (mask[protected_badge] > 0).mean() == 0
    assert (mask[smooth_zero] > 0).mean() == 0
    assert (mask[horizontal_wordmark] > 0).mean() == 0


def test_smart_tga_wide_yellow_white_service_sponsor_panel_demotes_from_numbers():
    n = 1024
    fixture = Path(
        "_smart_tga_runs/cycle460_dlm_batch08_tall_red_white_oval_controls_v1_nocache/"
        "Dirt_Late_Model_car_num_1135812"
    )
    required = [
        fixture / "source_1024.png",
        fixture / "masks" / "numbers.png",
        fixture / "masks" / "sponsors.png",
        fixture / "masks" / "template.png",
        fixture / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle460 DLM 1135812 artifact fixture is not available")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    panel = np.zeros(numbers.shape, bool)
    panel[718:774, 452:598] = numbers[718:774, 452:598] > 0

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "wide_yellow_white_service_sponsor_panel"
    )
    assert component["bbox"] == [452, 718, 146, 56]
    assert component["white_text_components"] >= 16
    assert component["dark_text_components"] >= 6
    assert component["colored_text_components"] >= 8
    assert (mask[panel] > 0).mean() > 0.90

    empty = np.zeros((n, n), np.uint8)
    rgb_protected = np.full((n, n, 3), np.array([74, 62, 48], np.uint8), np.uint8)
    numbers_protected = np.zeros((n, n), np.uint8)
    template_protected = np.zeros((n, n), np.uint8)
    protected_panel = np.zeros((n, n), bool)
    protected_panel[718:774, 452:598] = True
    numbers_protected[protected_panel] = 255
    template_protected[protected_panel] = 255
    rgb_protected[protected_panel] = np.array([172, 158, 138], np.uint8)
    protected_mask, protected_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_protected, numbers_protected, empty, template_protected, empty
    )
    assert protected_info["status"] == "empty"
    assert (protected_mask[protected_panel] > 0).mean() == 0

    rgb_green_number = np.full((n, n, 3), np.array([32, 30, 26], np.uint8), np.uint8)
    numbers_green = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))
    y0, x0, h, w = 718, 452, 82, 168
    digit_shell = np.zeros((n, n), bool)
    outer = ((xx - (x0 + 84)) / 82.0) ** 2 + ((yy - (y0 + 41)) / 39.0) ** 2 <= 1.0
    inner = ((xx - (x0 + 84)) / 56.0) ** 2 + ((yy - (y0 + 41)) / 22.0) ** 2 <= 1.0
    digit_shell |= outer & ~inner
    digit_shell[y0 + 8:y0 + 24, x0 + 23:x0 + w - 23] = True
    digit_shell[y0 + h - 24:y0 + h - 8, x0 + 23:x0 + w - 23] = True
    numbers_green[digit_shell] = 255
    rgb_green_number[digit_shell] = np.array([172, 214, 182], np.uint8)
    rgb_green_number[digit_shell & (xx % 19 < 5)] = np.array([242, 242, 232], np.uint8)
    rgb_green_number[digit_shell & (yy % 23 < 5)] = np.array([42, 68, 44], np.uint8)
    green_mask, green_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_green_number, numbers_green, empty, empty, empty
    )
    assert green_info["status"] == "empty"
    assert (green_mask[digit_shell] > 0).mean() == 0

    rgb_dark_number = np.full((n, n, 3), np.array([18, 16, 14], np.uint8), np.uint8)
    numbers_dark = np.zeros((n, n), np.uint8)
    true_number = np.zeros((n, n), bool)
    true_number[718:805, 291:472] = True
    true_number[735:788, 334:429] = False
    true_number[750:772, 374:472] = True
    numbers_dark[true_number] = 255
    rgb_dark_number[true_number] = np.array([44, 38, 18], np.uint8)
    rgb_dark_number[true_number & (xx % 17 < 5)] = np.array([194, 162, 38], np.uint8)
    dark_mask, dark_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_dark_number, numbers_dark, empty, empty, empty
    )
    assert dark_info["status"] == "empty"
    assert (dark_mask[true_number] > 0).mean() == 0


def test_smart_tga_wide_red_blue_white_sponsor_panel_demotes_from_numbers():
    n = 1024
    fixture = Path(
        "_smart_tga_runs/cycle461_dlm_batch09_tuckers_service_panel_controls_v1_nocache/"
        "Dirt_Late_Model_car_num_1117603"
    )
    required = [
        fixture / "source_1024.png",
        fixture / "masks" / "numbers.png",
        fixture / "masks" / "sponsors.png",
        fixture / "masks" / "template.png",
        fixture / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle461 DLM 1117603 artifact fixture is not available")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    panel = np.zeros(numbers.shape, bool)
    panel[282:335, 415:553] = numbers[282:335, 415:553] > 0

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    component = next(
        component
        for component in info["components"]
        if component["reason"] == "wide_red_blue_white_sponsor_panel"
    )
    assert component["bbox"] == [415, 282, 138, 53]
    assert component["blue_frac"] >= 0.20
    assert component["white_text_components"] >= 10
    assert component["dark_text_components"] >= 10
    assert (mask[panel] > 0).mean() > 0.90

    empty = np.zeros((n, n), np.uint8)
    rgb_protected = np.full((n, n, 3), np.array([35, 60, 185], np.uint8), np.uint8)
    numbers_protected = np.zeros((n, n), np.uint8)
    template_protected = np.zeros((n, n), np.uint8)
    protected_panel = np.zeros((n, n), bool)
    protected_panel[282:335, 415:553] = True
    numbers_protected[protected_panel] = 255
    template_protected[protected_panel] = 255
    rgb_protected[protected_panel] = np.array([184, 172, 208], np.uint8)
    protected_mask, protected_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_protected, numbers_protected, empty, template_protected, empty
    )
    assert protected_info["status"] == "empty"
    assert (protected_mask[protected_panel] > 0).mean() == 0

    yy, xx = np.indices((n, n))
    rgb_number = np.full((n, n, 3), np.array([22, 24, 32], np.uint8), np.uint8)
    numbers_number = np.zeros((n, n), np.uint8)
    true_number = np.zeros((n, n), bool)
    y0, x0, h, w = 282, 415, 62, 160
    outer = ((xx - (x0 + 80)) / 77.0) ** 2 + ((yy - (y0 + 31)) / 29.0) ** 2 <= 1.0
    inner = ((xx - (x0 + 80)) / 47.0) ** 2 + ((yy - (y0 + 31)) / 15.0) ** 2 <= 1.0
    true_number |= outer & ~inner
    true_number[y0 + 8:y0 + 22, x0 + 20:x0 + 140] = True
    true_number[y0 + 40:y0 + 54, x0 + 20:x0 + 140] = True
    numbers_number[true_number] = 255
    rgb_number[true_number] = np.array([224, 224, 220], np.uint8)
    rgb_number[true_number & (xx % 23 < 6)] = np.array([204, 36, 44], np.uint8)
    rgb_number[true_number & (yy % 29 < 7)] = np.array([48, 60, 178], np.uint8)
    number_mask, number_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb_number, numbers_number, empty, empty, empty
    )
    assert number_info["status"] == "empty"
    assert (number_mask[true_number] > 0).mean() == 0


def test_smart_tga_medium_sponsor_decal_logo_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 120, 650, 31, 73
    logo = np.zeros((n, n), bool)
    logo[y0:y0 + h, x0:x0 + w] = True
    logo[y0 + 7:y0 + 13, x0 + 9:x0 + 64] = False
    logo[y0 + 15:y0 + 18, x0 + 9:x0 + 64] = False
    logo[y0 + 21:y0 + 24, x0 + 7:x0 + 58] = False
    logo[y0 + 3:y0 + 28, x0 + 24:x0 + 28] = False
    logo[y0 + 2:y0 + 27, x0 + 47:x0 + 50] = False
    numbers[logo] = 255
    rgb[logo] = np.array([98, 126, 158], np.uint8)
    rgb[logo & ((xx - x0) % 13 < 5)] = np.array([232, 232, 220], np.uint8)
    rgb[logo & ((yy - y0) % 11 > 7)] = np.array([52, 62, 84], np.uint8)

    y1, x1, h1, w1 = 260, 810, 95, 26
    vertical_logo = np.zeros((n, n), bool)
    vertical_logo[y1:y1 + h1, x1:x1 + w1] = True
    vertical_logo[y1 + 5:y1 + 88, x1 + 8:x1 + 12] = False
    vertical_logo[y1 + 6:y1 + 88, x1 + 16:x1 + 20] = False
    vertical_logo[y1 + 14:y1 + 18, x1 + 2:x1 + 22] = False
    vertical_logo[y1 + 42:y1 + 47, x1 + 4:x1 + 25] = False
    numbers[vertical_logo] = 255
    rgb[vertical_logo] = np.array([84, 122, 162], np.uint8)
    rgb[vertical_logo & ((yy - y1) % 17 < 5)] = np.array([226, 226, 216], np.uint8)
    rgb[vertical_logo & ((xx - x1) % 9 > 5)] = np.array([56, 78, 108], np.uint8)

    red_digit = np.zeros((n, n), bool)
    red_digit[480:570, 260:304] = True
    red_digit[480:503, 260:350] = True
    red_digit[547:570, 260:350] = True
    red_digit[503:547, 304:350] = True
    numbers[red_digit] = 255
    rgb[red_digit] = np.array([236, 42, 38], np.uint8)

    smooth_pale_digit = np.zeros((n, n), bool)
    smooth_pale_digit[630:661, 650:723] = True
    numbers[smooth_pale_digit] = 255
    rgb[smooth_pale_digit] = np.array([228, 228, 220], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] >= 2
    assert sum(component["reason"] == "medium_sponsor_decal_logo" for component in info["components"]) == 2
    assert reasons <= {"medium_sponsor_decal_logo", "tiny_dense_logo_fragment"}
    assert (mask[logo] > 0).mean() > 0.90
    assert (mask[vertical_logo] > 0).mean() > 0.90
    assert (mask[red_digit] > 0).mean() < 0.05
    assert (mask[smooth_pale_digit] > 0).mean() == 0


def test_smart_tga_sponsor_logo_panels_demote_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 16, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    compact_label = (slice(234, 252), slice(552, 588))
    compact_mask = np.zeros((n, n), bool)
    compact_mask[compact_label] = True
    numbers[compact_label] = 255
    sponsors[228:258, 540:600] = 255
    rgb[compact_label] = np.array([176, 186, 214], np.uint8)
    rgb[compact_mask & ((xx - 552) % 9 < 4)] = np.array([242, 242, 236], np.uint8)
    rgb[compact_mask & ((yy - 234) % 17 < 1)] = np.array([188, 42, 44], np.uint8)
    rgb[compact_mask & ((xx - 552) % 17 > 13)] = np.array([92, 126, 215], np.uint8)

    medium_logo = np.zeros((n, n), bool)
    medium_logo[709:751, 28:156] = True
    medium_logo[715:720, 38:146] = False
    medium_logo[728:731, 36:150] = False
    medium_logo[739:742, 48:142] = False
    medium_logo[711:749, 82:86] = False
    numbers[medium_logo] = 255
    rgb[medium_logo] = np.array([155, 115, 70], np.uint8)
    rgb[medium_logo & ((xx + yy) % 20 < 5)] = np.array([245, 210, 20], np.uint8)
    rgb[medium_logo & ((xx * 2 + yy) % 20 >= 4) & ((xx * 2 + yy) % 20 < 8)] = np.array([210, 25, 20], np.uint8)
    rgb[medium_logo & ((xx + yy * 3) % 20 >= 7) & ((xx + yy * 3) % 20 < 10)] = np.array([10, 12, 24], np.uint8)
    rgb[medium_logo & ((xx * 3 + yy) % 20 == 10)] = np.array([240, 230, 210], np.uint8)

    true_number = np.zeros((n, n), bool)
    true_number[833:960, 809:951] = True
    true_number[852:941, 842:918] = False
    true_number[833:860, 809:951] = True
    true_number[918:960, 809:951] = True
    true_number[860:918, 809:850] = True
    numbers[true_number] = 255
    rgb[true_number] = np.array([238, 238, 232], np.uint8)
    rgb[true_number & ((xx - 809) % 13 < 3)] = np.array([232, 62, 58], np.uint8)
    rgb[true_number & ((yy - 833) % 19 < 3)] = np.array([150, 170, 180], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert {"bright_compact_sponsor_label_panel", "medium_sponsor_logo_panel"} <= reasons
    assert (mask[compact_mask] > 0).mean() > 0.95
    assert (mask[medium_logo] > 0).mean() > 0.95
    assert (mask[true_number] > 0).mean() < 0.05


def test_smart_tga_compact_pastel_sponsor_badge_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 812, 554, 21, 27
    badge = np.zeros((n, n), bool)
    local = np.zeros((h, w), bool)
    local[:, :] = True
    local[4:7, 5:23] = False
    local[10:12, 4:25] = False
    local[15:17, 7:22] = False
    local[3:18, 12:14] = False
    badge[y0:y0 + h, x0:x0 + w] = local
    numbers[badge] = 255
    rgb[badge] = np.array([214, 178, 193], np.uint8)
    rgb[badge & ((xx - x0) % 8 < 3)] = np.array([244, 240, 236], np.uint8)
    rgb[badge & ((yy - y0) % 7 == 0)] = np.array([210, 54, 86], np.uint8)
    rgb[badge & ((xx - x0 + yy - y0) % 17 == 0)] = np.array([78, 108, 192], np.uint8)

    tiny_number_a = np.zeros((n, n), bool)
    tiny_number_a[914:942, 260:298] = True
    tiny_number_a[918:926, 270:286] = False
    tiny_number_a[932:938, 270:288] = False
    numbers[tiny_number_a] = 255
    rgb[tiny_number_a] = np.array([188, 176, 174], np.uint8)
    rgb[tiny_number_a & ((xx - 260) % 11 < 3)] = np.array([236, 234, 228], np.uint8)
    rgb[tiny_number_a & ((yy - 914) % 13 == 0)] = np.array([72, 76, 82], np.uint8)

    tiny_number_b = np.zeros((n, n), bool)
    tiny_number_b[914:943, 546:585] = True
    tiny_number_b[919:926, 557:574] = False
    tiny_number_b[933:939, 558:575] = False
    numbers[tiny_number_b] = 255
    rgb[tiny_number_b] = np.array([184, 168, 168], np.uint8)
    rgb[tiny_number_b & ((xx - 546) % 12 < 4)] = np.array([232, 230, 224], np.uint8)
    rgb[tiny_number_b & ((yy - 914) % 13 == 1)] = np.array([76, 80, 88], np.uint8)

    smooth_pale_chip = np.zeros((n, n), bool)
    smooth_pale_chip[620:641, 650:677] = True
    numbers[smooth_pale_chip] = 255
    rgb[smooth_pale_chip] = np.array([230, 226, 220], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert any(component["reason"] == "compact_pastel_sponsor_badge" for component in info["components"])
    assert (mask[badge] > 0).mean() > 0.90
    assert (mask[tiny_number_a] > 0).mean() < 0.05
    assert (mask[tiny_number_b] > 0).mean() < 0.05
    assert (mask[smooth_pale_chip] > 0).mean() == 0


def test_smart_tga_compact_script_sponsor_wordmark_demotes_from_numbers():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.indices((n, n))

    y0, x0, h, w = 275, 188, 37, 107
    script_wordmark = np.zeros((n, n), bool)
    script_wordmark[y0:y0 + h, x0:x0 + w] = True
    script_wordmark[y0 + 3:y0 + 7, x0 + 9:x0 + 98] = False
    script_wordmark[y0 + 13:y0 + 16, x0 + 6:x0 + 104] = False
    script_wordmark[y0 + 22:y0 + 25, x0 + 10:x0 + 100] = False
    script_wordmark[y0 + 29:y0 + 33, x0 + 15:x0 + 95] = False
    script_wordmark[y0 + 6:y0 + 32, x0 + 43:x0 + 48] = False
    numbers[script_wordmark] = 255
    rgb[script_wordmark] = np.array([45, 65, 130], np.uint8)
    rgb[script_wordmark & ((xx - x0) % 11 < 4)] = np.array([235, 235, 225], np.uint8)
    rgb[script_wordmark & ((yy - y0) % 17 > 13)] = np.array([70, 95, 165], np.uint8)

    red_digit = np.zeros((n, n), bool)
    red_digit[500:590, 250:294] = True
    red_digit[500:523, 250:340] = True
    red_digit[567:590, 250:340] = True
    red_digit[523:567, 294:340] = True
    numbers[red_digit] = 255
    rgb[red_digit] = np.array([236, 42, 38], np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    assert info["status"] == "applied"
    assert any(component["reason"] == "compact_script_sponsor_wordmark" for component in info["components"])
    assert (mask[script_wordmark] > 0).mean() > 0.90
    assert (mask[red_digit] > 0).mean() < 0.05


def test_smart_tga_shallow_mixed_contingency_wordmark_strip_demotes_real_dlm_1006305():
    sample = Path(
        "_smart_tga_runs/cycle545_dlm_next4_after_1004124_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1006305"
    )
    paint = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/"
        "SPB Smart TGA Examples/Dirt Late Model/car_num_1006305.tga"
    )
    required = [
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        paint,
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle545 DLM 1006305 diagnostic artifact not present")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, *_ = load_paint_rgb_float01(str(paint), target_size=1024)
    rgb = np.clip(
        tex[:, :, :3] * (255.0 if float(np.nanmax(tex[:, :, :3])) <= 1.5 else 1.0),
        0,
        255,
    ).astype(np.uint8)
    numbers = np.array(Image.open(required[0]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    brand = np.zeros_like(numbers)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "shallow_mixed_contingency_wordmark_strip"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [17, 226, 133, 38]
    assert component["dark_text_components"] >= 12
    assert component["nonwhite_text_components"] >= 5
    assert component["broad_near_sponsor"] >= 0.90

    penske_strip = numbers[226:264, 17:150] > 0
    penske_demoted = mask[226:264, 17:150] > 0
    assert float((penske_demoted & penske_strip).sum()) / float(max(1, penske_strip.sum())) > 0.98

    top_true_number = numbers[207:334, 268:600] > 0
    side_true_number = numbers[723:824, 274:460] > 0
    lower_true_number = numbers[903:992, 829:956] > 0
    assert int((mask[207:334, 268:600] > 0).sum()) == 0
    assert int((mask[723:824, 274:460] > 0).sum()) == 0
    assert int((mask[903:992, 829:956] > 0).sum()) == 0
    assert top_true_number.any() and side_true_number.any() and lower_true_number.any()

    white_block_a = numbers[703:731, 695:750] > 0
    white_block_b = numbers[704:799, 696:912] > 0
    assert int((mask[703:731, 695:750] > 0).sum()) == 0
    assert int((mask[704:799, 696:912] > 0).sum()) == 0
    assert white_block_a.any() and white_block_b.any()


def test_smart_tga_number_trim_fragment_recovers_from_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([9, 12, 25], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[713:721, 260:424] = True
    number[713:760, 260:292] = True
    number[750:772, 260:410] = True
    number[760:802, 388:424] = True
    number[786:802, 260:424] = True
    numbers[number] = 255
    rgb[number] = np.array([250, 247, 242], np.uint8)

    def add_thin_component(y0, x0):
        h, w = 8, 114
        yy, xx = np.indices((h, w))
        mask = (yy == 3) | ((xx % 13 == 0) & (yy >= 0) & (yy < h))
        sponsors[y0:y0 + h, x0:x0 + w][mask] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[mask] = np.array([180, 28, 132], np.uint8)
        sub[mask & (xx % 11 == 0)] = np.array([236, 42, 176], np.uint8)
        return np.zeros((n, n), bool) | np.pad(mask, ((y0, n - y0 - h), (x0, n - x0 - w)))

    trim = add_thin_component(721, 300)
    interior_sponsor = add_thin_component(735, 300)
    outside_sponsor = add_thin_component(350, 720)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "number_trim_fragment"
    assert (mask[trim] > 0).mean() > 0.90
    assert (mask[interior_sponsor] > 0).mean() == 0
    assert (mask[outside_sponsor] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_dense_outline_sponsor_stripe():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[190:300, 250:440] = True
    numbers[number] = 255
    rgb[number] = np.array([238, 226, 24], np.uint8)

    def add_dense_stripe(
        y0,
        x0,
        h=32,
        w=2,
        color=np.array([220, 34, 214], np.uint8),
        protect=False,
        textured=True,
    ):
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = True
        numbers[full] = 0
        sponsors[full] = 255
        rgb[full] = color
        if textured:
            yy, xx = np.indices((h, w))
            sub = rgb[y0:y0 + h, x0:x0 + w]
            sub[(yy + xx) % 2 == 0] = np.array([236, 42, 202], np.uint8)
            sub[(yy + xx) % 2 == 1] = np.array([42, 206, 236], np.uint8)
        if protect:
            template[full] = 255
        return full

    positive = add_dense_stripe(220, 286)
    remote = add_dense_stripe(520, 286)
    protected = add_dense_stripe(232, 350, protect=True)
    thick = add_dense_stripe(240, 390, w=7)
    muted = add_dense_stripe(246, 410, color=np.array([118, 118, 122], np.uint8), textured=False)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert reasons == {"dense_number_outline_sponsor_fragment"}
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[remote] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0
    assert (mask[thick] > 0).mean() == 0
    assert (mask[muted] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_cool_blue_outline_sponsor_sliver():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[200:212, 100:260] = True
    number[200:320, 100:132] = True
    number[256:268, 100:260] = True
    number[256:320, 228:260] = True
    number[308:320, 100:260] = True
    positive = np.zeros((n, n), bool)
    positive[204:205, 170:195] = True
    number[positive] = False
    numbers[number] = 255
    rgb[number] = np.array([246, 246, 242], np.uint8)
    rgb[number & ((np.indices((n, n))[0] % 17) == 0)] = np.array([10, 18, 90], np.uint8)

    sponsors[positive] = 255
    rgb[positive] = np.array([0, 42, 226], np.uint8)

    remote = np.zeros((n, n), bool)
    remote[420:421, 170:195] = True
    sponsors[remote] = 255
    rgb[remote] = np.array([0, 42, 226], np.uint8)

    protected = np.zeros((n, n), bool)
    protected[206:207, 210:235] = True
    sponsors[protected] = 255
    template[protected] = 255
    rgb[protected] = np.array([0, 42, 226], np.uint8)

    warm = np.zeros((n, n), bool)
    warm[208:209, 136:161] = True
    sponsors[warm] = 255
    rgb[warm] = np.array([226, 92, 20], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert any(component["reason"] == "cool_blue_number_outline_sponsor_sliver" for component in info["components"])
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[remote] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0
    assert (mask[warm] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_red_number_outline_sponsor_shell():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[214:284, 190:295] = True
    numbers[number] = 255
    rgb[number] = np.array([246, 238, 238], np.uint8)

    def add_sparse_red_shell(y0, x0, h=84, w=121, protect=False):
        yy, xx = np.indices((h, w))
        shell = (yy < 3) | (yy >= h - 3) | (xx < 3) | (xx >= w - 3)
        shell &= ((xx + 2 * yy) % 3) != 0
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shell
        sponsors[full] = 255
        rgb[full] = np.array([182, 18, 18], np.uint8)
        rgb[full & ((np.indices((n, n))[0] % 7) == 0)] = np.array([226, 34, 34], np.uint8)
        if protect:
            template[full] = 255
        return full

    def add_red_chip(y0, x0, h=30, w=23, protect=False):
        yy, xx = np.indices((h, w))
        chip = ((xx >= yy * 0.34 + 2) & (xx <= yy * 0.34 + 10)) | (((yy % 6) == 0) & (xx < 19))
        chip &= ((xx + yy) % 5) != 0
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = chip
        numbers[full] = 0
        sponsors[full] = 255
        rgb[full] = np.array([170, 22, 22], np.uint8)
        if protect:
            template[full] = 255
        return full

    outline_shell = add_sparse_red_shell(206, 182)
    outline_chip = add_red_chip(232, 240)
    remote_shell = add_sparse_red_shell(506, 182)
    protected_chip = add_red_chip(244, 206, protect=True)

    remote_panel = np.zeros((n, n), bool)
    remote_panel[420:470, 506:646] = True
    sponsors[remote_panel] = 255
    rgb[remote_panel] = np.array([190, 24, 22], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"red_number_outline_sponsor_fragment"}
    assert (mask[outline_shell] > 0).mean() > 0.90
    assert (mask[outline_chip] > 0).mean() > 0.90
    assert (mask[remote_shell] > 0).mean() == 0
    assert (mask[protected_chip] > 0).mean() == 0
    assert (mask[remote_panel] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_micro_red_small_number_outline():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 16, 19], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    grid_y, grid_x = np.indices((n, n))

    def add_small_number_core(y0, x0):
        yy, xx = np.indices((67, 39))
        core = (
            ((xx >= yy * 0.22 + 5) & (xx <= yy * 0.22 + 24))
            | (((yy % 18) < 5) & (xx >= 6) & (xx <= 34))
        )
        core &= ((xx + 2 * yy) % 9) != 0
        full = np.zeros((n, n), bool)
        full[y0:y0 + 67, x0:x0 + 39] = core
        numbers[full] = 255
        rgb[full] = np.array([230, 230, 230], np.uint8)
        dark_core = full & ((grid_y + grid_x) % 5 == 0)
        mid_core = full & ((grid_y + 2 * grid_x) % 11 == 0)
        rgb[dark_core] = np.array([38, 38, 38], np.uint8)
        rgb[mid_core & ~dark_core] = np.array([138, 138, 138], np.uint8)
        return full

    add_small_number_core(404, 420)
    add_small_number_core(404, 520)

    def add_micro_chip(y0, x0, protect=False):
        cyy, cxx = np.indices((41, 29))
        center = np.rint(cyy * 0.56 + 2).astype(int)
        chip = cxx == center
        chip |= ((cyy % 8) == 0) & (cxx == center + 1)
        full = np.zeros((n, n), bool)
        full[y0:y0 + 41, x0:x0 + 29] = chip
        sponsors[full] = 255
        rgb[full] = np.array([160, 20, 20], np.uint8)
        rgb[full & ((grid_y % 3) == 0)] = np.array([72, 20, 20], np.uint8)
        if protect:
            template[full] = 255
        return full

    outline_chip = add_micro_chip(431, 423)
    remote_chip = add_micro_chip(740, 423)
    protected_chip = add_micro_chip(431, 523, protect=True)

    remote_logo = np.zeros((n, n), bool)
    remote_logo[180:210, 620:658] = True
    sponsors[remote_logo] = 255
    rgb[remote_logo] = np.array([168, 24, 24], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "micro_red_number_outline_sponsor_fragment"
    assert (mask[outline_chip] > 0).mean() > 0.90
    assert (mask[remote_chip] > 0).mean() == 0
    assert (mask[protected_chip] > 0).mean() == 0
    assert (mask[remote_logo] > 0).mean() == 0


def test_smart_tga_number_trim_recovers_red_dark_paint_outline_subcomponents_real_dlm_992082():
    sample = Path(
        "_smart_tga_runs/cycle581_dlm_next4_family_probe_v1_nocache/"
        "Dirt_Late_Model_car_num_992082"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle581 DLM 992082 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    reasons = {component["reason"] for component in info["components"]}
    assert "red_dark_number_outline_paint_subcomponent" in reasons
    assert "dark_number_shadow_paint_subcomponent" in reasons
    assert info["component_count"] >= 6

    red_outline = mask[920:931, 890:902] > 0
    assert int(red_outline.sum()) >= 28
    lower_red_outline = mask[947:958, 863:871] > 0
    assert int(lower_red_outline.sum()) >= 24
    dark_shadow = mask[863:889, 838:852] > 0
    assert int(dark_shadow.sum()) >= 72

    broad_lower_livery = mask[921:982, 811:853] > 0
    assert int(broad_lower_livery.sum()) == 0
    upper_sponsor_panel = mask[891:937, 852:876] > 0
    assert int(upper_sponsor_panel.sum()) <= 6
    mid_sponsor_panel = mask[891:947, 852:876] > 0
    assert int(mid_sponsor_panel.sum()) <= 16


def test_smart_tga_number_trim_recovers_neutral_paint_outline_subcomponents_real_dlm_1005403():
    sample = Path(
        "_smart_tga_runs/cycle589_dlm_1005403_left_edge_thin_crumb_v4_nocache/"
        "Dirt_Late_Model_car_num_1005403"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle589 DLM 1005403 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    reasons = {component["reason"] for component in info["components"]}
    assert "neutral_number_outline_paint_subcomponent" in reasons
    assert info["component_count"] >= 20
    assert info["added_px"] <= 700

    assert int((mask[296:311, 396:413] > 0).sum()) >= 12
    assert int((mask[750:756, 306:330] > 0).sum()) >= 20
    assert int((mask[250:252, 331:357] > 0).sum()) >= 10
    assert int((mask[328:332, 305:323] > 0).sum()) >= 20

    red_sponsor_review_control = mask[206:231, 751:768] > 0
    assert int(red_sponsor_review_control.sum()) == 0


def test_smart_tga_final_layer_priority_removes_real_dlm_992082_overlaps():
    sample = Path(
        "_smart_tga_runs/cycle581_dlm_992082_red_dark_number_outline_v1_nocache/"
        "Dirt_Late_Model_car_num_992082"
    )
    required = [
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle581 DLM 992082 diagnostic artifact not present")

    numbers = np.array(Image.open(required[0]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)

    assert int(((numbers > 0) & (sponsors > 0)).sum()) == 41
    assert int(((sponsors > 0) & (template > 0)).sum()) == 140

    info = car_layers_mod._enforce_smart_tga_layer_priority(
        numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["sponsor_from_numbers_px"] == 41
    assert info["template_from_sponsors_px"] == 140
    assert int(((numbers > 0) & (sponsors > 0)).sum()) == 0
    assert int(((numbers > 0) & (template > 0)).sum()) == 0
    assert int(((numbers > 0) & (brand > 0)).sum()) == 0
    assert int(((sponsors > 0) & (template > 0)).sum()) == 0
    assert int(((sponsors > 0) & (brand > 0)).sum()) == 0
    assert int(((template > 0) & (brand > 0)).sum()) == 0


def test_smart_tga_number_trim_fragment_recovers_cool_paint_outline_holes():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[120:250, 120:340] = True
    numbers[number] = 255
    rgb[number] = np.array([244, 238, 232], np.uint8)

    def carve_number_hole(y0, x0, h, w, color, warm=False):
        yy, xx = np.indices((h, w))
        if w <= 10:
            vertical_strokes = (xx == 1) | (xx == 2) | (xx == w - 2)
            cross_chips = ((yy % 6) == 0) & (xx >= 0) & (xx < w)
            hole = vertical_strokes | cross_chips
        else:
            hole = ((xx >= yy * 0.35) & (xx <= yy * 0.35 + 9)) | (((yy % 7) == 0) & (xx >= 1) & (xx < w - 1))
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = hole
        numbers[full] = 0
        rgb[full] = color
        if warm:
            rgb[full & ((np.indices((n, n))[0] + np.indices((n, n))[1]) % 5 == 0)] = np.array([236, 132, 16], np.uint8)
        return full

    cool_tall = carve_number_hole(146, 302, 29, 8, np.array([35, 134, 229], np.uint8))
    cool_diag = carve_number_hole(194, 238, 30, 19, np.array([28, 126, 220], np.uint8))
    warm_hole = carve_number_hole(132, 148, 26, 18, np.array([226, 120, 18], np.uint8), warm=True)

    sponsors[500:620, 500:650] = 255
    rgb[500:620, 500:650] = np.array([240, 240, 236], np.uint8)
    remote = np.zeros((n, n), bool)
    yy, xx = np.indices((26, 18))
    remote_hole = ((xx >= yy * 0.35) & (xx <= yy * 0.35 + 9))
    remote[540:566, 560:578] = remote_hole
    sponsors[remote] = 0
    rgb[remote] = np.array([30, 132, 224], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"cool_number_outline_paint_fragment"}
    assert (mask[cool_tall] > 0).mean() > 0.90
    assert (mask[cool_diag] > 0).mean() > 0.90
    assert (mask[warm_hole] > 0).mean() == 0
    assert (mask[remote] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_pale_paint_outline_chips():
    n = 768
    rgb = np.full((n, n, 3), np.array([16, 18, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[120:360, 80:330] = True
    numbers[number] = 255
    rgb[number] = np.array([246, 239, 235], np.uint8)

    sponsors[520:620, 500:650] = 255
    rgb[520:620, 500:650] = np.array([242, 242, 236], np.uint8)

    def carve_pale_chip(y0, x0, h, w, sparse=False):
        yy, xx = np.indices((h, w))
        if sparse:
            chip = ((xx >= yy) & (xx <= yy + 1)) | (((yy % 6) == 0) & (xx < 18))
        else:
            chip = ((xx + yy) % 4) != 0
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = chip
        numbers[full] = 0
        rgb[full] = np.array([236, 204, 222], np.uint8)
        rgb[full & ((np.indices((n, n))[0] + np.indices((n, n))[1]) % 5 == 0)] = np.array(
            [255, 246, 250], np.uint8
        )
        return full

    compact_chip = carve_pale_chip(196, 126, 10, 7)
    sparse_chip = carve_pale_chip(230, 185, 18, 24, sparse=True)

    remote = np.zeros((n, n), bool)
    yy, xx = np.indices((18, 24))
    remote_sparse = ((xx >= yy) & (xx <= yy + 1)) | (((yy % 6) == 0) & (xx < 18))
    remote[430:448, 90:114] = remote_sparse
    rgb[remote] = np.array([238, 206, 224], np.uint8)

    warm = np.zeros((n, n), bool)
    yy, xx = np.indices((14, 18))
    warm_chip = ((yy % 4) == 0) | ((xx == 4) & (yy > 1))
    warm[260:274, 250:268] = warm_chip
    numbers[warm] = 0
    rgb[warm] = np.array([232, 118, 32], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"pale_number_outline_paint_fragment"}
    assert (mask[compact_chip] > 0).mean() > 0.90
    assert (mask[sparse_chip] > 0).mean() > 0.90
    assert (mask[remote] > 0).mean() == 0
    assert (mask[warm] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_mixed_micro_number_detail():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[120:300, 120:430] = True
    numbers[number] = 255
    rgb[number] = np.array([242, 236, 226], np.uint8)

    sponsors[540:610, 540:650] = 255
    rgb[540:610, 540:650] = np.array([238, 238, 232], np.uint8)

    pattern = np.ones((5, 5), bool)

    def carve_micro(y0, x0, mode="mixed", protect=False):
        full = np.zeros((n, n), bool)
        full[y0:y0 + 5, x0:x0 + 5] = pattern
        numbers[full] = 0
        if protect:
            template[full] = 255
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if mode == "solid":
                rgb[yy0, xx0] = np.array([214, 96, 16], np.uint8)
            elif idx % 5 in (0, 1, 2):
                rgb[yy0, xx0] = np.array([214, 96, 16], np.uint8)
            elif idx % 5 == 3:
                rgb[yy0, xx0] = np.array([242, 236, 226], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([42, 30, 26], np.uint8)
        return full

    positive = carve_micro(196, 248)
    solid_inside_number = carve_micro(230, 300, mode="solid")
    protected = carve_micro(254, 354, protect=True)
    remote = carve_micro(430, 248)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert "mixed_number_micro_paint_detail" in reasons
    assert (mask[positive] > 0).mean() > 0.90
    assert (mask[solid_inside_number] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0
    assert (mask[remote] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_pale_number_interior_fill():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy_all, xx_all = np.indices((n, n))

    number = np.zeros((n, n), bool)
    number[126:272, 90:340] = True
    numbers[number] = 255
    rgb[number] = np.array([245, 242, 236], np.uint8)

    def carve_pale_fill(y0, x0, h, w):
        yy, xx = np.indices((h, w))
        shape = (xx >= yy * 0.45 + 4) & (xx <= yy * 0.45 + w - 12)
        shape |= ((yy < 8) & (xx >= 16) & (xx <= w - 18))
        shape |= ((yy > h - 9) & (xx >= 10) & (xx <= w - 24))
        shape &= ((xx + yy) % 4) != 0
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        numbers[full] = 0
        rgb[full] = np.array([226, 194, 194], np.uint8)
        texture = full & (((yy_all + xx_all) % 13 == 0) | ((xx_all - x0) % 17 == 0))
        rgb[texture] = np.array([206, 154, 154], np.uint8)
        return full

    pale_fill = carve_pale_fill(164, 158, 36, 64)

    red_livery_hole = np.zeros((n, n), bool)
    yy, xx = np.indices((34, 58))
    red_shape = (xx >= yy * 0.42 + 3) & (xx <= yy * 0.42 + 48)
    red_livery_hole[206:240, 224:282] = red_shape
    numbers[red_livery_hole] = 0
    rgb[red_livery_hole] = np.array([232, 48, 36], np.uint8)

    sponsors[510:620, 500:664] = 255
    rgb[510:620, 500:664] = np.array([242, 242, 236], np.uint8)
    remote_fill = np.zeros((n, n), bool)
    yy, xx = np.indices((36, 64))
    remote_shape = (xx >= yy * 0.45 + 4) & (xx <= yy * 0.45 + 52)
    remote_shape &= ((xx + yy) % 4) != 0
    remote_fill[542:578, 548:612] = remote_shape
    sponsors[remote_fill] = 0
    rgb[remote_fill] = np.array([226, 194, 194], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert reasons == {"pale_number_interior_paint_fill"}
    assert (mask[pale_fill] > 0).mean() > 0.90
    assert (mask[red_livery_hole] > 0).mean() == 0
    assert (mask[remote_fill] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_monochrome_number_interior_fill():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[120:360, 96:430] = True
    numbers[number] = 255
    rgb[number] = np.array([8, 8, 10], np.uint8)

    def carve_mono_fill(y0, x0, h=18, w=36, protect=False, colored=False):
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = True
        numbers[full] = 0
        if protect:
            template[full] = 255
        if colored:
            rgb[full] = np.array([220, 66, 24], np.uint8)
        else:
            rgb[full] = np.array([124, 124, 124], np.uint8)
            rgb[y0:y0 + 6, x0:x0 + w] = np.array([236, 236, 232], np.uint8)
            rgb[y0 + h - 6:y0 + h, x0:x0 + w] = np.array([34, 34, 36], np.uint8)
        return full

    def carve_sponsor_outline(y0, x0, h=16, w=30):
        local = np.zeros((h, w), bool)
        local[:2, :] = True
        local[-2:, :] = True
        local[:, :2] = True
        local[:, -2:] = True
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = local
        numbers[full] = 0
        sponsors[full] = 255
        rgb[full] = np.array([236, 236, 232], np.uint8)
        coords = np.argwhere(full)
        dark = coords[::4]
        rgb[dark[:, 0], dark[:, 1]] = np.array([36, 36, 38], np.uint8)
        return full

    paint_fill = carve_mono_fill(190, 226)
    sponsor_outline = carve_sponsor_outline(246, 250)
    remote_fill = carve_mono_fill(520, 226)
    colored_inside_number = carve_mono_fill(190, 310, colored=True)
    protected_inside_number = carve_mono_fill(292, 304, protect=True)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert reasons == {"monochrome_number_interior_fill"}
    assert info["component_count"] == 2
    assert (mask[paint_fill] > 0).mean() > 0.95
    assert (mask[sponsor_outline] > 0).mean() > 0.95
    assert (mask[remote_fill] > 0).mean() == 0
    assert (mask[colored_inside_number] > 0).mean() == 0
    assert (mask[protected_inside_number] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_warm_paint_outline_chips():
    n = 768
    rgb = np.full((n, n, 3), np.array([15, 18, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[120:300, 80:360] = True
    numbers[number] = 255
    rgb[number] = np.array([246, 241, 235], np.uint8)

    sponsors[530:620, 510:650] = 255
    rgb[530:620, 510:650] = np.array([242, 242, 236], np.uint8)

    def carve_warm_trim(y0, x0, h, w, color, dense=False):
        yy, xx = np.indices((h, w))
        if dense:
            chip = ((xx + yy) % 9) != 0
        else:
            chip = ((xx >= yy * 0.65) & (xx <= yy * 0.65 + 10)) | (((yy % 6) == 0) & (xx > 2))
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = chip
        numbers[full] = 0
        rgb[full] = color
        return full

    dark_brown_trim = carve_warm_trim(176, 210, 18, 34, np.array([92, 55, 30], np.uint8))
    yy_all, xx_all = np.indices((n, n))
    rgb[dark_brown_trim & (((yy_all + xx_all) % 5) == 0)] = np.array([150, 112, 40], np.uint8)
    muted_orange_chip = carve_warm_trim(235, 118, 10, 12, np.array([154, 112, 40], np.uint8), dense=True)
    bright_livery_hole = carve_warm_trim(250, 278, 18, 24, np.array([234, 125, 24], np.uint8))

    remote = np.zeros((n, n), bool)
    yy, xx = np.indices((18, 34))
    remote_chip = ((xx >= yy * 0.65) & (xx <= yy * 0.65 + 10)) | (((yy % 6) == 0) & (xx > 2))
    remote[430:448, 90:124] = remote_chip
    rgb[remote] = np.array([92, 55, 30], np.uint8)
    rgb[remote & (((yy_all + xx_all) % 5) == 0)] = np.array([150, 112, 40], np.uint8)

    red_chip = np.zeros((n, n), bool)
    yy, xx = np.indices((12, 14))
    red_shape = ((xx + yy) % 5) != 0
    red_chip[148:160, 316:330] = red_shape
    numbers[red_chip] = 0
    rgb[red_chip] = np.array([190, 30, 36], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert reasons == {"warm_number_outline_paint_fragment"}
    assert (mask[dark_brown_trim] > 0).mean() > 0.90
    assert (mask[muted_orange_chip] > 0).mean() > 0.90
    assert (mask[bright_livery_hole] > 0).mean() == 0
    assert (mask[remote] > 0).mean() == 0
    assert (mask[red_chip] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_dlm_tiny_number_detail_paint_chips():
    sample = Path(
        "_smart_tga_runs/cycle446_dlm_batch05_yellow_dark_wordmark_controls_v1/"
        "Dirt_Late_Model_car_num_1124938"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle446 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    detail_components = [
        component
        for component in info["components"]
        if component["reason"]
        in {
            "tiny_warm_number_detail_paint_chip",
            "tiny_dark_number_detail_paint_chip",
        }
    ]
    bboxes = {tuple(component["bbox"]) for component in detail_components}
    reasons = {component["reason"] for component in detail_components}

    assert info["status"] == "applied"
    assert bboxes == {
        (339, 248, 10, 6),
        (338, 258, 32, 35),
        (324, 304, 28, 25),
    }
    assert reasons == {
        "tiny_warm_number_detail_paint_chip",
        "tiny_dark_number_detail_paint_chip",
    }
    for x, y, w, h in bboxes | {(357, 730, 21, 7), (378, 764, 16, 6)}:
        assert (mask[y:y + h, x:x + w] > 0).sum() > 0
    assert (mask[245:258, 482:489] > 0).mean() == 0
    assert (mask[807:814, 135:141] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_dlm_warm_orange_number_shells():
    sample = Path(
        "_smart_tga_runs/cycle449_dlm_batch05_upper_mid_red_livery_slab_controls_v1/"
        "Dirt_Late_Model_car_num_1124938"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle449 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    shell_components = [
        component
        for component in info["components"]
        if component["reason"] == "warm_orange_number_shell_sponsor_fragment"
    ]
    bboxes = {tuple(component["bbox"]) for component in shell_components}

    assert info["status"] == "applied"
    assert bboxes == {
        (297, 241, 110, 65),
        (339, 259, 32, 35),
        (266, 717, 191, 96),
        (379, 765, 35, 32),
    }
    for x, y, w, h in bboxes:
        assert (mask[y:y + h, x:x + w] > 0).sum() > 0
    assert (mask[923:943, 333:408] > 0).mean() == 0
    assert (mask[63:74, 30:92] > 0).mean() == 0
    assert (mask[221:231, 326:373] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_tiny_warm_shell_sponsor_chip():
    n = 1024
    rgb = np.full((n, n, 3), np.array([30, 33, 37], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    anchor = np.zeros((n, n), bool)
    anchor[710:806, 262:453] = True
    numbers[anchor] = 255
    rgb[anchor] = np.array([242, 239, 231], np.uint8)

    yy_all, xx_all = np.indices((n, n))
    yy, xx = np.indices((11, 9))
    chip_shape = ((xx + yy) % 5) != 0
    number_chip = np.zeros((n, n), bool)
    number_chip[755:766, 332:341] = chip_shape
    numbers[number_chip] = 0
    sponsors[number_chip] = 255
    rgb[number_chip] = np.array([218, 95, 18], np.uint8)
    rgb[number_chip & (((xx_all + yy_all) % 3) == 0)] = np.array([120, 45, 10], np.uint8)

    remote_chip = np.zeros((n, n), bool)
    remote_chip[150:161, 332:341] = chip_shape
    sponsors[remote_chip] = 255
    rgb[remote_chip] = np.array([218, 95, 18], np.uint8)
    rgb[remote_chip & (((xx_all + yy_all) % 3) == 0)] = np.array([120, 45, 10], np.uint8)

    protected_chip = np.zeros((n, n), bool)
    protected_chip[748:759, 350:359] = chip_shape
    numbers[protected_chip] = 0
    sponsors[protected_chip] = 255
    template[protected_chip] = 255
    rgb[protected_chip] = np.array([218, 95, 18], np.uint8)
    rgb[protected_chip & (((xx_all + yy_all) % 3) == 0)] = np.array([120, 45, 10], np.uint8)

    red_chip = np.zeros((n, n), bool)
    red_chip[768:779, 366:375] = chip_shape
    numbers[red_chip] = 0
    sponsors[red_chip] = 255
    rgb[red_chip] = np.array([210, 25, 30], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    shell_components = [
        component
        for component in info["components"]
        if component["reason"] == "tiny_warm_number_shell_sponsor_chip"
    ]

    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in shell_components} == {(332, 755, 9, 11)}
    assert (mask[number_chip] > 0).mean() > 0.90
    assert (mask[remote_chip] > 0).mean() == 0
    assert (mask[protected_chip] > 0).mean() == 0
    assert (mask[red_chip] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_dlm_tiny_warm_shell_sponsor_chip():
    sample = Path(
        "_smart_tga_runs/cycle451_dlm_batch05_number_contained_sponsor_fragment_veto_controls_v1/"
        "Dirt_Late_Model_car_num_1124938"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle451 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand, used_warm_shell_px=3166
    )

    shell_components = [
        component
        for component in info["components"]
        if component["reason"] == "tiny_warm_number_shell_sponsor_chip"
    ]

    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in shell_components} == {(332, 755, 9, 11)}
    assert (mask[755:766, 332:341] > 0).sum() == 79
    assert (mask[730:753, 357:386] > 0).sum() == 0
    assert (mask[764:796, 378:413] > 0).sum() == 0


def test_smart_tga_number_trim_fragment_recovers_dense_dlm_number_shell_sponsor_chips_real_38631():
    sample = Path(
        "_smart_tga_runs/cycle568_dlm_38631_curved_red_white_swoosh_target_v1_nocache/"
        "Dirt_Late_Model_car_num_38631"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle568 DLM 38631 dense number-shell sponsor-chip fixture not present")

    paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/"
        "car_num_38631.tga"
    )
    if not paint_path.exists():
        pytest.skip("DLM 38631 source TGA fixture is not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(tex * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )
    dense_shell_components = [
        component
        for component in info["components"]
        if component["reason"] == "tiny_dense_warm_number_shell_sponsor_chip"
    ]

    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in dense_shell_components} == {
        (681, 565, 8, 6),
        (696, 565, 10, 6),
    }
    assert (mask[565:571, 681:689] > 0).sum() == 47
    assert (mask[565:571, 696:706] > 0).sum() == 59
    assert (mask[556:587, 713:714] > 0).sum() == 0
    assert (mask[244:249, 114:119] > 0).sum() == 0
    assert (mask[235:255, 59:109] > 0).sum() == 0
    assert (mask[324:336, 188:263] > 0).sum() == 0


def test_smart_tga_number_trim_fragment_recovers_wide_warm_number_underlines():
    n = 1024
    rgb = np.full((n, n, 3), np.array([28, 31, 35], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    anchor = np.zeros((n, n), bool)
    anchor[220:340, 300:600] = True
    numbers[anchor] = 255
    rgb[anchor] = np.array([238, 236, 228], np.uint8)
    warm_shell = anchor & ((((np.indices((n, n))[0] + np.indices((n, n))[1]) % 9) == 0))
    rgb[warm_shell] = np.array([216, 96, 22], np.uint8)

    yy, xx = np.indices((10, 112))
    underline_shape = (
        ((yy >= 2) & (yy <= 4) & (((xx + yy) % 3) != 0))
        | ((yy >= 5) & (yy <= 6) & ((xx % 6) == 0))
    )
    sponsor_underline = np.zeros((n, n), bool)
    sponsor_underline[333:343, 272:384] = underline_shape
    numbers[sponsor_underline] = 0
    sponsors[sponsor_underline] = 255
    rgb[sponsor_underline] = np.array([192, 72, 18], np.uint8)
    rgb[sponsor_underline & (((np.indices((n, n))[1]) % 7) == 0)] = np.array([76, 29, 9], np.uint8)

    paint_underline = np.zeros((n, n), bool)
    paint_underline[332:339, 410:491] = underline_shape[:7, :81]
    numbers[paint_underline] = 0
    rgb[paint_underline] = np.array([238, 114, 20], np.uint8)

    edge_chip = np.zeros((n, n), bool)
    edge_chip[288:304, 466:472] = ((np.indices((16, 6))[0] + np.indices((16, 6))[1]) % 3) != 0
    numbers[edge_chip] = 0
    rgb[edge_chip] = np.array([236, 50, 24], np.uint8)

    remote_underline = np.zeros((n, n), bool)
    remote_underline[560:570, 272:384] = underline_shape
    sponsors[remote_underline] = 255
    rgb[remote_underline] = np.array([192, 72, 18], np.uint8)

    protected_chip = np.zeros((n, n), bool)
    protected_chip[292:308, 486:492] = edge_chip[288:304, 466:472]
    numbers[protected_chip] = 0
    sponsors[protected_chip] = 255
    template[protected_chip] = 255
    rgb[protected_chip] = np.array([236, 50, 24], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand
    )

    reasons = {component["reason"] for component in info["components"]}
    assert "wide_warm_number_underline_sponsor_fragment" in reasons
    assert "wide_warm_number_underline_paint_fragment" in reasons
    assert "warm_number_edge_paint_chip" in reasons
    assert (mask[sponsor_underline] > 0).mean() > 0.80
    assert (mask[paint_underline] > 0).mean() > 0.80
    assert (mask[edge_chip] > 0).mean() > 0.80
    assert (mask[remote_underline] > 0).mean() == 0
    assert (mask[protected_chip] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_wide_warm_underline_from_background_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([26, 28, 32], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    anchor = np.zeros((n, n), bool)
    anchor[225:339, 297:599] = True
    numbers[anchor] = 255
    rgb[anchor] = np.array([238, 236, 228], np.uint8)
    warm_shell = anchor & ((((np.indices((n, n))[0] + np.indices((n, n))[1]) % 11) == 0))
    rgb[warm_shell] = np.array([218, 96, 22], np.uint8)

    yy, xx = np.indices((10, 115))
    underline_shape = (
        ((yy >= 2) & (yy <= 3))
        | ((xx == 0) & (yy >= 4) & (yy <= 8))
        | ((yy == 8) & ((xx % 2) == 0))
    )
    underline = np.zeros((n, n), bool)
    underline[333:343, 270:385] = underline_shape
    numbers[underline] = 0
    rgb[underline] = np.array([230, 105, 18], np.uint8)
    rgb[underline & (((np.indices((n, n))[1]) % 13) == 0)] = np.array([72, 30, 11], np.uint8)

    remote = np.zeros((n, n), bool)
    remote[650:660, 270:385] = underline_shape
    rgb[remote] = np.array([230, 105, 18], np.uint8)

    sponsors[760:790, 80:190] = 255
    rgb[760:790, 80:190] = np.array([245, 245, 238], np.uint8)

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand, used_warm_shell_px=0
    )

    reasons = {component["reason"] for component in info["components"]}
    assert "wide_warm_number_underline_paint_subcomponent" in reasons
    assert (mask[underline] > 0).mean() > 0.75
    assert (mask[remote] > 0).mean() == 0


def test_smart_tga_number_trim_fragment_recovers_real_dlm_wide_warm_number_underlines():
    sample = Path(
        "_smart_tga_runs/cycle456_dlm_batch06_large_stylized_number_shell_route_v1/"
        "Dirt_Late_Model_car_num_1124938"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle456 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, info = car_layers_mod._number_trim_fragment_supplement(
        rgb, numbers, sponsors, template, brand, used_warm_shell_px=2976
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert "wide_warm_number_underline_sponsor_fragment" in reasons
    assert "wide_warm_number_underline_paint_fragment" in reasons
    assert "warm_number_edge_paint_chip" in reasons
    assert (mask[334:344, 271:378] > 0).sum() > 250
    assert (mask[333:340, 298:377] > 0).sum() > 70
    assert (mask[288:304, 466:472] > 0).sum() > 45
    assert (mask[923:943, 333:408] > 0).sum() == 0
    assert (mask[63:74, 30:92] > 0).sum() == 0

    replay_numbers = numbers.copy()
    replay_sponsors = sponsors.copy()
    replay_template = template.copy()
    replay_brand = brand.copy()
    replay_guard, replay_accum, replay_applied = car_layers_mod._apply_number_trim_supplement(
        rgb,
        replay_numbers,
        replay_sponsors,
        replay_template,
        replay_brand,
        existing_guard=info,
        accum_mask=mask,
        phase="post_large_stylized_number_shell",
    )
    assert replay_applied is True
    assert replay_guard["status"] == "applied"
    assert (replay_accum[334:344, 271:378] > 0).sum() > 250
    assert (replay_numbers[334:344, 271:378] > 0).sum() > 250


def test_smart_tga_number_trim_fragment_reruns_after_final_badge_cleanup(monkeypatch):
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.07, 0.08, 0.10], np.float32)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)

    number = np.zeros((n, n), bool)
    number[120:250, 120:340] = True
    numbers[number] = 255
    tex[number] = np.array([0.96, 0.94, 0.91], np.float32)

    yy, xx = np.indices((30, 19))
    late_trim = ((xx >= yy * 0.35) & (xx <= yy * 0.35 + 9)) | (
        ((yy % 7) == 0) & (xx >= 1) & (xx < 18)
    )
    late_trim_full = np.zeros((n, n), bool)
    late_trim_full[194:224, 238:257] = late_trim
    numbers[late_trim_full] = 0
    sponsors[late_trim_full] = 255
    tex[late_trim_full] = np.array([0.11, 0.49, 0.86], np.float32)

    sponsors[500:620, 500:650] = 255
    tex[500:620, 500:650] = np.array([0.92, 0.92, 0.90], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": numbers.copy(),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    calls = {"badge_cleanup": 0}

    def late_badge_cleanup(_numbers, _sponsors, _template, _brand):
        calls["badge_cleanup"] += 1
        out = np.zeros((n, n), np.uint8)
        if calls["badge_cleanup"] >= 2:
            out[late_trim_full] = 255
            return out, {"status": "applied", "components": [{"reason": "late_test_cleanup"}]}
        return out, {"status": "empty", "components": []}

    monkeypatch.setattr(car_layers_mod, "_round_number_badge_interior_to_paint", late_badge_cleanup)

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    out_numbers = res["layers"]["numbers"]
    out_sponsors = res["layers"]["sponsors"]
    info = res["number_trim_fragment_guard"]
    assert (out_numbers[late_trim_full] > 0).mean() > 0.90
    assert (out_sponsors[late_trim_full] > 0).mean() == 0
    assert info["status"] == "applied"
    assert any(
        component.get("phase") == "post_final_false_positive_cleanup"
        and component.get("reason") == "cool_number_outline_paint_fragment"
        for component in info["components"]
    )


def test_smart_tga_number_badge_graphic_recovers_sibling_from_sponsors():
    n = 768
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_badge(mask_layer, y0, x0, tint):
        h, w = 64, 112
        shape = np.zeros((h, w), bool)
        shape[4:60, 4:108] = True
        shape[18:44, 30:76] = False
        yy, xx = np.indices((h, w))
        mask_layer[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = tint
        sub[shape & (yy < 14)] = np.array([222, 222, 216], np.uint8)
        sub[shape & (xx < 34) & (yy > 24)] = np.array([30, 28, 26], np.uint8)
        sub[shape & (yy > 48) & (xx > 68)] = np.array([146, 132, 88], np.uint8)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        return full

    number = add_badge(numbers, 78, 80, np.array([104, 102, 94], np.uint8))
    sibling = add_badge(sponsors, 344, 96, np.array([108, 102, 86], np.uint8))

    dark_panel = np.zeros((n, n), bool)
    dark_panel[350:404, 310:412] = True
    sponsors[dark_panel] = 255
    rgb[dark_panel] = np.array([36, 36, 35], np.uint8)

    red_strip = np.zeros((n, n), bool)
    red_strip[210:238, 282:430] = True
    sponsors[red_strip] = 255
    rgb[red_strip] = np.array([210, 38, 28], np.uint8)
    rgb[214:218, 292:420] = np.array([244, 244, 236], np.uint8)

    mask, info = car_layers_mod._number_badge_graphic_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "number_badge_graphic_sibling"
    assert (mask[sibling] > 0).mean() > 0.90
    assert (mask[number] > 0).mean() == 0
    assert (mask[dark_panel] > 0).mean() == 0
    assert (mask[red_strip] > 0).mean() == 0


def test_smart_tga_bright_red_outline_number_badge_recovers_rotated_sibling_from_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 62, 145], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_bright_number(mask_layer, y0, x0):
        h, w = 100, 155
        yy, xx = np.indices((h, w))
        shape = np.zeros((h, w), bool)
        shape[5:95, 5:150] = True
        shape[25:72, 34:76] = False
        shape[28:70, 100:132] = False
        shape[(yy > 70) & (xx < 42)] = False
        shape[(yy < 22) & (xx > 112)] = False
        mask_layer[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = np.array([246, 242, 238], np.uint8)
        red = shape & (
            ((yy >= 5) & (yy < 10))
            | ((yy > 91) & (yy < 95))
            | ((xx >= 5) & (xx < 9) & (yy > 20) & (yy < 75))
            | ((np.abs((xx - 48) - (yy - 24)) <= 1) & (yy > 24) & (yy < 82))
        )
        blue = shape & (xx >= 20) & (xx <= 42) & (yy >= 30) & (yy <= 82)
        sub[red] = np.array([210, 24, 20], np.uint8)
        sub[blue] = np.array([10, 70, 190], np.uint8)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        return full

    first_number = add_bright_number(numbers, 120, 120)
    second_number = add_bright_number(numbers, 720, 460)
    recovered = add_bright_number(sponsors, 300, 470)

    pale_panel = np.zeros((n, n), bool)
    pale_panel[120:228, 720:919] = True
    sponsors[pale_panel] = 255
    rgb[pale_panel] = np.array([242, 238, 226], np.uint8)
    rgb[124:132, 724:915] = np.array([220, 54, 42], np.uint8)
    rgb[210:218, 724:915] = np.array([18, 92, 210], np.uint8)

    mask, info = car_layers_mod._number_badge_graphic_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "bright_red_outline_number_sibling"
    assert (mask[recovered] > 0).mean() > 0.90
    assert (mask[first_number] > 0).mean() == 0
    assert (mask[second_number] > 0).mean() == 0
    assert (mask[pale_panel] > 0).mean() == 0


def test_smart_tga_bright_red_outline_number_badge_rejects_unaligned_sponsor_shape():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 62, 145], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_bright_number(mask_layer, y0, x0):
        h, w = 100, 155
        yy, xx = np.indices((h, w))
        shape = np.zeros((h, w), bool)
        shape[5:95, 5:150] = True
        shape[25:72, 34:76] = False
        shape[28:70, 100:132] = False
        shape[(yy > 70) & (xx < 42)] = False
        shape[(yy < 22) & (xx > 112)] = False
        mask_layer[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = np.array([246, 242, 238], np.uint8)
        red = shape & (
            ((yy >= 5) & (yy < 10))
            | ((yy > 91) & (yy < 95))
            | ((xx >= 5) & (xx < 9) & (yy > 20) & (yy < 75))
            | ((np.abs((xx - 48) - (yy - 24)) <= 1) & (yy > 24) & (yy < 82))
        )
        blue = shape & (xx >= 20) & (xx <= 42) & (yy >= 30) & (yy <= 82)
        sub[red] = np.array([210, 24, 20], np.uint8)
        sub[blue] = np.array([10, 70, 190], np.uint8)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        return full

    first_number = add_bright_number(numbers, 120, 120)
    second_number = add_bright_number(numbers, 720, 460)
    unaligned_sponsor = add_bright_number(sponsors, 500, 810)

    mask, info = car_layers_mod._number_badge_graphic_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "empty"
    assert info["component_count"] == 0
    assert (mask[unaligned_sponsor] > 0).mean() == 0
    assert (mask[first_number] > 0).mean() == 0
    assert (mask[second_number] > 0).mean() == 0


def test_smart_tga_dark_muted_number_badge_recovers_sibling_from_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([12, 13, 8], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_dark_digit(mask_layer, y0, x0, h=106, w=137):
        yy, xx = np.indices((h, w))
        shape = np.zeros((h, w), bool)
        shape[4:h - 4, 4:w - 4] = True
        shape[24:52, 31:72] = False
        shape[56:84, 82:120] = False
        shape[(yy < 18) & (xx > 104)] = False
        shape[(yy > h - 22) & (xx < 28)] = False
        mask_layer[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = np.array([42, 42, 8], np.uint8)
        sub[shape & (xx > int(w * 0.72))] = np.array([185, 175, 105], np.uint8)
        sub[shape & (yy < int(h * 0.34))] = np.array([0, 0, 0], np.uint8)
        sub[shape & ((xx % 17) < 2) & (yy > 20)] = np.array([8, 8, 2], np.uint8)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        return full

    first_number = add_dark_digit(numbers, 110, 120, h=106, w=137)
    second_number = add_dark_digit(numbers, 690, 520, h=106, w=137)
    recovered_first = add_dark_digit(sponsors, 300, 540, h=104, w=136)
    recovered_second = add_dark_digit(sponsors, 520, 410, h=106, w=137)

    wide_wordmark = np.zeros((n, n), bool)
    yy, xx = np.indices((100, 255))
    wide_shape = np.zeros((100, 255), bool)
    wide_shape[6:94, 8:247] = True
    wide_shape[36:65, 44:198] = False
    wide_shape[(yy < 24) & (xx > 196)] = False
    wide_shape[(yy > 75) & (xx < 34)] = False
    wide_wordmark[800:900, 260:515] = wide_shape
    sponsors[wide_wordmark] = 255
    word_sub = rgb[800:900, 260:515]
    word_sub[wide_shape] = np.array([42, 42, 8], np.uint8)
    word_sub[wide_shape & (xx > int(255 * 0.72))] = np.array([185, 175, 105], np.uint8)
    word_sub[wide_shape & (yy < int(100 * 0.34))] = np.array([0, 0, 0], np.uint8)

    mask, info = car_layers_mod._number_badge_graphic_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {c["reason"] for c in info["components"]} == {"dark_muted_number_sibling"}
    assert (mask[recovered_first] > 0).mean() > 0.90
    assert (mask[recovered_second] > 0).mean() > 0.90
    assert (mask[first_number] > 0).mean() == 0
    assert (mask[second_number] > 0).mean() == 0
    assert (mask[wide_wordmark] > 0).mean() == 0


def test_smart_tga_warm_red_square_number_badge_recovers_sibling_from_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([245, 245, 242], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_warm_number(mask_layer, y0, x0, h=103, w=105):
        yy, xx = np.indices((h, w))
        shape = np.zeros((h, w), bool)
        shape[4:h - 5, 4:w - 5] = True
        shape[int(h * 0.26):int(h * 0.54), int(w * 0.26):int(w * 0.60)] = False
        shape[int(h * 0.57):int(h * 0.84), int(w * 0.64):int(w * 0.88)] = False
        shape[(yy < int(h * 0.18)) & (xx > int(w * 0.78))] = False
        shape[(yy > int(h * 0.80)) & (xx < int(w * 0.22))] = False
        mask_layer[y0:y0 + h, x0:x0 + w][shape] = 255
        sub = rgb[y0:y0 + h, x0:x0 + w]
        sub[shape] = np.array([205, 55, 48], np.uint8)
        sub[shape & (xx < int(w * 0.16))] = np.array([26, 25, 22], np.uint8)
        sub[shape & (yy < int(h * 0.15))] = np.array([30, 28, 24], np.uint8)
        blue = shape & (xx > int(w * 0.56)) & (xx < int(w * 0.74)) & (yy > int(h * 0.24))
        blue |= shape & (((xx + 2 * yy) % 23) < 2)
        sub[blue] = np.array([22, 78, 184], np.uint8)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        return full

    square_ref = add_warm_number(numbers, 720, 500)
    tall_ref = add_warm_number(numbers, 718, 430, h=103, w=67)
    recovered = add_warm_number(sponsors, 170, 430)

    bright_logo = np.zeros((n, n), bool)
    bright_logo[520:598, 250:329] = True
    sponsors[bright_logo] = 255
    rgb[bright_logo] = np.array([238, 74, 92], np.uint8)
    rgb[542:552, 272:310] = np.array([245, 242, 238], np.uint8)

    vertical_logo = add_warm_number(sponsors, 410, 800, h=190, w=57)
    protected_match = add_warm_number(sponsors, 650, 730)
    template[protected_match] = 255

    mask, info = car_layers_mod._number_badge_graphic_supplement(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "warm_red_square_number_sibling"
    assert (mask[recovered] > 0).mean() > 0.90
    assert (mask[square_ref] > 0).mean() == 0
    assert (mask[tall_ref] > 0).mean() == 0
    assert (mask[bright_logo] > 0).mean() == 0
    assert (mask[vertical_logo] > 0).mean() == 0
    assert (mask[protected_match] > 0).mean() == 0


def test_smart_tga_round_badge_number_recovers_annulus_from_sponsors():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    def add_round_badge(mask_layer, cy, cx, ry, rx, full=False):
        norm = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        outer = norm <= 1.0
        inner = norm < 0.68 ** 2
        ring = outer & ~inner
        shape = outer if full else ring
        mask_layer[shape] = 255
        stripe = ((xx + 2 * yy) // 5) % 3
        rgb[outer & (stripe == 0)] = np.array([118, 46, 45], np.uint8)
        rgb[outer & (stripe == 1)] = np.array([70, 70, 68], np.uint8)
        rgb[outer & (stripe == 2)] = np.array([185, 185, 176], np.uint8)
        rgb[inner] = np.array([55, 55, 52], np.uint8)
        return ring, inner, outer

    add_round_badge(numbers, 768, 412, 50, 54)
    add_round_badge(numbers, 889, 874, 58, 58)
    missing_ring, missing_inner, _missing_outer = add_round_badge(
        sponsors, 282, 416, 56, 58, full=True
    )
    _decoy_ring, _decoy_inner, decoy_outer = add_round_badge(
        sponsors, 560, 760, 88, 90, full=True
    )

    mask, info = car_layers_mod._round_badge_number_supplement(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "round_badge_number_sibling"
    assert (mask[missing_ring] > 0).mean() > 0.90
    assert (mask[missing_inner] > 0).mean() == 0
    assert (mask[decoy_outer] > 0).mean() == 0


def test_smart_tga_repeated_round_sponsor_badges_promote_to_numbers_without_refs():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 20, 24], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    def add_blue_round_badge(cy, cx, r):
        norm = ((xx - cx) / float(r)) ** 2 + ((yy - cy) / float(r)) ** 2
        outer = norm <= 1.0
        stripe = ((xx + 2 * yy) // 7) % 3
        sponsors[outer] = 255
        rgb[outer & (stripe == 0)] = np.array([86, 108, 166], np.uint8)
        rgb[outer & (stripe == 1)] = np.array([226, 228, 232], np.uint8)
        rgb[outer & (stripe == 2)] = np.array([34, 50, 84], np.uint8)
        return outer

    side_06 = add_blue_round_badge(258, 112, 54)
    hood_06 = add_blue_round_badge(574, 484, 82)
    side_90 = add_blue_round_badge(907, 108, 53)
    small_90 = add_blue_round_badge(972, 246, 35)

    red_sponsor_logo = np.zeros((n, n), bool)
    red_sponsor_logo[120:182, 740:802] = True
    sponsors[red_sponsor_logo] = 255
    rgb[red_sponsor_logo] = np.array([230, 48, 42], np.uint8)

    protected_badge = add_blue_round_badge(780, 780, 54)
    template[protected_badge] = 255

    mask, info = car_layers_mod._repeated_round_badge_number_supplement(
        rgb, numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 4
    assert info["components"][0]["reason"] == "repeated_round_sponsor_badge_number"
    assert (mask[side_06] > 0).mean() > 0.90
    assert (mask[hood_06] > 0).mean() > 0.90
    assert (mask[side_90] > 0).mean() > 0.90
    assert (mask[small_90] > 0).mean() > 0.90
    assert (mask[red_sponsor_logo] > 0).mean() == 0
    assert (mask[protected_badge] > 0).mean() == 0


def test_smart_tga_round_badge_outer_sponsor_crumbs_recover_to_numbers():
    n = 1024
    empty = np.zeros((n, n), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    def add_number_badge(cy, cx, ry=56, rx=58):
        norm = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        ring = (norm <= 1.0) & (norm >= 0.70 ** 2)
        numbers[ring] = 255
        return norm

    top_norm = add_number_badge(282, 416)
    lower_norm = add_number_badge(768, 412, 50, 54)
    roof_norm = add_number_badge(889, 874, 58, 58)

    top_crumb = (top_norm >= 0.60 ** 2) & (top_norm <= 0.69 ** 2) & (yy < 258) & (xx < 416)
    lower_crumb = (lower_norm >= 0.64 ** 2) & (lower_norm <= 0.70 ** 2) & (yy > 768) & (xx > 412)
    centered_art = (top_norm < 0.38 ** 2) & (yy > 268) & (yy < 296) & (xx > 402) & (xx < 430)
    outside_sponsor = np.zeros((n, n), bool)
    outside_sponsor[120:146, 720:820] = True
    protected_template = (roof_norm >= 0.58 ** 2) & (roof_norm <= 0.66 ** 2) & (yy < 889) & (xx > 874)

    sponsors[top_crumb | lower_crumb | centered_art | outside_sponsor | protected_template] = 255
    template = np.zeros((n, n), np.uint8)
    template[protected_template] = 255

    mask, info = car_layers_mod._round_number_badge_sponsor_crumb_to_number(
        numbers, sponsors, template, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {c["reason"] for c in info["components"]} == {"round_badge_outer_sponsor_crumb"}
    assert (mask[top_crumb] > 0).mean() > 0.90
    assert (mask[lower_crumb] > 0).mean() > 0.90
    assert (mask[centered_art] > 0).mean() == 0
    assert (mask[outside_sponsor] > 0).mean() == 0
    assert (mask[protected_template] > 0).mean() == 0


def test_smart_tga_large_stylized_number_sponsor_shell_promotes_real_dlm_artifact():
    sample = Path(
        "_smart_tga_runs/cycle455_dlm_batch05_bud_monogram_controls_v1/"
        "Dirt_Late_Model_car_num_1124938"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle455 DLM 1124938 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "large_stylized_number_sponsor_shell"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [297, 225, 302, 111]
    assert component["number_bbox"] == [297, 239, 164, 100]
    assert component["area"] == 14182
    assert component["sponsor_bbox_overlap"] >= 0.47
    assert component["number_bbox_overlap"] >= 0.96
    target = sponsors[225:336, 297:599] > 0
    promoted = mask[225:336, 297:599] > 0
    assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.94


def test_smart_tga_large_stylized_number_shell_ignores_adjacent_sponsor_panel():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 36, 38], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    number_core = (slice(250, 350), slice(300, 465))
    numbers[number_core] = 255
    rgb[number_core] = np.array([238, 236, 226], np.uint8)

    x0, y0, w, h = 490, 235, 250, 105
    panel = (yy >= y0) & (yy < y0 + h) & (xx >= x0) & (xx < x0 + w)
    border = panel & (
        (xx - x0 < 8)
        | (x0 + w - xx <= 8)
        | (yy - y0 < 8)
        | (y0 + h - yy <= 8)
    )
    diagonal = panel & (((xx - x0 + 2 * (yy - y0)) % 34) < 11)
    sponsor_panel = border | diagonal
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel & (((xx + yy) % 4) == 0)] = np.array([230, 60, 28], np.uint8)
    rgb[sponsor_panel & (((xx + yy) % 4) == 1)] = np.array([248, 118, 24], np.uint8)
    rgb[sponsor_panel & (((xx + yy) % 4) == 2)] = np.array([236, 236, 228], np.uint8)
    rgb[sponsor_panel & (((xx + yy) % 4) == 3)] = np.array([34, 34, 34], np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, empty, empty
    )

    assert info["status"] == "empty"
    assert int((mask > 0).sum()) == 0


def test_smart_tga_large_stylized_number_shell_recovers_compact_pale_dlm_20_digits():
    sample = Path(
        "_smart_tga_runs/cycle600_dlm_next4_after_1017630_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1020021"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle600 DLM 1020021 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
        if component["reason"] == "compact_pale_digit_number_decal_sibling"
    }
    assert set(components) == {
        (376, 230, 80, 95),
        (299, 232, 82, 96),
        (312, 727, 78, 92),
    }
    for bbox, component in components.items():
        x, y, w, h = bbox
        target = sponsors[y : y + h, x : x + w] > 0
        promoted = mask[y : y + h, x : x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.92
        assert component["sibling_width_ratio"] >= 0.80
        assert component["white_frac"] >= 0.58

    wide_wordmark = sponsors[723:761, 28:169] > 0
    wide_promoted = mask[723:761, 28:169] > 0
    assert int((wide_promoted & wide_wordmark).sum()) == 0


def test_smart_tga_large_stylized_number_shell_recovers_large_pale_dlm_18_duplicate():
    sample = Path(
        "_smart_tga_runs/cycle600_dlm_next4_after_1017630_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1050549"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle600 DLM 1050549 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
        if component["reason"] == "large_pale_digit_block_number_decal_sibling"
    }
    assert set(components) == {(286, 720, 162, 99)}
    component = components[(286, 720, 162, 99)]
    assert 0.80 <= component["sibling_area_ratio"] <= 0.90
    assert component["sibling_center_dx"] <= 0.01
    assert component["white_frac"] >= 0.55

    target = sponsors[720:819, 286:448] > 0
    promoted = mask[720:819, 286:448] > 0
    assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.92

    rocket_textline = sponsors[911:952, 249:594] > 0
    textline_promoted = mask[911:952, 249:594] > 0
    assert int((textline_promoted & rocket_textline).sum()) == 0


def test_smart_tga_dark_neutral_dlm_15_pair_recovers_after_false_panel_demote():
    sample = Path(
        "_smart_tga_runs/cycle601_dlm_next4_after_1050549_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1063909"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle601 DLM 1063909 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    false_mask, false_info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )
    false_components = {
        tuple(component["bbox"]): component
        for component in false_info["components"]
        if component["reason"] == "white_logistics_sponsor_panel_false_number"
    }
    assert set(false_components) == {(0, 751, 176, 125)}

    numbers_after = numbers.copy()
    sponsors_after = sponsors.copy()
    numbers_after[false_mask > 0] = 0
    sponsors_after = np.maximum(sponsors_after, false_mask)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers_after, sponsors_after, template, brand
    )

    assert info["status"] == "applied"
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
        if component["reason"] == "no_anchor_repeated_dark_neutral_number_decal"
    }
    assert set(components) == {
        (285, 237, 191, 106),
        (297, 719, 140, 82),
    }
    for bbox, component in components.items():
        x, y, w, h = bbox
        target = sponsors[y : y + h, x : x + w] > 0
        promoted = mask[y : y + h, x : x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.92
        assert component["same_family_count"] == 2
        assert component["dark_frac"] >= 0.74

    anderson_wordmark = sponsors[714:760, 30:184] > 0
    assert int(((mask[714:760, 30:184] > 0) & anderson_wordmark).sum()) == 0


def test_smart_tga_large_stylized_number_sibling_chunk_promotes_real_dlm_1226283():
    sample = Path(
        "_smart_tga_runs/cycle515_dlm_batch_vertical_south_central_wordmark_v1_nocache/"
        "Dirt_Late_Model_car_num_1226283"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle515 DLM 1226283 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "large_stylized_number_sibling_chunk"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [880, 834, 73, 71]
    assert component["number_bbox"] == [304, 721, 155, 91]
    assert 0.24 <= component["sibling_area_ratio"] <= 0.34
    assert 0.42 <= component["sibling_width_ratio"] <= 0.52
    assert 0.70 <= component["sibling_height_ratio"] <= 0.86
    assert component["yellow_lime_frac"] >= 0.80
    assert component["colored_frac"] >= 0.80

    target = sponsors[834:905, 880:953] > 0
    promoted = mask[834:905, 880:953] > 0
    assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.92

    sponsor_column = sponsors[426:672, 54:146] > 0
    column_promoted = mask[426:672, 54:146] > 0
    assert float((column_promoted & sponsor_column).sum()) == 0.0

    lower_sponsor_strip = sponsors[714:760, 25:201] > 0
    strip_promoted = mask[714:760, 25:201] > 0
    assert float((strip_promoted & lower_sponsor_strip).sum()) == 0.0


def test_smart_tga_replicated_stylized_number_decal_chunks_promote_real_dlm_268864():
    sample = Path(
        "_smart_tga_runs/cycle526_dlm_next4_after_265439_scan_v1_nocache/"
        "car_num_268864/Dirt_Late_Model_car_num_268864"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle526 DLM 268864 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "replicated_stylized_number_decal_chunk"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[266, 259, 105, 85], [911, 908, 60, 73]]
    assert all(component["number_bbox"] == [270, 715, 153, 83] for component in components)
    assert all(0.18 <= component["sibling_area_ratio"] <= 0.70 for component in components)
    assert all(component["yellow_lime_frac"] >= 0.50 for component in components)
    assert all(0.10 <= component["white_frac"] <= 0.24 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.94

    logo_wordmark = sponsors[315:355, 75:161] > 0
    logo_promoted = mask[315:355, 75:161] > 0
    assert int((logo_promoted & logo_wordmark).sum()) == 0


def test_smart_tga_multicolor_gradient_number_decal_replicas_promote_real_dlm_33863():
    sample = Path(
        "_smart_tga_runs/cycle559_dlm_wrap_first8_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_33863"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle559 DLM 33863 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "multicolor_gradient_number_decal_replica"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[372, 239, 56, 89], [853, 837, 89, 86]]
    assert all(component["number_bbox"] == [305, 238, 83, 90] for component in components)
    assert all(component["red_frac"] >= 0.30 for component in components)
    assert all(component["orange_frac"] >= 0.30 for component in components)
    assert all(component["blue_frac"] >= 0.17 for component in components)
    assert all(component["magenta_frac"] >= 0.13 for component in components)
    assert all(0.08 <= component["edge_density"] <= 0.10 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.98

    upper_hair_nation = sponsors[297:369, 0:110] > 0
    upper_hair_promoted = mask[297:369, 0:110] > 0
    assert int((upper_hair_promoted & upper_hair_nation).sum()) == 0

    lower_hair_nation = sponsors[735:831, 9:65] > 0
    lower_hair_promoted = mask[735:831, 9:65] > 0
    assert int((lower_hair_promoted & lower_hair_nation).sum()) == 0

    triangle_logo = sponsors[187:213, 662:695] > 0
    triangle_promoted = mask[187:213, 662:695] > 0
    assert int((triangle_promoted & triangle_logo).sum()) == 0

    lower_blue_stripe = sponsors[874:887, 0:149] > 0
    stripe_promoted = mask[874:887, 0:149] > 0
    assert int((stripe_promoted & lower_blue_stripe).sum()) == 0


def test_smart_tga_saturated_warm_number_decal_replicas_promote_real_dlm_278708():
    sample = Path(
        "_smart_tga_runs/cycle528_dlm_278708_dense_sponsor_context_micro_holes_target_v1_nocache/"
        "Dirt_Late_Model_car_num_278708"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle528 DLM 278708 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "saturated_warm_number_decal_replica"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[280, 722, 154, 86], [845, 817, 123, 133]]
    assert all(component["number_bbox"] == [281, 246, 119, 94] for component in components)
    assert all(component["orange_frac"] >= 0.70 for component in components)
    assert all(component["colored_frac"] >= 0.86 for component in components)
    assert all(component["white_frac"] <= 0.01 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.94

    cowboy_graphic = sponsors[417:668, 41:258] > 0
    cowboy_promoted = mask[417:668, 41:258] > 0
    assert int((cowboy_promoted & cowboy_graphic).sum()) == 0

    edge_strip = sponsors[117:705, 1000:1024] > 0
    edge_promoted = mask[117:705, 1000:1024] > 0
    assert int((edge_promoted & edge_strip).sum()) == 0


def test_smart_tga_red_white_number_decal_replicas_promote_real_francis2001():
    paint_path = Path("C:/1Shokker Paint Car Examples/1-Francis2001.tga")
    sample = Path(
        "_smart_tga_runs/cycle577_francis2001_number_failure_baseline_v1_nocache/"
        "1Shokker_Paint_Car_Examples_1-Francis2001"
    )
    required = [
        paint_path,
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle577 Francis2001 diagnostic artifact not present")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _, _ = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(tex * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "red_white_number_decal_replica"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[288, 244, 140, 101], [289, 718, 138, 92]]
    assert all(component["number_bbox"] == [809, 833, 142, 127] for component in components)
    assert all(0.23 <= component["red_frac"] <= 0.27 for component in components)
    assert all(0.60 <= component["white_frac"] <= 0.62 for component in components)
    assert all(0.11 <= component["dark_frac"] <= 0.13 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.98

    valvoline_side_logo = sponsors[400:637, 786:825] > 0
    valvoline_promoted = mask[400:637, 786:825] > 0
    assert int((valvoline_promoted & valvoline_side_logo).sum()) == 0

    lower_francis_wordmark = sponsors[907:945, 337:597] > 0
    francis_promoted = mask[907:945, 337:597] > 0
    assert int((francis_promoted & lower_francis_wordmark).sum()) == 0


def test_smart_tga_hot_pink_number_decal_replicas_promote_real_dlm_281686():
    sample = Path(
        "_smart_tga_runs/cycle530_dlm_next4_after_278708_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_281686"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle530 DLM 281686 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "hot_pink_number_decal_replica"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[279, 719, 88, 94], [381, 239, 68, 94]]
    assert all(component["number_bbox"] == [293, 239, 106, 94] for component in components)
    assert all(component["magenta_frac"] >= 0.93 for component in components)
    assert all(component["hot_pink_frac"] >= 0.92 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.84

    negative_sample = Path(
        "_smart_tga_runs/cycle530_dlm_next4_after_278708_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_288718"
    )
    negative_required = [
        negative_sample / "source_1024.png",
        negative_sample / "masks" / "numbers.png",
        negative_sample / "masks" / "sponsors.png",
        negative_sample / "masks" / "template.png",
        negative_sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in negative_required):
        pytest.skip("Cycle530 DLM 288718 diagnostic artifact not present")

    neg_rgb = np.array(Image.open(negative_required[0]).convert("RGB"), dtype=np.uint8)
    neg_numbers = np.array(Image.open(negative_required[1]).convert("L"), dtype=np.uint8)
    neg_sponsors = np.array(Image.open(negative_required[2]).convert("L"), dtype=np.uint8)
    neg_template = np.array(Image.open(negative_required[3]).convert("L"), dtype=np.uint8)
    neg_brand = np.array(Image.open(negative_required[4]).convert("L"), dtype=np.uint8)

    neg_mask, neg_info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        neg_rgb, neg_numbers, neg_sponsors, neg_template, neg_brand
    )
    assert all(
        component["reason"] != "hot_pink_number_decal_replica"
        for component in neg_info.get("components", [])
    )

    edge_strip = neg_sponsors[116:706, 999:1024] > 0
    edge_promoted = neg_mask[116:706, 999:1024] > 0
    assert int((edge_promoted & edge_strip).sum()) == 0


def test_smart_tga_matched_cool_square_sponsor_logo_card_demotes_real_dlm_290060():
    sample = Path(
        "_smart_tga_runs/cycle530_dlm_next4_hot_pink_number_replica_controls_v1_nocache/"
        "Dirt_Late_Model_car_num_290060"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle530 DLM 290060 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "matched_cool_square_sponsor_logo_card"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [497, 765, 50, 56]
    assert component["cool_square_sponsor_siblings"] >= 1
    assert component["blue_frac"] >= 0.46
    assert component["white_text_components"] >= 5
    assert component["colored_text_components"] >= 8

    false_number_logo = numbers[765:821, 497:547] > 0
    false_number_demoted = mask[765:821, 497:547] > 0
    assert float((false_number_demoted & false_number_logo).sum()) / float(max(1, false_number_logo.sum())) > 0.92

    orange_number = sponsors[716:822, 281:452] > 0
    orange_demoted = mask[716:822, 281:452] > 0
    assert int((orange_demoted & orange_number).sum()) == 0


def test_smart_tga_matched_wide_mixed_sponsor_logo_card_demotes_real_dlm_297710():
    sample = Path(
        "_smart_tga_runs/cycle532_dlm_next4_after_290060_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_297710"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle532 DLM 297710 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "matched_wide_mixed_sponsor_logo_card"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [26, 294, 150, 58]
    assert component["wide_mixed_sponsor_siblings"] >= 1
    assert component["magenta_frac"] >= 0.09
    assert component["yellow_frac"] <= 0.11
    assert component["white_text_components"] >= 20
    assert component["colored_text_components"] >= 5

    swartz_card = numbers[294:352, 26:176] > 0
    swartz_demoted = mask[294:352, 26:176] > 0
    assert float((swartz_demoted & swartz_card).sum()) / float(max(1, swartz_card.sum())) > 0.98

    neon_number_art = numbers[675:764, 716:842] > 0
    neon_demoted = mask[675:764, 716:842] > 0
    assert int((neon_demoted & neon_number_art).sum()) == 0

    dark_roof_component = numbers[30:119, 317:479] > 0
    dark_demoted = mask[30:119, 317:479] > 0
    assert int((dark_demoted & dark_roof_component).sum()) == 0


def test_smart_tga_square_grayscale_racing_logo_badge_demotes_real_dlm_304107():
    sample = Path(
        "_smart_tga_runs/cycle533_dlm_next4_after_300314_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_304107"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle533 DLM 304107 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "square_grayscale_racing_logo_badge"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [802, 812, 155, 155]
    assert component["white_text_components"] >= 10
    assert component["dark_text_components"] >= 20
    assert component["colored_text_components"] == 0
    assert component["edge_density"] >= 0.30
    assert component["colored_frac"] <= 0.015

    coby_logo = numbers[812:967, 802:957] > 0
    coby_demoted = mask[812:967, 802:957] > 0
    assert float((coby_demoted & coby_logo).sum()) / float(max(1, coby_logo.sum())) > 0.98

    true_side_number = numbers[241:341, 291:481] > 0
    true_side_demoted = mask[241:341, 291:481] > 0
    assert int((true_side_demoted & true_side_number).sum()) == 0

    lower_number = numbers[725:801, 330:406] > 0
    lower_demoted = mask[725:801, 330:406] > 0
    assert int((lower_demoted & lower_number).sum()) == 0


def test_smart_tga_long_red_white_blue_service_wordmark_demotes_real_dlm_304107():
    sample = Path(
        "_smart_tga_runs/cycle533_dlm_next4_after_300314_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_304107"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle533 DLM 304107 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "long_red_white_blue_service_sponsor_wordmark"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [20, 302, 169, 51]
    assert component["white_text_components"] >= 18
    assert component["colored_text_components"] >= 10
    assert component["white_frac"] < 0.18
    assert component["broad_near_sponsor"] >= 0.65

    service_wordmark = numbers[302:353, 20:189] > 0
    service_demoted = mask[302:353, 20:189] > 0
    assert (
        float((service_demoted & service_wordmark).sum())
        / float(max(1, service_wordmark.sum()))
        > 0.98
    )

    true_side_number = numbers[241:341, 291:481] > 0
    true_side_demoted = mask[241:341, 291:481] > 0
    assert int((true_side_demoted & true_side_number).sum()) == 0

    lower_number = numbers[725:801, 330:406] > 0
    lower_demoted = mask[725:801, 330:406] > 0
    assert int((lower_demoted & lower_number).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_grayscale_badge_letter_chunk_real_dlm_304107():
    sample = Path(
        "_smart_tga_runs/cycle534_dlm_304107_long_service_wordmark_target_v1_nocache/"
        "Dirt_Late_Model_car_num_304107"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        sample / "masks" / "paint.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle534 DLM 304107 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    paint = np.array(Image.open(required[5]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["bucket"] == "sponsor_panel_grayscale_badge_letter_chunk"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [844, 925, 13, 13]
    assert component["sponsor_overlap"] == 1.0
    assert component["number_overlap"] == 0.0
    assert component["template_overlap"] == 0.0
    assert component["ring_sponsor"] >= 0.60
    assert component["sat_frac"] == 0.0

    badge_letter_pocket = paint[925:938, 844:857] > 0
    badge_letter_recovered = mask[925:938, 844:857] > 0
    assert (
        float((badge_letter_recovered & badge_letter_pocket).sum())
        / float(max(1, badge_letter_pocket.sum()))
        > 0.95
    )

    true_side_number = numbers[241:341, 291:481] > 0
    true_side_recovered = mask[241:341, 291:481] > 0
    assert int((true_side_recovered & true_side_number).sum()) == 0


def test_smart_tga_no_anchor_repeated_warm_number_decal_promotes_real_dlm_290060():
    sample = Path(
        "_smart_tga_runs/cycle531_dlm_290060_matched_cool_square_logo_target_v1_nocache/"
        "Dirt_Late_Model_car_num_290060"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle531 DLM 290060 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    assert int((numbers > 0).sum()) == 0

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["number_anchor_count"] == 0
    components = [
        component
        for component in info["components"]
        if component["reason"] == "no_anchor_repeated_warm_number_decal"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[281, 716, 171, 106], [286, 231, 181, 116]]
    assert all(component["same_family_count"] >= 2 for component in components)
    assert all(component["orange_frac"] >= 0.56 for component in components)
    assert all(component["white_frac"] <= 0.065 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.92

    penske_logo = sponsors[277:339, 459:588] > 0
    penske_promoted = mask[277:339, 459:588] > 0
    assert int((penske_promoted & penske_logo).sum()) == 0


def test_smart_tga_no_usable_anchor_repeated_orange_black_number_decal_promotes_real_dlm_1027044():
    sample = Path(
        "_smart_tga_runs/cycle547_dlm_next4_after_1020021_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1027044"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle547 DLM 1027044 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    assert int((numbers > 0).sum()) > 0

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["reason"] == "no_usable_number_anchor"
    assert info["number_anchor_count"] == 0
    components = [
        component
        for component in info["components"]
        if component["reason"] == "no_anchor_repeated_orange_black_number_decal"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[311, 237, 129, 106], [813, 802, 144, 172]]
    assert all(component["same_family_count"] >= 2 for component in components)
    assert all(component["family_kind"] == "rotated_orange_black" for component in components)
    assert all(component["orange_frac"] >= 0.61 for component in components)
    assert all(component["white_frac"] <= 0.01 for component in components)
    assert all(0.37 <= component["dark_frac"] <= 0.40 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.98

    outlaws_badge = sponsors[30:128, 596:737] > 0
    outlaws_promoted = mask[30:128, 596:737] > 0
    assert int((outlaws_promoted & outlaws_badge).sum()) == 0

    blue_flame_graphic = sponsors[391:509, 549:708] > 0
    flame_promoted = mask[391:509, 549:708] > 0
    assert int((flame_promoted & blue_flame_graphic).sum()) == 0

    orange_sponsor_strip = sponsors[311:340, 214:303] > 0
    strip_promoted = mask[311:340, 214:303] > 0
    assert int((strip_promoted & orange_sponsor_strip).sum()) == 0


def test_smart_tga_no_anchor_repeated_pale_gold_number_decal_promotes_real_dlm_1135812():
    sample = Path(
        "_smart_tga_runs/cycle553_dlm_next8_after_1122118_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1135812"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle553 DLM 1135812 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    assert int((numbers > 0).sum()) == 0

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["reason"] == "no_numbers"
    assert info["number_anchor_count"] == 0
    components = [
        component
        for component in info["components"]
        if component["reason"] == "no_anchor_repeated_pale_gold_number_decal"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[274, 717, 185, 97], [284, 237, 169, 99]]
    assert all(component["family_kind"] == "pale_gold_digit" for component in components)
    assert all(component["same_family_count"] >= 2 for component in components)
    assert all(component["white_frac"] >= 0.63 for component in components)
    assert all(0.09 <= component["gold_frac"] <= 0.11 for component in components)
    assert all(0.20 <= component["muted_dark_frac"] <= 0.22 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.98

    upper_service_wordmark = sponsors[275:333, 459:590] > 0
    upper_service_promoted = mask[275:333, 459:590] > 0
    assert int((upper_service_promoted & upper_service_wordmark).sum()) == 0

    lower_service_wordmark = sponsors[718:774, 465:598] > 0
    lower_service_promoted = mask[718:774, 465:598] > 0
    assert int((lower_service_promoted & lower_service_wordmark).sum()) == 0

    large_orange_sponsor_panel = sponsors[426:600, 664:877] > 0
    large_panel_promoted = mask[426:600, 664:877] > 0
    assert int((large_panel_promoted & large_orange_sponsor_panel).sum()) == 0


def test_smart_tga_no_anchor_repeated_pale_orange_number_decal_promotes_real_dlm_1328773():
    sample = Path(
        "_smart_tga_runs/cycle558_dlm_next8_after_1295543_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1328773"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle558 DLM 1328773 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["reason"] == "no_usable_number_anchor"
    assert info["number_anchor_count"] == 0
    components = [
        component
        for component in info["components"]
        if component["reason"] == "no_anchor_repeated_pale_orange_number_decal"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[265, 242, 236, 95], [284, 730, 156, 85]]
    assert all(component["family_kind"] == "pale_orange_digit" for component in components)
    assert all(component["same_family_count"] >= 2 for component in components)
    assert all(component["orange_frac"] >= 0.54 for component in components)
    assert all(0.07 <= component["white_frac"] <= 0.25 for component in components)
    assert all(component["dark_frac"] <= 0.18 for component in components)

    for x, y, w, h in bboxes:
        target = sponsors[y:y + h, x:x + w] > 0
        promoted = mask[y:y + h, x:x + w] > 0
        assert float((promoted & target).sum()) / float(max(1, target.sum())) > 0.98

    lower_orange_wordmark = sponsors[907:1013, 247:600] > 0
    lower_wordmark_promoted = mask[907:1013, 247:600] > 0
    assert int((lower_wordmark_promoted & lower_orange_wordmark).sum()) == 0

    tiny_red_contingency = sponsors[246:257, 534:542] > 0
    contingency_promoted = mask[246:257, 534:542] > 0
    assert int((contingency_promoted & tiny_red_contingency).sum()) == 0

    roof_triangle_graphic = sponsors[134:149, 599:612] > 0
    roof_triangle_promoted = mask[134:149, 599:612] > 0
    assert int((roof_triangle_promoted & roof_triangle_graphic).sum()) == 0


def test_smart_tga_yellow_panel_number_recovers_repeated_digit_pairs_from_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([245, 245, 242], np.uint8), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)

    def add_yellow_panel(x, y, w=118, h=58):
        rgb[y:y + h, x:x + w] = np.array([244, 198, 42], np.uint8)

    def add_digit_pair(x, y):
        first = np.zeros((n, n), bool)
        second = np.zeros((n, n), bool)
        first[y:y + 16, x:x + 5] = True
        first[y + 11:y + 16, x:x + 8] = True
        second[y:y + 16, x + 13:x + 18] = True
        second[y:y + 4, x + 13:x + 24] = True
        ink = first | second
        rgb[ink] = np.array([28, 31, 27], np.uint8)
        return ink

    add_yellow_panel(320, 244)
    first_pair = add_digit_pair(338, 262)
    add_yellow_panel(520, 730)
    second_pair = add_digit_pair(538, 748)
    add_yellow_panel(150, 540)
    single_decoy = np.zeros((n, n), bool)
    single_decoy[558:574, 168:173] = True
    rgb[single_decoy] = np.array([28, 31, 27], np.uint8)

    add_yellow_panel(720, 420)
    protected_pair = add_digit_pair(738, 438)
    sponsors[420:478, 720:838] = 255

    mask, info = car_layers_mod._yellow_panel_number_supplement(
        rgb, empty, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert info["components"][0]["reason"] == "yellow_panel_paired_digit_ink"
    assert (mask[first_pair] > 0).mean() > 0.85
    assert (mask[second_pair] > 0).mean() > 0.85
    assert (mask[single_decoy] > 0).mean() == 0
    assert (mask[protected_pair] > 0).mean() == 0


def test_smart_tga_yellow_panel_number_recovers_connected_digit_pairs_from_paint():
    n = 1024
    rgb = np.full((n, n, 3), np.array([245, 245, 242], np.uint8), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    def add_yellow_panel(x, y, w=118, h=58):
        rgb[y:y + h, x:x + w] = np.array([244, 198, 42], np.uint8)

    def add_connected_pair(x, y):
        ink = np.zeros((n, n), bool)
        ink[y:y + 17, x:x + 4] = True
        ink[y:y + 17, x + 16:x + 20] = True
        ink[y + 2:y + 3, x + 4:x + 16] = True
        rgb[ink] = np.array([25, 27, 24], np.uint8)
        return ink

    add_yellow_panel(320, 244)
    first_pair = add_connected_pair(338, 262)
    add_yellow_panel(520, 730)
    second_pair = add_connected_pair(538, 748)

    add_yellow_panel(150, 540)
    single_decoy = np.zeros((n, n), bool)
    single_decoy[558:575, 168:172] = True
    rgb[single_decoy] = np.array([25, 27, 24], np.uint8)

    sponsors = np.zeros((n, n), np.uint8)
    add_yellow_panel(720, 420)
    protected_pair = add_connected_pair(738, 438)
    sponsors[420:478, 720:838] = 255

    mask, info = car_layers_mod._yellow_panel_number_supplement(
        rgb, empty, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert info["components"][0]["reason"] == "yellow_panel_connected_digit_ink"
    assert (mask[first_pair] > 0).mean() > 0.85
    assert (mask[second_pair] > 0).mean() > 0.85
    assert (mask[single_decoy] > 0).mean() == 0
    assert (mask[protected_pair] > 0).mean() == 0


def test_smart_tga_hot_pink_paint_number_recovers_repeated_real_dlm_1169075():
    sample = Path(
        "_smart_tga_runs/cycle555_dlm_next8_after_1168248_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1169075"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
    ]
    for path in required:
        assert path.exists(), f"missing fixture artifact: {path}"

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.zeros_like(numbers)

    mask, info = car_layers_mod._hot_pink_paint_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] == "repeated_hot_pink_paint_number_core"
    ]
    assert len(components) == 2
    bboxes = sorted(component["bbox"] for component in components)
    assert bboxes == [[230, 242, 247, 108], [230, 707, 250, 98]]
    assert all(component["magenta_frac"] >= 0.92 for component in components)
    assert all(component["hot_pink_frac"] >= 0.72 for component in components)

    cv2 = car_layers_mod.cv2
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    protected = (numbers > 0) | (sponsors > 0) | (template > 0)
    hot_pink_open_paint = (
        (hue >= 150)
        & (hue <= 174)
        & (sat >= 80)
        & (val >= 110)
        & ~protected
    )
    for x, y, w, h in bboxes:
        target = hot_pink_open_paint[y:y + h, x:x + w]
        recovered = mask[y:y + h, x:x + w] > 0
        assert float((recovered & target).sum()) / float(max(1, target.sum())) > 0.95

    false_number_sponsor_panels = [
        [554, 417, 98, 34],
        [29, 770, 71, 23],
    ]
    false_number_white_panels = [
        [137, 904, 63, 108],
        [4, 908, 93, 95],
    ]
    for x, y, w, h in false_number_sponsor_panels + false_number_white_panels:
        assert int(mask[y:y + h, x:x + w].sum()) == 0

    bottom_oil_banner = [252, 957, 341, 43]
    x, y, w, h = bottom_oil_banner
    assert int(mask[y:y + h, x:x + w].sum()) == 0


def test_smart_tga_black_blue_number_family_recovers_real_dlm_1005403():
    sample = Path(
        "_smart_tga_runs/cycle588_dlm_first4_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1005403"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    for path in required:
        assert path.exists(), f"missing fixture artifact: {path}"

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._black_blue_paint_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    components = [
        component
        for component in info["components"]
        if component["reason"] in {
            "repeated_black_blue_side_number_core",
            "black_blue_rear_number_family_core",
        }
    ]
    assert len(components) == 3
    assert sorted(component["bbox"] for component in components) == [
        [284, 241, 171, 97],
        [284, 721, 171, 94],
        [810, 818, 140, 143],
    ]
    assert all(0.54 <= component["dark_frac"] <= 0.68 for component in components)
    assert all(0.14 <= component["white_frac"] <= 0.24 for component in components)
    assert all(0.15 <= component["blue_frac"] <= 0.24 for component in components)

    hard_negatives = [
        [672, 422, 113, 195],
        [20, 295, 161, 57],
        [447, 278, 144, 52],
        [999, 115, 25, 588],
    ]
    for x, y, w, h in hard_negatives:
        assert int(mask[y:y + h, x:x + w].sum()) == 0


def test_smart_tga_white_purple_number_family_recovers_real_dlm_1004124():
    sample = Path(
        "_smart_tga_runs/cycle595_dlm_1004124_dark_livery_plate_guard_v7_nocache/"
        "Dirt_Late_Model_car_num_1004124"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    for path in required:
        assert path.exists(), f"missing fixture artifact: {path}"

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_purple_paint_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 5
    assert info["candidate_count"] == 5
    assert info["capped"] is False
    components = info["components"]
    assert sorted(component["bbox"] for component in components) == [
        [272, 725, 124, 67],
        [277, 262, 124, 74],
        [349, 725, 124, 69],
        [354, 258, 124, 75],
        [849, 842, 129, 58],
    ]
    side_components = [
        component
        for component in components
        if component["reason"] == "repeated_white_purple_side_number_core"
    ]
    rear_components = [
        component
        for component in components
        if component["reason"] == "white_purple_rear_number_family_core"
    ]
    assert len(side_components) == 4
    assert len(rear_components) == 1
    assert all(component["purple_ring_frac"] >= 0.93 for component in components)
    assert all(component["sponsor_overlap"] == 0.0 for component in components)

    target_bboxes = [
        [277, 262, 124, 74],
        [354, 258, 124, 75],
        [272, 725, 124, 67],
        [349, 725, 124, 69],
        [849, 842, 129, 58],
    ]
    for x, y, w, h in target_bboxes:
        assert float((mask[y:y + h, x:x + w] > 0).mean()) >= 0.76

    hard_negatives = [
        [595, 727, 180, 197],  # white body panel near the side number
        [251, 942, 342, 27],   # long white/purple lower livery bar
        [2, 159, 177, 145],    # left sponsor panel, not a race number
        [483, 293, 108, 17],   # sponsor wordmark textline
    ]
    for x, y, w, h in hard_negatives:
        assert int(mask[y:y + h, x:x + w].sum()) == 0


def test_smart_tga_left_edge_dlm_body_panels_leave_numbers_real_1005403():
    sample = Path(
        "_smart_tga_runs/cycle588_dlm_1005403_black_blue_number_target_v3_nocache/"
        "Dirt_Late_Model_car_num_1005403"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    for path in required:
        assert path.exists(), f"missing fixture artifact: {path}"

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert sorted(component["bbox"] for component in info["components"]) == [
        [6, 0, 242, 72],
        [6, 11, 18, 128],
        [6, 81, 242, 75],
        [167, 72, 81, 6],
        [168, 37, 78, 27],
    ]
    assert {component["reason"] for component in info["components"]} == {
        "left_edge_dark_warm_body_panel",
        "left_edge_dark_warm_body_seam",
        "left_edge_warm_livery_crumb",
    }

    true_number_bboxes = [
        [284, 239, 172, 101],
        [284, 719, 171, 97],
        [810, 818, 140, 143],
    ]
    for x, y, w, h in true_number_bboxes:
        assert int(mask[y:y + h, x:x + w].sum()) == 0


def test_smart_tga_left_edge_dlm_crumb_cleanup_after_anchor_demote_real_1005403():
    sample = Path(
        "_smart_tga_runs/cycle588_dlm_1005403_black_blue_number_target_v4_nocache/"
        "Dirt_Late_Model_car_num_1005403"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    for path in required:
        assert path.exists(), f"missing fixture artifact: {path}"

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert sorted(component["bbox"] for component in info["components"]) == [
        [167, 72, 81, 6],
        [168, 37, 78, 27],
    ]
    assert {component["reason"] for component in info["components"]} == {
        "left_edge_warm_livery_crumb",
    }

    true_number_bboxes = [
        [284, 239, 172, 101],
        [284, 719, 171, 97],
        [810, 818, 140, 143],
    ]
    for x, y, w, h in true_number_bboxes:
        assert int(mask[y:y + h, x:x + w].sum()) == 0


def test_smart_tga_pale_sponsor_panel_number_recovers_ink_only():
    n = 1024
    rgb = np.full((n, n, 3), np.array([14, 15, 8], np.uint8), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)

    panel = np.zeros((135, 297), bool)
    panel[0:36, 0:170] = True
    panel[36:135, 0:95] = True
    panel[80:100, 95:197] = True
    panel[20:125, 197:287] = True
    full_panel = np.zeros((n, n), bool)
    full_panel[889:1024, 0:297] = panel
    sponsors[full_panel] = 255
    sub = rgb[889:1024, 0:297]
    sub[panel] = np.array([165, 205, 14], np.uint8)
    sub[0:36, 0:170][panel[0:36, 0:170]] = np.array([15, 16, 4], np.uint8)

    ink = np.zeros((n, n), bool)
    ink[940:982, 184:192] = True
    ink[973:986, 184:221] = True
    ink[954:962, 206:221] = True
    ink[935:1000, 230:268] = True
    ink[943:970, 238:260] = False
    ink[978:992, 238:260] = False
    left_digit = np.zeros((n, n), bool)
    left_digit[966:997, 142:169] = True
    left_digit[978:990, 156:169] = False
    left_digit[990:1001, 142:154] = False
    ink |= left_digit
    rgb[ink] = np.array([8, 8, 2], np.uint8)
    sponsors[ink] = 255

    wordmark = np.zeros((100, 255), bool)
    wordmark[8:88, 16:238] = True
    wordmark[36:62, 50:198] = False
    sponsors[804:904, 271:526][wordmark] = 255
    word_sub = rgb[804:904, 271:526]
    word_sub[wordmark] = np.array([62, 62, 6], np.uint8)
    word_ink = np.zeros((n, n), bool)
    word_ink[838:854, 334:450] = True
    rgb[word_ink] = np.array([12, 12, 4], np.uint8)
    sponsors[word_ink] = 255

    mask, info = car_layers_mod._pale_sponsor_panel_number_supplement(
        rgb, empty, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 1
    assert info["components"][0]["reason"] == "pale_sponsor_panel_number_ink"
    assert (mask[ink] > 0).mean() > 0.75
    assert info["components"][0]["bbox"][0] <= 145
    assert info["components"][0]["bbox"][2] >= 120
    assert (mask[full_panel & ~ink] > 0).mean() < 0.10
    assert (mask[word_ink] > 0).mean() == 0


def _draw_red_digit_one(tex, y0, x0):
    white = np.array([0.96, 0.96, 0.94], np.float32)
    outline_blue = np.array([0.03, 0.18, 0.86], np.float32)
    red = np.array([0.94, 0.04, 0.03], np.float32)

    white_mask = np.zeros(tex.shape[:2], bool)
    white_mask[y0 - 4:y0 + 54, x0:x0 + 47] = True
    white_mask[y0 + 30:y0 + 54, x0 - 4:x0 + 78] = True
    tex[white_mask] = white

    blue_mask = np.zeros(tex.shape[:2], bool)
    blue_mask[y0:y0 + 50, x0 + 3:x0 + 42] = True
    blue_mask[y0 + 34:y0 + 50, x0:x0 + 76] = True
    tex[blue_mask] = outline_blue

    red_mask = np.zeros(tex.shape[:2], bool)
    red_mask[y0 + 4:y0 + 48, x0 + 8:x0 + 35] = True
    red_mask[y0 + 34:y0 + 48, x0 + 6:x0 + 70] = True
    tex[red_mask] = red
    return red_mask, blue_mask


def _draw_red_outline_six(tex, y0, x0):
    white = np.array([0.96, 0.96, 0.94], np.float32)
    red = np.array([0.94, 0.04, 0.03], np.float32)

    red_mask = np.zeros(tex.shape[:2], bool)
    red_mask[y0:y0 + 5, x0:x0 + 108] = True
    red_mask[y0:y0 + 88, x0:x0 + 5] = True
    red_mask[y0 + 38:y0 + 43, x0:x0 + 82] = True
    red_mask[y0 + 83:y0 + 88, x0:x0 + 96] = True
    red_mask[y0 + 42:y0 + 88, x0 + 91:x0 + 96] = True

    white_mask = np.zeros(tex.shape[:2], bool)
    white_mask[y0 + 10:y0 + 36, x0 + 12:x0 + 88] = True
    white_mask[y0 + 48:y0 + 80, x0 + 14:x0 + 84] = True

    tex[white_mask] = white
    tex[red_mask] = red
    return red_mask, white_mask


def _draw_red_yellow_context_eight(tex, y0, x0, h=100, w=148):
    cv2 = car_layers_mod.cv2
    white = np.array([0.96, 0.96, 0.94], np.float32)
    dark = np.array([0.03, 0.03, 0.035], np.float32)
    red = np.array([0.95, 0.22, 0.20], np.float32)

    yy, xx = np.ogrid[:h, :w]
    outer = (((yy - h * 0.50) / (h * 0.48)) ** 2 + ((xx - w * 0.50) / (w * 0.47)) ** 2) <= 1.0
    hole_a = (((yy - h * 0.32) / (h * 0.13)) ** 2 + ((xx - w * 0.52) / (w * 0.23)) ** 2) <= 1.0
    hole_b = (((yy - h * 0.68) / (h * 0.14)) ** 2 + ((xx - w * 0.50) / (w * 0.24)) ** 2) <= 1.0
    local_red = outer & ~(hole_a | hole_b)

    red_mask = np.zeros(tex.shape[:2], bool)
    red_mask[y0:y0 + h, x0:x0 + w] = local_red
    red_u8 = red_mask.astype(np.uint8)
    white_mask = (cv2.dilate(red_u8, np.ones((5, 5), np.uint8)) > 0) & ~red_mask
    dark_mask = (cv2.dilate(red_u8, np.ones((9, 9), np.uint8)) > 0) & ~(white_mask | red_mask)

    tex[dark_mask] = dark
    tex[white_mask] = white
    tex[red_mask] = red
    return red_mask, white_mask, dark_mask


def _draw_red_two_digit_17(tex, y0, x0):
    cv2 = car_layers_mod.cv2
    white = np.array([0.96, 0.96, 0.94], np.float32)
    outline_blue = np.array([0.04, 0.18, 0.86], np.float32)
    red = np.array([0.94, 0.04, 0.03], np.float32)
    dark_cut = np.array([0.08, 0.08, 0.09], np.float32)

    red_mask = np.zeros(tex.shape[:2], bool)
    red_mask[y0 + 15:y0 + 76, x0 + 24:x0 + 42] = True
    red_mask[y0 + 14:y0 + 28, x0 + 10:x0 + 58] = True
    red_mask[y0 + 62:y0 + 80, x0 + 12:x0 + 64] = True
    red_mask[y0 + 14:y0 + 30, x0 + 60:x0 + 150] = True
    for dy in range(18, 78):
        x = x0 + 132 - int((dy - 18) * 0.72)
        red_mask[y0 + dy:y0 + dy + 5, x:x + 18] = True
    red_mask[y0 + 68:y0 + 82, x0 + 78:x0 + 135] = True
    red_mask[y0 + 62:y0 + 74, x0 + 42:x0 + 86] = True

    red_u8 = red_mask.astype(np.uint8)
    white_mask = (cv2.dilate(red_u8, np.ones((13, 13), np.uint8)) > 0) & ~red_mask
    blue_mask = (cv2.dilate(red_u8, np.ones((17, 17), np.uint8)) > 0) & ~white_mask & ~red_mask
    tex[blue_mask] = outline_blue
    tex[white_mask] = white
    tex[red_mask] = red
    for off in range(8, 66, 11):
        tex[y0 + off:y0 + off + 2, x0 + 18:x0 + 145] = dark_cut
    tex[y0 + 20:y0 + 78:9, x0 + 52:x0 + 55] = white
    return red_mask, white_mask, blue_mask


def test_smart_tga_red_single_digit_recovers_numbers_and_demotes_logo_numbers(monkeypatch):
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.02, 0.34, 0.20], np.float32)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)

    red_a, _blue_a = _draw_red_digit_one(tex, 70, 80)
    red_b, _blue_b = _draw_red_digit_one(tex, 250, 270)
    red_c, _blue_c = _draw_red_digit_one(tex, 380, 90)
    sponsors[red_b] = 255

    tiny_logo = (slice(76, 92), slice(420, 434))
    numbers[tiny_logo] = 255
    tex[tiny_logo] = np.array([0.92, 0.06, 0.04], np.float32)
    tex[78:91:3, 421:433] = np.array([0.96, 0.96, 0.94], np.float32)

    wide_logo = (slice(462, 478), slice(185, 305))
    numbers[wide_logo] = 255
    tex[wide_logo] = np.array([0.94, 0.94, 0.92], np.float32)
    tex[464:476:3, 190:300] = np.array([0.78, 0.02, 0.03], np.float32)
    tex[465:476:4, 190:300] = np.array([0.04, 0.12, 0.82], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": numbers.copy(),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    out_numbers = res["layers"]["numbers"]
    out_sponsors = res["layers"]["sponsors"]
    for red_mask in (red_a, red_b, red_c):
        assert (out_numbers[red_mask] > 0).mean() > 0.95
        assert (out_sponsors[red_mask] > 0).mean() < 0.05
    assert (out_numbers[tiny_logo] > 0).mean() == 0
    assert (out_numbers[wide_logo] > 0).mean() == 0
    assert (out_sponsors[tiny_logo] > 0).mean() > 0.95
    assert (out_sponsors[wide_logo] > 0).mean() > 0.95
    assert res["red_single_digit_number_guard"]["status"] == "applied"
    assert res["red_single_digit_number_guard"]["component_count"] == 3
    assert res["number_logo_false_positive_guard"]["status"] == "applied"
    assert res["number_logo_false_positive_guard"]["component_count"] == 2


def test_smart_tga_red_white_outline_digit_recovers_repeated_sixes_from_paint():
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.015, 0.015, 0.018], np.float32)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    red_a, white_a = _draw_red_outline_six(tex, 80, 90)
    red_b, white_b = _draw_red_outline_six(tex, 420, 320)
    protected_red, protected_white = _draw_red_outline_six(tex, 245, 540)
    template[protected_red | protected_white] = 255

    sponsor_bar = (slice(640, 660), slice(90, 250))
    tex[sponsor_bar] = np.array([0.92, 0.04, 0.03], np.float32)
    tex[645:650, 105:235] = np.array([0.96, 0.96, 0.94], np.float32)

    mask, info = car_layers_mod._red_single_digit_number_supplement(
        (tex * 255).astype(np.uint8), numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert info["outline_candidate_count"] == 2
    assert info["components"][0]["reason"] == "red_white_outline_single_digit"
    for red_mask, white_mask in ((red_a, white_a), (red_b, white_b)):
        assert (mask[red_mask] > 0).mean() > 0.95
        assert (mask[white_mask] > 0).mean() > 0.35
    assert (mask[sponsor_bar] > 0).mean() == 0
    assert (mask[protected_red | protected_white] > 0).mean() == 0


def test_smart_tga_red_yellow_sibling_digit_recovers_sponsor_eights():
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.96, 0.78, 0.05], np.float32)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)

    ref_red, ref_white, ref_dark = _draw_red_yellow_context_eight(tex, 330, 96)
    sponsors_red_a, sponsors_white_a, sponsors_dark_a = _draw_red_yellow_context_eight(tex, 72, 104)
    sponsors_red_b, sponsors_white_b, sponsors_dark_b = _draw_red_yellow_context_eight(tex, 552, 432, h=92, w=126)
    numbers[ref_red | ref_white | ref_dark] = 255
    sponsors[sponsors_red_a | sponsors_white_a | sponsors_dark_a] = 255
    sponsors[sponsors_red_b | sponsors_white_b | sponsors_dark_b] = 255

    frag_y, frag_x = np.ogrid[:12, :28]
    frag_local = (((frag_y - 6) / 5.1) ** 2 + ((frag_x - 14) / 12.8) ** 2) <= 1.0
    fragment_a = np.zeros((n, n), bool)
    fragment_a[98:110, 167:195] = frag_local
    frag_y2, frag_x2 = np.ogrid[:11, :26]
    frag_local_b = (((frag_y2 - 5) / 4.7) ** 2 + ((frag_x2 - 13) / 11.8) ** 2) <= 1.0
    fragment_b = np.zeros((n, n), bool)
    fragment_b[610:621, 482:508] = frag_local_b
    tex[fragment_a | fragment_b] = np.array([0.95, 0.22, 0.20], np.float32)
    sponsors[fragment_a | fragment_b] = 255

    sponsor_bar = (slice(206, 230), slice(460, 660))
    tex[sponsor_bar] = np.array([0.94, 0.04, 0.03], np.float32)
    tex[212:218, 476:644] = np.array([0.96, 0.96, 0.94], np.float32)
    sponsors[sponsor_bar] = 255

    mask, info = car_layers_mod._red_single_digit_number_supplement(
        (tex * 255).astype(np.uint8), numbers, sponsors, empty, empty
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 2
    assert {item["reason"] for item in info["components"]} == {"red_yellow_sibling_single_digit"}
    for red_mask, white_mask in ((sponsors_red_a, sponsors_white_a), (sponsors_red_b, sponsors_white_b)):
        assert (mask[red_mask] > 0).mean() > 0.95
        assert (mask[white_mask] > 0).mean() > 0.20
    assert sum(item.get("number_fragment_count", 0) for item in info["components"]) == 2
    assert (mask[fragment_a] > 0).mean() > 0.90
    assert (mask[fragment_b] > 0).mean() > 0.90
    assert (mask[ref_red] > 0).mean() == 0
    assert (mask[sponsor_bar] > 0).mean() == 0

    existing_numbers = numbers.copy()
    existing_numbers[sponsors_red_a | sponsors_white_a | sponsors_dark_a] = 255
    existing_numbers[sponsors_red_b | sponsors_white_b | sponsors_dark_b] = 255
    residual_sponsors = np.zeros_like(sponsors)
    residual_sponsors[fragment_a | fragment_b] = 255
    residual_sponsors[sponsor_bar] = 255
    mask_existing, info_existing = car_layers_mod._red_single_digit_number_supplement(
        (tex * 255).astype(np.uint8), existing_numbers, residual_sponsors, empty, empty
    )

    assert info_existing["status"] == "applied"
    assert info_existing["component_count"] == 2
    assert info_existing["existing_number_fragment_count"] == 2
    assert {item["reason"] for item in info_existing["components"]} == {
        "red_yellow_existing_number_interior_fragment"
    }
    assert (mask_existing[fragment_a] > 0).mean() > 0.90
    assert (mask_existing[fragment_b] > 0).mean() > 0.90
    assert (mask_existing[sponsor_bar] > 0).mean() == 0


def test_smart_tga_red_white_dark_wide_digit_pair_recovers_real_dlm_38631():
    artifact = Path(
        "_smart_tga_runs/cycle565_dlm_lowend8_post564_control_v1_nocache/"
        "Dirt_Late_Model_car_num_38631"
    )
    required = [
        artifact / "source_1024.png",
        artifact / "masks" / "numbers.png",
        artifact / "masks" / "sponsors.png",
        artifact / "masks" / "template.png",
        artifact / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle565 DLM 38631 diagnostic artifact not present")

    rgb = np.asarray(Image.open(artifact / "source_1024.png").convert("RGB"))

    def read_mask(name):
        return np.asarray(Image.open(artifact / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._red_single_digit_number_supplement(
        rgb,
        read_mask("numbers"),
        read_mask("sponsors"),
        read_mask("template"),
        read_mask("brand_graphics"),
    )

    assert info["status"] == "applied"
    components = [
        item for item in info["components"]
        if item["reason"] == "red_white_dark_wide_single_digit"
    ]
    assert {tuple(item["bbox"]) for item in components} == {
        (279, 235, 210, 109),
        (278, 716, 219, 101),
    }

    upper_three = (slice(234, 344), slice(288, 424))
    lower_three = (slice(716, 817), slice(278, 497))
    holley_sponsor = (slice(707, 800), slice(66, 180))
    right_side_sponsor_strip = (slice(117, 705), slice(927, 1024))

    assert (mask[upper_three] > 0).mean() > 0.80
    assert (mask[lower_three] > 0).mean() > 0.60
    assert (mask[holley_sponsor] > 0).mean() == 0
    assert (mask[right_side_sponsor_strip] > 0).mean() == 0


def test_smart_tga_raw_red_black_single_digit_recovers_real_dlm_1101717():
    artifact = Path(
        "_smart_tga_runs/cycle603_dlm_1101717_raw_red6_watermark_target_v2_nocache/"
        "Dirt_Late_Model_car_num_1101717"
    )
    required = [
        artifact / "source_1024.png",
        artifact / "masks" / "numbers.png",
        artifact / "masks" / "sponsors.png",
        artifact / "masks" / "template.png",
        artifact / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle603 DLM 1101717 diagnostic artifact not present")

    rgb = np.asarray(Image.open(artifact / "source_1024.png").convert("RGB"))

    def read_mask(name):
        return np.asarray(Image.open(artifact / "masks" / f"{name}.png").convert("L"))

    empty_numbers = np.zeros_like(read_mask("numbers"))
    mask, info = car_layers_mod._red_single_digit_number_supplement(
        rgb,
        empty_numbers,
        read_mask("sponsors"),
        read_mask("template"),
        read_mask("brand_graphics"),
    )

    assert info["status"] == "applied"
    components = [
        item for item in info["components"]
        if item["reason"] == "raw_red_black_single_digit"
    ]
    assert {tuple(item["bbox"]) for item in components} == {
        (271, 241, 110, 93),
        (278, 725, 118, 90),
        (814, 856, 144, 96),
    }

    upper_six = (slice(241, 334), slice(271, 381))
    lower_six = (slice(725, 815), slice(278, 396))
    deck_six = (slice(856, 952), slice(814, 958))
    gray_watermark_a = (slice(119, 157), slice(820, 864))
    gray_watermark_b = (slice(506, 552), slice(948, 994))

    assert (mask[upper_six] > 0).mean() > 0.65
    assert (mask[lower_six] > 0).mean() > 0.65
    assert (mask[deck_six] > 0).mean() > 0.55
    assert (mask[gray_watermark_a] > 0).mean() == 0
    assert (mask[gray_watermark_b] > 0).mean() == 0


def test_smart_tga_paired_neutral_watermark_number_glyphs_demote_dlm_1101717():
    artifact = Path(
        "_smart_tga_runs/cycle603_dlm_1101717_raw_red6_watermark_target_v1_nocache/"
        "Dirt_Late_Model_car_num_1101717"
    )
    required = [
        artifact / "source_1024.png",
        artifact / "masks" / "numbers.png",
        artifact / "masks" / "sponsors.png",
        artifact / "masks" / "template.png",
        artifact / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle603 DLM 1101717 pre-demotion diagnostic artifact not present")

    rgb = np.asarray(Image.open(artifact / "source_1024.png").convert("RGB"))

    def read_mask(name):
        return np.asarray(Image.open(artifact / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._white_livery_number_panel_to_paint(
        rgb,
        read_mask("numbers"),
        read_mask("sponsors"),
        read_mask("template"),
        read_mask("brand_graphics"),
    )

    components = [
        item for item in info["components"]
        if item["reason"] == "paired_neutral_watermark_number_glyph"
    ]
    assert {tuple(item["bbox"]) for item in components} == {
        (820, 119, 44, 38),
        (948, 506, 46, 46),
    }
    assert (mask[119:157, 820:864] > 0).mean() > 0.65
    assert (mask[506:552, 948:994] > 0).mean() > 0.55
    assert (mask[225:350, 254:397] > 0).mean() == 0
    assert (mask[709:831, 262:412] > 0).mean() == 0


def test_smart_tga_red_two_digit_number_recovers_repeated_17s_from_paint_and_sponsors():
    n = 1024
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.015, 0.015, 0.018], np.float32)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    red_a, white_a, blue_a = _draw_red_two_digit_17(tex, 120, 140)
    red_b, white_b, blue_b = _draw_red_two_digit_17(tex, 520, 280)
    red_c, white_c, blue_c = _draw_red_two_digit_17(tex, 720, 760)
    sponsors[red_c | white_c | blue_c] = 255

    protected_red, protected_white, protected_blue = _draw_red_two_digit_17(tex, 330, 720)
    template[protected_red | protected_white | protected_blue] = 255
    sponsor_bar = (slice(900, 925), slice(80, 260))
    tex[sponsor_bar] = np.array([0.93, 0.04, 0.03], np.float32)
    tex[907:912, 90:250] = np.array([0.96, 0.96, 0.94], np.float32)

    mask, info = car_layers_mod._red_two_digit_number_supplement(
        (tex * 255).astype(np.uint8), numbers, sponsors, template, brand
    )

    assert info["status"] == "applied"
    assert info["component_count"] == 3
    assert info["candidate_count"] == 3
    assert {component["reason"] for component in info["components"]} == {"red_white_blue_two_digit"}
    for red_mask, white_mask, blue_mask in (
        (red_a, white_a, blue_a),
        (red_b, white_b, blue_b),
        (red_c, white_c, blue_c),
    ):
        assert (mask[red_mask] > 0).mean() > 0.95
        assert (mask[white_mask | blue_mask] > 0).mean() > 0.55
    assert (mask[sponsor_bar] > 0).mean() == 0
    assert (mask[protected_red | protected_white | protected_blue] > 0).mean() == 0


def test_smart_tga_red_multi_digit_number_recovers_real_dlm_187s_without_budweiser_wordmark():
    sample = Path(
        "_smart_tga_runs/cycle482_dlm_batch_white_context_red_orange_arc_v1_nocache/"
        "Dirt_Late_Model_car_num_1158781"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle482 DLM 1158781 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._red_two_digit_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "red_white_dark_multi_digit"
    ]
    assert info["status"] == "applied"
    assert len(components) == 3
    assert {tuple(component["bbox"]) for component in components} == {
        (284, 245, 173, 96),
        (284, 721, 189, 82),
        (814, 844, 134, 89),
    }
    assert all(component["outline_near_frac"] >= 0.18 for component in components)
    assert float((mask[711:748, 24:250] > 0).mean()) == 0.0


def test_smart_tga_red_companion_side_number_recovers_real_dlm_1160062():
    sample = Path(
        "_smart_tga_runs/cycle487_dlm_batch_right_edge_top_template_panel_v2_nocache/"
        "Dirt_Late_Model_car_num_1160062"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle487 DLM 1160062 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._red_two_digit_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "red_white_dark_companion_side_number"
    ]
    assert info["status"] == "applied"
    assert len(components) == 1
    component = components[0]
    assert tuple(component["bbox"]) == (362, 724, 82, 79)
    assert tuple(component["anchor_bbox"]) == (271, 239, 184, 103)
    assert component["sponsor_overlap"] >= 0.99
    assert component["outline_near_frac"] >= 0.45
    assert component["area_ratio"] >= 0.20
    assert float((mask[720:808, 363:448] > 0).mean()) > 0.70
    assert float((mask[916:944, 352:567] > 0).mean()) == 0.0
    assert float((mask[710:751, 23:249] > 0).mean()) == 0.0


def test_smart_tga_red_two_digit_number_recovers_mixed_color_sibling_real_dlm_1256032():
    sample = Path(
        "_smart_tga_runs/cycle513_dlm_batch_green_cyan_swoosh_v1_nocache/"
        "Dirt_Late_Model_car_num_1256032"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle513 DLM 1256032 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._red_two_digit_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "red_white_dark_mixed_color_sibling_number"
    ]
    assert info["status"] == "applied"
    assert len(components) == 1
    component = components[0]
    assert tuple(component["bbox"]) == (803, 845, 150, 82)
    assert tuple(component["anchor_bbox"]) == (307, 227, 187, 106)
    assert component["sponsor_overlap"] >= 0.99
    assert component["anchor_green_frac"] >= 0.60
    assert component["area_ratio"] >= 0.50
    assert component["aspect_ratio"] >= 0.90
    assert float((mask[842:934, 797:956] > 0).mean()) > 0.80
    assert float((mask[281:319, 475:589] > 0).mean()) == 0.0


def test_smart_tga_mixed_red_white_dark_sponsor_logos_demote_after_real_dlm_187_recovery():
    sample = Path(
        "_smart_tga_runs/cycle483_dlm_1158781_red_multi_digit_187_target_v1_nocache/"
        "Dirt_Late_Model_car_num_1158781"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle483 DLM 1158781 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "mixed_red_white_dark_sponsor_logo_panel"
    ]
    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (466, 285, 120, 46),
        (676, 446, 52, 146),
    }
    assert all(component["edge_density"] >= 0.25 for component in components)
    assert all(component["white_text_components"] >= 8 for component in components)
    assert all(component["dark_text_components"] >= 4 for component in components)
    assert all(component["colored_text_components"] >= 4 for component in components)
    assert float((mask[285:331, 466:586] > 0).mean()) > 0.75
    assert float((mask[446:592, 676:728] > 0).mean()) > 0.52
    assert float((mask[233:348, 272:463] > 0).mean()) == 0.0
    assert float((mask[715:815, 272:485] > 0).mean()) == 0.0
    assert float((mask[839:938, 809:954] > 0).mean()) == 0.0


def test_smart_tga_left_edge_neutral_sponsor_logo_strip_demotes_from_real_dlm_numbers():
    sample = Path(
        "_smart_tga_runs/cycle484_dlm_batch_png_boundary_mixed_sponsor_logo_false_number_v1_nocache/"
        "Dirt_Late_Model_car_num_1157074"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle484 DLM 1157074 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "left_edge_neutral_sponsor_logo_strip"
    ]
    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (0, 223, 162, 61),
    }
    component = components[0]
    assert component["white_frac"] >= 0.72
    assert component["dark_text_components"] >= 12
    assert component["nonwhite_text_components"] >= 14
    assert component["broad_near_sponsor"] >= 0.88
    assert float((mask[223:284, 0:162] > 0).mean()) > 0.50
    assert float((mask[0:72, 0:149] > 0).mean()) == 0.0
    assert float((mask[320:717, 820:977] > 0).mean()) == 0.0
    assert float((mask[906:1015, 95:198] > 0).mean()) == 0.0


def test_smart_tga_dense_neutral_service_sponsor_panel_demotes_from_real_dlm_number():
    sample = Path(
        "_smart_tga_runs/cycle488_dlm_batch_red_companion_side_number_v1_nocache/"
        "Dirt_Late_Model_car_num_1149779"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle488 DLM 1149779 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in info["components"]
        if component["reason"] == "dense_neutral_service_sponsor_panel"
    ]
    assert info["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (464, 274, 124, 52),
    }
    component = components[0]
    assert component["edge_density"] >= 0.26
    assert component["white_text_components"] >= 8
    assert component["dark_text_components"] >= 6
    assert component["colored_text_components"] <= 3
    assert component["broad_near_sponsor"] >= 0.70
    assert float((mask[274:326, 464:588] > 0).mean()) > 0.80
    assert float((mask[722:812, 304:465] > 0).mean()) == 0.0


def test_smart_tga_colored_micro_logo_residual_recovers_embedded_sponsor_crumb(monkeypatch):
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.02, 0.32, 0.14], np.float32)
    sponsors = np.zeros((n, n), np.uint8)

    sponsor_white = np.array([0.96, 0.96, 0.94], np.float32)
    sponsor_blue = np.array([0.05, 0.18, 0.82], np.float32)
    embedded_crumb = (slice(103, 109), slice(135, 150))
    remote_livery_dash = (slice(310, 316), slice(330, 345))

    sponsors[100:112, 118:134] = 255
    tex[100:112, 118:134] = sponsor_white
    sponsors[100:112, 151:166] = 255
    tex[100:112, 151:166] = sponsor_white
    sponsors[96:101, 120:164] = 255
    tex[96:101, 120:164] = sponsor_blue
    sponsors[112:117, 120:164] = 255
    tex[112:117, 120:164] = sponsor_blue

    tex[embedded_crumb] = np.array([0.03, 0.82, 0.95], np.float32)
    tex[remote_livery_dash] = np.array([0.03, 0.82, 0.95], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    out_sponsors = res["layers"]["sponsors"]
    assert (out_sponsors[embedded_crumb] > 0).mean() > 0.95
    assert (out_sponsors[remote_livery_dash] > 0).mean() == 0
    assert res["colored_micro_logo_guard"]["status"] == "applied"
    assert res["colored_micro_logo_guard"]["component_count"] == 1


def test_smart_tga_panel_text_residual_recovers_blue_dark_wordmark_crumbs_from_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle504_dlm_batch_horizontal_stripe_v1_nocache/"
        "Dirt_Late_Model_car_num_1250296"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    assert all(path.exists() for path in required)

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_blue_dark_wordmark_crumb"] == 2
    boxes = {
        tuple(component["bbox"])
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_blue_dark_wordmark_crumb"
    }
    assert boxes == {(54, 160, 25, 2), (136, 134, 9, 16)}
    assert (mask[160:162, 54:79] > 0).mean() > 0.45
    assert (mask[134:150, 136:145] > 0).mean() > 0.12


def test_smart_tga_panel_text_residual_recovers_grayscale_wordmark_gap_crumbs_from_real_dlm():
    samples = [
        (
            Path(
                "_smart_tga_runs/cycle505_dlm_batch_blue_dark_wordmark_v1_nocache/"
                "Dirt_Late_Model_car_num_1250841"
            ),
            (445, 924, 7, 3),
        ),
        (
            Path(
                "_smart_tga_runs/cycle505_dlm_batch_blue_dark_wordmark_v1_nocache/"
                "Dirt_Late_Model_car_num_1295543"
            ),
            (520, 258, 7, 6),
        ),
    ]

    accepted_boxes = set()
    for sample, expected_box in samples:
        required = [
            sample / "source_1024.png",
            sample / "masks" / "numbers.png",
            sample / "masks" / "sponsors.png",
            sample / "masks" / "template.png",
            sample / "masks" / "brand_graphics.png",
        ]
        assert all(path.exists() for path in required)

        rgb = np.array(Image.open(required[0]).convert("RGB"))
        numbers = np.array(Image.open(required[1]).convert("L"))
        sponsors = np.array(Image.open(required[2]).convert("L"))
        template = np.array(Image.open(required[3]).convert("L"))
        brand = np.array(Image.open(required[4]).convert("L"))

        mask, guard = car_layers_mod._panel_text_residual_supplement(
            rgb, numbers, sponsors, template, brand
        )

        assert guard["status"] == "applied"
        assert guard["bucket_counts"]["sponsor_panel_grayscale_wordmark_gap_crumb"] == 1
        boxes = {
            tuple(component["bbox"])
            for component in guard["components"]
            if component["bucket"] == "sponsor_panel_grayscale_wordmark_gap_crumb"
        }
        assert boxes == {expected_box}
        x, y, w, h = expected_box
        assert (mask[y:y + h, x:x + w] > 0).mean() > 0.68
        accepted_boxes.update(boxes)

    assert accepted_boxes == {(445, 924, 7, 3), (520, 258, 7, 6)}


def test_smart_tga_panel_text_residual_recovers_red_tan_logo_gap_crumbs_from_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle506_dlm_batch_grayscale_wordmark_gap_v1_nocache/"
        "Dirt_Late_Model_car_num_1256032"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    assert all(path.exists() for path in required)

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_red_tan_logo_gap_crumb"] == 2
    boxes = {
        tuple(component["bbox"])
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_red_tan_logo_gap_crumb"
    }
    assert boxes == {(774, 570, 15, 19), (790, 570, 17, 14)}
    assert (mask[570:589, 774:789] > 0).mean() > 0.12
    assert (mask[570:584, 790:807] > 0).mean() > 0.12


def test_smart_tga_panel_text_residual_recovers_yellow_dark_hairline_logo_gap_from_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle507_dlm_batch_red_tan_logo_gap_v1_nocache/"
        "Dirt_Late_Model_car_num_1226283"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    assert all(path.exists() for path in required)

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_yellow_dark_hairline_logo_gap"] == 1
    boxes = {
        tuple(component["bbox"])
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_yellow_dark_hairline_logo_gap"
    }
    assert boxes == {(714, 550, 10, 3)}
    assert (mask[550:553, 714:724] > 0).mean() > 0.70


def test_smart_tga_bright_panel_micro_logo_residual_recovers_white_panel_crumbs():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([5, 42, 18], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    panel = (slice(150, 190), slice(120, 240))
    sponsors[panel] = 255
    rgb[panel] = np.array([242, 242, 236], np.uint8)

    colored_crumb = (slice(164, 170), slice(160, 176))
    white_crumb = (slice(176, 182), slice(205, 219))
    remote_dark_dash = (slice(350, 356), slice(380, 396))
    sponsors[colored_crumb] = 0
    sponsors[white_crumb] = 0
    rgb[colored_crumb] = np.array([18, 205, 238], np.uint8)
    rgb[white_crumb] = np.array([248, 248, 244], np.uint8)
    rgb[remote_dark_dash] = np.array([18, 205, 238], np.uint8)

    mask, guard = car_layers_mod._bright_panel_micro_logo_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 2
    assert (mask[165:170, 161:176] > 0).mean() > 0.95
    assert (mask[177:182, 206:219] > 0).mean() > 0.95
    assert (mask[remote_dark_dash] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_edge_clipped_saturated_textline():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([10, 10, 12], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    edge_panel = (slice(260, 320), slice(0, 110))
    sponsors[edge_panel] = 255
    rgb[edge_panel] = np.array([22, 44, 212], np.uint8)
    rgb[296:320, 0:110] = np.array([8, 10, 20], np.uint8)
    text_box = (slice(276, 310), slice(0, 68))
    yy, xx = np.indices((text_box[0].stop - text_box[0].start, text_box[1].stop - text_box[1].start))
    edge_text_hole = np.zeros_like(xx, dtype=bool)
    edge_text_hole[:, 0] = True
    for row in (0, 16, 32):
        edge_text_hole[row, :68] = True
    edge_full = np.zeros((n, n), bool)
    edge_full[text_box] = edge_text_hole
    sponsors[edge_full] = 0
    edge_rgb = rgb[text_box]
    edge_rgb[edge_text_hole & ((xx + yy) % 3 == 0)] = np.array([10, 20, 88], np.uint8)
    edge_rgb[edge_text_hole & ((xx + yy) % 3 != 0)] = np.array([20, 58, 238], np.uint8)

    center_panel = (slice(430, 500), slice(310, 420))
    sponsors[center_panel] = 255
    rgb[center_panel] = np.array([22, 44, 212], np.uint8)
    rgb[472:500, 310:420] = np.array([8, 10, 20], np.uint8)
    center_box = (slice(446, 480), slice(314, 382))
    center_full = np.zeros((n, n), bool)
    center_full[center_box] = edge_text_hole
    sponsors[center_full] = 0
    center_rgb = rgb[center_box]
    center_rgb[edge_text_hole] = np.array([20, 58, 238], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_saturated_border_textline"] == 1
    assert (mask[edge_full] > 0).mean() > 0.95
    assert (mask[center_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_labels_inside_bright_number_panel():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([12, 168, 178], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    panel = (slice(210, 300), slice(190, 410))
    numbers[panel] = 255
    rgb[panel] = np.array([246, 246, 240], np.uint8)

    word_a = (slice(247, 259), slice(296, 331))
    word_b = (slice(263, 274), slice(346, 374))
    for word in (word_a, word_b):
        numbers[word] = 0
        yy, xx = np.indices((word[0].stop - word[0].start, word[1].stop - word[1].start))
        letters = ((xx % 5) <= 2) | ((yy % 4) == 0)
        sub = rgb[word]
        sub[letters] = np.array([24, 132, 42], np.uint8)
        sub[~letters] = np.array([24, 24, 22], np.uint8)

    sponsor_panel = (slice(334, 349), slice(440, 506))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([236, 226, 42], np.uint8)
    crumb = np.ones((3, 25), bool)
    crumb_slice = (slice(339, 342), slice(455, 480))
    crumb_full = np.zeros((n, n), bool)
    crumb_full[crumb_slice] = crumb
    sponsors[crumb_full] = 0
    yy, xx = np.indices(crumb.shape)
    crumb_rgb = rgb[crumb_slice]
    crumb_rgb[xx % 4 <= 1] = np.array([18, 205, 238], np.uint8)
    crumb_rgb[xx % 4 > 1] = np.array([18, 42, 120], np.uint8)

    trim = (slice(226, 249), slice(212, 258))
    numbers[trim] = 0
    rgb[trim] = np.array([235, 88, 4], np.uint8)
    rgb[230:246, 220:254] = np.array([18, 18, 18], np.uint8)

    yellow_panel = (slice(490, 555), slice(455, 560))
    numbers[yellow_panel] = 255
    rgb[yellow_panel] = np.array([220, 224, 4], np.uint8)
    decorative_number = np.zeros((24, 42), bool)
    decorative_number[4:7, 5:34] = True
    decorative_number[7:18, 31:35] = True
    decorative_number[18:21, 8:35] = True
    decorative_slice = (slice(510, 534), slice(485, 527))
    decorative_full = np.zeros((n, n), bool)
    decorative_full[decorative_slice] = decorative_number
    numbers[decorative_full] = 0
    rgb[decorative_full] = np.array([245, 93, 6], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] >= 3
    assert guard["bucket_counts"]["number_panel_word"] >= 2
    assert guard["bucket_counts"]["sponsor_panel_crumb"] >= 1
    assert (mask[word_a] > 0).mean() > 0.95
    assert (mask[word_b] > 0).mean() > 0.95
    assert (mask[crumb_full] > 0).mean() > 0.95
    assert (mask[trim] > 0).mean() == 0
    assert (mask[decorative_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_vertical_sponsor_glyph():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([22, 22, 26], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(250, 330), slice(460, 560))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([245, 245, 238], np.uint8)
    rgb[250:330, 460:520] = np.array([238, 88, 12], np.uint8)

    glyph_slice = (slice(276, 301), slice(525, 535))
    glyph = np.zeros((25, 10), bool)
    glyph[:, 5] = True
    glyph[5, 0:6] = True
    glyph[15, 5:10] = True
    glyph_full = np.zeros((n, n), bool)
    glyph_full[glyph_slice] = glyph
    sponsors[glyph_full] = 0
    rgb[glyph_full] = np.array([248, 248, 242], np.uint8)
    red_bits = glyph_full.copy()
    red_bits[:glyph_slice[0].start + 4, :] = False
    red_bits[glyph_slice[0].start + 7:, :] = False
    rgb[red_bits] = np.array([238, 58, 24], np.uint8)

    rgb[270:322, 536:556] = np.array([244, 190, 24], np.uint8)
    warm_slice = (slice(282, 314), slice(548, 552))
    warm_glyph = np.zeros((32, 4), bool)
    warm_glyph[:, 1] = True
    warm_glyph[5:9, :] = True
    warm_glyph[21:25, :] = True
    warm_full = np.zeros((n, n), bool)
    warm_full[warm_slice] = warm_glyph
    sponsors[warm_full] = 0
    rgb[warm_full] = np.array([238, 54, 18], np.uint8)
    warm_white = warm_full.copy()
    warm_white[:warm_slice[0].start + 6, :] = False
    warm_white[warm_slice[0].start + 10:, :] = False
    rgb[warm_white] = np.array([248, 246, 228], np.uint8)

    adjacent_number_panel = (slice(278, 322), slice(556, 616))
    numbers[adjacent_number_panel] = 255
    rgb[adjacent_number_panel] = np.array([244, 190, 24], np.uint8)

    dark_logo_panel = (slice(390, 408), slice(530, 549))
    sponsors[dark_logo_panel] = 255
    rgb[dark_logo_panel] = np.array([245, 245, 238], np.uint8)
    dark_hole = np.zeros((18, 19), bool)
    dark_hole[2:16:3, 2:17] = True
    dark_full = np.zeros((n, n), bool)
    dark_full[dark_logo_panel] = dark_hole
    sponsors[dark_full] = 0
    rgb[dark_full] = np.array([18, 32, 40], np.uint8)

    orange_number_panel = (slice(470, 500), slice(290, 302))
    numbers[orange_number_panel] = 255
    rgb[orange_number_panel] = np.array([246, 246, 240], np.uint8)
    trim = np.zeros((30, 12), bool)
    trim[2:27:2, 5:8] = True
    trim_full = np.zeros((n, n), bool)
    trim_full[orange_number_panel] = trim
    numbers[trim_full] = 0
    rgb[trim_full] = np.array([238, 88, 8], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_vertical_glyph"] == 1
    assert guard["bucket_counts"]["sponsor_panel_warm_vertical_glyph"] == 1
    assert guard["component_count"] == 2
    assert (mask[glyph_full] > 0).mean() > 0.95
    assert (mask[warm_full] > 0).mean() > 0.95
    assert (mask[dark_full] > 0).mean() == 0
    assert (mask[trim_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_yellow_sponsor_wordmark():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([30, 30, 34], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    yy, xx = np.indices((7, 40))
    word = ((yy % 3) == 0) | ((xx % 4) <= 1)
    global_x = np.indices((n, n))[1]

    sponsor_panel = (slice(220, 270), slice(250, 350))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([246, 190, 22], np.uint8)

    word_slice = (slice(246, 253), slice(286, 326))
    word_full = np.zeros((n, n), bool)
    word_full[word_slice] = word
    sponsors[word_full] = 0
    rgb[word_full] = np.array([245, 245, 235], np.uint8)
    rgb[word_full & (((global_x - word_slice[1].start) % 7) == 0)] = np.array([224, 42, 24], np.uint8)
    rgb[word_full & np.isin((global_x - word_slice[1].start) % 8, (0, 2))] = np.array([42, 44, 40], np.uint8)

    nearby_number = (slice(238, 266), slice(330, 392))
    numbers[nearby_number] = 255
    rgb[nearby_number] = np.array([244, 196, 30], np.uint8)

    number_panel = (slice(386, 430), slice(250, 350))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([246, 190, 22], np.uint8)
    number_word_slice = (slice(404, 411), slice(286, 326))
    number_word_full = np.zeros((n, n), bool)
    number_word_full[number_word_slice] = word
    numbers[number_word_full] = 0
    rgb[number_word_full] = np.array([245, 245, 235], np.uint8)
    rgb[number_word_full & (((global_x - number_word_slice[1].start) % 7) == 0)] = np.array([224, 42, 24], np.uint8)
    rgb[number_word_full & np.isin((global_x - number_word_slice[1].start) % 8, (0, 2))] = np.array([42, 44, 40], np.uint8)

    remote_slice = (slice(548, 555), slice(486, 526))
    remote_full = np.zeros((n, n), bool)
    remote_full[remote_slice] = word
    rgb[540:568, 474:540] = np.array([246, 190, 22], np.uint8)
    rgb[remote_full] = np.array([245, 245, 235], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_yellow_wordmark"] == 1
    assert (mask[word_full] > 0).mean() > 0.95
    assert (mask[number_word_full] > 0).mean() == 0
    assert (mask[remote_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_warm_wordmark_crumb():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([14, 14, 16], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    panel = (slice(214, 254), slice(280, 388))
    sponsors[panel] = 255
    rgb[panel] = np.array([16, 16, 14], np.uint8)

    rgb[222:238, 284:382] = np.array([216, 168, 26], np.uint8)
    sponsors[222:238, 284:382] = 255
    rgb[222:236, 306:324] = np.array([18, 18, 16], np.uint8)

    yy, xx = np.indices((8, 12))
    crumb = (
        (xx == 0)
        | (yy == 0)
        | ((yy == 3) & (xx <= 9))
    )
    crumb_slice = (slice(224, 232), slice(308, 320))
    crumb_full = np.zeros((n, n), bool)
    crumb_full[crumb_slice] = crumb
    sponsors[crumb_full] = 0
    rgb[crumb_full] = np.array([220, 156, 22], np.uint8)
    crumb_dark_local = np.zeros_like(crumb, bool)
    crumb_dark_local[np.where(crumb)] = (np.arange(int(crumb.sum())) % 4) == 0
    crumb_dark = np.zeros((n, n), bool)
    crumb_dark[crumb_slice] = crumb_dark_local
    rgb[crumb_dark] = np.array([8, 8, 6], np.uint8)

    number_panel = (slice(390, 430), slice(280, 388))
    numbers[number_panel] = 255
    template[number_panel] = 255
    rgb[number_panel] = np.array([16, 16, 14], np.uint8)
    rgb[398:414, 284:382] = np.array([216, 168, 26], np.uint8)
    near_number_full = np.zeros((n, n), bool)
    near_number_full[slice(400, 408), slice(308, 320)] = crumb
    numbers[near_number_full] = 0
    template[near_number_full] = 0
    rgb[near_number_full] = np.array([220, 156, 22], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_warm_wordmark_crumb"] == 1
    assert (mask[crumb_full] > 0).mean() > 0.95
    assert (mask[near_number_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_yellow_dark_wordmark_crumb():
    sample = Path(
        "_smart_tga_runs/cycle445_dlm_batch05_red_white_number_panel_outline_controls_v1/"
        "Dirt_Late_Model_car_num_1111190"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle445 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_yellow_dark_wordmark_crumb"] == 5
    bboxes = {
        tuple(component["bbox"])
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_yellow_dark_wordmark_crumb"
    }
    assert bboxes == {
        (538, 271, 5, 9),
        (532, 272, 4, 7),
        (519, 775, 4, 8),
        (526, 775, 4, 8),
        (508, 778, 8, 5),
    }
    assert int((mask > 0).sum()) >= 100


def test_smart_tga_panel_text_residual_recovers_vertical_mixed_text_sliver():
    sample = Path(
        "_smart_tga_runs/cycle447_dlm_batch05_tiny_number_detail_controls_v2/"
        "Dirt_Late_Model_car_num_1103278"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle447 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["bucket_counts"]["sponsor_panel_vertical_mixed_text_sliver"] == 1
    assert guard["components"][0]["bbox"] == [58, 456, 3, 7]
    assert guard["components"][0]["bucket"] == "sponsor_panel_vertical_mixed_text_sliver"
    assert (mask[456:463, 58:61] > 0).mean() > 0.95
    assert (mask[503:512, 696:700] > 0).mean() == 0
    assert (mask[547:556, 696:700] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_dark_sponsor_logo_shard():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([8, 18, 22], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    panel = (slice(236, 304), slice(238, 326))
    sponsors[panel] = 255
    rgb[panel] = np.array([4, 20, 28], np.uint8)
    rgb[236:304, 238:248] = np.array([32, 180, 218], np.uint8)

    yy, xx = np.indices((18, 19))
    shard = (np.abs(yy - (xx * 0.75 + 2.0)) <= 1.4) | (
        np.abs(yy - (19.0 - xx * 0.55)) <= 1.0
    )
    logo_slice = (slice(258, 276), slice(270, 289))
    logo_full = np.zeros((n, n), bool)
    logo_full[logo_slice] = shard
    sponsors[logo_full] = 0
    logo_patch = rgb[logo_slice]
    cyan_bits = shard & ((xx % 3) == 0)
    logo_patch[shard & ~cyan_bits] = np.array([4, 18, 24], np.uint8)
    logo_patch[cyan_bits] = np.array([18, 180, 224], np.uint8)

    red_full = np.zeros((n, n), bool)
    red_full[slice(258, 276), slice(296, 315)] = shard
    sponsors[red_full] = 0
    rgb[red_full] = np.array([220, 32, 20], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[slice(520, 538), slice(530, 549)] = shard
    remote_patch = rgb[520:538, 530:549]
    remote_patch[shard & ~cyan_bits] = np.array([4, 18, 24], np.uint8)
    remote_patch[cyan_bits] = np.array([18, 180, 224], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["bucket_counts"]["sponsor_panel_dark_logo_shard"] == 1
    assert (mask[logo_full] > 0).mean() > 0.95
    assert (mask[red_full] > 0).mean() == 0
    assert (mask[remote_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_dark_sponsor_text_crumbs():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([10, 10, 12], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    panel = (slice(300, 380), slice(140, 310))
    sponsors[panel] = 255
    rgb[panel] = np.array([7, 7, 8], np.uint8)
    rgb[366:380, 140:310] = np.array([232, 36, 28], np.uint8)

    def add_letter_crumb(y0, x0, h, w):
        crumb = np.ones((h, w), bool)
        crumb_full = np.zeros((n, n), bool)
        crumb_full[y0:y0 + h, x0:x0 + w] = crumb
        sponsors[crumb_full] = 0
        patch = rgb[y0:y0 + h, x0:x0 + w]
        yy, xx = np.indices((h, w))
        white = (xx == w // 2) | (yy == h // 2)
        patch[white] = np.array([246, 246, 242], np.uint8)
        patch[~white] = np.array([10, 10, 10], np.uint8)
        return crumb_full

    crumb_a = add_letter_crumb(325, 214, 5, 4)
    crumb_b = add_letter_crumb(342, 250, 6, 4)

    remote_crumb = np.zeros((n, n), bool)
    remote_crumb[520:526, 500:504] = True
    remote_patch = rgb[520:526, 500:504]
    remote_patch[:, 2] = np.array([246, 246, 242], np.uint8)
    remote_patch[:, :2] = np.array([10, 10, 10], np.uint8)
    remote_patch[:, 3:] = np.array([10, 10, 10], np.uint8)

    number_panel = (slice(410, 500), slice(390, 520))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([8, 8, 10], np.uint8)
    number_decoy = np.zeros((n, n), bool)
    number_decoy[442:448, 450:454] = True
    numbers[number_decoy] = 0
    number_patch = rgb[442:448, 450:454]
    number_patch[:, 2] = np.array([246, 246, 242], np.uint8)
    number_patch[:, :2] = np.array([10, 10, 10], np.uint8)
    number_patch[:, 3:] = np.array([10, 10, 10], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_dark_text_crumb"] == 2
    assert guard["component_count"] == 2
    assert (mask[crumb_a] > 0).mean() > 0.95
    assert (mask[crumb_b] > 0).mean() > 0.95
    assert (mask[remote_crumb] > 0).mean() == 0
    assert (mask[number_decoy] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_white_sponsor_logo_fill():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([248, 248, 244], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_badge = (slice(250, 318), slice(300, 430))
    sponsors[sponsor_badge] = 255
    rgb[sponsor_badge] = np.array([12, 12, 14], np.uint8)
    rgb[296:318, 300:430] = np.array([228, 42, 78], np.uint8)

    lens_shape = np.zeros((10, 37), bool)
    for xx in range(37):
        yy = (xx * 9) // 36
        lens_shape[yy, xx] = True
        if xx % 3 == 0 and yy + 1 < 10:
            lens_shape[yy + 1, xx] = True

    lens_slice = (slice(268, 278), slice(340, 377))
    lens_full = np.zeros((n, n), bool)
    lens_full[lens_slice] = lens_shape
    sponsors[lens_full] = 0
    rgb[lens_full] = np.array([246, 246, 242], np.uint8)

    remote_slice = (slice(520, 530), slice(500, 537))
    remote_full = np.zeros((n, n), bool)
    remote_full[remote_slice] = lens_shape
    rgb[remote_full] = np.array([246, 246, 242], np.uint8)

    number_badge = (slice(420, 500), slice(180, 320))
    numbers[number_badge] = 255
    rgb[number_badge] = np.array([12, 12, 14], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(450, 460), slice(230, 267)] = lens_shape
    numbers[number_full] = 0
    rgb[number_full] = np.array([246, 246, 242], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_white_logo_fill"] == 1
    assert guard["component_count"] == 1
    assert (mask[lens_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_vertical_white_wordmark_holes():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([30, 92, 64], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(230, 330), slice(300, 430))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([226, 216, 30], np.uint8)
    rgb[230:330, 300:318] = np.array([44, 150, 66], np.uint8)
    rgb[230:330, 410:430] = np.array([62, 166, 68], np.uint8)
    yy_strip, xx_strip = np.indices((62, 83))
    pale_panel_text = ((yy_strip + xx_strip) % 3) == 0
    rgb[250:312, 322:405][pale_panel_text] = np.array([246, 246, 238], np.uint8)

    def small_wordmark_shape(h, w, target):
        shape = np.zeros((h, w), bool)
        shape[:, 0] = True
        shape[0, :] = True
        shape[h // 2, :] = True
        shape[h - 1, :] = True
        if shape.sum() < target:
            shape[1, w - 1] = True
        coords = np.argwhere(shape)
        if coords.shape[0] > target:
            for yx in coords[target:]:
                shape[tuple(yx)] = False
        return shape

    def add_wordmark_hole(y0, x0, h, w, target):
        shape = small_wordmark_shape(h, w, target)
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = shape
        sponsors[full] = 0
        yy, xx = np.indices((h, w))
        yellow = shape & (((yy + xx) % 3) == 0)
        white = shape & ~yellow
        local = rgb[y0:y0 + h, x0:x0 + w]
        yellow_rgb = np.array([180, 190, 28], np.uint8)
        if target >= 57:
            yellow_rgb = np.array([150, 165, 24], np.uint8)
        local[yellow] = yellow_rgb
        local[white] = np.array([244, 244, 238], np.uint8)
        return full

    hole_a = add_wordmark_hole(264, 350, 12, 11, 43)
    hole_b = add_wordmark_hole(282, 351, 15, 15, 57)

    remote_hole = np.zeros((n, n), bool)
    remote_shape = small_wordmark_shape(12, 11, 43)
    remote_hole[500:512, 510:521] = remote_shape
    rgb[500:512, 510:521][remote_shape] = np.array([244, 244, 238], np.uint8)

    number_panel = (slice(410, 510), slice(260, 390))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([226, 216, 30], np.uint8)
    number_hole = np.zeros((n, n), bool)
    number_shape = small_wordmark_shape(12, 11, 43)
    number_hole[448:460, 320:331] = number_shape
    numbers[number_hole] = 0
    rgb[448:460, 320:331][number_shape] = np.array([244, 244, 238], np.uint8)

    template_panel = (slice(120, 220), slice(475, 605))
    template[template_panel] = 255
    rgb[template_panel] = np.array([226, 216, 30], np.uint8)
    template_hole = np.zeros((n, n), bool)
    template_shape = small_wordmark_shape(15, 15, 57)
    template_hole[160:175, 535:550] = template_shape
    template[template_hole] = 0
    rgb[160:175, 535:550][template_shape] = np.array([244, 244, 238], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_vertical_white_wordmark_hole"] == 2
    assert guard["component_count"] == 2
    assert (mask[hole_a] > 0).mean() > 0.95
    assert (mask[hole_b] > 0).mean() > 0.95
    assert (mask[remote_hole] > 0).mean() == 0
    assert (mask[number_hole] > 0).mean() == 0
    assert (mask[template_hole] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_tiny_red_black_contingency_logo():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([116, 120, 118], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def tiny_logo_shape():
        dark = np.zeros((8, 6), bool)
        dark[:, 0] = True
        dark[3:5, 1] = True
        white = np.zeros((8, 6), bool)
        white[4, 2] = True
        red = np.zeros((8, 6), bool)
        red[2:6, 3:6] = True
        shape = dark | white | red
        assert int(shape.sum()) == 23
        return shape, dark, white, red

    shape, dark, white, red = tiny_logo_shape()

    def paint_logo_context(layer, y0, x0):
        local_rect = (slice(y0 - 6, y0 + 14), slice(x0 - 6, x0 + 12))
        layer[local_rect] = 255
        rgb[local_rect] = np.array([116, 120, 118], np.uint8)
        rgb[y0 - 6:y0 + 2, x0 - 6:x0 + 12] = np.array([246, 246, 238], np.uint8)
        rgb[y0 + 2:y0 + 10, x0 - 6:x0 - 3] = np.array([36, 156, 52], np.uint8)
        rgb[y0 + 2:y0 + 10, x0 + 9:x0 + 12] = np.array([36, 156, 52], np.uint8)
        rgb[y0 + 2:y0 + 10, x0 - 3:x0] = np.array([204, 30, 38], np.uint8)
        rgb[y0 + 2:y0 + 10, x0 + 6:x0 + 9] = np.array([204, 30, 38], np.uint8)
        rgb[y0 + 10:y0 + 14, x0 - 6:x0 + 12] = np.array([25, 27, 25], np.uint8)

        full = np.zeros((n, n), bool)
        full[y0:y0 + 8, x0:x0 + 6] = shape
        layer[full] = 0
        local = rgb[y0:y0 + 8, x0:x0 + 6]
        local[dark] = np.array([18, 19, 21], np.uint8)
        local[white] = np.array([238, 238, 232], np.uint8)
        local[red] = np.array([216, 26, 32], np.uint8)
        return full

    sponsor_logo = paint_logo_context(sponsors, 286, 350)

    remote_logo = np.zeros((n, n), bool)
    remote_logo[500:508, 500:506] = shape
    rgb[500:508, 500:506][dark] = np.array([18, 19, 21], np.uint8)
    rgb[500:508, 500:506][white] = np.array([238, 238, 232], np.uint8)
    rgb[500:508, 500:506][red] = np.array([216, 26, 32], np.uint8)

    number_logo = paint_logo_context(numbers, 430, 220)
    template_logo = paint_logo_context(template, 158, 560)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_tiny_red_black_contingency_logo"] == 1
    assert guard["component_count"] == 1
    assert (mask[sponsor_logo] > 0).mean() > 0.95
    assert (mask[remote_logo] > 0).mean() == 0
    assert (mask[number_logo] > 0).mean() == 0
    assert (mask[template_logo] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_sponsor_shell_logo_fill():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([18, 20, 24], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def logo_shape():
        shape = np.zeros((41, 72), bool)
        shape[1:5, 3:69] = True
        shape[36:40, 3:69] = True
        shape[1:40, 3:8] = True
        shape[1:40, 64:69] = True
        shape[18:23, 7:65] = True
        return shape

    shape = logo_shape()
    sponsor_badge = (slice(888, 961), slice(816, 948))
    sponsors[sponsor_badge] = 255
    rgb[sponsor_badge] = np.array([252, 230, 24], np.uint8)
    rgb[888:896, 816:948] = np.array([246, 52, 24], np.uint8)
    rgb[952:961, 816:948] = np.array([246, 52, 24], np.uint8)
    logo_slice = (slice(913, 954), slice(823, 895))
    logo_full = np.zeros((n, n), bool)
    logo_full[logo_slice] = shape
    sponsors[logo_full] = 0
    rgb[logo_full] = np.array([214, 238, 24], np.uint8)
    rgb[logo_full & ((np.indices((n, n))[1] % 17) < 2)] = np.array([240, 54, 28], np.uint8)

    number_badge = (slice(180, 253), slice(180, 312))
    numbers[number_badge] = 255
    rgb[number_badge] = np.array([236, 236, 232], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(205, 246), slice(187, 259)] = shape
    numbers[number_full] = 0
    rgb[number_full] = np.array([214, 238, 24], np.uint8)

    template_badge = (slice(430, 503), slice(180, 312))
    template[template_badge] = 255
    rgb[template_badge] = np.array([252, 230, 24], np.uint8)
    template_full = np.zeros((n, n), bool)
    template_full[slice(455, 496), slice(187, 259)] = shape
    template[template_full] = 0
    rgb[template_full] = np.array([214, 238, 24], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_shell_logo_fill"] == 1
    assert guard["component_count"] == 1
    assert (mask[logo_full] > 0).mean() > 0.95
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_pale_sponsor_hairline_text():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([250, 250, 250], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(220, 286), slice(38, 138))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([18, 64, 22], np.uint8)
    rgb[232:275, 52:128] = np.array([24, 32, 28], np.uint8)

    yy, xx = np.indices((2, 19))
    sparse_line = ((xx + yy) % 2) == 0
    line_slice = (slice(258, 260), slice(63, 82))
    line_full = np.zeros((n, n), bool)
    line_full[line_slice] = sparse_line
    sponsors[line_full] = 0
    rgb[line_full] = np.array([190, 190, 186], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[slice(500, 502), slice(500, 519)] = sparse_line
    rgb[remote_full] = np.array([190, 190, 186], np.uint8)

    number_badge = (slice(410, 476), slice(42, 142))
    numbers[number_badge] = 255
    rgb[number_badge] = np.array([24, 32, 28], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(448, 450), slice(63, 82)] = sparse_line
    numbers[number_full] = 0
    rgb[number_full] = np.array([190, 190, 186], np.uint8)

    dark_line_full = np.zeros((n, n), bool)
    dark_line_full[slice(260, 262), slice(96, 115)] = sparse_line
    sponsors[dark_line_full] = 0
    rgb[dark_line_full] = np.array([90, 0, 160], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_hairline_text"] == 1
    assert guard["component_count"] == 1
    assert (mask[line_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[dark_line_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_neutral_textline_gaps_real_dlm_310926():
    sample = Path(
        "_smart_tga_runs/cycle536_dlm_next4_high_saturation_right_edge_red_strip_controls_v1_nocache/"
        "Dirt_Late_Model_car_num_310926"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle536 DLM 310926 route artifacts are not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    masks = {
        name: np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"), dtype=np.uint8)
        for name in ("numbers", "sponsors", "template", "brand_graphics")
    }

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb,
        masks["numbers"],
        masks["sponsors"],
        masks["template"],
        masks["brand_graphics"],
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_neutral_textline_gap"] == 3
    recovered = {
        tuple(component["bbox"]): component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_neutral_textline_gap"
    }
    assert set(recovered) == {
        (90, 226, 40, 3),
        (68, 229, 21, 2),
        (47, 231, 19, 2),
    }
    for bbox, component in recovered.items():
        x, y, w, h = bbox
        assert int((mask[y:y + h, x:x + w] > 0).sum()) == component["area"]
        assert component["sponsor_overlap"] == 1.0
        assert component["number_overlap"] == 0.0
        assert component["ring_sponsor"] >= 0.96
        assert component["bbox_number_fill"] == 0.0
        assert component["bbox_template_fill"] == 0.0

    # Nearby red vertical number-art/logo shard sits in Sponsor dilation too,
    # but it is saturated/tall and must remain editable Paint/number context.
    assert int((mask[269:320, 359:381] > 0).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_single_pixel_sponsor_hairline_text():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([22, 22, 24], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(300, 372), slice(382, 504))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([18, 18, 20], np.uint8)
    rgb[324:329, 408:476] = np.array([236, 236, 230], np.uint8)
    rgb[332:337, 408:476] = np.array([236, 236, 230], np.uint8)
    rgb[329:332, 410:474] = np.array([28, 36, 76], np.uint8)

    def paint_mixed_line(row, x0, length, red=False):
        full = np.zeros((n, n), bool)
        full[row, x0:x0 + length] = True
        if red:
            rgb[full] = np.array([210, 18, 22], np.uint8)
            return full
        for offset, xx in enumerate(range(x0, x0 + length)):
            if offset % 10 == 0:
                rgb[row, xx] = np.array([38, 76, 190], np.uint8)
            elif offset % 10 == 1:
                rgb[row, xx] = np.array([44, 44, 46], np.uint8)
            else:
                rgb[row, xx] = np.array([232, 232, 226], np.uint8)
        return full

    positive_full = paint_mixed_line(330, 424, 38)
    sponsors[positive_full] = 0

    remote_full = paint_mixed_line(620, 424, 38)

    number_panel = (slice(430, 502), slice(382, 504))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([236, 236, 230], np.uint8)
    number_full = paint_mixed_line(460, 424, 38, red=True)
    numbers[number_full] = 0

    template_panel = (slice(540, 612), slice(382, 504))
    template[template_panel] = 255
    rgb[template_panel] = np.array([236, 236, 230], np.uint8)
    template_full = paint_mixed_line(570, 424, 38)
    template[template_full] = 0

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_single_pixel_hairline_text"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_cool_sponsor_hairline_logo():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([248, 248, 248], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(206, 248), slice(490, 546))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([18, 14, 18], np.uint8)
    rgb[208:224, 492:502] = np.array([238, 205, 38], np.uint8)
    rgb[238:246, 534:544] = np.array([238, 205, 38], np.uint8)
    rgb[216:238, 506:532] = np.array([24, 20, 24], np.uint8)

    line_full = np.zeros((n, n), bool)
    line_full[230:232, 516:526] = True
    sponsors[line_full] = 0
    rgb[230:231, 516:526] = np.array([42, 0, 74], np.uint8)
    rgb[231:232, 516:526] = np.array([100, 0, 170], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[500:502, 516:526] = True
    rgb[remote_full] = np.array([100, 0, 170], np.uint8)

    number_panel = (slice(390, 432), slice(490, 546))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([18, 14, 18], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[410:412, 516:526] = True
    numbers[number_full] = 0
    rgb[410:411, 516:526] = np.array([42, 0, 74], np.uint8)
    rgb[411:412, 516:526] = np.array([100, 0, 170], np.uint8)

    red_line_full = np.zeros((n, n), bool)
    red_line_full[234:236, 516:526] = True
    sponsors[red_line_full] = 0
    rgb[red_line_full] = np.array([168, 0, 20], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_cool_hairline_logo"] == 1
    assert guard["component_count"] == 1
    assert (mask[line_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_line_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_lime_dark_sponsor_hairline_logo():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([246, 246, 246], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_panel(y0, x0, owner):
        panel = (slice(y0, y0 + 52), slice(x0, x0 + 82))
        owner[panel] = 255
        rgb[panel] = np.array([18, 20, 14], np.uint8)
        rgb[y0 + 12:y0 + 25, x0 + 12:x0 + 46] = np.array([202, 178, 24], np.uint8)
        rgb[y0 + 30:y0 + 43, x0 + 48:x0 + 76] = np.array([202, 178, 24], np.uint8)

    def paint_hairline(y0, x0):
        full = np.zeros((n, n), bool)
        full[y0:y0 + 2, x0:x0 + 11] = True
        rgb[y0:y0 + 1, x0:x0 + 11] = np.array([38, 42, 12], np.uint8)
        rgb[y0 + 1:y0 + 2, x0:x0 + 11] = np.array([72, 150, 18], np.uint8)
        return full

    def paint_scaled_hairline(y0, x0):
        full = np.zeros((n, n), bool)
        full[y0:y0 + 4, x0:x0 + 22] = True
        rgb[y0:y0 + 1, x0:x0 + 22] = np.array([38, 42, 12], np.uint8)
        rgb[y0 + 1:y0 + 2, x0:x0 + 22] = np.array([72, 150, 18], np.uint8)
        rgb[y0 + 2:y0 + 3, x0:x0 + 22] = np.array([38, 42, 12], np.uint8)
        rgb[y0 + 3:y0 + 4, x0:x0 + 22] = np.array([72, 150, 18], np.uint8)
        return full

    paint_panel(300, 300, sponsors)
    positive_full = paint_hairline(328, 338)
    sponsors[positive_full] = 0

    paint_panel(390, 300, sponsors)
    scaled_positive_full = paint_scaled_hairline(418, 338)
    sponsors[scaled_positive_full] = 0

    remote_full = paint_hairline(520, 338)

    paint_panel(610, 300, sponsors)
    number_panel = (slice(618, 648), slice(330, 390))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([18, 20, 14], np.uint8)
    number_full = paint_hairline(628, 338)
    numbers[number_full] = 0

    paint_panel(720, 300, sponsors)
    template_panel = (slice(728, 758), slice(330, 390))
    template[template_panel] = 255
    rgb[template_panel] = np.array([18, 20, 14], np.uint8)
    template_full = paint_hairline(738, 338)
    template[template_full] = 0

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_lime_dark_hairline_logo"] == 2
    assert guard["component_count"] == 2
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[scaled_positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_blue_sponsor_micro_logo_crumbs():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([246, 246, 246], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(880, 940), slice(650, 735))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([16, 74, 196], np.uint8)
    rgb[890:930, 650:678] = np.array([238, 242, 246], np.uint8)
    rgb[902:916, 706:732] = np.array([236, 240, 244], np.uint8)

    crumb_shape = np.zeros((6, 14), bool)
    crumb_shape[:, 0:2] = True
    crumb_shape[0, 2:8] = True
    crumb_shape[1, 8] = True
    crumb_shape[2, 9] = True
    crumb_shape[3, 10] = True
    crumb_shape[4, 11] = True
    crumb_shape[5, 12:14] = True
    crumb_white = np.zeros((6, 14), bool)
    crumb_white[:, 0] = True
    crumb_white[0, 2:5] = True
    crumb_white[5, 12] = True

    crumb_slice = (slice(900, 906), slice(678, 692))
    crumb_full = np.zeros((n, n), bool)
    crumb_full[crumb_slice] = crumb_shape
    sponsors[crumb_full] = 0
    rgb[crumb_full] = np.array([18, 96, 218], np.uint8)
    crumb_white_full = np.zeros((n, n), bool)
    crumb_white_full[crumb_slice] = crumb_shape & crumb_white
    rgb[crumb_white_full] = np.array([238, 242, 246], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[slice(480, 486), slice(678, 692)] = crumb_shape
    rgb[remote_full] = np.array([18, 96, 218], np.uint8)

    number_panel = (slice(720, 780), slice(650, 735))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([16, 74, 196], np.uint8)
    rgb[730:770, 650:678] = np.array([238, 242, 246], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(740, 746), slice(678, 692)] = crumb_shape
    numbers[number_full] = 0
    rgb[number_full] = np.array([18, 96, 218], np.uint8)

    red_full = np.zeros((n, n), bool)
    red_full[slice(910, 916), slice(694, 708)] = crumb_shape
    sponsors[red_full] = 0
    rgb[red_full] = np.array([220, 38, 32], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_blue_micro_logo_crumb"] == 1
    assert guard["component_count"] == 1
    assert (mask[crumb_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_mixed_blue_sponsor_micro_logo_crumbs():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([246, 246, 246], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(880, 940), slice(650, 735))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([16, 74, 196], np.uint8)
    rgb[890:930, 650:678] = np.array([238, 242, 246], np.uint8)
    rgb[902:916, 706:732] = np.array([236, 240, 244], np.uint8)

    residual_shape = np.zeros((6, 14), bool)
    residual_shape[:, 0:2] = True
    residual_shape[0, 2:8] = True
    residual_shape[1, 8:11] = True
    residual_shape[2, 9:12] = True
    residual_shape[3, 10] = True
    residual_shape[4, 11] = True
    residual_shape[5, 12:14] = True

    residual_white = np.zeros((6, 14), bool)
    residual_white[:, 0] = True
    residual_white[0, 2:6] = True
    residual_white[1, 8:10] = True
    residual_white[5, 12] = True

    crumb_slice = (slice(900, 906), slice(678, 692))
    crumb_full = np.zeros((n, n), bool)
    crumb_full[crumb_slice] = residual_shape
    sponsors[crumb_full] = 0
    rgb[crumb_full] = np.array([18, 96, 218], np.uint8)
    crumb_white_full = np.zeros((n, n), bool)
    crumb_white_full[crumb_slice] = residual_shape & residual_white
    rgb[crumb_white_full] = np.array([238, 242, 246], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[slice(480, 486), slice(678, 692)] = residual_shape
    rgb[remote_full] = np.array([18, 96, 218], np.uint8)

    number_panel = (slice(720, 780), slice(650, 735))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([16, 74, 196], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(740, 746), slice(678, 692)] = residual_shape
    numbers[number_full] = 0
    rgb[number_full] = np.array([18, 96, 218], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_mixed_blue_micro_logo_crumb"] == 1
    assert guard["component_count"] == 1
    assert (mask[crumb_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_tiny_blue_sponsor_wordmark_crumbs():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([238, 238, 238], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(780, 820), slice(790, 850))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([236, 240, 246], np.uint8)
    rgb[790:804, 807:835] = np.array([50, 132, 210], np.uint8)
    rgb[786:802, 794:806] = np.array([236, 240, 246], np.uint8)
    rgb[804:818, 832:848] = np.array([236, 240, 246], np.uint8)

    dot_shape = np.ones((5, 5), bool)
    dot_shape[0, 0] = False
    dot_shape[0, 4] = False
    dot_shape[4, 0] = False
    dot_shape[4, 4] = False
    dot_full = np.zeros((n, n), bool)
    dot_full[793:798, 826:831] = dot_shape
    sponsors[dot_full] = 0
    rgb[dot_full] = np.array([58, 132, 206], np.uint8)
    rgb[793, 827] = np.array([236, 240, 246], np.uint8)
    rgb[794, 830] = np.array([236, 240, 246], np.uint8)
    rgb[797, 827] = np.array([236, 240, 246], np.uint8)

    word_shape = np.zeros((9, 18), bool)
    word_shape[:, 0:9] = True
    word_shape[2:7, 9:14] = True
    word_full = np.zeros((n, n), bool)
    word_full[795:804, 807:825] = word_shape
    sponsors[word_full] = 0
    rgb[word_full] = np.array([72, 140, 210], np.uint8)
    word_white = np.zeros((n, n), bool)
    word_white[795:804, 807:825] = word_shape & (np.indices((9, 18))[1] % 17 == 0)
    rgb[word_white] = np.array([236, 240, 246], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[580:585, 826:831] = True
    rgb[remote_full] = np.array([58, 132, 206], np.uint8)

    number_panel = (slice(700, 740), slice(790, 850))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([236, 240, 246], np.uint8)
    rgb[710:736, 790:850] = np.array([50, 132, 210], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[713:718, 826:831] = True
    numbers[number_full] = 0
    rgb[number_full] = np.array([58, 132, 206], np.uint8)

    red_full = np.zeros((n, n), bool)
    red_full[806:811, 826:831] = True
    sponsors[red_full] = 0
    rgb[red_full] = np.array([210, 34, 40], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_tiny_blue_wordmark_crumb"] >= 1
    assert guard["component_count"] >= 1
    assert (mask[word_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_blue_sponsor_underline_strip():
    n = 1024
    rgb = np.full((n, n, 3), np.array([26, 28, 30], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def blue_strip(
        y0,
        x0,
        *,
        unanchored=False,
        number_context=False,
        template_stripe=False,
        single_row=False,
    ):
        panel = (slice(y0 - 9, y0 + 11), slice(x0 - 6, x0 + 42))
        if not unanchored:
            sponsors[panel] = 255
        rgb[panel] = np.array([36, 40, 48], np.uint8)
        rgb[y0 - 7:y0 - 1, x0 - 5:x0 + 40] = np.array([242, 242, 238], np.uint8)

        if template_stripe:
            template[y0 - 9:y0 + 11, x0 - 12:x0 + 48] = 255
            sponsors[y0 - 2:y0 + 2, x0 - 3:x0 + 37] = 255
            rgb[y0 - 9:y0 + 11, x0 - 12:x0 + 48] = np.array([30, 34, 36], np.uint8)
            rgb[y0 - 8:y0 + 9, x0 + 18:x0 + 48] = np.array([30, 242, 242], np.uint8)

        if number_context:
            numbers[y0 - 12:y0 + 12, x0 - 8:x0 + 44] = 255

        full = np.zeros((n, n), bool)
        full[y0, x0:x0 + 34] = True
        if not single_row:
            full[y0 + 1, x0] = True
        rgb[full] = np.array([12, 76, 198], np.uint8)
        sponsors[full] = 0
        numbers[full] = 0
        template[full] = 0
        return full

    positive = blue_strip(180, 180)
    single_row_positive = blue_strip(180, 500, single_row=True)
    unanchored = blue_strip(260, 180, unanchored=True)
    number_context = blue_strip(340, 180, number_context=True)
    template_context = blue_strip(420, 180, template_stripe=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_blue_underline_strip"] == 2
    assert guard["component_count"] == 2
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[single_row_positive] > 0).mean() > 0.95
    assert (mask[unanchored] > 0).mean() == 0
    assert (mask[number_context] > 0).mean() == 0
    assert (mask[template_context] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_dark_blue_white_vertical_logo_stroke():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([20, 22, 26], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    stroke_shape = np.zeros((12, 9), bool)
    stroke_shape[:, 1] = True
    stroke_shape[0, 2:9] = True
    stroke_shape[5, 2:9] = True

    def paint_dark_panel_stroke(
        y0,
        x0,
        *,
        sponsor_context=True,
        number_context=False,
        template_context=False,
        grayscale=False,
    ):
        panel = (slice(y0 - 18, y0 + 30), slice(x0 - 28, x0 + 38))
        rgb[panel] = np.array([20, 22, 26], np.uint8)
        if sponsor_context:
            sponsors[panel] = 255
            rgb[y0 - 4:y0 + 18, x0 + 10:x0 + 14] = np.array([34, 104, 220], np.uint8)
            rgb[y0 - 2:y0 + 16, x0 - 6:x0 - 3] = np.array([218, 224, 230], np.uint8)
        if number_context:
            numbers[panel] = 255

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 12), slice(x0, x0 + 9)] = stroke_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if grayscale:
                rgb[yy0, xx0] = np.array([220, 222, 224], np.uint8)
            elif idx % 3 == 0:
                rgb[yy0, xx0] = np.array([36, 112, 226], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([226, 230, 234], np.uint8)
        sponsors[full] = 0
        numbers[full] = 0
        if template_context:
            template[full] = 255
        return full

    positive_full = paint_dark_panel_stroke(860, 880)
    remote_full = paint_dark_panel_stroke(660, 880, sponsor_context=False)
    number_full = paint_dark_panel_stroke(760, 880, number_context=True)
    template_full = paint_dark_panel_stroke(560, 880, template_context=True)
    grayscale_full = paint_dark_panel_stroke(460, 880, grayscale=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_dark_blue_white_vertical_logo_stroke"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0
    assert (mask[grayscale_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_grayscale_micro_text_crumbs():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([16, 16, 18], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def sponsor_panel(y0, x0, h=46, w=72):
        panel = (slice(y0, y0 + h), slice(x0, x0 + w))
        sponsors[panel] = 255
        rgb[panel] = np.array([108, 108, 112], np.uint8)
        rgb[y0 + 4:y0 + 9, x0 + 8:x0 + w - 8] = np.array([232, 232, 232], np.uint8)
        rgb[y0 + h - 10:y0 + h - 5, x0 + 6:x0 + w - 6] = np.array([58, 58, 62], np.uint8)
        return panel

    def local_gray_context(y0, x0, h, w):
        sponsors[y0 - 8:y0 + h + 8, x0 - 8:x0 + w + 8] = 255
        rgb[y0 - 8:y0 - 2, x0 - 8:x0 + w + 8] = np.array([226, 226, 226], np.uint8)
        rgb[y0 - 2:y0 + h, x0 - 8:x0 + w + 8] = np.array([112, 112, 116], np.uint8)
        rgb[y0 + h:y0 + h + 8, x0 - 8:x0 + w + 8] = np.array([58, 58, 62], np.uint8)

    def carve_rect(y0, x0, h, w, *, sponsor=True, number=False, tmpl=False):
        if sponsor:
            sponsor_panel(y0 - 16, x0 - 18)
            local_gray_context(y0, x0, h, w)
        if number:
            numbers[y0 - 16:y0 + h + 16, x0 - 18:x0 + w + 18] = 255
        if tmpl:
            template[y0 - 16:y0 + h + 16, x0 - 18:x0 + w + 18] = 255
        full = np.zeros((n, n), bool)
        full[y0:y0 + h, x0:x0 + w] = True
        sponsors[full] = 0
        numbers[full] = 0
        rgb[full] = np.array([226, 226, 226], np.uint8)
        rgb[y0:y0 + h, x0:x0 + max(1, w // 2)] = np.array([42, 42, 44], np.uint8)
        return full

    solid_o = carve_rect(720, 770, 7, 4)

    sparse_vertical = np.zeros((n, n), bool)
    sponsor_panel(632, 742)
    local_gray_context(648, 768, 16, 7)
    sparse_vertical[648:664, 768] = True
    sparse_vertical[648, 769:775] = True
    sparse_vertical[663, 769] = True
    sponsors[sparse_vertical] = 0
    rgb[sparse_vertical] = np.array([236, 236, 236], np.uint8)
    rgb[656:662, 768] = np.array([48, 48, 50], np.uint8)
    rgb[663, 769] = np.array([48, 48, 50], np.uint8)

    square_logo = np.zeros((n, n), bool)
    sponsor_panel(544, 742)
    local_gray_context(560, 768, 7, 7)
    square_logo[560:567, 768:770] = True
    square_logo[560, 770:775] = True
    square_logo[566, 770:775] = True
    square_logo[563, 770:772] = True
    sponsors[square_logo] = 0
    rgb[square_logo] = np.array([224, 224, 224], np.uint8)
    rgb[560:567, 768:770] = np.array([54, 54, 56], np.uint8)

    hairline = np.zeros((n, n), bool)
    sponsor_panel(456, 742)
    local_gray_context(474, 764, 3, 20)
    hairline[474, 764:784] = True
    hairline[476, 766:768] = True
    sponsors[hairline] = 0
    rgb[hairline] = np.array([238, 238, 238], np.uint8)
    rgb[474, 774:784:2] = np.array([48, 48, 50], np.uint8)
    rgb[476, 766:768] = np.array([48, 48, 50], np.uint8)

    remote = carve_rect(420, 770, 7, 4, sponsor=False)
    number_context = carve_rect(360, 770, 7, 4, number=True)
    template_context = carve_rect(300, 770, 7, 4, tmpl=True)
    saturated_trim = carve_rect(240, 770, 7, 4)
    rgb[saturated_trim] = np.array([220, 28, 42], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_grayscale_micro_text_crumb"] == 2
    assert (mask[solid_o] > 0).mean() > 0.95
    assert (mask[square_logo] > 0).mean() > 0.95
    assert (mask[sparse_vertical] > 0).mean() == 0
    assert (mask[hairline] > 0).mean() == 0
    assert (mask[remote] > 0).mean() == 0
    assert (mask[number_context] > 0).mean() == 0
    assert (mask[template_context] > 0).mean() == 0
    assert (mask[saturated_trim] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_dark_grayscale_micro_logo_inside_number_dilation():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([18, 18, 20], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_dark_badge_context(y0, x0):
        sponsors[y0 - 2:y0 + 9, x0 - 9:x0 + 38] = 255
        sponsors[y0 + 15:y0 + 22, x0 - 20:x0 + 40] = 255
        sponsors[y0 - 4:y0 + 11, x0 + 18:x0 + 56] = 255
        rgb[y0 - 10:y0 + 25, x0 - 22:x0 + 58] = np.array([16, 16, 18], np.uint8)
        rgb[y0 - 2:y0 + 9, x0 - 9:x0 + 38] = np.array([54, 54, 58], np.uint8)
        rgb[y0 + 15:y0 + 22, x0 - 20:x0 + 40] = np.array([42, 42, 44], np.uint8)
        rgb[y0 - 4:y0 + 11, x0 + 18:x0 + 56] = np.array([64, 64, 68], np.uint8)
        rgb[y0 - 3:y0 + 10, x0 - 3:x0 + 10] = np.array([96, 96, 98], np.uint8)

    def micro_logo(y0, x0, *, sponsor_context=True, number_local=False, number_dilated=False,
                   template_context=False, weak_sponsor_bbox=False):
        if sponsor_context:
            paint_dark_badge_context(y0, x0)
        full_bbox = np.zeros((n, n), bool)
        full_bbox[y0:y0 + 7, x0:x0 + 7] = True
        sponsors[full_bbox] = 255 if not weak_sponsor_bbox else 0
        comp = np.zeros((n, n), bool)
        comp[y0:y0 + 7, x0:x0 + 2] = True
        comp[y0, x0 + 2:x0 + 7] = True
        comp[y0 + 6, x0 + 2:x0 + 7] = True
        comp[y0 + 3, x0 + 2:x0 + 4] = True
        sponsors[comp] = 0
        rgb[comp] = np.array([156, 156, 158], np.uint8)
        rgb[y0:y0 + 7, x0:x0 + 2] = np.array([48, 48, 50], np.uint8)
        rgb[full_bbox & ~comp] = np.array([18, 18, 20], np.uint8)
        if number_dilated:
            numbers[y0:y0 + 7, x0 + 30:x0 + 39] = 255
        if number_local:
            numbers[y0 - 3:y0 + 10, x0 - 3:x0 + 10] = 255
        if template_context:
            template[y0 - 3:y0 + 10, x0 - 3:x0 + 10] = 255
        return comp

    positive = micro_logo(720, 760, number_dilated=True)
    remote = micro_logo(650, 760, sponsor_context=False)
    local_number = micro_logo(580, 760, number_local=True)
    template_context = micro_logo(510, 760, template_context=True)
    weak_bbox = micro_logo(440, 760, weak_sponsor_bbox=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_dark_grayscale_micro_logo_crumb"] == 1
    assert (mask[positive] > 0).mean() > 0.95
    assert (mask[remote] > 0).mean() == 0
    assert (mask[local_number] > 0).mean() == 0
    assert (mask[template_context] > 0).mean() == 0
    assert (mask[weak_bbox] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_bright_sponsor_micro_text_dot():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([248, 248, 248], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(740, 790), slice(748, 820))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([238, 240, 242], np.uint8)
    rgb[750:766, 771:777] = np.array([34, 38, 42], np.uint8)
    rgb[766:773, 771:785] = np.array([118, 118, 118], np.uint8)

    dot_full = np.zeros((n, n), bool)
    dot_full[758:765, 779:784] = True
    sponsors[dot_full] = 0
    rgb[dot_full] = np.array([240, 242, 246], np.uint8)
    rgb[758:765, 779] = np.array([118, 118, 118], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[518:525, 779:784] = True
    rgb[remote_full] = np.array([240, 242, 246], np.uint8)

    number_panel = (slice(640, 690), slice(748, 820))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([238, 240, 242], np.uint8)
    rgb[650:666, 771:777] = np.array([34, 38, 42], np.uint8)
    rgb[666:673, 771:785] = np.array([118, 118, 118], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[658:665, 779:784] = True
    numbers[number_full] = 0
    rgb[number_full] = np.array([240, 242, 246], np.uint8)
    rgb[658:665, 779] = np.array([118, 118, 118], np.uint8)

    red_full = np.zeros((n, n), bool)
    red_full[768:775, 794:799] = True
    sponsors[red_full] = 0
    rgb[red_full] = np.array([224, 40, 32], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_bright_micro_text_dot"] == 1
    assert guard["component_count"] == 1
    assert (mask[dot_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_bright_red_white_micro_text_crumb():
    n = 1024
    rgb = np.full((n, n, 3), np.array([246, 246, 246], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_crumb(y0, x0):
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 9), slice(x0, x0 + 5)] = True
        rgb[full] = np.array([252, 236, 238], np.uint8)
        full_coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(full_coords):
            if idx % 5 == 0:
                rgb[yy0, xx0] = np.array([228, 34, 52], np.uint8)
            elif idx % 11 == 0:
                rgb[yy0, xx0] = np.array([242, 124, 136], np.uint8)
        return full

    def add_red_white_sponsor_context(y0, x0):
        band = (slice(y0 - 4, y0 + 13), slice(x0 - 76, x0 + 84))
        sponsors[band] = 255
        rgb[band] = np.array([248, 248, 248], np.uint8)
        rgb[slice(y0 - 2, y0 + 4), slice(x0 - 72, x0 - 2)] = np.array(
            [224, 20, 40], np.uint8
        )
        rgb[slice(y0 + 5, y0 + 12), slice(x0 + 7, x0 + 80)] = np.array(
            [224, 20, 40], np.uint8
        )

    add_red_white_sponsor_context(805, 137)
    positive_full = paint_crumb(805, 137)
    sponsors[positive_full] = 0

    remote_full = paint_crumb(805, 337)

    add_red_white_sponsor_context(905, 137)
    number_full = paint_crumb(905, 137)
    sponsors[number_full] = 0
    numbers[slice(897, 922), slice(128, 153)] = 255
    numbers[number_full] = 0

    add_red_white_sponsor_context(805, 537)
    protected_full = paint_crumb(805, 537)
    sponsors[protected_full] = 0
    template[protected_full] = 255

    livery_full = paint_crumb(905, 537)
    rgb[slice(898, 922), slice(520, 565)] = np.array([224, 20, 40], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_bright_red_white_micro_text_crumb"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[livery_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_tiny_red_sponsor_wordmark_dot():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([230, 230, 230], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    dot_shape = np.ones((5, 5), bool)
    dot_shape[0, 0] = False
    dot_shape[0, 4] = False
    dot_shape[4, 0] = False
    dot_shape[4, 4] = False

    def paint_dot(y0, x0):
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 5), slice(x0, x0 + 5)] = dot_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 7 in (0, 1, 2):
                rgb[yy0, xx0] = np.array([38, 4, 8], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([188, 14, 24], np.uint8)
        return full

    sponsor_panel = (slice(905, 950), slice(925, 1000))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([14, 14, 16], np.uint8)
    rgb[920:940, 928:948] = np.array([236, 236, 230], np.uint8)
    rgb[920:940, 972:990] = np.array([236, 236, 230], np.uint8)
    dot_full = paint_dot(925, 957)
    sponsors[dot_full] = 0

    remote_full = paint_dot(720, 957)

    number_panel = (slice(805, 850), slice(925, 1000))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([14, 14, 16], np.uint8)
    rgb[820:840, 928:956] = np.array([236, 236, 230], np.uint8)
    number_full = paint_dot(825, 957)
    numbers[number_full] = 0

    ornamental_full = np.zeros((n, n), bool)
    ornamental_full[912:970, 140:164:2] = True
    sponsors[900:980, 120:185] = 255
    sponsors[ornamental_full] = 0
    rgb[900:980, 120:185] = np.array([72, 64, 60], np.uint8)
    rgb[ornamental_full] = np.array([224, 224, 220], np.uint8)

    protected_full = paint_dot(925, 1010)
    sponsors[916:944, 1002:1023] = 255
    template[protected_full] = 255

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_tiny_red_wordmark_dot"] == 1
    assert guard["component_count"] == 1
    assert (mask[dot_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[ornamental_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_sidecar_red_logo_chip_inside_number_bleed():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([232, 232, 232], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    chip_shape = np.ones((6, 7), bool)
    chip_shape[0, 0] = False
    chip_shape[5, 6] = False

    def paint_chip(y0, x0):
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 6), slice(x0, x0 + 7)] = chip_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx < 26:
                rgb[yy0, xx0] = np.array([188, 14, 24], np.uint8)
            elif idx < 38:
                rgb[yy0, xx0] = np.array([30, 4, 8], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([214, 214, 208], np.uint8)
        return full

    def add_number_bleed_nameplate(y0, x0, *, with_sponsor=True):
        number_panel = (slice(y0 - 30, y0 + 76), slice(x0 - 62, x0 + 142))
        numbers[number_panel] = 255
        rgb[number_panel] = np.array([232, 232, 232], np.uint8)
        if with_sponsor:
            sponsor_panel = (slice(y0, y0 + 22), slice(x0 + 10, x0 + 96))
            sponsors[sponsor_panel] = 255
            numbers[sponsor_panel] = 0
            rgb[sponsor_panel] = np.array([28, 28, 30], np.uint8)
            rgb[slice(y0 + 4, y0 + 16), slice(x0 + 18, x0 + 88)] = np.array(
                [236, 236, 230], np.uint8
            )
            rgb[slice(y0 + 1, y0 + 8), slice(x0 + 7, x0 + 10)] = np.array(
                [178, 18, 26], np.uint8
            )

    add_number_bleed_nameplate(420, 407, with_sponsor=True)
    positive_full = paint_chip(420, 407)
    numbers[positive_full] = 0
    sponsors[positive_full] = 0

    remote_full = paint_chip(720, 407)

    add_number_bleed_nameplate(610, 407, with_sponsor=False)
    number_only_full = paint_chip(610, 407)
    numbers[number_only_full] = 0

    add_number_bleed_nameplate(420, 700, with_sponsor=True)
    template_full = paint_chip(420, 700)
    numbers[template_full] = 0
    sponsors[template_full] = 0
    template[template_full] = 255

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_sidecar_red_logo_chip"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_only_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_red_dark_separator_crumb():
    n = 1024
    rgb = np.full((n, n, 3), np.array([224, 224, 224], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    crumb_shape = np.zeros((5, 9), bool)
    crumb_shape[0, 1:5] = True
    crumb_shape[1, 0:8] = True
    crumb_shape[2, 4:6] = True
    crumb_shape[3, 2:6] = True
    crumb_shape[4, 6:8] = True

    def paint_separator(y0, x0, *, use_numbers=False, use_template=False, remote=False):
        panel = (slice(y0 - 18, y0 + 24), slice(x0 - 38, x0 + 50))
        if not remote:
            (numbers if use_numbers else sponsors)[panel] = 255
        rgb[panel] = np.array([12, 12, 14], np.uint8)
        rgb[y0 - 12:y0 + 14, x0 - 34:x0 - 1] = np.array([238, 238, 232], np.uint8)
        rgb[y0 - 12:y0 + 14, x0 + 8:x0 + 44] = np.array([238, 238, 232], np.uint8)
        rgb[y0 - 8:y0, x0 - 6:x0 + 16] = np.array([238, 238, 232], np.uint8)
        rgb[y0 + 6:y0 + 12, x0 - 16:x0 + 26] = np.array([210, 22, 28], np.uint8)
        rgb[y0 - 1:y0 + 6, x0 - 3:x0] = np.array([12, 12, 14], np.uint8)
        rgb[y0 - 1:y0 + 6, x0 + 8:x0 + 11] = np.array([12, 12, 14], np.uint8)

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 5), slice(x0, x0 + 9)] = crumb_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 2 == 0:
                rgb[yy0, xx0] = np.array([206, 18, 30], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([38, 3, 8], np.uint8)
        if not remote:
            (numbers if use_numbers else sponsors)[full] = 0
        if use_template:
            template[full] = 255
        return full

    def paint_dark_badge_separator(y0, x0, *, use_numbers=False, use_template=False, remote=False):
        panel = (slice(y0 - 18, y0 + 24), slice(x0 - 28, x0 + 44))
        if not remote:
            (numbers if use_numbers else sponsors)[panel] = 255
        rgb[panel] = np.array([11, 12, 14], np.uint8)
        rgb[y0 - 13:y0 - 4, x0 - 22:x0 + 34] = np.array([206, 18, 30], np.uint8)
        rgb[y0 + 7:y0 + 13, x0 - 18:x0 + 30] = np.array([236, 236, 230], np.uint8)

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 2), slice(x0, x0 + 12)] = True
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 12 < 7:
                rgb[yy0, xx0] = np.array([206, 18, 30], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([36, 3, 8], np.uint8)
        if not remote:
            (numbers if use_numbers else sponsors)[full] = 0
        if use_template:
            template[full] = 255
        return full

    positive_full = paint_separator(138, 160)
    dark_positive_full = paint_dark_badge_separator(238, 160)
    remote_full = paint_separator(338, 160, remote=True)
    dark_remote_full = paint_dark_badge_separator(438, 160, remote=True)
    number_full = paint_separator(538, 160, use_numbers=True)
    dark_number_full = paint_dark_badge_separator(638, 160, use_numbers=True)
    template_full = paint_separator(738, 160, use_template=True)
    dark_template_full = paint_dark_badge_separator(838, 160, use_template=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_red_dark_separator_crumb"] == 2
    assert guard["component_count"] == 2
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[dark_positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[dark_remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[dark_number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0
    assert (mask[dark_template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_red_dark_logo_interior_crumb():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 36, 38], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    crumb_shape = np.zeros((7, 14), bool)
    crumb_shape[0, 1:6] = True
    crumb_shape[1, 0:5] = True
    crumb_shape[2, 3:8] = True
    crumb_shape[3, 6:14] = True
    crumb_shape[4, 8:11] = True
    crumb_shape[5, 9:11] = True
    crumb_shape[6, 11:13] = True

    def paint_logo_interior(
        y0,
        x0,
        *,
        use_numbers=False,
        use_template=False,
        remote=False,
        unanchored=False,
    ):
        panel = (slice(y0 - 18, y0 + 26), slice(x0 - 40, x0 + 52))
        if not remote and not unanchored:
            (numbers if use_numbers else sponsors)[panel] = 255
        rgb[panel] = np.array([218, 24, 30], np.uint8)
        rgb[y0 - 7:y0 + 15, x0 - 8:x0 - 2] = np.array([238, 238, 232], np.uint8)
        rgb[y0 - 6:y0 + 14, x0 + 15:x0 + 25] = np.array([238, 238, 232], np.uint8)
        rgb[y0 - 10:y0 - 8, x0 - 18:x0 + 32] = np.array([32, 4, 8], np.uint8)
        rgb[y0 + 10:y0 + 12, x0 - 16:x0 + 30] = np.array([36, 5, 8], np.uint8)

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 7), slice(x0, x0 + 14)] = crumb_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 3 == 0:
                rgb[yy0, xx0] = np.array([42, 4, 8], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([206, 18, 28], np.uint8)
        if not remote and not unanchored:
            (numbers if use_numbers else sponsors)[full] = 0
        if use_template:
            template[full] = 255
        return full

    positive_full = paint_logo_interior(180, 170)
    remote_full = paint_logo_interior(300, 170, remote=True)
    number_full = paint_logo_interior(420, 170, use_numbers=True)
    template_full = paint_logo_interior(540, 170, use_template=True)
    unanchored_full = paint_logo_interior(660, 170, unanchored=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_red_dark_logo_interior_crumb"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0
    assert (mask[unanchored_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_grayscale_logo_interior_stroke():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 36, 38], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def paint_logo_stroke(
        y0,
        x0,
        *,
        use_numbers=False,
        use_template=False,
        unanchored=False,
    ):
        panel = (slice(y0 - 18, y0 + 24), slice(x0 - 36, x0 + 52))
        if not unanchored:
            (numbers if use_numbers else sponsors)[panel] = 255
        rgb[panel] = np.array([30, 30, 32], np.uint8)
        rgb[y0 - 6:y0 + 8, x0 - 6:x0 + 22] = np.array([236, 236, 232], np.uint8)

        full = np.zeros((n, n), bool)
        full[y0:y0 + 3, x0:x0 + 14] = True
        rgb[full] = np.array([40, 40, 42], np.uint8)
        rgb[y0:y0 + 3, x0:x0 + 2] = np.array([238, 238, 234], np.uint8)
        rgb[y0:y0 + 3, x0 + 4:x0 + 6] = np.array([238, 238, 234], np.uint8)
        rgb[y0:y0 + 3, x0 + 8:x0 + 9] = np.array([238, 238, 234], np.uint8)
        if not unanchored:
            (numbers if use_numbers else sponsors)[full] = 0
        if use_template:
            template[full] = 255
        return full

    positive_full = paint_logo_stroke(180, 170)
    unanchored_full = paint_logo_stroke(300, 170, unanchored=True)
    number_full = paint_logo_stroke(420, 170, use_numbers=True)
    template_full = paint_logo_stroke(540, 170, use_template=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_grayscale_logo_interior_stroke"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[unanchored_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_grayscale_logo_interior_fill():
    n = 1024
    rgb = np.full((n, n, 3), np.array([34, 36, 38], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    fill_shape = np.array([
        [False, True, True, False, False, False, False],
        [True, True, True, True, False, False, False],
        [False, True, False, True, True, True, True],
        [True, True, False, True, True, False, False],
        [False, True, True, False, False, True, False],
        [False, False, True, False, False, False, False],
        [False, True, True, True, True, False, False],
        [False, True, True, False, False, False, False],
        [False, False, True, False, False, False, False],
    ], dtype=bool)

    def paint_logo_fill(
        y0,
        x0,
        *,
        use_numbers=False,
        use_template=False,
        unanchored=False,
    ):
        panel = (slice(y0 - 24, y0 + 34), slice(x0 - 32, x0 + 44))
        if not unanchored:
            (numbers if use_numbers else sponsors)[panel] = 255
        rgb[panel] = np.array([228, 228, 224], np.uint8)
        rgb[y0 - 24:y0 + 34:4, x0 - 32:x0 + 44] = np.array([38, 38, 40], np.uint8)
        rgb[y0 - 24:y0 + 34, x0 - 32:x0 + 44:13] = np.array([42, 42, 44], np.uint8)

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 9), slice(x0, x0 + 7)] = fill_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 3 == 0:
                rgb[yy0, xx0] = np.array([238, 238, 234], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([42, 42, 44], np.uint8)

        bridge = np.zeros((n, n), bool)
        bridge[y0 + 9:y0 + 34, x0 + 2] = True
        rgb[bridge] = np.array([122, 122, 122], np.uint8)
        if not unanchored:
            (numbers if use_numbers else sponsors)[full | bridge] = 0
        if use_template:
            template[full] = 255
        return full, bridge

    positive_full, positive_bridge = paint_logo_fill(180, 170)
    unanchored_full, _ = paint_logo_fill(320, 170, unanchored=True)
    number_full, _ = paint_logo_fill(460, 170, use_numbers=True)
    template_full, _ = paint_logo_fill(600, 170, use_template=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_grayscale_logo_interior_fill"] == 1
    assert guard["component_count"] == 1
    assert guard["components"][0]["id"] < -2000
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[positive_bridge] > 0).mean() == 0
    assert (mask[unanchored_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_dark_grayscale_logo_interior_fill():
    n = 1024
    rgb = np.full((n, n, 3), np.array([24, 24, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    fill_shape = np.array([
        [False, True, True, False, False, False],
        [True, True, True, False, False, False],
        [False, True, False, True, True, False],
        [False, True, True, True, False, False],
        [True, True, False, True, True, False],
        [False, False, True, False, True, True],
        [False, True, True, True, False, True],
    ], dtype=bool)

    def paint_dark_logo_fill(
        y0,
        x0,
        *,
        number_context=False,
        template_context=False,
        bright_context=False,
    ):
        local = (slice(y0 - 8, y0 + 15), slice(x0 - 8, x0 + 14))
        panel = (slice(y0 - 22, y0 + 28), slice(x0 - 30, x0 + 40))
        sponsors[panel] = 255
        sponsors[local] = 255
        rgb[panel] = np.array([28, 28, 30], np.uint8)
        rgb[local] = np.array([54, 54, 56], np.uint8)
        rgb[y0 - 8:y0 + 15:3, x0 - 8:x0 + 14] = np.array([112, 112, 114], np.uint8)
        rgb[y0 - 6:y0 + 12, x0 - 4:x0 + 18:8] = np.array([218, 218, 214], np.uint8)
        if bright_context:
            rgb[local] = np.array([224, 224, 220], np.uint8)
        if number_context:
            numbers[panel] = 255
            numbers[y0 - 12:y0 + 18, x0 - 12:x0 + 18] = 255

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + fill_shape.shape[0]), slice(x0, x0 + fill_shape.shape[1])] = fill_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 2:
                rgb[yy0, xx0] = np.array([224, 224, 220], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([48, 48, 50], np.uint8)

        sponsors[full] = 0
        numbers[full] = 0
        if template_context:
            template[full] = 255
        return full

    positive_full = paint_dark_logo_fill(180, 170)
    number_full = paint_dark_logo_fill(320, 170, number_context=True)
    bright_full = paint_dark_logo_fill(460, 170, bright_context=True)
    template_full = paint_dark_logo_fill(600, 170, template_context=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_dark_grayscale_logo_interior_fill"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[bright_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_saturated_sponsor_logo_crumbs():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([26, 28, 30], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sparse_shape = np.zeros((12, 12), bool)
    sparse_shape[1, 1:7] = True
    sparse_shape[1:11, 6] = True
    sparse_shape[10, 6:11] = True

    red_shape = np.zeros((8, 6), bool)
    red_shape[:, 2] = True
    red_shape[0, :] = True
    red_shape[7, :] = True
    red_shape[3:5, 3:5] = True

    dash_shape = np.zeros((7, 13), bool)
    dash_shape[0, 0:8] = True
    dash_shape[1:7, 7] = True
    dash_shape[6, 7:13] = True
    dash_shape[3, 2:10] = True

    def paint_logo_crumb(
        y0,
        x0,
        shape,
        *,
        panel_color,
        crumb_color,
        remote=False,
        number_context=False,
        template_context=False,
    ):
        panel = (slice(y0 - 16, y0 + 28), slice(x0 - 20, x0 + 44))
        if not remote:
            sponsors[panel] = 255
        if number_context:
            numbers[panel] = 255
        rgb[panel] = np.array(panel_color, np.uint8)

        full = np.zeros((n, n), bool)
        h, w = shape.shape
        full[slice(y0, y0 + h), slice(x0, x0 + w)] = shape
        rgb[full] = np.array(crumb_color, np.uint8)
        if not remote:
            sponsors[full] = 0
        if number_context:
            numbers[full] = 0
        if template_context:
            template[full] = 255
        return full

    green_positive = paint_logo_crumb(
        120,
        130,
        sparse_shape,
        panel_color=[0, 96, 12],
        crumb_color=[214, 18, 192],
    )
    yellow_positive = paint_logo_crumb(
        220,
        130,
        red_shape,
        panel_color=[238, 220, 26],
        crumb_color=[216, 18, 28],
    )
    orange_positive = paint_logo_crumb(
        320,
        130,
        dash_shape,
        panel_color=[226, 96, 18],
        crumb_color=[224, 24, 56],
    )
    remote_full = paint_logo_crumb(
        500,
        130,
        sparse_shape,
        panel_color=[0, 96, 12],
        crumb_color=[214, 18, 192],
        remote=True,
    )
    number_full = paint_logo_crumb(
        620,
        130,
        red_shape,
        panel_color=[238, 220, 26],
        crumb_color=[216, 18, 28],
        number_context=True,
    )
    template_full = paint_logo_crumb(
        740,
        130,
        dash_shape,
        panel_color=[226, 96, 18],
        crumb_color=[224, 24, 56],
        template_context=True,
    )

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_saturated_logo_crumb"] == 3
    assert guard["component_count"] == 3
    assert (mask[green_positive] > 0).mean() > 0.95
    assert (mask[yellow_positive] > 0).mean() > 0.95
    assert (mask[orange_positive] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[template_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_tiny_green_wordmark_crumb():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([24, 26, 24], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    crumb_shape = np.zeros((7, 14), bool)
    crumb_shape[1, 1:9] = True
    crumb_shape[2:6, 7] = True
    crumb_shape[5, 7:13] = True
    crumb_shape[3, 3:8] = True
    route_dark_shape = np.zeros((7, 14), bool)
    route_dark_shape[0, 0] = True
    route_dark_shape[1, 1:10] = True
    route_dark_shape[2:5, 7] = True
    route_dark_shape[5, 7:13] = True
    route_dark_shape[6, 13] = True

    def paint_green_crumb(
        y0,
        x0,
        *,
        sponsor_context=False,
        number_context=False,
        protected=False,
        route_dark_antialias=False,
    ):
        panel = (slice(y0 - 13, y0 + 20), slice(x0 - 16, x0 + 36))
        rgb[panel] = np.array([26, 230, 72], np.uint8)
        rgb[y0 - 12:y0 + 19, x0 + 7:x0 + 35] = np.array([238, 238, 232], np.uint8)
        if route_dark_antialias:
            rgb[y0 - 8:y0 + 15, x0 - 10:x0 - 3] = np.array([3, 25, 5], np.uint8)
        else:
            rgb[y0 - 10:y0 + 17, x0 - 14:x0 - 2] = np.array([20, 110, 22], np.uint8)
        if sponsor_context:
            sponsors[panel] = 255
        if number_context:
            numbers[panel] = 255

        full = np.zeros((n, n), bool)
        shape = route_dark_shape if route_dark_antialias else crumb_shape
        full[slice(y0, y0 + 7), slice(x0, x0 + 14)] = shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if route_dark_antialias:
                if idx == 0:
                    rgb[yy0, xx0] = np.array([216, 204, 217], np.uint8)
                elif idx < 11:
                    rgb[yy0, xx0] = np.array([8, 116, 0], np.uint8)
                elif idx < 13:
                    rgb[yy0, xx0] = np.array([4, 70, 4], np.uint8)
                else:
                    rgb[yy0, xx0] = np.array([3, 25, 5], np.uint8)
            elif idx == 0:
                rgb[yy0, xx0] = np.array([216, 204, 217], np.uint8)
            elif idx % 7 == 0:
                rgb[yy0, xx0] = np.array([3, 25, 5], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([8, 116, 0], np.uint8)
        if sponsor_context:
            sponsors[full] = 0
        if number_context:
            numbers[full] = 0
        if protected:
            template[full] = 255
        return full

    positive_full = paint_green_crumb(300, 120, sponsor_context=True)
    route_dark_full = paint_green_crumb(
        300,
        520,
        sponsor_context=True,
        route_dark_antialias=True,
    )
    remote_full = paint_green_crumb(300, 320)
    number_full = paint_green_crumb(500, 120, sponsor_context=True, number_context=True)
    protected_full = paint_green_crumb(700, 120, sponsor_context=True, protected=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_tiny_green_wordmark_crumb"] == 2
    assert guard["component_count"] == 2
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[route_dark_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_green_logo_edge_shard():
    n = 1024
    rgb = np.full((n, n, 3), np.array([22, 24, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def shard_shape(h, w, wide=False):
        yy, xx = np.indices((h, w))
        if wide:
            diag = np.clip((yy * (w - 1)) // max(1, h - 1), 0, w - 1)
            return (
                (xx == diag)
                | ((xx == np.minimum(diag + 1, w - 1)) & ((yy % 3) == 0))
                | (((yy == 3) | (yy == h - 4)) & (xx >= 3) & (xx < w - 4))
            )
        diag = np.clip((yy * (w - 1)) // max(1, h - 1), 0, w - 1)
        return (
            (xx == diag)
            | ((xx == np.minimum(diag + 1, w - 1)) & ((yy % 2) == 0))
            | ((yy == h // 2) & (xx >= 1) & (xx < w - 1))
            | ((yy == 2) & (xx >= 3) & (xx < w - 2))
        )

    def paint_shard(y0, x0, h, w, *, sponsor_context=False, number_context=False, protected=False, wide=False):
        panel = (slice(y0 - 18, y0 + h + 20), slice(x0 - 24, x0 + w + 30))
        sponsor_panel = (slice(y0 - 24, y0 + h + 24), slice(x0 - 110, x0 + w + 110))
        rgb[panel] = np.array([238, 238, 232], np.uint8)
        rgb[y0 + h // 2:y0 + h + 18, x0 - 20:x0 + w + 24] = np.array([12, 18, 12], np.uint8)
        if sponsor_context:
            sponsors[sponsor_panel] = 255
        if number_context:
            numbers[sponsor_panel] = 255

        full = np.zeros((n, n), bool)
        shape = shard_shape(h, w, wide=wide)
        full[y0:y0 + h, x0:x0 + w] = shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 5 == 0:
                rgb[yy0, xx0] = np.array([24, 42, 22], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([42, 172, 54], np.uint8)
        if sponsor_context:
            sponsors[full] = 0
        if number_context:
            numbers[full] = 0
        if protected:
            template[full] = 255
        return full

    tall_positive = paint_shard(260, 120, 24, 11, sponsor_context=True)
    remote = paint_shard(520, 120, 24, 11)
    number_art = paint_shard(520, 340, 24, 11, sponsor_context=True, number_context=True)
    protected = paint_shard(700, 120, 24, 11, sponsor_context=True, protected=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_green_logo_edge_shard"] == 1
    assert (mask[tall_positive] > 0).mean() > 0.85
    assert (mask[remote] > 0).mean() == 0
    assert (mask[number_art] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_sparse_green_logo_edge_shard():
    n = 1024
    rgb = np.full((n, n, 3), np.array([22, 24, 22], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def sparse_shape(h=31, w=22):
        yy, xx = np.indices((h, w))
        diag = np.clip(((yy - 2) * (w - 1)) // max(1, h - 5), 0, w - 1)
        return (
            (xx == diag)
            | ((xx == np.minimum(diag + 1, w - 1)) & ((yy % 3) == 0))
            | ((yy == 4) & (xx >= 3) & (xx <= 14))
        )

    def paint_sparse(y0, x0, *, sponsor_context=False, number_context=False, template_context=False, cyan=False):
        h, w = 31, 22
        panel = (slice(y0 - 18, y0 + h + 20), slice(x0 - 24, x0 + w + 30))
        sponsor_panel = (slice(y0 - 18, y0 + h + 20), slice(x0 - 90, x0 + w + 90))
        rgb[panel] = np.array([232, 232, 226], np.uint8)
        rgb[y0 + 12:y0 + h + 12, x0 - 24:x0 + w + 28] = np.array([42, 42, 42], np.uint8)
        if sponsor_context:
            sponsors[sponsor_panel] = 255
        if number_context:
            numbers[sponsor_panel] = 255
        if template_context:
            template[sponsor_panel] = 255

        full = np.zeros((n, n), bool)
        shape = sparse_shape(h, w)
        full[y0:y0 + h, x0:x0 + w] = shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if cyan:
                rgb[yy0, xx0] = np.array([40, 190, 216], np.uint8)
            elif idx % 4 == 0:
                rgb[yy0, xx0] = np.array([38, 48, 34], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([34, 174, 52], np.uint8)
        sponsors[full] = 0
        numbers[full] = 0
        template[full] = 0
        return full

    positive = paint_sparse(300, 376, sponsor_context=True)
    cyan_template = paint_sparse(500, 376, sponsor_context=True, template_context=True, cyan=True)
    number_art = paint_sparse(700, 376, sponsor_context=True, number_context=True)
    remote = paint_sparse(300, 720)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_sparse_green_logo_edge_shard"] == 1
    assert (mask[positive] > 0).mean() > 0.85
    assert (mask[cyan_template] > 0).mean() == 0
    assert (mask[number_art] > 0).mean() == 0
    assert (mask[remote] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_mixed_contingency_strip_crumbs():
    n = 1024
    rgb = np.full((n, n, 3), np.array([22, 24, 26], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    white_shape = np.ones((3, 7), bool)
    blue_shape = np.ones((19, 24), bool)
    green_shape = np.ones((4, 9), bool)
    green_shape[0, 0] = False
    green_shape[3, 8] = False

    def paint_strip_crumb(
        y0,
        x0,
        shape,
        mode,
        *,
        sponsor_context=False,
        number_context=False,
        template_context=False,
    ):
        h, w = shape.shape
        panel = (slice(y0 - 14, y0 + h + 14), slice(x0 - 80, x0 + w + 80))
        rgb[panel] = np.array([236, 236, 230], np.uint8)
        rgb[y0 - 8:y0 + h + 8, x0 - 62:x0 - 10] = np.array([214, 18, 34], np.uint8)
        rgb[y0 - 8:y0 + h + 8, x0 + w + 10:x0 + w + 62] = np.array([26, 84, 218], np.uint8)
        if mode == "green":
            rgb[panel] = np.array([8, 10, 8], np.uint8)
            rgb[y0 - 7:y0 + h + 7, x0 - 62:x0 - 10] = np.array([18, 206, 46], np.uint8)
            rgb[y0 - 7:y0 + h + 7, x0 + w + 10:x0 + w + 62] = np.array([22, 188, 40], np.uint8)
        if sponsor_context:
            sponsors[panel] = 255
        if number_context:
            numbers[panel] = 255
        if template_context:
            template[panel] = 255

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + h), slice(x0, x0 + w)] = shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if mode == "white":
                rgb[yy0, xx0] = (
                    np.array([238, 238, 232], np.uint8)
                    if idx % 3 != 0
                    else np.array([18, 158, 216], np.uint8)
                )
            elif mode == "blue":
                rgb[yy0, xx0] = (
                    np.array([34, 102, 224], np.uint8)
                    if idx % 4 == 0
                    else np.array([240, 240, 234], np.uint8)
                    if idx % 4 in (1, 2)
                    else np.array([44, 44, 48], np.uint8)
                )
            else:
                rgb[yy0, xx0] = (
                    np.array([22, 206, 54], np.uint8)
                    if idx % 2 == 0
                    else np.array([2, 30, 4], np.uint8)
                )
        sponsors[full] = 0
        numbers[full] = 0
        template[full] = 0
        return full

    white_positive = paint_strip_crumb(220, 180, white_shape, "white", sponsor_context=True)
    blue_positive = paint_strip_crumb(360, 180, blue_shape, "blue", sponsor_context=True)
    green_positive = paint_strip_crumb(520, 180, green_shape, "green", sponsor_context=True)
    remote = paint_strip_crumb(220, 560, white_shape, "white")
    number_art = paint_strip_crumb(
        660,
        180,
        white_shape,
        "white",
        sponsor_context=True,
        number_context=True,
    )
    protected = paint_strip_crumb(
        800,
        180,
        green_shape,
        "green",
        sponsor_context=True,
        template_context=True,
    )

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_mixed_contingency_strip_crumb"] == 3
    assert guard["component_count"] == 3
    assert (mask[white_positive] > 0).mean() > 0.95
    assert (mask[blue_positive] > 0).mean() > 0.95
    assert (mask[green_positive] > 0).mean() > 0.95
    assert (mask[remote] > 0).mean() == 0
    assert (mask[number_art] > 0).mean() == 0
    assert (mask[protected] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_flat_red_white_contingency_strip_gap_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle527_dlm_next4_after_269333_scan_v1_nocache/"
        "car_num_270422/Dirt_Late_Model_car_num_270422"
    )
    negative = Path(
        "_smart_tga_runs/cycle527_dlm_next4_after_269333_scan_v1_nocache/"
        "car_num_272622/Dirt_Late_Model_car_num_272622"
    )
    required = []
    for folder in (sample, negative):
        required.extend([
            folder / "source_1024.png",
            folder / "masks" / "numbers.png",
            folder / "masks" / "sponsors.png",
            folder / "masks" / "template.png",
            folder / "masks" / "brand_graphics.png",
        ])
    if not all(path.exists() for path in required):
        pytest.skip("Cycle527 DLM diagnostic artifacts are not present")

    def load_inputs(folder: Path):
        rgb = np.array(Image.open(folder / "source_1024.png").convert("RGB"), dtype=np.uint8)
        masks = {
            name: np.array(Image.open(folder / "masks" / f"{name}.png").convert("L"), dtype=np.uint8)
            for name in ("numbers", "sponsors", "template", "brand_graphics")
        }
        return rgb, masks

    rgb, masks = load_inputs(sample)
    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb,
        masks["numbers"],
        masks["sponsors"],
        masks["template"],
        masks["brand_graphics"],
    )

    assert guard["status"] == "applied"
    components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_flat_red_white_contingency_strip_gap"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [328, 830, 21, 4]
    assert component["area"] == 55
    assert component["sponsor_overlap"] == 1.0
    assert component["number_overlap"] == 0.0
    assert component["bbox_template_fill"] == 0.0
    assert 0.40 <= component["red_frac"] <= 0.48
    assert 0.52 <= component["white_frac"] <= 0.62

    target = mask[830:834, 328:349] > 0
    assert int(target.sum()) == component["area"]

    neg_rgb, neg_masks = load_inputs(negative)
    neg_mask, _neg_guard = car_layers_mod._panel_text_residual_supplement(
        neg_rgb,
        neg_masks["numbers"],
        neg_masks["sponsors"],
        neg_masks["template"],
        neg_masks["brand_graphics"],
    )
    underline = neg_mask[754:756, 88:118] > 0
    assert int(underline.sum()) == 0


def test_smart_tga_panel_text_residual_recovers_dense_sponsor_context_micro_holes_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle528_dlm_278708_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_278708"
    )
    negative = Path(
        "_smart_tga_runs/cycle528_dlm_next4_after_272622_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_275289"
    )
    required = []
    for folder in (sample, negative):
        required.extend([
            folder / "source_1024.png",
            folder / "masks" / "numbers.png",
            folder / "masks" / "sponsors.png",
            folder / "masks" / "template.png",
            folder / "masks" / "brand_graphics.png",
        ])
    if not all(path.exists() for path in required):
        pytest.skip("Cycle528 DLM diagnostic artifacts are not present")

    def load_inputs(folder: Path):
        rgb = np.array(Image.open(folder / "source_1024.png").convert("RGB"), dtype=np.uint8)
        masks = {
            name: np.array(Image.open(folder / "masks" / f"{name}.png").convert("L"), dtype=np.uint8)
            for name in ("numbers", "sponsors", "template", "brand_graphics")
        }
        return rgb, masks

    rgb, masks = load_inputs(sample)
    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb,
        masks["numbers"],
        masks["sponsors"],
        masks["template"],
        masks["brand_graphics"],
    )

    assert guard["status"] == "applied"
    buckets = {component["bucket"]: component for component in guard["components"]}
    dark = buckets["sponsor_panel_dense_context_dark_text_stroke"]
    assert dark["bbox"] == [88, 51, 16, 7]
    assert dark["area"] == 23
    assert dark["sponsor_overlap"] == 1.0
    assert dark["number_overlap"] == 0.0
    assert dark["bbox_sponsor_fill"] >= 0.78
    assert dark["ring_sponsor"] >= 0.90

    saturated = buckets["sponsor_panel_dense_context_saturated_logo_hole"]
    assert saturated["bbox"] == [136, 558, 10, 10]
    assert saturated["area"] == 26
    assert saturated["sponsor_overlap"] == 1.0
    assert saturated["number_overlap"] == 0.0
    assert saturated["bbox_sponsor_fill"] >= 0.70
    assert saturated["ring_sponsor"] >= 0.88

    assert int((mask[51:58, 88:104] > 0).sum()) == dark["area"]
    assert int((mask[558:568, 136:146] > 0).sum()) == saturated["area"]

    neg_rgb, neg_masks = load_inputs(negative)
    neg_mask, _neg_guard = car_layers_mod._panel_text_residual_supplement(
        neg_rgb,
        neg_masks["numbers"],
        neg_masks["sponsors"],
        neg_masks["template"],
        neg_masks["brand_graphics"],
    )
    number_adjacent_mark = neg_mask[297:310, 507:515] > 0
    assert int(number_adjacent_mark.sum()) == 0


def test_smart_tga_panel_text_residual_recovers_red_logo_gaps_real_dlm_38631():
    sample = Path(
        "_smart_tga_runs/cycle564_dlm_38631_vertical_red_edge_target_v1_nocache/"
        "Dirt_Late_Model_car_num_38631"
    )
    paint_path = Path(
        r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing"
        r"\SPB Smart TGA Examples\Dirt Late Model\car_num_38631.tga"
    )
    required = [
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not paint_path.exists() or not all(path.exists() for path in required):
        pytest.skip("Cycle564 DLM 38631 diagnostic artifacts are not present")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    rgb_float, _alpha, _meta = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(rgb_float[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(required[0]).convert("L"))
    sponsors = np.array(Image.open(required[1]).convert("L"))
    template = np.array(Image.open(required[2]).convert("L"))
    brand = np.array(Image.open(required[3]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    by_bucket = {}
    for component in guard.get("components", []):
        by_bucket.setdefault(component["bucket"], []).append(component)

    assert guard["status"] == "applied"
    assert int((sponsors[761:776, 82:98] > 0).sum()) >= 26
    assert {
        tuple(component["bbox"])
        for component in by_bucket["sponsor_panel_vertical_red_edge_logo_stroke"]
    } == {(1015, 275, 1, 26)}
    assert int((mask[275:301, 1015:1016] > 0).sum()) == 26

    red_white_gap_bboxes = {
        tuple(component["bbox"])
        for component in by_bucket["sponsor_panel_local_red_white_wordmark_gap"]
    }
    assert red_white_gap_bboxes == {(50, 250, 7, 7), (107, 807, 6, 6)}
    assert int((mask[250:257, 50:57] > 0).sum()) == 43
    assert int((mask[807:813, 107:113] > 0).sum()) == 34

    # Nearby vertical red number-halo/livery fragments remain Paint.
    assert int((mask[555:588, 713:730] > 0).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_vertical_grayscale_wordmark_stroke_real_dlm():
    positive = Path(
        "_smart_tga_runs/cycle562_dlm_wrap8_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_33863"
    )
    positive_paint = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/"
        "SPB Smart TGA Examples/Dirt Late Model/car_num_33863.tga"
    )
    required = [
        positive / "masks" / "numbers.png",
        positive / "masks" / "sponsors.png",
        positive / "masks" / "template.png",
        positive / "masks" / "brand_graphics.png",
        positive_paint,
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle562 DLM 33863 route artifacts are not present")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    rgb_float, _alpha, _meta = load_paint_rgb_float01(str(positive_paint), target_size=1024)
    rgb = np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(positive / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(positive / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(positive / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(positive / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )
    stroke_components = [
        component
        for component in guard.get("components", [])
        if component["bucket"] == "sponsor_panel_vertical_grayscale_wordmark_stroke"
    ]

    assert guard["status"] == "applied"
    assert {tuple(component["bbox"]) for component in stroke_components} == {
        (67, 708, 3, 10)
    }
    assert int((mask[708:718, 67:70] > 0).sum()) == 21

    # Red livery/number-edge slivers and template-dominant white panels are
    # intentionally outside this sponsor-letter recovery family.
    hard_negatives = [
        (
            Path(
                "_smart_tga_runs/cycle562_dlm_wrap8_current_scan_v1_nocache/"
                "Dirt_Late_Model_car_num_15129"
            ),
            Path(
                "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/"
                "SPB Smart TGA Examples/Dirt Late Model/car_num_15129.tga"
            ),
            (99, 640, 3, 17),
        ),
        (
            Path(
                "_smart_tga_runs/cycle562_dlm_wrap8_current_scan_v1_nocache/"
                "Dirt_Late_Model_car_num_42206"
            ),
            Path(
                "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/"
                "SPB Smart TGA Examples/Dirt Late Model/car_num_42206.tga"
            ),
            (933, 660, 15, 16),
        ),
    ]
    for sample, paint_path, (x, y, w, h) in hard_negatives:
        negative_required = [
            sample / "masks" / "numbers.png",
            sample / "masks" / "sponsors.png",
            sample / "masks" / "template.png",
            sample / "masks" / "brand_graphics.png",
            paint_path,
        ]
        if not all(path.exists() for path in negative_required):
            pytest.skip(f"{sample.name} route artifacts are not present")
        negative_rgb_float, _negative_alpha, _negative_meta = load_paint_rgb_float01(
            str(paint_path), target_size=1024
        )
        negative_mask, _negative_guard = car_layers_mod._panel_text_residual_supplement(
            np.clip(negative_rgb_float * 255.0, 0, 255).astype(np.uint8),
            np.array(Image.open(sample / "masks" / "numbers.png").convert("L")),
            np.array(Image.open(sample / "masks" / "sponsors.png").convert("L")),
            np.array(Image.open(sample / "masks" / "template.png").convert("L")),
            np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L")),
        )
        assert int((negative_mask[y:y + h, x:x + w] > 0).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_dlm_blue_white_logo_tail():
    sample = Path(
        "_smart_tga_runs/cycle496_dlm_batch_multicolor_livery_stripe_v1_nocache/"
        "Dirt_Late_Model_car_num_1205342"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle496 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    tail_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_blue_white_logo_tail"
    ]
    embedded_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "number_panel_embedded_contingency_strip_crumb"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_blue_white_logo_tail"] == 1
    assert guard["bucket_counts"]["number_panel_embedded_contingency_strip_crumb"] == 1
    assert {tuple(component["bbox"]) for component in tail_components} == {(540, 921, 24, 19)}
    assert {tuple(component["bbox"]) for component in embedded_components} == {(17, 822, 22, 5)}
    assert (mask[921:940, 540:564] > 0).sum() >= 40
    assert (mask[822:827, 17:39] > 0).sum() >= 100

    real_paint = Path(
        r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\SPB Smart TGA Examples\Dirt Late Model\car_num_1205342.tga"
    )
    if real_paint.exists():
        from engine.spec_sculpt.core import load_paint_rgb_float01

        tex, _, _ = load_paint_rgb_float01(str(real_paint), target_size=1024)
        loaded_rgb = np.clip(
            np.asarray(tex[:, :, :3]) * (255.0 if np.asarray(tex).max() <= 1.5 else 1.0),
            0,
            255,
        ).astype(np.uint8)
        loaded_mask, loaded_guard = car_layers_mod._panel_text_residual_supplement(
            loaded_rgb, numbers, sponsors, template, brand
        )
        assert loaded_guard["status"] == "applied"
        assert loaded_guard["bucket_counts"]["sponsor_panel_blue_white_logo_tail"] == 1
        assert loaded_guard["bucket_counts"]["number_panel_embedded_contingency_strip_crumb"] == 1
        assert (loaded_mask[921:940, 540:564] > 0).sum() >= 40
        assert (loaded_mask[822:827, 17:39] > 0).sum() >= 100

    top_sample = Path(
        "_smart_tga_runs/cycle496_dlm_batch_multicolor_livery_stripe_v1_nocache/"
        "Dirt_Late_Model_car_num_1171722"
    )
    if (top_sample / "source_1024.png").exists():
        top_rgb = np.array(Image.open(top_sample / "source_1024.png").convert("RGB"))
        top_numbers = np.array(Image.open(top_sample / "masks" / "numbers.png").convert("L"))
        top_sponsors = np.array(Image.open(top_sample / "masks" / "sponsors.png").convert("L"))
        top_template = np.array(Image.open(top_sample / "masks" / "template.png").convert("L"))
        top_brand = np.array(Image.open(top_sample / "masks" / "brand_graphics.png").convert("L"))

        top_mask, top_guard = car_layers_mod._panel_text_residual_supplement(
            top_rgb, top_numbers, top_sponsors, top_template, top_brand
        )

        assert top_guard["bucket_counts"]["sponsor_panel_blue_white_logo_tail"] == 0
        assert all(
            component["bucket"] != "sponsor_panel_blue_white_logo_tail"
            for component in top_guard["components"]
        )


def test_smart_tga_panel_text_residual_recovers_local_blue_wordmark_edges_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle516_dlm_batch_lime_number_sibling_chunk_v1_nocache/"
        "Dirt_Late_Model_car_num_1250841"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle516 DLM 1250841 partial-sponsor fixture not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    blue_wordmark_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_local_blue_wordmark_edge"
    ]
    grayscale_wordmark_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_local_grayscale_wordmark_edge"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_local_blue_wordmark_edge"] == 5
    assert guard["bucket_counts"]["sponsor_panel_local_grayscale_wordmark_edge"] == 1
    assert {tuple(component["bbox"]) for component in blue_wordmark_components} == {
        (20, 829, 17, 2),
        (41, 830, 17, 2),
        (48, 779, 24, 2),
        (61, 831, 38, 3),
        (101, 833, 13, 2),
    }
    assert {tuple(component["bbox"]) for component in grayscale_wordmark_components} == {
        (46, 811, 56, 21),
    }
    assert (mask[815:834, 49:113] > 0).sum() >= 220
    assert (mask[811:835, 46:115] > 0).sum() >= 240
    assert (mask[828:832, 64:89] > 0).sum() >= 48
    assert (mask[865:920, 0:180] > 0).sum() == 0
    assert (mask[650:820, 270:520] > 0).sum() == 0


def test_smart_tga_panel_text_residual_recovers_green_wordmark_chunk_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle524_dlm_23371_current_residual_probe_v1_nocache/"
        "Dirt_Late_Model_car_num_23371"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle524 DLM 23371 green wordmark chunk fixture not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )
    green_wordmark_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_green_wordmark_chunk"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_green_wordmark_chunk"] == 1
    assert {tuple(component["bbox"]) for component in green_wordmark_components} == {
        (185, 715, 35, 31),
    }
    assert (mask[715:746, 185:220] > 0).sum() >= 300
    assert (mask[516:577, 92:143] > 0).sum() == 0


def test_smart_tga_panel_text_residual_recovers_vertical_blue_logo_stroke_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle525_dlm_next4_partial_sponsor_scan_v1_nocache/"
        "car_num_263952/Dirt_Late_Model_car_num_263952"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle 525 real DLM 263952 fixture not generated")

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )
    blue_stroke_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_vertical_blue_logo_stroke"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_vertical_blue_logo_stroke"] == 1
    assert {tuple(component["bbox"]) for component in blue_stroke_components} == {
        (164, 801, 8, 16),
    }
    assert (mask[801:817, 164:172] > 0).sum() >= 20
    assert (mask[96:101, 344:441] > 0).sum() == 0
    assert (mask[322:325, 925:956] > 0).sum() == 0


def test_smart_tga_panel_text_residual_recovers_vertical_blue_logo_stroke_route_resize_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle525_dlm_263952_vertical_blue_logo_stroke_target_v2_nocache/"
        "Dirt_Late_Model_car_num_263952"
    )
    paint = Path(
        r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing"
        r"\SPB Smart TGA Examples\Dirt Late Model\car_num_263952.tga"
    )
    required = [
        paint,
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle 525 route-resize DLM 263952 fixture not generated")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(paint), target_size=1024)
    rgb = np.clip(tex[:, :, :3] * (255.0 if (tex.size and tex.max() <= 1.5) else 1.0), 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )
    blue_stroke_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_vertical_blue_logo_stroke"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_vertical_blue_logo_stroke"] == 1
    assert {tuple(component["bbox"]) for component in blue_stroke_components} == {
        (164, 801, 8, 16),
    }
    assert (mask[801:817, 164:172] > 0).sum() >= 20
    assert (mask[96:101, 344:441] > 0).sum() == 0
    assert (mask[322:325, 925:956] > 0).sum() == 0


def test_smart_tga_panel_text_residual_recovers_number_dilated_dark_text_crumbs_real_dlm():
    sample = Path(
        "_smart_tga_runs/cycle518_dlm_batch_next8_partial_flipped_baseline_v1_nocache/"
        "Dirt_Late_Model_car_num_1328773"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle518 DLM 1328773 number-dilated sponsor text fixture not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    recovered = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_number_dilated_dark_text_crumb"
    ]
    same_wordmark_completion = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_dilated_wordmark_completion_crumb"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_number_dilated_dark_text_crumb"] == 2
    assert guard["bucket_counts"]["sponsor_panel_dilated_wordmark_completion_crumb"] == 2
    assert {tuple(component["bbox"]) for component in recovered} == {
        (453, 253, 47, 19),
        (470, 268, 30, 10),
    }
    assert {tuple(component["bbox"]) for component in same_wordmark_completion} == {
        (447, 255, 18, 14),
        (632, 251, 18, 5),
    }
    assert (mask[253:272, 453:500] > 0).sum() >= 320
    assert (mask[255:269, 447:465] > 0).sum() >= 35
    assert (mask[268:278, 470:500] > 0).sum() >= 120
    assert (mask[251:256, 632:650] > 0).sum() >= 20
    assert (mask[130:154, 595:616] > 0).sum() == 0


def test_smart_tga_bright_red_dlm_livery_panels_fall_back_to_paint_real_artifact():
    sample = Path(
        "_smart_tga_runs/cycle518_dlm_batch_next8_partial_flipped_baseline_v1_nocache/"
        "Dirt_Late_Model_car_num_1308069"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle518 DLM 1308069 bright red livery panel fixture not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )

    components = info["components"]
    reasons_by_bbox = {tuple(component["bbox"]): component["reason"] for component in components}

    assert info["status"] == "applied"
    assert reasons_by_bbox[(39, 16, 64, 42)] == "upper_left_solid_red_dlm_livery_panel"
    assert reasons_by_bbox[(991, 745, 30, 248)] == "right_edge_bright_red_dlm_livery_strip"
    assert (mask[16:58, 39:103] > 0).mean() > 0.75
    assert (mask[745:993, 991:1021] > 0).mean() > 0.90
    assert (mask[28:183, 861:1024] > 0).sum() == 0
    assert (mask[463:526, 781:807] > 0).sum() == 0
    assert (mask[721:812, 296:438] > 0).sum() == 0


def test_smart_tga_red_white_dlm_body_slabs_fall_back_to_paint_real_artifacts():
    samples = {
        "right_edge": Path(
            "_smart_tga_runs/cycle521_dlm_next8_after_wordmark_completion_baseline_v1_nocache/"
            "Dirt_Late_Model_car_num_1317463"
        ),
        "right_body": Path(
            "_smart_tga_runs/cycle521_dlm_next8_after_wordmark_completion_baseline_v1_nocache/"
            "Dirt_Late_Model_car_num_1320723"
        ),
        "bright_right_edge": Path(
            "_smart_tga_runs/cycle522_dlm_next8_after_1341065_baseline_v1_nocache/"
            "Dirt_Late_Model_car_num_15129"
        ),
    }
    required = [
        sample / item
        for sample in samples.values()
        for item in (
            Path("source_1024.png"),
            Path("masks/sponsors.png"),
            Path("masks/numbers.png"),
            Path("masks/template.png"),
            Path("masks/brand_graphics.png"),
        )
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle521/Cycle522 DLM red/white body slab fixtures not present")

    def run(sample: Path) -> tuple[np.ndarray, dict]:
        rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

        def load_mask(name: str) -> np.ndarray:
            return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

        return car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
            rgb,
            load_mask("sponsors"),
            load_mask("numbers"),
            load_mask("template"),
            load_mask("brand_graphics"),
        )

    right_edge_mask, right_edge_info = run(samples["right_edge"])
    right_body_mask, right_body_info = run(samples["right_body"])
    bright_edge_mask, bright_edge_info = run(samples["bright_right_edge"])
    edge_reasons = {
        tuple(component["bbox"]): component["reason"]
        for component in right_edge_info["components"]
    }
    body_reasons = {
        tuple(component["bbox"]): component["reason"]
        for component in right_body_info["components"]
    }
    bright_edge_reasons = {
        tuple(component["bbox"]): component["reason"]
        for component in bright_edge_info["components"]
    }

    assert right_edge_info["status"] == "applied"
    assert right_body_info["status"] == "applied"
    assert bright_edge_info["status"] == "applied"
    assert edge_reasons[(998, 116, 26, 589)] == "right_edge_tall_red_white_context_dlm_livery_strip"
    assert body_reasons[(948, 407, 50, 69)] == "right_body_solid_red_white_context_dlm_livery_panel"
    assert bright_edge_reasons[(998, 115, 26, 590)] == "right_edge_tall_red_white_context_dlm_livery_strip"
    assert bright_edge_reasons[(953, 356, 44, 52)] == "right_side_compact_orange_white_dlm_livery_patch"
    assert (right_edge_mask[116:705, 998:1024] > 0).mean() > 0.75
    assert (right_body_mask[407:476, 948:998] > 0).mean() > 0.90
    assert (bright_edge_mask[115:705, 998:1024] > 0).mean() > 0.75
    assert (bright_edge_mask[356:408, 953:997] > 0).mean() > 0.45
    assert (right_edge_mask[618:649, 774:789] > 0).sum() == 0


def test_smart_tga_upper_side_hot_pink_dlm_livery_band_demotes_without_sponsor_panel_real_1006305():
    sample = Path(
        "_smart_tga_runs/cycle588_dlm_first4_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1006305"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle588 DLM 1006305 hot-pink livery-band fixture not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
    }

    assert info["status"] == "applied"
    assert components[(290, 115, 332, 58)]["reason"] == "upper_side_hot_pink_dlm_livery_band"
    assert (mask[115:173, 290:622] > 0).mean() > 0.55
    assert (mask[296:356, 16:195] > 0).sum() == 0


def test_smart_tga_upper_left_orange_black_dlm_livery_panel_splits_from_real_artifact():
    sample = Path(
        "_smart_tga_runs/cycle566_dlm_38631_red_white_dark_wide3_target_v1_nocache/"
        "Dirt_Late_Model_car_num_38631"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle566 DLM 38631 upper-left orange/black panel fixture not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
    }

    assert info["status"] == "applied"
    component = components[(2, 144, 262, 159)]
    assert component["reason"] == "upper_left_orange_black_dlm_livery_panel_partial"
    assert 0.52 <= component["partial_demote_frac"] <= 0.60
    assert component["preserved_dark_frac"] >= 0.82
    assert components[(801, 340, 75, 115)]["reason"] == "right_mid_curved_red_white_dlm_livery_swoosh"
    assert (mask[144:303, 2:264] > 0).sum() >= 10000
    assert (mask[117:705, 927:1000] > 0).sum() == 0
    assert (mask[117:705, 1000:1024] > 0).sum() >= 9900
    assert (mask[340:455, 801:876] > 0).sum() >= 2400
    assert (mask[235:255, 59:109] > 0).sum() == 0


def test_smart_tga_right_edge_contingency_column_preserves_sponsors_while_demoting_livery_strip():
    sample = Path(
        "_smart_tga_runs/cycle569_dlm_38631_dense_number_shell_chip_target_v3_nocache/"
        "Dirt_Late_Model_car_num_38631"
    )
    required = [
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle569 DLM 38631 right-edge contingency-column fixture not present")

    paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/"
        "car_num_38631.tga"
    )
    if not paint_path.exists():
        pytest.skip("DLM 38631 source TGA fixture is not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(tex * 255.0, 0, 255).astype(np.uint8)

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
    }

    assert info["status"] == "applied"
    component = components[(927, 117, 97, 588)]
    assert component["reason"] == "right_edge_embedded_contingency_red_dlm_livery_strip_partial"
    assert 0.72 <= component["partial_demote_frac"] <= 0.80
    assert component["preserved_area"] >= 2800
    assert component["preserved_dark_frac"] >= 0.50
    assert (mask[117:705, 1000:1024] > 0).sum() >= 9900
    assert (mask[117:705, 927:1000] > 0).sum() == 0
    assert (mask[235:255, 59:109] > 0).sum() == 0
    assert (mask[324:336, 188:263] > 0).sum() == 0


def test_smart_tga_left_mid_pale_orange_dlm_livery_slab_demotes_without_sponsor_text():
    sample = Path(
        "_smart_tga_runs/cycle570_dlm_38631_embedded_contingency_edge_strip_target_v1_nocache/"
        "Dirt_Late_Model_car_num_38631"
    )
    required = [
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle570 DLM 38631 left-mid livery-slab fixture not present")

    paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/"
        "car_num_38631.tga"
    )
    if not paint_path.exists():
        pytest.skip("DLM 38631 source TGA fixture is not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(tex * 255.0, 0, 255).astype(np.uint8)

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
    }

    assert info["status"] == "applied"
    assert components[(47, 265, 31, 94)]["reason"] == "left_mid_pale_orange_dlm_livery_slab"
    assert (mask[265:359, 47:78] > 0).sum() >= 1700
    assert (mask[235:255, 59:109] > 0).sum() == 0
    assert (mask[324:336, 188:263] > 0).sum() == 0
    assert (mask[246:255, 68:73] > 0).sum() == 0
    assert (mask[250:257, 50:57] > 0).sum() == 0
    assert (mask[556:587, 713:714] > 0).sum() == 0


def test_smart_tga_upper_side_cream_dlm_livery_panel_demotes_without_wordmarks():
    sample = Path(
        "_smart_tga_runs/cycle572_dlm_lowend4_post571_control_v1_nocache/"
        "Dirt_Late_Model_car_num_50232"
    )
    control = Path(
        "_smart_tga_runs/cycle572_dlm_lowend4_post571_control_v1_nocache/"
        "Dirt_Late_Model_car_num_15129"
    )
    required = [
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        control / "masks" / "sponsors.png",
        control / "masks" / "numbers.png",
        control / "masks" / "template.png",
        control / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle572 DLM 50232/15129 cream-panel fixtures not present")

    paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/"
        "car_num_50232.tga"
    )
    control_paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/"
        "car_num_15129.tga"
    )
    if not paint_path.exists() or not control_paint_path.exists():
        pytest.skip("DLM 50232/15129 source TGA fixtures are not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    def route_rgb(path: Path) -> np.ndarray:
        tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(path), target_size=1024)
        return np.clip(tex * 255.0, 0, 255).astype(np.uint8)

    def load_mask(root: Path, name: str) -> np.ndarray:
        return np.array(Image.open(root / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        route_rgb(paint_path),
        load_mask(sample, "sponsors"),
        load_mask(sample, "numbers"),
        load_mask(sample, "template"),
        load_mask(sample, "brand_graphics"),
    )
    components = {
        tuple(component["bbox"]): component
        for component in info["components"]
    }

    assert info["status"] == "applied"
    assert components[(280, 128, 339, 93)]["reason"] == "upper_side_smooth_cream_dlm_livery_panel"
    assert (mask[128:221, 280:619] > 0).sum() >= 25000
    assert (mask[780:790, 516:578] > 0).sum() == 0
    assert (mask[719:815, 309:446] > 0).sum() == 0

    control_mask, control_info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        route_rgb(control_paint_path),
        load_mask(control, "sponsors"),
        load_mask(control, "numbers"),
        load_mask(control, "template"),
        load_mask(control, "brand_graphics"),
    )
    control_components = {
        tuple(component["bbox"]): component
        for component in control_info["components"]
    }
    assert (
        control_components[(12, 393, 222, 310)]["reason"]
        == "left_side_mixed_logo_peach_dlm_livery_fill_partial"
    )
    assert 0.42 <= control_components[(12, 393, 222, 310)]["partial_demote_frac"] <= 0.48
    assert control_components[(12, 393, 222, 310)]["preserved_white_frac"] >= 0.24
    assert control_components[(12, 393, 222, 310)]["preserved_dark_frac"] >= 0.28
    assert (control_mask[393:703, 12:234] > 0).sum() >= 22000
    assert (control_mask[958:1003, 249:596] > 0).sum() == 0
    assert (control_mask[268:316, 67:182] > 0).sum() == 0


def test_smart_tga_high_saturation_right_edge_red_dlm_livery_strip_falls_back_to_paint_real_310184():
    sample = Path(
        "_smart_tga_runs/cycle536_dlm_next4_after_308339_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_310184"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle536 DLM 310184 right-edge red livery fixture not present")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))

    def load_mask(name: str) -> np.ndarray:
        return np.array(Image.open(sample / "masks" / f"{name}.png").convert("L"))

    mask, info = car_layers_mod._smooth_red_body_panel_sponsor_to_paint(
        rgb,
        load_mask("sponsors"),
        load_mask("numbers"),
        load_mask("template"),
        load_mask("brand_graphics"),
    )
    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in info["components"]
    }

    assert info["status"] == "applied"
    assert (
        reasons_by_bbox[(995, 115, 29, 590)]
        == "right_edge_high_saturation_red_dlm_livery_strip"
    )
    assert (mask[115:705, 995:1024] > 0).mean() > 0.70
    assert (mask[592:642, 35:250] > 0).sum() == 0
    assert (mask[714:772, 22:176] > 0).sum() == 0


def test_smart_tga_panel_text_residual_recovers_top_edge_contingency_crumbs():
    sample = Path(
        "_smart_tga_runs/cycle497_dlm_batch_blue_white_logo_tail_v1_nocache/"
        "Dirt_Late_Model_car_num_1171722"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle497 DLM 1171722 top-edge contingency fixture not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"))
    numbers = np.array(Image.open(required[1]).convert("L"))
    sponsors = np.array(Image.open(required[2]).convert("L"))
    template = np.array(Image.open(required[3]).convert("L"))
    brand = np.array(Image.open(required[4]).convert("L"))

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    top_components = [
        component
        for component in guard["components"]
        if component["bucket"] == "number_panel_top_edge_contingency_crumb"
    ]

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["number_panel_top_edge_contingency_crumb"] == 3
    assert {tuple(component["bbox"]) for component in top_components} == {
        (36, 64, 7, 7),
        (60, 65, 24, 5),
        (104, 66, 7, 6),
    }
    assert (mask[64:71, 36:43] > 0).sum() >= 40
    assert (mask[65:70, 60:84] > 0).sum() >= 110
    assert (mask[66:72, 104:111] > 0).sum() >= 38
    assert (mask[33:116, 319:476] > 0).sum() == 0

    paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/car_num_1171722.tga"
    )
    if not paint_path.exists():
        pytest.skip("DLM 1171722 source paint is not present for production-loader RGB coverage")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(paint_path), target_size=1024)
    prod_rgb = (np.clip(tex[:, :, :3], 0.0, 1.0) * 255.0).astype(np.uint8)
    prod_mask, prod_guard = car_layers_mod._panel_text_residual_supplement(
        prod_rgb, numbers, sponsors, template, brand
    )

    prod_components = [
        component
        for component in prod_guard["components"]
        if component["bucket"] == "number_panel_top_edge_contingency_crumb"
    ]
    assert prod_guard["bucket_counts"]["number_panel_top_edge_contingency_crumb"] == 3
    assert {tuple(component["bbox"]) for component in prod_components} == {
        (36, 64, 7, 7),
        (60, 65, 24, 5),
        (104, 66, 7, 6),
    }
    assert (prod_mask[64:71, 36:43] > 0).sum() >= 40
    assert (prod_mask[65:70, 60:84] > 0).sum() >= 110
    assert (prod_mask[66:72, 104:111] > 0).sum() >= 38
    assert (prod_mask[33:116, 319:476] > 0).sum() == 0


def test_smart_tga_panel_text_residual_recovers_warm_long_hairline_logo():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([22, 24, 26], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    hairline_shape = np.zeros((3, 67), bool)
    hairline_shape[0, :] = True
    hairline_shape[1, 0:17] = True
    hairline_shape[2, 0:16] = True

    def paint_hairline(
        y0,
        x0,
        *,
        sponsor_context=False,
        number_context=False,
        protected=False,
        pale=False,
    ):
        panel = (slice(y0 - 10, y0 + 13), slice(x0 - 12, x0 + 90))
        rgb[panel] = np.array([24, 24, 26], np.uint8)
        rgb[y0 - 8:y0 + 11, x0 - 10:x0 + 28] = np.array([210, 24, 50], np.uint8)
        rgb[y0 - 8:y0 + 11, x0 + 28:x0 + 88] = np.array([16, 16, 18], np.uint8)
        if sponsor_context:
            sponsors[panel] = 255
        if number_context:
            numbers[panel] = 255

        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 3), slice(x0, x0 + 67)] = hairline_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if pale:
                rgb[yy0, xx0] = np.array([218, 218, 210], np.uint8)
            elif idx < 92 and idx % 2 == 0:
                rgb[yy0, xx0] = np.array([24, 20, 22], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([230, 18, 42], np.uint8)
        if sponsor_context:
            sponsors[full] = 0
        if number_context:
            numbers[full] = 0
        if protected:
            template[full] = 255
        return full

    positive_full = paint_hairline(120, 120, sponsor_context=True)
    remote_full = paint_hairline(220, 120)
    number_full = paint_hairline(320, 120, sponsor_context=True, number_context=True)
    protected_full = paint_hairline(420, 120, sponsor_context=True, protected=True)
    pale_full = paint_hairline(520, 120, sponsor_context=True, pale=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_warm_long_hairline_logo"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0
    assert (mask[pale_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_warm_dark_wordmark_strip_real_dlm_326360():
    sample = Path(
        "_smart_tga_runs/cycle538_dlm_next4_rotated_badge_control_v1_nocache/"
        "Dirt_Late_Model_car_num_326360"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        sample / "masks" / "paint.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle538 DLM 326360 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    paint = np.array(Image.open(required[5]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_warm_dark_wordmark_strip_gap"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [806, 949, 142, 10]
    assert component["sponsor_overlap"] == 1.0
    assert component["number_overlap"] < 0.75
    assert component["bbox_sponsor_fill"] >= 0.30
    assert component["bbox_number_fill"] == 0.0
    assert component["bbox_template_fill"] == 0.0
    assert component["ring_number"] == 0.0
    assert component["ring_template"] == 0.0
    assert component["ring_sponsor"] >= 0.30

    wordmark_strip = paint[949:959, 806:948] > 0
    recovered_strip = mask[949:959, 806:948] > 0
    assert (
        float((recovered_strip & wordmark_strip).sum())
        / float(max(1, wordmark_strip.sum()))
        > 0.95
    )

    lower_blue_plate = paint[998:1024, 702:758] > 0
    recovered_lower_blue = mask[998:1024, 702:758] > 0
    assert int((recovered_lower_blue & lower_blue_plate).sum()) == 0

    left_blue_plate = paint[976:1002, 646:680] > 0
    recovered_left_blue = mask[976:1002, 646:680] > 0
    assert int((recovered_left_blue & left_blue_plate).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_vertical_neutral_text_strokes_real_dlm_336528():
    sample = Path(
        "_smart_tga_runs/cycle539_dlm_next4_warm_dark_wordmark_strip_control_v1_nocache/"
        "Dirt_Late_Model_car_num_336528"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        sample / "masks" / "paint.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle539 DLM 336528 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    paint = np.array(Image.open(required[5]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_vertical_neutral_text_stroke"
    ]
    assert len(components) == 2
    boxes = {tuple(component["bbox"]) for component in components}
    assert boxes == {(591, 823, 1, 37), (161, 799, 1, 27)}
    for component in components:
        assert component["sponsor_overlap"] == 1.0
        assert component["bbox_number_fill"] == 0.0
        assert component["bbox_template_fill"] == 0.0
        assert component["ring_sponsor"] >= 0.74
        assert component["side_band_sponsor"] >= 0.90
        assert component["near_number"] == 0.0

    right_stroke = paint[823:860, 591:592] > 0
    left_stroke = paint[799:826, 161:162] > 0
    assert (mask[823:860, 591:592] > 0).mean() > 0.95
    assert (mask[799:826, 161:162] > 0).mean() > 0.95
    assert int(((mask[823:860, 591:592] > 0) & right_stroke).sum()) == int(right_stroke.sum())
    assert int(((mask[799:826, 161:162] > 0) & left_stroke).sum()) == int(left_stroke.sum())

    true_number = numbers[720:803, 285:461] > 0
    recovered_number = mask[720:803, 285:461] > 0
    assert int((recovered_number & true_number).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_sparse_neutral_outline_crumb_real_dlm_326360():
    sample = Path(
        "_smart_tga_runs/cycle540_dlm_next4_vertical_neutral_strokes_control_v1_nocache/"
        "Dirt_Late_Model_car_num_326360"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        sample / "masks" / "paint.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle540 DLM 326360 route artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)
    paint = np.array(Image.open(required[5]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    components = [
        component
        for component in guard["components"]
        if component["bucket"] == "sponsor_panel_sparse_neutral_outline_crumb"
    ]
    assert len(components) == 1
    component = components[0]
    assert component["bbox"] == [261, 728, 18, 7]
    assert component["sponsor_overlap"] == 1.0
    assert component["number_overlap"] == 0.0
    assert component["bbox_sponsor_fill"] >= 0.80
    assert component["bbox_number_fill"] == 0.0
    assert component["bbox_template_fill"] == 0.0
    assert component["ring_sponsor"] >= 0.94
    assert component["ring_template"] == 0.0
    assert component["near_number"] == 0.0
    assert component["near_template"] == 0.0

    outline_crumb = paint[728:735, 261:279] > 0
    recovered_crumb = mask[728:735, 261:279] > 0
    assert int((recovered_crumb & outline_crumb).sum()) == int(outline_crumb.sum())

    lower_blue_plate = paint[998:1024, 702:758] > 0
    recovered_lower_blue = mask[998:1024, 702:758] > 0
    assert int((recovered_lower_blue & lower_blue_plate).sum()) == 0

    left_blue_plate = paint[976:1002, 646:680] > 0
    recovered_left_blue = mask[976:1002, 646:680] > 0
    assert int((recovered_left_blue & left_blue_plate).sum()) == 0

    true_number = numbers[730:830, 260:410] > 0
    recovered_number = mask[730:830, 260:410] > 0
    assert int((recovered_number & true_number).sum()) == 0


def test_smart_tga_panel_text_residual_recovers_warm_mixed_logo_crumbs_inside_number_bleed():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([36, 38, 42], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    dense_shape = np.ones((10, 10), bool)
    dense_shape[0:3, 0:5] = False
    dense_shape[7:10, 5:10] = False

    dot_shape = np.ones((7, 6), bool)

    dash_shape = np.zeros((5, 16), bool)
    dash_shape[1:3, :] = True
    dash_shape[0, 0:8] = True
    dash_shape[4, 3:11] = True
    dash_shape[0:5, 5] = True

    def paint_logo_crumb(y0, x0, shape, route_dark_antialias=False):
        full = np.zeros((n, n), bool)
        h, w = shape.shape
        full[slice(y0, y0 + h), slice(x0, x0 + w)] = shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if route_dark_antialias and idx % 8 == 0:
                rgb[yy0, xx0] = np.array([42, 34, 30], np.uint8)
            elif idx % 5 in (0, 1):
                rgb[yy0, xx0] = np.array([220, 34, 28], np.uint8)
            elif idx % 5 == 2:
                rgb[yy0, xx0] = np.array([226, 186, 22], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([246, 246, 238], np.uint8)
        return full

    bleed_panel = (slice(112, 176), slice(96, 250))
    numbers[bleed_panel] = 255
    rgb[bleed_panel] = np.array([248, 248, 242], np.uint8)
    sponsors[134:168, 112:224] = 255
    rgb[134:168, 112:224] = np.array([226, 190, 24], np.uint8)
    rgb[145:158, 118:218] = np.array([232, 38, 28], np.uint8)
    positive_dense = paint_logo_crumb(120, 122, dense_shape)
    positive_dot = paint_logo_crumb(124, 148, dot_shape, route_dark_antialias=True)
    positive_dash = paint_logo_crumb(124, 172, dash_shape)
    numbers[positive_dense | positive_dot | positive_dash] = 0
    sponsors[positive_dense | positive_dot | positive_dash] = 0

    remote_full = paint_logo_crumb(500, 122, dense_shape)

    number_panel = (slice(292, 356), slice(96, 250))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([248, 248, 242], np.uint8)
    rgb[316:348, 112:224] = np.array([226, 190, 24], np.uint8)
    number_only = paint_logo_crumb(324, 122, dense_shape)
    numbers[number_only] = 0

    sponsor_panel = (slice(412, 476), slice(96, 250))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([248, 248, 242], np.uint8)
    rgb[436:468, 112:224] = np.array([226, 190, 24], np.uint8)
    sponsor_only = paint_logo_crumb(444, 122, dense_shape)
    sponsors[sponsor_only] = 0

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_warm_mixed_logo_crumb"] == 3
    assert guard["component_count"] == 3
    assert (mask[positive_dense] > 0).mean() > 0.95
    assert (mask[positive_dot] > 0).mean() > 0.95
    assert (mask[positive_dash] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_only] > 0).mean() == 0
    assert (mask[sponsor_only] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_red_sponsor_logo_cap():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([24, 24, 24], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    cap_shape = np.ones((23, 25), bool)
    cap_shape[5:18, 7:19] = False

    def paint_cap(y0, x0, mode="red"):
        full = np.zeros((n, n), bool)
        h, w = cap_shape.shape
        full[slice(y0, y0 + h), slice(x0, x0 + w)] = cap_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if mode == "bright":
                rgb[yy0, xx0] = np.array([222, 42, 26], np.uint8)
            elif yy0 < y0 + 3 and xx0 >= x0 + 18:
                rgb[yy0, xx0] = np.array([238, 238, 230], np.uint8)
            elif yy0 >= y0 + 19 and xx0 < x0 + 6:
                rgb[yy0, xx0] = np.array([42, 38, 34], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([222, 42, 26], np.uint8)
        return full

    def add_sponsor_stack(y0, x0, bright=False):
        panel = (slice(y0 - 18, y0 + 52), slice(x0 - 18, x0 + 58))
        sponsors[panel] = 255
        rgb[panel] = np.array([232, 232, 226] if bright else [26, 24, 22], np.uint8)
        if not bright:
            rgb[y0 - 8:y0 + 30, x0 - 7:x0 - 3] = np.array([190, 28, 22], np.uint8)
            rgb[y0 + 28:y0 + 42, x0 + 4:x0 + 48] = np.array([38, 104, 212], np.uint8)
        rgb[y0 + 38:y0 + 46, x0 + 6:x0 + 52] = np.array([235, 235, 230], np.uint8)

    add_sponsor_stack(500, 80)
    sponsors[500:523, 80:105] = 255
    positive_full = paint_cap(500, 80)
    sponsors[positive_full] = 0

    remote_full = paint_cap(500, 280)

    number_panel = (slice(650, 720), slice(62, 138))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([26, 24, 22], np.uint8)
    number_full = paint_cap(672, 80)
    numbers[number_full] = 0

    add_sponsor_stack(800, 80, bright=True)
    sponsors[800:823, 80:105] = 255
    bright_full = paint_cap(800, 80, mode="bright")
    sponsors[bright_full] = 0

    add_sponsor_stack(900, 80)
    protected_full = paint_cap(900, 80)
    template[protected_full] = 255

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_red_logo_cap"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[bright_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_green_wordmark_edge():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([24, 28, 24], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    edge_shape = np.zeros((45, 16), bool)
    edge_shape[:, 0:10] = True
    edge_shape[8:21, 10:16] = True

    def paint_green_edge(y0, x0, sponsor_context=False, number_context=False, protected=False):
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 45), slice(x0, x0 + 16)] = edge_shape
        local = (slice(y0 - 10, y0 + 55), slice(x0 - 14, x0 + 40))
        rgb[local] = np.array([34, 40, 34], np.uint8)
        rgb[y0 - 8:y0 + 53, x0 - 10:x0 + 4] = np.array([28, 218, 78], np.uint8)
        rgb[y0 + 4:y0 + 38, x0 + 17:x0 + 36] = np.array([24, 226, 72], np.uint8)
        rgb[full] = np.array([22, 230, 78], np.uint8)
        if sponsor_context:
            sponsors[local] = 255
            sponsors[full] = 0
        if number_context:
            numbers[local] = 255
            numbers[full] = 0
        if protected:
            template[full] = 255
        return full

    positive_full = paint_green_edge(300, 120, sponsor_context=True)
    remote_full = paint_green_edge(300, 320)
    number_full = paint_green_edge(500, 120, sponsor_context=True, number_context=True)
    protected_full = paint_green_edge(700, 120, sponsor_context=True, protected=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_green_wordmark_edge"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[protected_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_neutral_sponsor_logo_crumb():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([238, 238, 238], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    crumb_shape = np.zeros((19, 18), bool)
    crumb_shape[:, 0:2] = True
    crumb_shape[8:10, 2:18] = True

    def paint_crumb(y0, x0, color_mode="neutral"):
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 19), slice(x0, x0 + 18)] = crumb_shape
        if color_mode == "red":
            rgb[full] = np.array([174, 8, 24], np.uint8)
            return full
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if idx % 5 in (0, 1):
                rgb[yy0, xx0] = np.array([212, 212, 208], np.uint8)
            elif idx % 5 in (2, 3):
                rgb[yy0, xx0] = np.array([40, 40, 42], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([112, 112, 112], np.uint8)
        return full

    sponsor_panel = (slice(300, 372), slice(80, 170))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([40, 42, 44], np.uint8)
    rgb[314:322, 108:142] = np.array([205, 205, 200], np.uint8)
    rgb[322:342, 108:116] = np.array([205, 205, 200], np.uint8)
    positive_full = paint_crumb(322, 116)
    sponsors[positive_full] = 0

    remote_full = paint_crumb(500, 116)

    number_panel = (slice(620, 692), slice(80, 170))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([40, 42, 44], np.uint8)
    rgb[634:642, 108:142] = np.array([205, 205, 200], np.uint8)
    rgb[642:662, 108:116] = np.array([205, 205, 200], np.uint8)
    number_full = paint_crumb(642, 116)
    numbers[number_full] = 0

    red_panel = (slice(760, 832), slice(80, 170))
    sponsors[red_panel] = 255
    rgb[red_panel] = np.array([40, 42, 44], np.uint8)
    rgb[774:782, 108:142] = np.array([205, 205, 200], np.uint8)
    rgb[782:802, 108:116] = np.array([205, 205, 200], np.uint8)
    red_full = paint_crumb(782, 116, color_mode="red")
    sponsors[red_full] = 0

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_neutral_logo_crumb"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_mixed_sponsor_hairline_text():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([238, 238, 238], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    stroke_shape = np.zeros((4, 17), bool)
    stroke_shape[2, :] = True
    stroke_shape[0:2, 4] = True
    stroke_shape[3, 12] = True

    def paint_mixed_stroke(y0, x0, color_mode="mixed"):
        full = np.zeros((n, n), bool)
        full[slice(y0, y0 + 4), slice(x0, x0 + 17)] = stroke_shape
        coords = np.argwhere(full)
        for idx, (yy0, xx0) in enumerate(coords):
            if color_mode == "red":
                rgb[yy0, xx0] = np.array([178, 8, 26], np.uint8)
            elif idx % 4 == 0:
                rgb[yy0, xx0] = np.array([178, 8, 26], np.uint8)
            elif idx % 4 in (1, 2):
                rgb[yy0, xx0] = np.array([226, 226, 222], np.uint8)
            else:
                rgb[yy0, xx0] = np.array([34, 30, 32], np.uint8)
        return full

    sponsor_panel = (slice(940, 984), slice(600, 676))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([226, 226, 222], np.uint8)
    rgb[954:974, 621:630] = np.array([34, 30, 32], np.uint8)
    rgb[954:974, 646:652] = np.array([178, 8, 26], np.uint8)
    positive_full = paint_mixed_stroke(962, 629)
    sponsors[positive_full] = 0

    remote_full = paint_mixed_stroke(500, 629)

    number_panel = (slice(820, 864), slice(600, 676))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([226, 226, 222], np.uint8)
    rgb[834:854, 621:630] = np.array([34, 30, 32], np.uint8)
    rgb[834:854, 646:652] = np.array([178, 8, 26], np.uint8)
    number_full = paint_mixed_stroke(842, 629)
    numbers[number_full] = 0

    red_panel = (slice(720, 764), slice(600, 676))
    sponsors[red_panel] = 255
    rgb[red_panel] = np.array([226, 226, 222], np.uint8)
    rgb[734:754, 621:630] = np.array([34, 30, 32], np.uint8)
    rgb[734:754, 646:652] = np.array([178, 8, 26], np.uint8)
    red_full = paint_mixed_stroke(742, 629, color_mode="red")
    sponsors[red_full] = 0

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_mixed_hairline_text"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_large_white_sponsor_wordmark():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([18, 18, 20], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    word_shape = np.zeros((19, 134), bool)
    word_shape[2:17, :] = True
    word_shape[5:8, 24:34] = False
    word_shape[10:13, 61:73] = False
    word_shape[4:15, 103:109] = False
    word_shape[2:17, 0:5] = True
    word_shape[2:17, 129:134] = True
    word_shape[0:3, 0:5] = True
    word_shape[16:19, 129:134] = True

    sponsor_panel = (slice(520, 584), slice(320, 520))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([238, 214, 18], np.uint8)
    rgb[520:584, 320:342] = np.array([208, 0, 188], np.uint8)
    rgb[558:584, 320:520] = np.array([220, 196, 22], np.uint8)

    word_slice = (slice(543, 562), slice(354, 488))
    word_full = np.zeros((n, n), bool)
    word_full[word_slice] = word_shape
    sponsors[word_full] = 0
    rgb[word_full] = np.array([246, 246, 242], np.uint8)
    stripe = np.zeros_like(word_shape)
    stripe[:, 10::7] = word_shape[:, 10::7]
    stripe_full = np.zeros((n, n), bool)
    stripe_full[word_slice] = stripe
    rgb[stripe_full] = np.array([238, 118, 242], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[slice(210, 229), slice(354, 488)] = word_shape
    rgb[remote_full] = np.array([246, 246, 242], np.uint8)

    dark_panel = (slice(700, 764), slice(320, 520))
    sponsors[dark_panel] = 255
    rgb[dark_panel] = np.array([24, 24, 26], np.uint8)
    dark_full = np.zeros((n, n), bool)
    dark_full[slice(723, 742), slice(354, 488)] = word_shape
    sponsors[dark_full] = 0
    rgb[dark_full] = np.array([246, 246, 242], np.uint8)

    number_panel = (slice(820, 884), slice(320, 520))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([238, 214, 18], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(843, 862), slice(354, 488)] = word_shape
    numbers[number_full] = 0
    rgb[number_full] = np.array([246, 246, 242], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_large_white_wordmark"] == 1
    assert guard["component_count"] == 1
    assert (mask[word_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[dark_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_border_grayscale_sponsor_wordmark():
    n = 1024
    rgb = np.full((n, n, 3), np.array([18, 18, 20], np.uint8), np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.full((n, n), 255, np.uint8)
    brand = np.zeros((n, n), np.uint8)

    yy, xx = np.indices((26, 56))
    word_shape = np.ones((26, 56), bool)
    word_shape[2:6, 8:14] = False
    word_shape[9:13, 23:29] = False
    word_shape[16:20, 39:45] = False
    word_shape[4:8, 49:53] = False
    word_shape[20:22, 4:12] = False
    dark_strokes = word_shape & (
        (xx < 18) | ((xx >= 36) & (xx < 42)) | ((yy >= 10) & (yy < 14) & (xx < 50))
    )

    def paint_wordmark(x0, sponsor_anchor=True, number_anchor=False):
        y0 = n - 26
        full = np.zeros((n, n), bool)
        full[y0:n, x0:x0 + 56] = word_shape
        dark_full = np.zeros((n, n), bool)
        dark_full[y0:n, x0:x0 + 56] = dark_strokes
        template[full] = 0
        rgb[full] = np.array([232, 232, 232], np.uint8)
        rgb[dark_full] = np.array([32, 32, 34], np.uint8)
        if sponsor_anchor:
            sponsors[950:980, max(0, x0 - 30):min(n, x0 + 86)] = 255
            rgb[950:980, max(0, x0 - 30):min(n, x0 + 86)] = np.array([28, 28, 30], np.uint8)
        if number_anchor:
            numbers[950:980, max(0, x0 - 30):min(n, x0 + 86)] = 255
            rgb[950:980, max(0, x0 - 30):min(n, x0 + 86)] = np.array([236, 236, 232], np.uint8)
        return full

    positive_full = paint_wordmark(704, sponsor_anchor=True)
    remote_full = paint_wordmark(96, sponsor_anchor=False)
    number_full = paint_wordmark(356, sponsor_anchor=True, number_anchor=True)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_border_grayscale_wordmark"] == 1
    assert guard["component_count"] == 1
    assert (mask[positive_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0


def test_smart_tga_panel_text_residual_recovers_dark_sponsor_logo_fill():
    n = 1024
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([248, 248, 248], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    sponsor_panel = (slice(900, 952), slice(250, 314))
    sponsors[sponsor_panel] = 255
    rgb[sponsor_panel] = np.array([16, 14, 16], np.uint8)
    rgb[915:939, 262:296] = np.array([230, 202, 32], np.uint8)
    rgb[918:936, 266:292] = np.array([20, 16, 18], np.uint8)
    rgb[923:939, 262:266] = np.array([230, 202, 32], np.uint8)
    rgb[923:939, 286:290] = np.array([230, 202, 32], np.uint8)

    yy, xx = np.indices((12, 12))
    fill_shape = ((xx - 5.5) ** 2 + (yy - 5.5) ** 2) <= 42
    fill_shape[0, 2:10] = True
    fill_shape[11, 2:10] = True
    fill_slice = (slice(927, 939), slice(270, 282))
    fill_full = np.zeros((n, n), bool)
    fill_full[fill_slice] = fill_shape
    sponsors[fill_full] = 0
    rgb[fill_full] = np.array([44, 12, 54], np.uint8)
    accent = np.zeros((12, 12), bool)
    accent[2:5, 4:8] = fill_shape[2:5, 4:8]
    accent[7:9, 5:9] = fill_shape[7:9, 5:9]
    accent_full = np.zeros((n, n), bool)
    accent_full[fill_slice] = accent
    rgb[accent_full] = np.array([94, 0, 152], np.uint8)

    remote_full = np.zeros((n, n), bool)
    remote_full[slice(500, 512), slice(270, 282)] = fill_shape
    rgb[remote_full] = np.array([44, 12, 54], np.uint8)

    number_panel = (slice(700, 752), slice(250, 314))
    numbers[number_panel] = 255
    rgb[number_panel] = np.array([16, 14, 16], np.uint8)
    rgb[715:739, 262:296] = np.array([230, 202, 32], np.uint8)
    number_full = np.zeros((n, n), bool)
    number_full[slice(727, 739), slice(270, 282)] = fill_shape
    numbers[number_full] = 0
    rgb[number_full] = np.array([44, 12, 54], np.uint8)

    red_full = np.zeros((n, n), bool)
    red_full[slice(927, 939), slice(292, 304)] = fill_shape
    sponsors[red_full] = 0
    rgb[red_full] = np.array([160, 0, 20], np.uint8)

    no_yellow_panel = (slice(580, 632), slice(250, 314))
    sponsors[no_yellow_panel] = 255
    rgb[no_yellow_panel] = np.array([18, 20, 24], np.uint8)
    no_yellow_full = np.zeros((n, n), bool)
    no_yellow_full[slice(607, 619), slice(270, 282)] = fill_shape
    sponsors[no_yellow_full] = 0
    rgb[no_yellow_full] = np.array([44, 12, 54], np.uint8)

    mask, guard = car_layers_mod._panel_text_residual_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["bucket_counts"]["sponsor_panel_dark_logo_fill"] == 1
    assert guard["component_count"] == 1
    assert (mask[fill_full] > 0).mean() > 0.95
    assert (mask[remote_full] > 0).mean() == 0
    assert (mask[number_full] > 0).mean() == 0
    assert (mask[red_full] > 0).mean() == 0
    assert (mask[no_yellow_full] > 0).mean() == 0


def test_smart_tga_stacked_front_clip_parts_move_from_sponsors_to_template(monkeypatch):
    n = 768
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.025, 0.027, 0.030], np.float32)
    sponsors = np.zeros((n, n), np.uint8)
    front_parts = []

    def draw_part(y0, x0, h, w, base, accent):
        part = np.ones((h, w), bool)
        for yy in range(6, h - 6, 9):
            part[yy:yy + 2, 4:w - 4] = False
        sub_sp = sponsors[y0:y0 + h, x0:x0 + w]
        sub_sp[part] = 255
        sub_tex = tex[y0:y0 + h, x0:x0 + w]
        sub_tex[part] = base
        yy, xx = np.indices((h, w))
        highlight = part & ((((yy * 2) + xx) % 10) < 3)
        shadow = part & ((((yy * 3) + (xx * 2)) % 13) == 0)
        sub_tex[highlight] = accent
        sub_tex[shadow] = np.maximum(base * 0.58, 0.02)
        front_parts.append((slice(y0, y0 + h), slice(x0, x0 + w), part.copy()))

    draw_part(120, 630, 60, 20, np.array([0.38, 0.39, 0.38], np.float32), np.array([0.64, 0.65, 0.63], np.float32))
    draw_part(258, 632, 76, 16, np.array([0.23, 0.24, 0.25], np.float32), np.array([0.47, 0.48, 0.49], np.float32))
    draw_part(394, 630, 60, 20, np.array([0.38, 0.39, 0.38], np.float32), np.array([0.64, 0.65, 0.63], np.float32))

    wordmark = (slice(170, 320), slice(562, 600))
    sponsors[wordmark] = 255
    tex[wordmark] = np.array([0.92, 0.92, 0.90], np.float32)
    tex[176:314:10, 568:594] = np.array([0.08, 0.08, 0.08], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    out_template = res["layers"]["template"]
    out_sponsors = res["layers"]["sponsors"]
    for ys, xs, part in front_parts:
        assert (out_template[ys, xs][part] > 0).mean() > 0.95
        assert (out_sponsors[ys, xs][part] > 0).mean() < 0.05
    assert (out_sponsors[wordmark] > 0).mean() > 0.95
    assert (out_template[wordmark] > 0).mean() < 0.05
    assert res["stacked_front_clip_template_guard"]["status"] == "applied"
    assert res["stacked_front_clip_template_guard"]["component_count"] == 3


def test_smart_tga_horizontal_front_clip_group_moves_from_sponsors_to_template(monkeypatch):
    n = 512
    tex = np.zeros((n, n, 3), np.float32)
    tex[:, :] = np.array([0.024, 0.026, 0.030], np.float32)
    sponsors = np.zeros((n, n), np.uint8)
    front_parts = []

    def draw_front_part(y0, x0, h, w):
        part = np.ones((h, w), bool)
        for yy in range(5, h - 4, 8):
            part[yy:yy + 2, 3:w - 3] = False
        sub_sp = sponsors[y0:y0 + h, x0:x0 + w]
        sub_sp[part] = 255
        sub_tex = tex[y0:y0 + h, x0:x0 + w]
        sub_tex[part] = np.array([0.22, 0.23, 0.23], np.float32)
        yy, xx = np.indices((h, w))
        highlight = part & ((((yy * 2) + xx) % 11) < 3)
        shadow = part & ((((yy * 3) + (xx * 2)) % 17) == 0)
        sub_tex[highlight] = np.array([0.46, 0.47, 0.46], np.float32)
        sub_tex[shadow] = np.array([0.08, 0.085, 0.09], np.float32)
        front_parts.append((slice(y0, y0 + h), slice(x0, x0 + w), part.copy()))

    draw_front_part(16, 24, 30, 28)
    draw_front_part(50, 78, 15, 96)
    draw_front_part(16, 228, 30, 28)

    top_color_sponsor = (slice(18, 48), slice(386, 448))
    sponsors[top_color_sponsor] = 255
    tex[top_color_sponsor] = np.array([0.90, 0.12, 0.08], np.float32)
    tex[22:45:7, 392:442] = np.array([0.98, 0.82, 0.18], np.float32)

    lower_gray_sponsor = (slice(148, 178), slice(44, 112))
    sponsors[lower_gray_sponsor] = 255
    tex[lower_gray_sponsor] = np.array([0.34, 0.35, 0.35], np.float32)
    tex[152:174:7, 50:106] = np.array([0.64, 0.65, 0.64], np.float32)

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": np.zeros((n, n), np.uint8),
            "sponsors": sponsors.copy(),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, auto_id=False, use_template=False, use_ocr=True, brand_graphics_merge="sponsors"
    )

    out_template = res["layers"]["template"]
    out_sponsors = res["layers"]["sponsors"]
    for ys, xs, part in front_parts:
        assert (out_template[ys, xs][part] > 0).mean() > 0.95
        assert (out_sponsors[ys, xs][part] > 0).mean() < 0.05
    assert (out_sponsors[top_color_sponsor] > 0).mean() > 0.95
    assert (out_template[top_color_sponsor] > 0).mean() < 0.05
    assert (out_sponsors[lower_gray_sponsor] > 0).mean() > 0.95
    assert (out_template[lower_gray_sponsor] > 0).mean() < 0.05
    assert res["horizontal_front_clip_template_guard"]["status"] == "applied"
    assert res["horizontal_front_clip_template_guard"]["component_count"] == 3


def test_smart_tga_paired_rear_lamps_move_from_sponsors_to_template():
    n = 768
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([8, 8, 10], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)
    lamps = []

    def draw_lamp(y0, x0, h, w, gray_lens=False):
        lamp = np.ones((h, w), bool)
        yy, xx = np.indices((h, w))
        lamp[((yy * 3 + xx * 2) % 13) == 0] = False
        lamp[5:h - 5:8, 6:w - 6] = False
        sub_sp = sponsors[y0:y0 + h, x0:x0 + w]
        sub_rgb = rgb[y0:y0 + h, x0:x0 + w]
        sub_sp[lamp] = 255
        sub_rgb[lamp] = np.array([218, 26, 34], np.uint8)
        sub_rgb[lamp & (((yy + xx) % 11) < 3)] = np.array([245, 68, 74], np.uint8)
        sub_rgb[lamp & (((yy * 5 + xx) % 23) == 0)] = np.array([118, 10, 18], np.uint8)
        if gray_lens:
            lens = lamp & (yy >= 7) & (yy <= (h * 3) // 4) & (xx >= 7) & (xx <= w - 7)
            sub_rgb[lens] = np.array([104, 110, 120], np.uint8)
        lamps.append((slice(y0, y0 + h), slice(x0, x0 + w), lamp.copy()))

    draw_lamp(22, 390, 32, 76, gray_lens=True)
    draw_lamp(24, 585, 32, 78)

    red_gray_sponsor_card = (slice(26, 58), slice(10, 84))
    sponsors[red_gray_sponsor_card] = 255
    rgb[red_gray_sponsor_card] = np.array([224, 22, 28], np.uint8)
    rgb[34:50, 20:74] = np.array([104, 110, 120], np.uint8)

    isolated_red_sponsor = (slice(26, 84), slice(70, 128))
    sponsors[isolated_red_sponsor] = 255
    rgb[isolated_red_sponsor] = np.array([224, 22, 28], np.uint8)

    yellow_red_sponsor = (slice(28, 64), slice(205, 284))
    sponsors[yellow_red_sponsor] = 255
    rgb[yellow_red_sponsor] = np.array([220, 34, 30], np.uint8)
    rgb[32:60:5, 210:278] = np.array([245, 202, 24], np.uint8)

    mask, guard = car_layers_mod._paired_rear_lamp_template_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 2
    assert guard["pair_count"] == 1
    assert any(
        component.get("lamp_color_family") == "red_gray_lens"
        for component in guard["components"]
    )
    for ys, xs, lamp in lamps:
        assert (mask[ys, xs][lamp] > 0).mean() > 0.95
    assert (mask[red_gray_sponsor_card] > 0).mean() < 0.05
    assert (mask[isolated_red_sponsor] > 0).mean() < 0.05
    assert (mask[yellow_red_sponsor] > 0).mean() < 0.05


def test_smart_tga_number_template_false_positive_moves_right_edge_panel_to_template():
    sample = Path(
        "_smart_tga_runs/cycle486_dlm_batch_dark_panel_angular_white_livery_graphic_v1_nocache/"
        "Dirt_Late_Model_car_num_1167712"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle486 DLM 1167712 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_template_false_positive_to_template(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in guard["components"]
        if component["reason"] == "right_edge_top_template_instrument_panel"
    ]
    assert guard["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (875, 28, 149, 254),
    }
    component = components[0]
    assert component["white_components"] >= 16
    assert component["dark_components"] >= 16
    assert component["ring_template_frac"] >= 0.12
    assert component["ring_dark_frac"] >= 0.70
    assert float((mask[28:282, 875:1024] > 0).mean()) > 0.45
    assert float((mask[816:976, 834:933] > 0).mean()) == 0.0
    assert float((mask[239:342, 271:455] > 0).mean()) == 0.0


def test_smart_tga_number_template_false_positive_moves_dark_clustered_hardware_bars_to_template():
    sample = Path(
        "_smart_tga_runs/cycle557_dlm_next8_after_1244323_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1250296"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle557 DLM 1250296 diagnostic artifact not present")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_template_false_positive_to_template(
        rgb, numbers, sponsors, template, brand
    )

    components = [
        component
        for component in guard["components"]
        if component["reason"] == "clustered_dark_template_hardware_bar_false_number"
    ]
    assert guard["status"] == "applied"
    assert {tuple(component["bbox"]) for component in components} == {
        (724, 677, 95, 25),
        (695, 703, 56, 29),
        (783, 704, 58, 30),
        (718, 738, 103, 24),
    }
    assert all(component["cluster_count"] >= 3 for component in components)
    assert all(component["broad_template_frac"] >= 0.16 for component in components)
    assert all(component["broad_sponsor_frac"] <= 0.04 for component in components)
    assert float((mask[677:762, 695:841] > 0).mean()) > 0.25
    assert float((mask[817:822, 854:902] > 0).mean()) == 0.0
    assert float((mask[908:935, 934:971] > 0).mean()) == 0.0
    assert float((mask[927:993, 51:98] > 0).mean()) == 0.0


def test_smart_tga_template_contained_paint_trim_moves_from_paint_to_template():
    n = 512
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([9, 10, 12], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def trim_stroke(h=5, w=24):
        stroke = np.zeros((h, w), bool)
        stroke[0:h, 0] = True
        stroke[0:h, w - 1] = True
        stroke[1, :] = True
        stroke[3, :] = True
        return stroke

    anchor = (slice(50, 60), slice(320, 368))
    template[anchor] = 255
    rgb[anchor] = np.array([52, 53, 54], np.uint8)
    target = (slice(53, 58), slice(332, 356))
    target_stroke = trim_stroke()
    template[target][target_stroke] = 0
    rgb[target][target_stroke] = np.array([154, 154, 150], np.uint8)
    rgb[target][target_stroke & (np.indices(target_stroke.shape)[1] % 3 == 0)] = np.array([42, 42, 42], np.uint8)

    colored_anchor = (slice(86, 96), slice(320, 368))
    template[colored_anchor] = 255
    rgb[colored_anchor] = np.array([54, 54, 54], np.uint8)
    colored_target = (slice(89, 94), slice(332, 356))
    colored_stroke = trim_stroke()
    template[colored_target][colored_stroke] = 0
    rgb[colored_target][colored_stroke] = np.array([218, 26, 18], np.uint8)

    smooth_anchor = (slice(122, 132), slice(320, 368))
    template[smooth_anchor] = 255
    rgb[smooth_anchor] = np.array([54, 54, 54], np.uint8)
    smooth_target = (slice(125, 130), slice(332, 356))
    template[smooth_target] = 0
    rgb[smooth_target] = np.array([190, 190, 186], np.uint8)

    adjacent_anchor = (slice(72, 82), slice(380, 452))
    template[adjacent_anchor] = 255
    rgb[adjacent_anchor] = np.array([50, 51, 52], np.uint8)
    adjacent_surround = (slice(59, 69), slice(390, 426))
    template[adjacent_surround] = 255
    rgb[adjacent_surround] = np.array([48, 49, 50], np.uint8)
    adjacent_target = (slice(63, 68), slice(394, 422))
    adjacent_stroke = trim_stroke(w=28)
    template[adjacent_target][adjacent_stroke] = 0
    rgb[adjacent_target][adjacent_stroke] = np.array([150, 150, 146], np.uint8)
    rgb[adjacent_target][adjacent_stroke & (np.indices(adjacent_stroke.shape)[1] % 4 == 0)] = np.array([38, 38, 39], np.uint8)

    remote_surround = (slice(87, 100), slice(390, 426))
    template[remote_surround] = 255
    rgb[remote_surround] = np.array([48, 49, 50], np.uint8)
    remote_target = (slice(91, 96), slice(394, 422))
    remote_stroke = trim_stroke(w=28)
    template[remote_target][remote_stroke] = 0
    rgb[remote_target][remote_stroke] = np.array([150, 150, 146], np.uint8)
    rgb[remote_target][remote_stroke & (np.indices(remote_stroke.shape)[1] % 4 == 0)] = np.array([38, 38, 39], np.uint8)

    mask, guard = car_layers_mod._template_contained_paint_trim_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 2
    assert {component["reason"] for component in guard["components"]} == {"contained_grayscale_trim_island"}
    assert (mask[target][target_stroke] > 0).mean() > 0.95
    assert (mask[adjacent_target][adjacent_stroke] > 0).mean() > 0.95
    assert (mask[colored_target][colored_stroke] > 0).mean() < 0.05
    assert (mask[smooth_target] > 0).mean() < 0.05
    assert (mask[remote_target][remote_stroke] > 0).mean() < 0.05


def test_smart_tga_adjacent_front_clip_grayscale_strip_moves_from_paint_to_template():
    n = 512
    rgb = np.zeros((n, n, 3), np.uint8)
    rgb[:, :] = np.array([9, 10, 12], np.uint8)
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    template = np.zeros((n, n), np.uint8)
    brand = np.zeros((n, n), np.uint8)

    def textured_strip(h=9, w=40):
        strip = np.zeros((h, w), bool)
        strip[1:3, :] = True
        strip[5:7, :] = True
        strip[:, 0:2] = True
        strip[:, w - 2:w] = True
        strip[3:6, 16:23] = True
        return strip

    shell = (slice(56, 80), slice(186, 274))
    template[shell] = 255
    rgb[shell] = np.array([48, 49, 50], np.uint8)
    target = (slice(58, 67), slice(192, 232))
    target_strip = textured_strip()
    template[target][target_strip] = 0
    rgb[target][target_strip] = np.array([148, 148, 144], np.uint8)
    rgb[target][target_strip & (np.indices(target_strip.shape)[1] % 5 == 0)] = np.array([38, 38, 39], np.uint8)

    red_shell = (slice(96, 120), slice(186, 274))
    template[red_shell] = 255
    rgb[red_shell] = np.array([48, 49, 50], np.uint8)
    red_target = (slice(98, 107), slice(192, 232))
    red_strip = textured_strip()
    template[red_target][red_strip] = 0
    rgb[red_target][red_strip] = np.array([218, 34, 18], np.uint8)

    remote_shell = (slice(250, 274), slice(186, 274))
    template[remote_shell] = 255
    rgb[remote_shell] = np.array([48, 49, 50], np.uint8)
    remote_target = (slice(252, 261), slice(192, 232))
    remote_strip = textured_strip()
    template[remote_target][remote_strip] = 0
    rgb[remote_target][remote_strip] = np.array([148, 148, 144], np.uint8)
    rgb[remote_target][remote_strip & (np.indices(remote_strip.shape)[1] % 5 == 0)] = np.array([38, 38, 39], np.uint8)

    mask, guard = car_layers_mod._template_contained_paint_trim_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert guard["components"][0]["reason"] == "adjacent_grayscale_front_clip_strip"
    assert guard["components"][0]["anchor_overlap_x"] >= 0.55
    assert (mask[target][target_strip] > 0).mean() > 0.95
    assert (mask[red_target][red_strip] > 0).mean() == 0
    assert (mask[remote_target][remote_strip] > 0).mean() == 0


def _ring_mask(n, cy, cx, outer, inner):
    yy, xx = np.ogrid[:n, :n]
    d2 = (yy - cy) ** 2 + (xx - cx) ** 2
    return (d2 <= outer ** 2) & (d2 >= inner ** 2)


def test_smart_tga_centered_badge_sponsor_island_falls_back_to_paint():
    n = 256
    numbers = np.zeros((n, n), np.uint8)
    sponsors = np.zeros((n, n), np.uint8)
    empty = np.zeros((n, n), np.uint8)
    yy, xx = np.ogrid[:n, :n]

    for cy, cx in ((64, 64), (64, 192), (192, 192)):
        numbers[_ring_mask(n, cy, cx, 20, 12)] = 255

    centered = ((yy - 192) ** 2 + (xx - 192) ** 2) <= 11 ** 2
    centered &= ((yy - 192) ** 2 + (xx - 192) ** 2) >= 9 ** 2
    sponsors[centered] = 255

    outside_badge = (slice(35, 58), slice(105, 128))
    sponsors[outside_badge] = 255

    mask, info = car_layers_mod._round_number_badge_interior_to_paint(
        numbers, sponsors, empty, empty
    )

    reasons = {component["reason"] for component in info["components"]}
    assert info["status"] == "applied"
    assert "centered_badge_sponsor_island" in reasons
    assert (mask[centered] > 0).mean() > 0.95
    assert (mask[outside_badge] > 0).mean() == 0


def test_smart_tga_round_badge_number_crumbs_fall_back_to_paint(monkeypatch):
    n = 256
    tex = np.zeros((n, n, 3), np.float32)
    numbers = np.zeros((n, n), np.uint8)
    for cy, cx in ((64, 64), (64, 192), (192, 192)):
        numbers[_ring_mask(n, cy, cx, 17, 10)] = 255
    crumb = (slice(190, 193), slice(188, 192))
    numbers[crumb] = 255  # tiny disconnected interior art crumb inside the lower-right zero

    monkeypatch.setattr(
        smart_sep_mod,
        "separate_livery_layers_smart",
        lambda _tex: {
            "numbers": numbers.copy(),
            "sponsors": np.zeros((n, n), np.uint8),
            "paint": np.zeros((n, n), np.uint8),
        },
    )

    res = car_layers_mod.separate_into_layers(
        tex, car_slug="dirtlatemodel_358", use_template=False, use_ocr=True
    )

    out_numbers = res["layers"]["numbers"]
    out_paint = res["layers"]["paint"]
    assert (out_numbers[_ring_mask(n, 64, 64, 17, 10)] > 0).mean() > 0.98
    assert (out_numbers[_ring_mask(n, 64, 192, 17, 10)] > 0).mean() > 0.98
    assert (out_numbers[_ring_mask(n, 192, 192, 17, 10)] > 0).mean() > 0.98
    assert (out_numbers[crumb] > 0).mean() == 0
    assert (out_paint[crumb] > 0).mean() == 1
    assert res["badge_number_crumb_guard"]["status"] == "applied"
    assert res["badge_number_crumb_guard"]["component_count"] == 1


def test_smart_tga_neutral_body_watermark_template_demotes_real_dlm_105686():
    sample = Path(
        "_smart_tga_runs/cycle579_dlm_fourth4_fresh_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_105686"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle579 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"), dtype=np.uint8)
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._neutral_body_watermark_template_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    bboxes = {tuple(component["bbox"]) for component in guard.get("components", [])}
    assert guard["status"] == "applied"
    assert guard["component_count"] >= 12
    assert (567, 341, 94, 15) in bboxes
    assert (660, 294, 36, 10) in bboxes
    assert (527, 699, 26, 7) in bboxes
    assert (225, 905, 25, 12) in bboxes
    assert int((mask[341:356, 567:661] > 0).sum()) >= 900
    assert int((mask[294:304, 660:696] > 0).sum()) >= 200
    assert int((mask[699:706, 527:553] > 0).sum()) >= 130
    assert int((mask[905:917, 225:250] > 0).sum()) >= 190
    assert int((mask[137:217, 860:919] > 0).sum()) == 0
    assert int((mask[404:448, 306:338] > 0).sum()) == 0


def test_smart_tga_neutral_body_watermark_family_demotes_real_dlm_105686():
    sample = Path(
        "_smart_tga_runs/cycle580_dlm_105686_neutral_body_watermark_template_v2_nocache/"
        "Dirt_Late_Model_car_num_105686"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle580 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"), dtype=np.uint8)
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._neutral_body_watermark_template_to_paint(
        rgb, numbers, sponsors, template, brand
    )

    bboxes = {tuple(component["bbox"]) for component in guard.get("components", [])}
    family_reasons = {
        component["reason"]
        for component in guard.get("components", [])
        if tuple(component["bbox"]) in {
            (157, 52, 230, 180),
            (596, 158, 167, 133),
            (598, 922, 179, 102),
        }
    }
    assert guard["status"] == "applied"
    assert guard["capped"] is False
    assert guard["component_count"] >= 5
    assert (157, 52, 230, 180) in bboxes
    assert (596, 158, 167, 133) in bboxes
    assert (598, 922, 179, 102) in bboxes
    assert family_reasons == {"neutral_body_watermark_family_template"}
    assert int((mask[52:232, 157:387] > 0).sum()) >= 7200
    assert int((mask[158:291, 596:763] > 0).sum()) >= 5300
    assert int((mask[922:1024, 598:777] > 0).sum()) >= 4900
    assert int((mask[137:217, 860:919] > 0).sum()) == 0
    assert int((mask[404:448, 306:338] > 0).sum()) == 0
    assert int((mask[966:1024, 906:988] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_blue_vertical_sponsor_strip_dlm_105686():
    sample = Path(
        "_smart_tga_runs/cycle584_dlm_105686_watermark_family_v1_nocache/"
        "Dirt_Late_Model_car_num_105686"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle584 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"), dtype=np.uint8)
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert guard["component_count"] >= 1
    assert reasons_by_bbox[(695, 470, 17, 102)] == (
        "narrow_vertical_blue_white_sponsor_strip_false_number"
    )
    assert int((mask[470:572, 695:712] > 0).sum()) == 1120
    assert int((mask[238:339, 317:453] > 0).sum()) == 0
    assert int((mask[737:814, 318:440] > 0).sum()) == 0
    assert int((mask[844:941, 818:947] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_right_neutral_stack_dlm_105686():
    sample = Path(
        "_smart_tga_runs/cycle585_dlm_105686_blue_vertical_sponsor_strip_v1_nocache/"
        "Dirt_Late_Model_car_num_105686"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle585 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"), dtype=np.uint8)
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert reasons_by_bbox[(926, 222, 64, 62)] == (
        "right_side_neutral_contingency_stack_false_number"
    )
    assert int((mask[222:284, 926:990] > 0).sum()) == 2181
    assert int((mask[238:339, 317:453] > 0).sum()) == 0
    assert int((mask[737:814, 318:440] > 0).sum()) == 0
    assert int((mask[844:941, 818:947] > 0).sum()) == 0
    assert int((mask[726:784, 407:440] > 0).sum()) == 0


def test_smart_tga_large_shell_recovers_francis_red_white_door_15_family():
    sample = Path(
        "_smart_tga_runs/cycle587_francis2001_baseline_nocache/"
        "1Shokker_Paint_Car_Examples_1-Francis2001"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle587 Francis DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"), dtype=np.uint8)
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"), dtype=np.uint8)

    first_mask, first_guard = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )
    first_reasons = {
        tuple(component["bbox"]): component["reason"]
        for component in first_guard.get("components", [])
    }
    assert first_guard["status"] == "applied"
    assert first_reasons[(285, 241, 147, 103)] == "red_white_dark_outline_number_decal_replica"
    assert first_reasons[(299, 252, 77, 84)] == "white_core_number_decal_replica"

    numbers = np.maximum(numbers, first_mask)
    sponsors[first_mask > 0] = 0
    second_mask, second_guard = car_layers_mod._large_stylized_number_sponsor_shell_to_number(
        rgb, numbers, sponsors, template, brand
    )
    second_reasons = {
        tuple(component["bbox"]): component["reason"]
        for component in second_guard.get("components", [])
    }
    assert second_guard["status"] == "applied"
    assert second_reasons[(278, 714, 140, 92)] == "red_white_dark_outline_number_decal_replica"
    assert int((second_mask[714:806, 278:418] > 0).sum()) == 7688


def test_smart_tga_small_sponsor_panel_demotes_francis_vertical_valvoline_wordmark():
    sample = Path(
        "_smart_tga_runs/cycle587_francis2001_baseline_nocache/"
        "1Shokker_Paint_Car_Examples_1-Francis2001"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle587 Francis DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"), dtype=np.uint8)
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._small_sponsor_panel_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )
    reasons = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert guard["component_count"] == 1
    assert reasons[(786, 398, 39, 238)] == "tall_blue_white_vertical_sponsor_wordmark"
    assert int((mask[398:636, 786:825] > 0).sum()) == 4178
    assert int((mask[241:344, 285:432] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_rotated_grayscale_service_badge_dlm():
    sample = Path(
        "_smart_tga_runs/cycle538_dlm_next4_after_321255_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_331993"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle538 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    rotated_badges = [
        component
        for component in guard["components"]
        if component["reason"] == "muted_grayscale_rotated_sponsor_badge"
    ]
    assert guard["status"] == "applied"
    assert {tuple(component["bbox"]) for component in rotated_badges} == {(443, 278, 132, 61)}
    assert (mask[278:339, 443:575] > 0).sum() >= 5900

    true_number_controls = [
        (
            Path("_smart_tga_runs/cycle538_dlm_next4_after_321255_scan_v1_nocache/Dirt_Late_Model_car_num_336528"),
            (285, 720, 176, 83),
        ),
        (
            Path("_smart_tga_runs/cycle537_dlm_next4_neutral_textline_gap_controls_v1_nocache/Dirt_Late_Model_car_num_321255"),
            (272, 717, 176, 95),
        ),
    ]
    for control_sample, (x, y, w, h) in true_number_controls:
        if not (control_sample / "source_1024.png").exists():
            continue
        control_rgb = np.array(Image.open(control_sample / "source_1024.png").convert("RGB"))
        control_numbers = np.array(Image.open(control_sample / "masks" / "numbers.png").convert("L"))
        control_sponsors = np.array(Image.open(control_sample / "masks" / "sponsors.png").convert("L"))
        control_template = np.array(Image.open(control_sample / "masks" / "template.png").convert("L"))
        control_brand = np.array(Image.open(control_sample / "masks" / "brand_graphics.png").convert("L"))

        control_mask, control_guard = car_layers_mod._number_logo_false_positive_to_sponsor(
            control_rgb,
            control_numbers,
            control_sponsors,
            control_template,
            control_brand,
        )
        control_reasons = {
            component["reason"]
            for component in control_guard.get("components", [])
        }
        assert "muted_grayscale_rotated_sponsor_badge" not in control_reasons
        assert int((control_mask[y:y + h, x:x + w] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_mid_dlm_sponsor_panels():
    sample = Path(
        "_smart_tga_runs/cycle543_dlm_first6_partial_sponsor_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1004124"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle543 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert reasons_by_bbox[(314, 627, 130, 43)] == "mid_blue_purple_sponsor_logo_panel"
    assert reasons_by_bbox[(0, 796, 202, 87)] == "lower_edge_pale_sponsor_deck"
    assert reasons_by_bbox[(404, 222, 38, 14)] == "compact_mixed_contingency_sponsor_badge"
    assert int((mask[627:670, 314:444] > 0).sum()) >= 3900
    assert int((mask[796:883, 0:202] > 0).sum()) >= 9500
    assert int((mask[222:236, 404:442] > 0).sum()) >= 470
    assert int((mask[37:63, 169:246] > 0).sum()) == 0
    assert int((mask[703:761, 695:840] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_wide_grayscale_dlm_sponsor_deck():
    sample = Path(
        "_smart_tga_runs/cycle546_dlm_next4_after_1008063_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1008314"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle546 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert reasons_by_bbox[(293, 720, 300, 89)] == "wide_grayscale_sponsor_deck_with_embedded_number"
    assert reasons_by_bbox[(284, 787, 47, 14)] == "compact_grayscale_contingency_sponsor_tab"
    assert int((mask[720:809, 293:593] > 0).sum()) >= 14000
    assert int((mask[787:801, 284:331] > 0).sum()) >= 520
    assert int((mask[28:321, 875:1024] > 0).sum()) == 0
    assert int((mask[828:937, 802:965] > 0).sum()) == 0

    control_sample = Path(
        "_smart_tga_runs/cycle545_dlm_next4_shallow_wordmark_strip_control_v1_nocache/"
        "Dirt_Late_Model_car_num_1006305"
    )
    if (control_sample / "source_1024.png").exists():
        control_rgb = np.array(Image.open(control_sample / "source_1024.png").convert("RGB"))
        control_numbers = np.array(Image.open(control_sample / "masks" / "numbers.png").convert("L"))
        control_sponsors = np.array(Image.open(control_sample / "masks" / "sponsors.png").convert("L"))
        control_template = np.array(Image.open(control_sample / "masks" / "template.png").convert("L"))
        control_brand = np.array(Image.open(control_sample / "masks" / "brand_graphics.png").convert("L"))

        control_mask, control_guard = car_layers_mod._number_logo_false_positive_to_sponsor(
            control_rgb,
            control_numbers,
            control_sponsors,
            control_template,
            control_brand,
        )
        control_reasons = {
            component["reason"]
            for component in control_guard.get("components", [])
        }
        assert "wide_grayscale_sponsor_deck_with_embedded_number" not in control_reasons
        assert "compact_grayscale_contingency_sponsor_tab" not in control_reasons
        assert int((control_mask[207:334, 268:600] > 0).sum()) == 0
        assert int((control_mask[723:824, 274:460] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_dark_neutral_dlm_sponsor_badges():
    sample = Path(
        "_smart_tga_runs/cycle556_dlm_next8_after_1197281_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1199313"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle556 DLM artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    reason = "compact_dark_neutral_sponsor_badge_false_number"
    assert guard["status"] == "applied"
    assert reasons_by_bbox[(553, 716, 49, 35)] == reason
    assert reasons_by_bbox[(452, 747, 104, 31)] == reason
    assert int((mask[716:751, 553:602] > 0).sum()) >= 1300
    assert int((mask[747:778, 452:556] > 0).sum()) >= 3000

    # The saturated blue/magenta 111 decals remain editable Numbers.
    assert int((mask[231:336, 283:435] > 0).sum()) == 0
    assert int((mask[717:820, 345:404] > 0).sum()) == 0
    assert int((mask[840:942, 810:869] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_tall_dark_gold_oval_badge_dlm():
    sample = Path(
        "_smart_tga_runs/cycle559_dlm_wrap_first8_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_50232"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle559 DLM 50232 artifact fixture is not available")

    paint_path = Path(
        "C:/DRIVE E BACKUP/Claude Code Assistant/12-iRacing Misc/"
        "Shokker iRacing/SPB Smart TGA Examples/Dirt Late Model/"
        "car_num_50232.tga"
    )
    if not paint_path.exists():
        pytest.skip("DLM 50232 source TGA fixture is not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    tex, _orig_hw, _final_hw = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(tex * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    reason = "tall_dark_gold_oval_sponsor_badge_false_number"
    assert guard["status"] == "applied"
    assert reasons_by_bbox[(753, 428, 66, 180)] == reason

    target = numbers[428:608, 753:819] > 0
    assert target.any()
    recovered = (mask[428:608, 753:819] > 0) & target
    assert float(recovered.sum() / target.sum()) >= 0.98

    # The true black/gold 46 number art remains editable as Numbers.
    for x, y, w, h in [
        (309, 719, 137, 96),
        (602, 864, 160, 160),
        (314, 242, 66, 92),
    ]:
        assert int((mask[y:y + h, x:x + w] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_demotes_real_dlm_1027044_logo_scraps():
    sample = Path(
        "_smart_tga_runs/cycle548_dlm_1027044_pre_decorative_number_shell_target_v1_nocache/"
        "Dirt_Late_Model_car_num_1027044"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle548 DLM 1027044 artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert reasons_by_bbox[(953, 115, 45, 35)] == "bright_orange_logo_tile_false_number"
    assert reasons_by_bbox[(932, 233, 61, 16)] == "bright_orange_logo_bar_false_number"
    assert reasons_by_bbox[(896, 472, 20, 95)] == "narrow_neutral_vertical_logo_sliver_false_number"
    assert reasons_by_bbox[(687, 560, 21, 34)] == "bright_orange_logo_tile_false_number"
    assert reasons_by_bbox[(684, 598, 24, 33)] == "bright_orange_logo_tile_false_number"

    for x, y, w, h in [
        (953, 115, 45, 35),
        (932, 233, 61, 16),
        (896, 472, 20, 95),
        (687, 560, 21, 34),
        (684, 598, 24, 33),
    ]:
        target = numbers[y:y + h, x:x + w] > 0
        assert target.any()
        recovered = (mask[y:y + h, x:x + w] > 0) & target
        assert float(recovered.sum() / target.sum()) >= 0.92

    for x, y, w, h in [
        (311, 237, 129, 106),
        (321, 714, 120, 104),
        (813, 802, 144, 172),
    ]:
        assert int((mask[y:y + h, x:x + w] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_vertical_red_white_sponsor_card_dlm():
    sample = Path(
        "_smart_tga_runs/cycle551_dlm_next8_after_1051317_current_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1073597"
    )
    if not (sample / "source_1024.png").exists():
        pytest.skip("Cycle551 DLM 1073597 artifact fixture is not available")

    rgb = np.array(Image.open(sample / "source_1024.png").convert("RGB"))
    numbers = np.array(Image.open(sample / "masks" / "numbers.png").convert("L"))
    sponsors = np.array(Image.open(sample / "masks" / "sponsors.png").convert("L"))
    template = np.array(Image.open(sample / "masks" / "template.png").convert("L"))
    brand = np.array(Image.open(sample / "masks" / "brand_graphics.png").convert("L"))

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert guard["status"] == "applied"
    assert reasons_by_bbox[(699, 473, 36, 94)] == "compact_vertical_red_white_sponsor_card_false_number"
    assert int((mask[473:567, 699:735] > 0).sum()) >= 2800
    assert int((mask[838:942, 792:965] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_tall_grayscale_vertical_sponsor_panels_dlm():
    sample = Path(
        "_smart_tga_runs/cycle597_dlm_next2_sponsor_family_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1008063"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle597 DLM 1008063 artifact fixture is not available")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    components = [
        component
        for component in guard.get("components", [])
        if component["reason"] == "tall_grayscale_vertical_sponsor_panel_false_number"
    ]
    assert len(components) == 2
    assert sorted(component["bbox"] for component in components) == [
        [48, 405, 96, 223],
        [731, 409, 101, 211],
    ]
    assert all(component["near_sponsor"] >= 0.91 for component in components)
    assert all(component["sat_mean"] <= 0.041 for component in components)
    assert all(component["white_text_components"] >= 12 for component in components)
    assert all(component["dark_text_components"] >= 15 for component in components)

    for x, y, w, h in ([48, 405, 96, 223], [731, 409, 101, 211]):
        target = numbers[y:y + h, x:x + w] > 0
        recovered = mask[y:y + h, x:x + w] > 0
        assert float((recovered & target).sum()) / float(max(1, target.sum())) >= 0.98

    true_green_number_boxes = [
        [363, 250, 94, 86],
        [247, 259, 69, 40],
        [281, 719, 104, 86],
        [893, 876, 74, 101],
    ]
    for x, y, w, h in true_green_number_boxes:
        assert int(mask[y:y + h, x:x + w].sum()) == 0


def test_smart_tga_number_logo_false_positive_recovers_compact_red_dlm_wordmarks():
    sample = Path(
        "_smart_tga_runs/cycle599_dlm_next4_after_1008063_scan_v1_nocache/"
        "Dirt_Late_Model_car_num_1017630"
    )
    required = [
        sample / "source_1024.png",
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle599 DLM 1017630 artifact fixture is not available")

    rgb = np.array(Image.open(required[0]).convert("RGB"), dtype=np.uint8)
    numbers = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[4]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert reasons_by_bbox[(384, 216, 36, 22)] == "compact_red_white_sponsor_tag_false_number"
    assert reasons_by_bbox[(217, 315, 59, 26)] == "compact_dark_red_sponsor_wordmark_false_number"
    assert reasons_by_bbox[(267, 964, 53, 33)] == "compact_red_white_sponsor_tag_false_number"
    assert int((mask[216:238, 384:420] > 0).sum()) == 721
    assert int((mask[315:341, 217:276] > 0).sum()) == 1171
    assert int((mask[964:997, 267:320] > 0).sum()) == 1117
    assert int((mask[915:943, 269:313] > 0).sum()) == 0


def test_smart_tga_number_logo_false_positive_handles_production_rgb_1017630():
    sample = Path(
        "_smart_tga_runs/cycle599_dlm_1017630_compact_red_wordmark_fix_v3_nocache/"
        "Dirt_Late_Model_car_num_1017630"
    )
    paint_path = Path(
        r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing"
        r"\SPB Smart TGA Examples\Dirt Late Model\car_num_1017630.tga"
    )
    required = [
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        paint_path,
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle599 DLM 1017630 production fixture is not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    rgb_float, _alpha, _meta = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(rgb_float[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(required[0]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    reasons_by_bbox = {
        tuple(component["bbox"]): component["reason"]
        for component in guard.get("components", [])
    }
    assert reasons_by_bbox[(384, 216, 36, 22)] == "compact_red_white_sponsor_tag_false_number"
    assert reasons_by_bbox[(267, 964, 53, 33)] == "compact_red_white_sponsor_tag_false_number"
    assert int((mask[216:238, 384:420] > 0).sum()) == 721
    assert int((mask[964:997, 267:320] > 0).sum()) == 1117
    assert int((mask[915:943, 269:313] > 0).sum()) == 0


def test_smart_tga_red_white_dark_paint_number_family_recovers_real_dlm_1017630():
    sample = Path(
        "_smart_tga_runs/cycle599_dlm_1017630_compact_red_wordmark_fix_v3_nocache/"
        "Dirt_Late_Model_car_num_1017630"
    )
    paint_path = Path(
        r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing"
        r"\SPB Smart TGA Examples\Dirt Late Model\car_num_1017630.tga"
    )
    required = [
        sample / "masks" / "numbers.png",
        sample / "masks" / "sponsors.png",
        sample / "masks" / "template.png",
        sample / "masks" / "brand_graphics.png",
        paint_path,
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Cycle599 DLM 1017630 production fixture is not available")

    from engine.spec_sculpt.core import load_paint_rgb_float01

    rgb_float, _alpha, _meta = load_paint_rgb_float01(str(paint_path), target_size=1024)
    rgb = np.clip(rgb_float[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
    numbers = np.array(Image.open(required[0]).convert("L"), dtype=np.uint8)
    sponsors = np.array(Image.open(required[1]).convert("L"), dtype=np.uint8)
    template = np.array(Image.open(required[2]).convert("L"), dtype=np.uint8)
    brand = np.array(Image.open(required[3]).convert("L"), dtype=np.uint8)

    mask, guard = car_layers_mod._red_white_dark_paint_number_supplement(
        rgb, numbers, sponsors, template, brand
    )

    assert guard["status"] == "applied"
    assert guard["component_count"] == 3
    assert guard["candidate_count"] >= 3
    assert guard["capped"] is False
    boxes = {tuple(component["bbox"]): component for component in guard.get("components", [])}
    assert set(boxes) == {
        (291, 246, 174, 97),
        (291, 721, 164, 83),
        (797, 848, 164, 91),
    }
    assert all(component["reason"] == "red_white_dark_number_family_core" for component in boxes.values())
    assert int((mask[246:343, 291:465] > 0).sum()) > 2600
    assert int((mask[721:804, 291:455] > 0).sum()) > 2400
    assert int((mask[848:939, 797:961] > 0).sum()) > 2500
    assert int((mask[216:238, 384:420] > 0).sum()) == 0


def test_smart_tga_number_logo_guard_uses_repeated_palette_family_and_glyph_anatomy():
    cv2 = car_layers_mod.cv2
    if cv2 is None:
        pytest.skip("OpenCV unavailable")
    size = 512
    rgb = np.full((size, size, 3), 28, np.uint8)
    numbers = np.zeros((size, size), np.uint8)
    empty = np.zeros_like(numbers)

    def add_ellipse(x, y, width, height, base, accent, bars=0, target_mask=None):
        if target_mask is None:
            target_mask = numbers
        local = np.zeros((height, width), np.uint8)
        cv2.ellipse(
            local,
            (width // 2, height // 2),
            (max(1, width // 2 - 1), max(1, height // 2 - 1)),
            0,
            0,
            360,
            255,
            -1,
        )
        target_mask[y:y + height, x:x + width] = np.maximum(
            target_mask[y:y + height, x:x + width], local
        )
        region = rgb[y:y + height, x:x + width]
        region[local > 0] = np.asarray(base, np.uint8)
        if bars:
            for index in range(bars):
                bx = 3 + index * max(3, (width - 6) // bars)
                region[3:height - 3, bx:bx + 2] = np.asarray(accent, np.uint8)
        else:
            region[(local > 0) & (np.indices(local.shape)[1] < width // 3)] = np.asarray(accent, np.uint8)

    # Three large anchors and one scale variant share the same purple/yellow
    # ink family. Two differently colored compact graphics are logo controls.
    for x, y in ((35, 40), (205, 55), (355, 340)):
        add_ellipse(x, y, 80, 60, (36, 20, 82), (238, 202, 24))
    true_small_number = (410, 45, 24, 16)
    add_ellipse(*true_small_number, (36, 20, 82), (238, 202, 24))
    false_tiny_logo = (40, 410, 24, 12)
    add_ellipse(*false_tiny_logo, (35, 70, 210), (240, 240, 245), bars=4)
    false_wordmark = (90, 420, 38, 16)
    add_ellipse(*false_wordmark, (232, 32, 45), (245, 245, 245), bars=6)

    mask, info = car_layers_mod._number_logo_false_positive_to_sponsor(
        rgb, numbers, empty, empty, empty
    )

    tx, ty, tw, th = true_small_number
    fx, fy, fw, fh = false_tiny_logo
    wx, wy, ww, wh = false_wordmark
    assert int((mask[ty:ty + th, tx:tx + tw] > 0).sum()) == 0
    assert int((mask[fy:fy + fh, fx:fx + fw] > 0).sum()) > 0
    assert int((mask[wy:wy + wh, wx:wx + ww] > 0).sum()) > 0
    assert info["number_family_anchor_count"] >= 3
    assert info["number_family_protected_count"] == 1
    assert info["number_family_wordmark_count"] == 1
    assert "compact_multiglyph_wordmark_family" in {
        component["reason"] for component in info.get("components", [])
    }

    from engine.spec_sculpt.component_evidence import number_family_template_inlay

    corrected_numbers = numbers.copy()
    corrected_numbers[mask > 0] = 0
    template = np.zeros_like(numbers)
    matching_template_inlay = (330, 180, 24, 16)
    add_ellipse(
        *matching_template_inlay,
        (36, 20, 82),
        (238, 202, 24),
        target_mask=template,
    )
    single_color_hardware = (380, 180, 24, 16)
    add_ellipse(
        *single_color_hardware,
        (238, 202, 24),
        (238, 202, 24),
        target_mask=template,
    )
    inlay_mask, inlay_info = number_family_template_inlay(
        rgb, corrected_numbers, template
    )
    ix, iy, iw, ih = matching_template_inlay
    hx, hy, hw, hh = single_color_hardware
    assert int((inlay_mask[iy:iy + ih, ix:ix + iw] > 0).sum()) > 0
    assert int((inlay_mask[hy:hy + hh, hx:hx + hw] > 0).sum()) == 0
    assert inlay_info["status"] == "applied"
    assert inlay_info["component_count"] == 1
