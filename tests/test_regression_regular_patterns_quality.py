import json
import subprocess
from pathlib import Path

import numpy as np

import shokker_engine_v2 as eng


REPO = Path(__file__).resolve().parent.parent
SHAPE = (96, 96)
eng._ensure_expansions_loaded()


def _load_pattern_groups() -> dict[str, list[str]]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
console.log(JSON.stringify(vm.runInContext('PATTERN_GROUPS', ctx)));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def _norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _fine_energy(arr):
    arr = _norm01(arr)
    return float(np.mean(np.abs(arr[:, 1:] - arr[:, :-1])) + np.mean(np.abs(arr[1:, :] - arr[:-1, :])))


def _residual_energy(arr):
    arr = _norm01(arr)
    pad = np.pad(arr, 1, mode="edge")
    smooth = (
        pad[:-2, :-2] + pad[:-2, 1:-1] + pad[:-2, 2:]
        + pad[1:-1, :-2] + pad[1:-1, 1:-1] + pad[1:-1, 2:]
        + pad[2:, :-2] + pad[2:, 1:-1] + pad[2:, 2:]
    ) / 9.0
    return float(np.mean(np.abs(arr - smooth)))


def test_all_grouped_regular_patterns_resolve_and_procedural_patterns_have_detail():
    groups = _load_pattern_groups()
    missing = []
    crashed = []
    weak = []
    mask = np.ones(SHAPE, dtype=np.float32)

    for group, ids in groups.items():
        for pattern_id in ids:
            entry = eng.PATTERN_REGISTRY.get(pattern_id)
            if not isinstance(entry, dict):
                missing.append((group, pattern_id))
                continue
            texture_fn = entry.get("texture_fn")
            if not callable(texture_fn):
                continue
            try:
                tex = texture_fn(SHAPE, mask, seed=8301, sm=1.0)
                pattern_val = np.asarray(tex.get("pattern_val"), dtype=np.float32)
                if pattern_val.shape[:2] != SHAPE:
                    crashed.append((group, pattern_id, "bad shape", tuple(pattern_val.shape)))
                    continue
                flags = []
                if float(pattern_val.max() - pattern_val.min()) < 0.18:
                    flags.append("LOW_RANGE")
                if _fine_energy(pattern_val) < 0.010:
                    flags.append("LOW_FINE")
                if _residual_energy(pattern_val) < 0.006:
                    flags.append("LOW_RESIDUAL")
                if flags:
                    weak.append((group, pattern_id, flags))
            except Exception as exc:  # pragma: no cover - assertion payload
                crashed.append((group, pattern_id, type(exc).__name__, str(exc)))

    assert not missing, f"PATTERN_GROUPS ids missing Python PATTERN_REGISTRY entries: {missing[:20]}"
    assert not crashed, f"Grouped procedural patterns crashed: {crashed[:20]}"
    assert not weak, f"Grouped procedural patterns lack 2048-scale detail: {weak[:20]}"


def test_image_backed_regular_patterns_overlay_paint_and_respect_zone_mask():
    groups = _load_pattern_groups()
    image_backed = []
    for group, ids in groups.items():
        for pattern_id in ids:
            entry = eng.PATTERN_REGISTRY.get(pattern_id)
            if isinstance(entry, dict) and entry.get("image_path"):
                image_backed.append((group, pattern_id))

    assert image_backed, "Expected UI PATTERN_GROUPS to include image-backed patterns"

    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.24, dtype=np.float32)
    mask = np.zeros(SHAPE, dtype=np.float32)
    mask[:, : SHAPE[1] // 2] = 1.0
    bb = np.zeros(SHAPE, dtype=np.float32)
    weak = []
    leaks = []

    for group, pattern_id in image_backed:
        out = eng.overlay_pattern_paint(
            paint.copy(),
            pattern_id,
            SHAPE,
            mask,
            seed=9401,
            pm=1.0,
            bb=bb,
            scale=1.0,
            opacity=0.85,
            rotation=0,
            spec_mult=1.0,
        )
        inside_delta = float(np.mean(np.abs(out[:, : SHAPE[1] // 2, :3] - paint[:, : SHAPE[1] // 2, :])))
        outside_delta = float(np.mean(np.abs(out[:, SHAPE[1] // 2 :, :3] - paint[:, SHAPE[1] // 2 :, :])))
        if inside_delta < 0.010:
            weak.append((group, pattern_id, round(inside_delta, 5)))
        if outside_delta > 1e-5:
            leaks.append((group, pattern_id, round(outside_delta, 6)))

    assert not weak, f"Image-backed regular patterns rendered as overlay no-ops: {weak[:20]}"
    assert not leaks, f"Image-backed regular patterns leaked outside zone mask: {leaks[:20]}"
