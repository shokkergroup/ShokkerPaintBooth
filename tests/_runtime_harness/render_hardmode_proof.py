"""HEENAN HARDMODE — render before/after spec-map proof grid.

For each finish that was tuned in the SIGNATURE FINISH TRUST PASS HARDMODE
run, generate a 256x256 spec-map render (M, R, CC channels packed into
RGB) so we have visual evidence of the parameter widening, not just diff
text.

Output: docs/hardmode_proof/<finish_id>_spec.png

Notes:
 - We only render the AFTER state (the BEFORE state is captured in the
   commit history and the inline old-value comments in the source).
 - Spec map encoding for the proof PNG:
     R channel = M (metallic)         -> reds = metallic zones
     G channel = R (roughness)        -> greens = rough zones
     B channel = CC (clearcoat dull)  -> blues = duller clearcoat
   So a chrome flip (high M, low R, low CC) renders as bright-red-only;
   a matte zone (low M, high R, high CC) renders as cyan-ish.
"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "docs" / "hardmode_proof"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SHAPE = (256, 256)
SEED = 42
SM = 1.0  # full strength
BASE_M = 200
BASE_R = 30


def _save_spec_png(name, M, R, CC):
    """Pack (M,R,CC) into RGB and save as PNG."""
    try:
        from PIL import Image
    except ImportError:
        # Fallback: write a simple PPM
        rgb = np.stack([M, R, CC], axis=-1).clip(0, 255).astype(np.uint8)
        path = OUT_DIR / f"{name}_spec.ppm"
        with open(path, "wb") as f:
            f.write(b"P6\n%d %d\n255\n" % rgb.shape[:2])
            f.write(rgb.tobytes())
        return path
    rgb = np.stack([M, R, CC], axis=-1).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(rgb, mode="RGB")
    path = OUT_DIR / f"{name}_spec.png"
    img.save(path)
    return path


def _stats_line(label, M, R, CC):
    return (
        f"{label:24s} "
        f"M[{M.min():3.0f}..{M.max():3.0f}] dM={M.max()-M.min():3.0f} "
        f"R[{R.min():3.0f}..{R.max():3.0f}] dR={R.max()-R.min():3.0f} "
        f"CC[{CC.min():3.0f}..{CC.max():3.0f}] dCC={CC.max()-CC.min():3.0f}"
    )


def render_shokk_finishes():
    """Render SHOKK spec functions tuned in HARDMODE round 1 + 2 + 3
    plus the audit-fix void."""
    from engine.shokk_series import (
        # Round 1:
        spec_shokk_flux, spec_shokk_phase, spec_shokk_dual,
        spec_shokk_prism, spec_shokk_rift, spec_shokk_cipher,
        # Round 2:
        spec_shokk_aurora, spec_shokk_helix, spec_shokk_polarity,
        spec_shokk_wraith, spec_shokk_mirage,
        # Round 3 + audit remediation:
        spec_shokk_apex, spec_shokk_vortex, spec_shokk_void,
    )
    rows = []
    for name, fn in [
        # Round 1:
        ("shokk_flux",     spec_shokk_flux),
        ("shokk_phase",    spec_shokk_phase),
        ("shokk_dual",     spec_shokk_dual),
        ("shokk_prism",    spec_shokk_prism),
        ("shokk_rift",     spec_shokk_rift),
        ("shokk_cipher",   spec_shokk_cipher),
        # Round 2:
        ("shokk_aurora",   spec_shokk_aurora),
        ("shokk_helix",    spec_shokk_helix),
        ("shokk_polarity", spec_shokk_polarity),
        ("shokk_wraith",   spec_shokk_wraith),
        ("shokk_mirage",   spec_shokk_mirage),
        # Round 3 + audit fixes:
        ("shokk_apex",     spec_shokk_apex),
        ("shokk_vortex",   spec_shokk_vortex),
        ("shokk_void",     spec_shokk_void),
    ]:
        M, R, CC = fn(SHAPE, SEED, SM, BASE_M, BASE_R)
        path = _save_spec_png(name, M, R, CC)
        rows.append(_stats_line(name, M, R, CC) + f"  -> {path.relative_to(REPO)}")
    return rows


def render_colorshoxx_heroes():
    """Render structural_color heroes touched in HARDMODE round 1 + 2."""
    from engine.paint_v2.structural_color import (
        spec_colorshoxx_inferno, spec_colorshoxx_arctic,
        spec_colorshoxx_venom, spec_colorshoxx_solar,
        spec_colorshoxx_phantom,
        spec_cx_aurora_borealis, spec_cx_frozen_nebula,
        spec_cx_prism_shatter, spec_cx_acid_rain, spec_cx_royal_spectrum,
    )
    rows = []
    for name, fn in [
        ("cx_inferno",         spec_colorshoxx_inferno),
        ("cx_arctic",          spec_colorshoxx_arctic),
        ("cx_venom",           spec_colorshoxx_venom),
        ("cx_solar",           spec_colorshoxx_solar),
        ("cx_phantom",         spec_colorshoxx_phantom),
        # Round 2:
        ("cx_aurora_borealis", spec_cx_aurora_borealis),
        ("cx_frozen_nebula",   spec_cx_frozen_nebula),
        ("cx_prism_shatter",   spec_cx_prism_shatter),
        ("cx_acid_rain",       spec_cx_acid_rain),
        ("cx_royal_spectrum",  spec_cx_royal_spectrum),
    ]:
        M, R, CC = fn(SHAPE, SEED, SM, BASE_M, BASE_R)
        path = _save_spec_png(name, M, R, CC)
        rows.append(_stats_line(name, M, R, CC) + f"  -> {path.relative_to(REPO)}")
    return rows


def render_dual_shift_paints():
    """Render the 8 dual_color_shift paint outputs (paint result, not spec)."""
    from engine.dual_color_shift import (
        DUAL_SHIFT_PRESETS, paint_dual_shift, spec_dual_shift,
    )
    rows = []
    for name, preset in DUAL_SHIFT_PRESETS.items():
        # Build a neutral-gray paint canvas to apply the duo onto.
        paint = np.full((*SHAPE, 4), 0.5, dtype=np.float32)
        paint[..., 3] = 1.0
        mask = np.ones(SHAPE, dtype=np.float32)
        bb = np.zeros(SHAPE, dtype=np.float32)
        out = paint_dual_shift(
            paint, SHAPE, mask, SEED, 1.0, bb,
            color_a=preset["color_a"],
            color_b=preset["color_b"],
            shift_intensity=1.0,
            blend_strength=preset.get("blend_strength", 0.85),
            flow_complexity=preset.get("flow_complexity", 3),
            field_style=preset.get("field_style", "sweep"),
            field_seed_offset=preset.get("field_seed_offset", 0),
            edge_bias=preset.get("edge_bias", 0.0),
            turbulence=preset.get("turbulence", 1.0),
            band_sharpness=preset.get("band_sharpness", 0.0),
            transition_mid=preset.get("transition_mid", 0.5),
            transition_width=preset.get("transition_width", 0.4),
            transition_gamma=preset.get("transition_gamma", 1.0),
            flake_cell_size=preset.get("flake_cell_size", 5),
            flake_hue_strength=preset.get("flake_hue_strength", 0.03),
        )
        rgb = (out[..., :3] * 255.0).clip(0, 255).astype(np.uint8)
        try:
            from PIL import Image
            path = OUT_DIR / f"dualshift_{name}_paint.png"
            Image.fromarray(rgb, mode="RGB").save(path)
        except ImportError:
            path = OUT_DIR / f"dualshift_{name}_paint.ppm"
            with open(path, "wb") as f:
                f.write(b"P6\n%d %d\n255\n" % rgb.shape[:2])
                f.write(rgb.tobytes())
        rows.append(
            f"dual_{name:18s} style={preset['field_style']:8s} "
            f"tw={preset['transition_width']:.2f} tg={preset['transition_gamma']:.2f} "
            f"bs={preset['band_sharpness']:.2f} turb={preset['turbulence']:.2f} "
            f"flake={preset['flake_cell_size']} -> {path.relative_to(REPO)}"
        )
    return rows


def render_foundation_finishes():
    """Render the 4 Foundation entries tuned this run.

    Foundation entries don't have dedicated spec_*_fn signatures matching
    the (shape, seed, sm, base_m, base_r) shape — they are static M/R/CC
    triples + optional perlin noise that the engine applies. We synthesize
    a per-pixel field by sampling the engine's noise helpers using each
    base's parameters from BASE_REGISTRY.
    """
    from engine.base_registry_data import BASE_REGISTRY
    from engine.core import multi_scale_noise, perlin_multi_octave
    rows = []
    for fid in ("piano_black", "wet_look", "gloss", "silk", "flat_black", "primer"):
        e = BASE_REGISTRY[fid]
        M0 = float(e["M"]); R0 = float(e["R"]); CC0 = float(e["CC"])
        if e.get("perlin"):
            n = perlin_multi_octave(
                SHAPE,
                octaves=int(e.get("perlin_octaves", 3)),
                persistence=float(e.get("perlin_persistence", 0.5)),
                lacunarity=float(e.get("perlin_lacunarity", 2.0)),
                seed=SEED,
            )
            n = (n - n.min()) / (n.max() - n.min() + 1e-8) - 0.5  # center on 0
        elif "noise_scales" in e:
            n = multi_scale_noise(
                SHAPE,
                e["noise_scales"],
                e.get("noise_weights", [1.0 / len(e["noise_scales"])] * len(e["noise_scales"])),
                SEED,
            )
            n = (n - n.min()) / (n.max() - n.min() + 1e-8) - 0.5
        else:
            n = np.zeros(SHAPE, dtype=np.float32)
        nm = float(e.get("noise_M", 0))
        nr = float(e.get("noise_R", 0))
        M = np.clip(M0 + n * nm * 2.0, 0, 255).astype(np.float32)
        R = np.clip(R0 + n * nr * 2.0, 15, 255).astype(np.float32)
        CC = np.full(SHAPE, CC0, dtype=np.float32)
        path = _save_spec_png(f"foundation_{fid}", M, R, CC)
        rows.append(_stats_line(fid, M, R, CC) + f"  -> {path.relative_to(REPO)}")
    return rows


def render_cs_duo_samples():
    """Render a 6-pair sample of the cs_* duo bank to prove each pair now
    has a unique flake field (HARDMODE-R3-MICRO)."""
    import numpy as np
    from engine.micro_flake_shift import CS_DUO_MICRO_MONOLITHICS
    rows = []
    mask = np.ones(SHAPE, dtype=np.float32)
    for fid in ("cs_fire_ice", "cs_pink_purple", "cs_crimson_jade",
                "cs_sunset_ocean", "cs_copper_teal", "cs_burgundy_gold"):
        spec_fn, _paint_fn = CS_DUO_MICRO_MONOLITHICS[fid]
        spec = spec_fn(SHAPE, mask, SEED, SM)
        M = spec[:, :, 0].astype(np.float32)
        R = spec[:, :, 1].astype(np.float32)
        CC = spec[:, :, 2].astype(np.float32)
        path = _save_spec_png(fid, M, R, CC)
        rows.append(_stats_line(fid, M, R, CC) + f"  -> {path.relative_to(REPO)}")
    return rows


def main():
    print(f"Output dir: {OUT_DIR.relative_to(REPO)}")
    print()
    print("=" * 72)
    print("SHOKK spec proofs (HARDMODE-SHOKK-1..11 + R3-APEX/VORTEX + FIX-VOID)")
    print("=" * 72)
    for line in render_shokk_finishes():
        print("  " + line)
    print()
    print("=" * 72)
    print("COLORSHOXX hero spec proofs (HARDMODE-CX-7..13 + 3 unchanged)")
    print("=" * 72)
    for line in render_colorshoxx_heroes():
        print("  " + line)
    print()
    print("=" * 72)
    print("Dual-shift paint proofs (HARDMODE-CX-1..6 tuned + 2 unchanged)")
    print("=" * 72)
    for line in render_dual_shift_paints():
        print("  " + line)
    print()
    print("=" * 72)
    print("Foundation spec proofs (HARDMODE-FOUND-1..6)")
    print("=" * 72)
    for line in render_foundation_finishes():
        print("  " + line)
    print()
    print("=" * 72)
    print("CS_DUO sample proofs (HARDMODE-R3-MICRO — per-pair seed_offset)")
    print("=" * 72)
    for line in render_cs_duo_samples():
        print("  " + line)
    print()
    print(f"Done. {len(list(OUT_DIR.glob('*')))} proof artifacts in {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
