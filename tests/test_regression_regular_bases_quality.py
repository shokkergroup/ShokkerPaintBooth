from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

import shokker_engine_v2 as eng
from engine.expansions.arsenal_24k import spec_metallic_standard_24k
from engine.spec_patterns import PATTERN_CATALOG


REPO = Path(__file__).resolve().parent.parent
SHAPE = (128, 128)
eng._ensure_expansions_loaded()

CLASSIC_FOUNDATION_IDS = {
    "ceramic",
    "gloss",
    "piano_black",
    "wet_look",
    "semi_gloss",
    "satin",
    "scuffed_satin",
    "silk",
    "eggshell",
    "clear_matte",
    "primer",
    "flat_black",
    "matte",
    "living_matte",
    "chalky_base",
}


def _load_base_groups() -> dict[str, list[str]]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
console.log(JSON.stringify(vm.runInContext('BASE_GROUPS', ctx)));
"""
    result = subprocess.run(["node", "-e", script], cwd=REPO, capture_output=True, text=True, check=True)
    import json
    return json.loads(result.stdout)


def _load_spec_pattern_groups() -> dict[str, list[str]]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
console.log(JSON.stringify(vm.runInContext('SPEC_PATTERN_GROUPS', ctx)));
"""
    result = subprocess.run(["node", "-e", script], cwd=REPO, capture_output=True, text=True, check=True)
    import json
    return json.loads(result.stdout)


def _fine_energy(arr: np.ndarray) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    return float(np.abs(np.diff(arr, axis=0)).mean() + np.abs(np.diff(arr, axis=1)).mean())


