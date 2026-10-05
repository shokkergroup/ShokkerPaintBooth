"""Mechanical floors for the isolated Fractured Cryptid rejection rebuild.

SPB-WILDS WR-10.  These tests deliberately say nothing about owner acceptance;
the 2026-08-24 rejection proved that green mechanics can still hide lazy art.
"""
from __future__ import annotations

import hashlib
import time

import cv2
import numpy as np

from engine.expansions import fractured_wilds_cryptid_rebuild_2026 as mod


EXPECTED = {
    "fc_sasquatch_fur", "fc_quill_bristle", "fc_coarse_hide", "fc_eyeshine",
    "fc_bog_murk", "fc_claw_rake", "fc_bark_camo", "fc_feathered_wing",
    "fc_dorsal_ridge", "fc_webbed_membrane", "fc_toad_skin", "fc_antler_bone",
    "fc_mossy_stone", "fc_will_o_wisp", "fc_snakeskin", "fc_batwing",
    "fc_gator_hide", "fc_hide_scale_glass", "fc_dragon_hex_glass",
    "fc_crackle_eyeshine_glass",
}


def _sha(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    a = cv2.resize(left, (96, 96), interpolation=cv2.INTER_AREA).astype(np.float32)
    b = cv2.resize(right, (96, 96), interpolation=cv2.INTER_AREA).astype(np.float32)
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.sum(a * b) / denominator) if denominator > 1.0e-6 else 1.0


def test_exact_scope_and_causal_material_floors():
    assert set(mod.CRYPTID_IDS) == EXPECTED
    paints, nulls, specs = set(), set(), set()
    for fid in mod.CRYPTID_IDS:
        grammar = mod.debug_grammar(fid)
        assert len(grammar.marks) >= 7
        paint, spec = mod._compose(grammar, mod._HUES[fid])
        assert paint.shape == (512, 512, 3)
        assert spec.shape == (512, 512, 3)
        assert all(float(spec[:, :, channel].std()) >= 20.0 for channel in range(3))

        for bank in ("A", "B"):
            masks = [mask for _name, mask, owner in grammar.marks if owner == bank]
            assert masks, (fid, bank)
            union = np.maximum.reduce(masks)
            # A token 1–2% flash is not meaningful Fractured ownership.
            assert float((union > 0.08).mean()) >= 0.03, (fid, bank)

        paints.add(_sha(np.clip(paint * 255.0, 0, 255).astype(np.uint8)))
        nulls.add(_sha(np.clip(mod.debug_hue_null(fid) * 255.0, 0, 255).astype(np.uint8)))
        specs.add(_sha(spec))
    assert len(paints) == len(EXPECTED)
    assert len(nulls) == len(EXPECTED)
    assert len(specs) == len(EXPECTED)


def test_no_high_pairwise_paint_or_spec_substrate_collision():
    fields = {}
    for fid in mod.CRYPTID_IDS:
        grammar = mod.debug_grammar(fid)
        _paint, spec = mod._compose(grammar, mod._HUES[fid])
        fields[fid] = (mod.debug_hue_null(fid)[:, :, 0],
                       spec[:, :, 0], spec[:, :, 1], spec[:, :, 2])
    ids = list(mod.CRYPTID_IDS)
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            for channel in range(4):
                assert _corr(fields[left][channel], fields[right][channel]) < 0.80, (
                    left, right, channel)


def test_install_is_exact_and_2048_sample_stays_under_budget():
    registry = {"unrelated": (None, None)}
    mod.install_into_engine(registry)
    assert "unrelated" in registry
    assert {fid for fid in registry if fid.startswith("fc_")} == EXPECTED

    mask = np.ones((2048, 2048), np.float32)
    source = np.zeros((2048, 2048, 3), np.float32)
    for fid in ("fc_sasquatch_fur", "fc_will_o_wisp", "fc_dragon_hex_glass"):
        mod.clear_cache()
        spec_fn, paint_fn = registry[fid]
        started = time.perf_counter()
        paint = paint_fn(source, (2048, 2048), mask, 7, 1.0, None)
        spec = spec_fn((2048, 2048), mask, 7, 1.0)
        elapsed = time.perf_counter() - started
        assert paint.shape == (2048, 2048, 3)
        assert spec.shape == (2048, 2048, 4)
        assert np.all(spec[:, :, 3] == 255)
        assert elapsed < 3.0, (fid, elapsed)
