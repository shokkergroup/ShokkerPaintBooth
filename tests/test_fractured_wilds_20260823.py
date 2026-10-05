"""SPB-WILDS 2026-08-23 regression gates for Cryptid + Morpho.

Owner verdict: "Too much redundancy way too similar looks. Must be VERY
UNIQUE" and every finish must retain the FRACTURED color flip.  These tests
pin the 70-ID/API contract, fine-feature diversity, independent eight-tier
material response, determinism, and mask/strength semantics.  Measured visual
before -> after and native-2048 timing live in ``_wilds_work/report.json``.
"""
from __future__ import annotations

import numpy as np
import pytest

from engine.expansions import fractured_morpho_2026 as morpho
from engine.expansions import fractured_themes_2026 as themes
from engine.expansions import fractured_themes_fix_2026 as fixes
from engine.expansions import fractured_wilds_signatures_2026 as wilds
from scripts import spb_wilds_audit as audit


def _entries():
    result = {}
    for fid in sorted(themes.CRYPTID):
        result[fid] = fixes._mk(fid) if fid in fixes.FIX else themes._mk(fid)
    for fid in sorted(morpho.ALL):
        result[fid] = morpho._mk(fid)
    return result


@pytest.fixture(scope="module")
def rendered():
    shape = (256, 256)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    bb = np.zeros(shape, np.float32)
    output = {}
    for fid, (spec_fn, paint_fn) in _entries().items():
        output[fid] = (
            paint_fn(source.copy(), shape, mask, 20260823, 1.0, bb),
            spec_fn(shape, mask, 20260823, 1.0),
        )
    return output


def test_wilds_id_and_fine_doctrine_contract():
    entries = _entries()
    assert len(themes.CRYPTID) == 20
    assert len(morpho.ALL) == 50
    assert len(entries) == 70
    assert set(entries) == set(themes.CRYPTID) | set(morpho.ALL)
    assert wilds._DESIGN == 512  # 2-8 work px = 8-32 px at native 2048.
    assert len(wilds._MARK_TIERS) == 8
    assert len(wilds._METAL_TIERS) == 8
    assert len(wilds._ROUGH_TIERS) == 8
    assert len(wilds._COAT_TIERS) == 8
    assert len(wilds._CRYPTID_STYLE) == 20


def test_wilds_all_ids_author_seven_distinct_visible_noun_families():
    for fid, recipe in {**themes.CRYPTID, **morpho.ALL}.items():
        if fid in wilds._OWNER_EYE_TOPOLOGY:
            kinds = wilds._OWNER_EYE_TOPOLOGY[fid][0]
        else:
            if fid.startswith("fc_"):
                primary = wilds._CRYPTID_STYLE[fid][0]
            else:
                engine_name = str(recipe.get("engine", ""))
                primary = wilds._MORPHO_STYLE.get(
                    fid, wilds._MORPHO_MOTIFS.get(engine_name)
                )
            kinds = wilds._SEMANTIC_FAMILIES[primary]
        assert len(kinds) == 7, fid
        assert len(set(kinds)) == 7, fid


def test_wilds_outputs_are_deterministic_and_api_safe(rendered):
    shape = (256, 256)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    bb = np.zeros(shape, np.float32)
    for fid, (spec_fn, paint_fn) in _entries().items():
        rgb, spec = rendered[fid]
        assert rgb.shape == (256, 256, 3)
        assert rgb.dtype == np.float32
        assert spec.shape == (256, 256, 4)
        assert spec.dtype == np.uint8
        assert np.isfinite(rgb).all()
        assert 0.0 <= float(rgb.min()) <= float(rgb.max()) <= 1.0
        assert np.array_equal(spec[:, :, 3], np.full(shape, 255, np.uint8))
        assert np.array_equal(rgb, paint_fn(source, shape, mask, 7, 1.0, bb))
        assert np.array_equal(spec, spec_fn(shape, mask, 7, 1.0))
        assert paint_fn.__name__ == f"paint_{fid}"
        assert spec_fn.__name__ == f"spec_{fid}"