def _residual_energy(arr: np.ndarray, block: int = 8) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    h, w = arr.shape[:2]
    hh = h - h % block
    ww = w - w % block
    cropped = arr[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    up = np.repeat(np.repeat(coarse, block, axis=0), block, axis=1)
    return float(np.abs(cropped - up).mean())


def _color_population(rgb: np.ndarray) -> int:
    bins = np.floor(np.clip(rgb[:, :, :3], 0, 0.999) * 8).astype(np.int16)
    packed = bins[:, :, 0] * 64 + bins[:, :, 1] * 8 + bins[:, :, 2]
    counts = np.bincount(packed.ravel(), minlength=512)
    return int((counts > (rgb.shape[0] * rgb.shape[1] * 0.002)).sum())


def _norm01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _render_base(fid: str):
    entry = eng.BASE_REGISTRY[fid]
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.34, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    bb = np.zeros(SHAPE, dtype=np.float32)
    rgb = entry["paint_fn"](paint, SHAPE, mask, seed=5101, pm=1.0, bb=bb)
    m, r, cc = entry["base_spec_fn"](SHAPE, seed=5101, sm=1.0, base_m=entry["M"], base_r=entry["R"])
    return np.asarray(rgb[:, :, :3], dtype=np.float32), np.asarray(m, dtype=np.float32), np.asarray(r, dtype=np.float32), np.asarray(cc, dtype=np.float32)


def _spec_range(m: np.ndarray, r: np.ndarray, cc: np.ndarray) -> float:
    return float(max(m.max() - m.min(), r.max() - r.min(), cc.max() - cc.min()))


def test_redundant_regular_base_categories_are_hidden_from_picker():
    groups = _load_base_groups()
    assert "Reference Foundations" not in groups
    assert "PARADIGM" not in groups


def test_paint_technique_bases_are_real_renderers_not_dead_catalog_tiles():
    ids = [
        "paint_drip_gravity",
        "paint_splatter_loose",
        "paint_sponge_stipple",
        "paint_roller_streak",
        "paint_spray_fade",
        "paint_brush_stroke",
    ]
    for fid in ids:
        assert fid in eng.BASE_REGISTRY
        rgb, m, r, cc = _render_base(fid)
        lum = rgb.mean(axis=2)
        assert np.isfinite(rgb).all(), fid
        assert float(rgb.max() - rgb.min()) > 0.08, fid
        assert _fine_energy(lum) > 0.006, fid
        assert float(max(m.max() - m.min(), r.max() - r.min(), cc.max() - cc.min())) > 35.0, fid


def test_named_regular_base_rebuilds_have_fine_detail_and_spec_range():
    ids = [
        "brushed_aluminum",
        "titanium_raw",
        "xirallic",
        "chromaflair",
        "rose_gold",
        "hypershift_spectral",
        "jelly_pearl",
        "holographic_base",
        "metallic",
        "copper",
    ]
    for fid in ids:
        rgb, m, r, cc = _render_base(fid)
        lum = rgb.mean(axis=2)
        assert np.isfinite(rgb).all(), fid
        assert float(rgb.max() - rgb.min()) > 0.09, fid
        assert _fine_energy(lum) > 0.006, fid
        assert _spec_range(m, r, cc) > 30.0, fid


def test_all_shipping_regular_bases_have_renderable_python_paths():
    groups = _load_base_groups()
    missing = []
    crashed = []
    for group, ids in groups.items():
        if "Foundation" in group:
            continue
        for fid in ids:
            if fid in CLASSIC_FOUNDATION_IDS:
                continue
            if fid not in eng.BASE_REGISTRY:
                missing.append((group, fid))
                continue
            try:
                rgb, m, r, cc = _render_base(fid)
                assert np.isfinite(rgb).all()
                assert np.isfinite(m).all()
                assert np.isfinite(r).all()
                assert np.isfinite(cc).all()
            except Exception as exc:  # pragma: no cover - assertion payload
                crashed.append((group, fid, type(exc).__name__, str(exc)))
    assert not missing, f"BASE_GROUPS ids missing Python BASE_REGISTRY renderers: {missing[:20]}"
    assert not crashed, f"Grouped bases crashed direct render/spec path: {crashed[:20]}"


def test_non_foundation_regular_bases_have_dense_2048_scale_detail():
    groups = _load_base_groups()
    monochrome_ok = {"Satin & Wrap", "Industrial & Tactical", "OEM Automotive", "Ceramic & Glass"}
    weak = []
    for group, ids in groups.items():
        if "Foundation" in group:
            continue
        for fid in ids:
            if fid in CLASSIC_FOUNDATION_IDS:
                continue
            rgb, m, r, cc = _render_base(fid)
            lum = rgb.mean(axis=2)
            flags = []
            if _fine_energy(lum) < 0.010:
                flags.append("LOW_FINE")
            if _residual_energy(lum) < 0.006:
                flags.append("LOW_RESIDUAL")
            if _color_population(rgb) < 2 and group not in monochrome_ok:
                flags.append("LOW_COLOR_POP")
            if _spec_range(m, r, cc) < 45.0:
                flags.append("LOW_SPEC_RANGE")
            if flags:
                weak.append((group, fid, ",".join(flags)))
    assert not weak, f"Regular base category quality ratchet failed: {weak[:30]}"


def test_all_spec_pattern_overlay_groups_render_dense_spec_only_fields():
    groups = _load_spec_pattern_groups()
    missing = []
    weak = []
    mask = np.ones(SHAPE, dtype=np.float32)
    for group, ids in groups.items():
        for pid in ids:
            try:
                if pid in PATTERN_CATALOG:
                    arr = PATTERN_CATALOG[pid](SHAPE, 7301, 1.0)
                elif pid in eng.PATTERN_REGISTRY and eng.PATTERN_REGISTRY[pid].get("texture_fn"):
                    tex = eng.PATTERN_REGISTRY[pid]["texture_fn"](SHAPE, mask, 7301, 1.0)
                    arr = tex["pattern_val"] if isinstance(tex, dict) and "pattern_val" in tex else tex
                else:
                    missing.append((group, pid))
                    continue
                if isinstance(arr, tuple):
                    arr = arr[0]
                arr = np.asarray(arr, dtype=np.float32)
                if arr.ndim == 3:
                    arr = arr[:, :, 0]
                norm = _norm01(arr)
                flags = []
                if _fine_energy(norm) < 0.010:
                    flags.append("LOW_FINE")
                if _residual_energy(norm) < 0.006:
                    flags.append("LOW_RESIDUAL")
                if float(arr.max() - arr.min()) < 0.15:
                    flags.append("LOW_RANGE")
                if flags:
                    weak.append((group, pid, ",".join(flags)))
            except Exception as exc:  # pragma: no cover - assertion payload
                weak.append((group, pid, f"{type(exc).__name__}: {exc}"))
    assert not missing, f"Spec pattern UI ids missing renderers: {missing[:30]}"
    assert not weak, f"Spec pattern overlay quality ratchet failed: {weak[:30]}"


def test_legacy_metallic_standard_spec_signature_cannot_crash_satan_apple():
    mask = np.ones(SHAPE, dtype=np.float32)
    old_sig = spec_metallic_standard_24k(SHAPE, mask, 27, 1.0)
    base_sig = spec_metallic_standard_24k(SHAPE, 27, 1.0, 230, 2)
    for out in (*old_sig, *base_sig):
        assert np.asarray(out).shape == SHAPE
        assert np.isfinite(out).all()