def test_wilds_strength_and_mask_contract():
    shape = (96, 112)
    source = np.zeros((*shape, 3), np.float32)
    source[:, :, 0] = 0.17
    source[:, :, 1] = 0.31
    source[:, :, 2] = 0.49
    mask = np.zeros(shape, np.float32)
    mask[18:74, 23:91] = 1.0
    bb = np.zeros(shape, np.float32)
    calm = np.asarray([4, 120, 16], np.uint8)
    representatives = (
        "fc_sasquatch_fur", "fc_dragon_hex_glass", "fmo_glasswing",
        "fmo_fire_agate", "fmo_oil_beetle", "fmo_paua_storm",
    )
    entries = _entries()
    for fid in representatives:
        spec_fn, paint_fn = entries[fid]
        assert np.array_equal(paint_fn(source, shape, mask, 1, 0.0, bb), source)
        zero_spec = spec_fn(shape, mask, 1, 0.0)
        assert np.array_equal(zero_spec[:, :, :3], np.broadcast_to(calm, (*shape, 3)))
        rgb = paint_fn(source, shape, mask, 1, 1.0, bb)
        spec = spec_fn(shape, mask, 1, 1.0)
        outside = mask == 0
        assert np.array_equal(rgb[outside], source[outside])
        assert np.array_equal(spec[outside, :3], np.broadcast_to(calm, (outside.sum(), 3)))
        assert not np.array_equal(rgb[mask == 1], source[mask == 1])


def test_wilds_every_finish_has_wide_independent_flip_channels(rendered):
    for fid, (_, spec4) in rendered.items():
        spec = spec4[:, :, :3].astype(np.float32)
        expected = (wilds._METAL_TIERS, wilds._ROUGH_TIERS, wilds._COAT_TIERS)
        for index, minimum_range in enumerate((220.0, 190.0, 220.0)):
            channel = spec[:, :, index]
            assert float(channel.std()) >= 20.0, fid
            assert float(channel.max() - channel.min()) >= minimum_range, fid
            values, counts = np.unique(channel.astype(np.uint8), return_counts=True)
            assert np.array_equal(values, expected[index].astype(np.uint8)), fid
            # "Eight tier" must mean materially occupied shades, not one-off
            # antialias pixels. Rank bins currently hold ~12.5% each; 5% leaves
            # safe implementation headroom without allowing token tiers.
            assert int(counts.min()) >= int(channel.size * 0.05), fid
        corr = np.corrcoef(spec.reshape(-1, 3), rowvar=False)
        assert float(np.max(np.abs(corr[np.triu_indices(3, 1)]))) < 0.75, fid
        metal, rough, coat = spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]
        response_a = (audit.ANGLE_A_WEIGHTS[0] * metal
                      + audit.ANGLE_A_WEIGHTS[1] * (255.0 - rough)
                      + audit.ANGLE_A_WEIGHTS[2] * coat)
        response_b = (audit.ANGLE_B_WEIGHTS[0] * metal
                      + audit.ANGLE_B_WEIGHTS[1] * (255.0 - rough)
                      + audit.ANGLE_B_WEIGHTS[2] * coat)
        assert float(np.mean(np.abs(response_a - response_b))) >= 45.0, fid


def test_wilds_every_finish_is_fine_color_rich_and_unique(rendered):
    rows = []
    for fid, (rgb, spec) in rendered.items():
        row = audit._row(fid, rgb, spec)
        assert row["paint_fine_energy"] >= 0.02, fid
        assert row["color_population"] >= 12, fid
        assert row["flip_colored_pixel_fraction"] >= 0.20, fid
        assert row["flip_hue_histogram_tv"] >= 0.12, fid
        rows.append(row)
    similarity = audit._similarity(rows)
    assert similarity["structural_ge_0_80"] == 0
    assert similarity["look_ge_0_80"] == 0
    assert similarity["max_structural_similarity"] < 0.80
