"""GRADIENTS catalog engine (2026-06-18) — 🌈 GRADIENTS group, 11 finishes.

ONE curated palette per gradient_math structure (NOT the 11x11 cross product). Hard reason:
scripts/spb_uniqueness_gate.py is COLOR-INDEPENDENT (luma pHash + structural descriptor), so the
same structure under a different palette is the same luma layout = >80% similar = FAIL. The
gradient_math.gradient_similarity gate IS colour-aware, but it does NOT run at booth runtime — the
catalog uniqueness gate is the ship gate and it is colour-blind. One palette per structure therefore
guarantees zero intra-group structural collisions (and 11 is the clean count to eyeball-test the
engine without near-dup clutter).

Machine mirrors fractured_themes_2026 exactly:
  paint_fn  -> gradient_math.GRADIENT_STRUCTURES[structure]((fw,fh), seed, palette=pal)
               blended onto the base via src*(1-kk) + art*kk, kk = clip(mask*pm).
  spec_fn   -> the proven fracture_spec(art, mask, ignition=0.7, decorrelation=0.15, as_uint8=True)
               GRADIENT DEFAULT SPEC: a smooth glossy clearcoat/metallic sheen that follows the
               gradient's bright bands (ridges / sheen lines / hue peaks) with calm matte troughs.
               Lower ignition + lower decorrelation than the FRACTURED finishes = clean gloss, not a
               hard flame. Zero new spec code (iron-safe, masked, traces the paint).

Self-contained, <3s/finish, work-res art cached via lru_cache.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.gradient_math as gm
from engine.spec_sculpt.fracture import fracture_spec

_WORK = 1152

# Structures whose generator takes NO palette kwarg (built-in _SPECTRUM ramp).
_NO_PALETTE = {"spectral_sweep", "holo_foil"}

# ── 🌈 GRADIENTS — one curated structure->palette pairing each (max visual spread) ──
# fid = f"grd_{structure}" ; palette None where the generator takes no palette kwarg.
GRAD_FINISHES = {
    "grd_oklab_flow":           dict(structure="oklab_flow",           palette="sunset_drift",
        name="OKLab Flow",            seed=7001,
        desc="A perceptual OKLab sunset ramp drifting along a curl-noise flow — organic, never a dead-straight band. A GRADIENTS finish."),
    "grd_iridescent":           dict(structure="iridescent",           palette="oilslick",
        name="Iridescent",            seed=7002,
        desc="Oil-slick holographic hue travelling the spectrum along a warped radial coordinate with thin-film sheen — iridescent metal film. A GRADIENTS finish."),
    "grd_ridged_contour":       dict(structure="ridged_contour",       palette="deep_sea",
        name="Ridged Contour",        seed=7003,
        desc="A warped deep-sea ramp quantised into smooth topographic contour bands with bright ridge-lines — a designed banded surface. A GRADIENTS finish."),
    "grd_mesh_bleed":           dict(structure="mesh_bleed",           palette="aurora",
        name="Mesh Bleed",            seed=7004,
        desc="Several aurora colour sources bleeding into each other so colour pools and flows — a multi-source gradient mesh. A GRADIENTS finish."),
    "grd_duotone_grain":        dict(structure="duotone_grain",        palette="candy_chrome",
        name="Duotone Grain",         seed=7005,
        desc="A candy-chrome two-anchor OKLab ramp broken by fine ordered dither-grain so the transition shimmers with premium micro-texture. A GRADIENTS finish."),
    "grd_chromatic_aberration": dict(structure="chromatic_aberration", palette="miami",
        name="Chromatic Aberration",  seed=7006,
        desc="The same warped miami ramp sampled at three per-channel offsets so R/G/B diverge into prismatic colour fringing — lens-edge chromatic aberration. A GRADIENTS finish."),
    "grd_spectral_sweep":       dict(structure="spectral_sweep",       palette=None,
        name="Spectral Sweep",        seed=7007,
        desc="A full-spectrum rainbow sweeping once along a warped diagonal, OKLab-smooth so the hues stay clean — a single flowing rainbow band. A GRADIENTS finish."),
    "grd_liquid_marble":        dict(structure="liquid_marble",        palette="royal",
        name="Liquid Marble",         seed=7008,
        desc="Iteratively domain-warped royal-purple veins folded into stirred-paint marbling, read off a multi-hue OKLab ramp. A GRADIENTS finish."),
    "grd_moire_interference":   dict(structure="moire_interference",   palette="chrome_ice",
        name="Moire Interference",    seed=7009,
        desc="Two crossed near-orthogonal wave fields beating into shimmering chrome-ice interference bands — a woven optical gradient. A GRADIENTS finish."),
    "grd_holo_foil":            dict(structure="holo_foil",            palette=None,
        name="Holo Foil",             seed=7010,
        desc="Fine repeated diagonal rainbow strips with a crossing sheen band — a holographic foil catching light. A GRADIENTS finish."),
    "grd_radial_burst":         dict(structure="radial_burst",         palette="molten",
        name="Radial Burst",          seed=7011,
        desc="Molten colour swept by angle around a point with a bright radial burst falling off outward — a starburst gradient. A GRADIENTS finish."),
}

GROUP = "🌈 GRADIENTS"
GROUPS = {GROUP: GRAD_FINISHES}

# id -> recipe (single group, but keep the themes-style ALL for parity).
ALL = dict(GRAD_FINISHES)


def _seed_int(seed):
    try:
        return int(seed)
    except Exception:
        return abs(hash(str(seed))) % (2 ** 31)


def _art(d, work):
    """Work-res art (HxWx3 float 0..1). Built-in-spectrum structures take no palette kwarg."""
    fn = gm.GRADIENT_STRUCTURES[d["structure"]]
    seed = _seed_int(d["seed"])
    if d["structure"] in _NO_PALETTE or d.get("palette") is None:
        field = fn((work, work), seed)
    else:
        field = fn((work, work), seed, palette=d["palette"])
    return np.clip(np.asarray(field, np.float32), 0.0, 1.0)


@lru_cache(maxsize=16)
def _art_cached(fid):
    return _art(ALL[fid], _WORK)


def _mask2(mask, fh, fw):
    m2 = np.asarray(mask, np.float32)
    if m2.ndim == 3:
        m2 = m2[:, :, 0]
    if m2.shape[:2] != (fh, fw):
        m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
    return m2


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = _mask2(mask, fh, fw)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        out = src * (1.0 - kk) + art * kk
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = _mask2(mask, fh, fw)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        # GRADIENT DEFAULT SPEC: smooth glossy clearcoat sheen tracing the gradient's bright bands;
        # lower ignition / decorrelation than the FRACTURED finishes = clean gloss, not a hard flame.
        return fracture_spec(art, m2, ignition=0.7, decorrelation=0.15, as_uint8=True)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register every GRADIENTS finish into the monolithic + both FUSION registries (mirrors themes)."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    n = 0
    for fid in ALL:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    return f"gradients: {n} finishes live ({GROUP.split(' ', 1)[-1]}:{n})"


# ── representative swatch hex per finish (palette mid-stop; built-in spectrum -> spectrum mid) ──
def _hex(rgb01):
    r, g, b = (int(round(max(0.0, min(1.0, c)) * 255)) for c in rgb01)
    return f"#{r:02x}{g:02x}{b:02x}"


def _palette_mid_rgb(palette):
    if palette is None:
        stops = gm._SPECTRUM
    else:
        stops = gm.PALETTES[palette]
    # the stop nearest t=0.5 is the most representative "look" colour
    best = min(stops, key=lambda s: abs(s[0] - 0.5))
    return best[1]


def swatch_hex(fid):
    """Representative hex for the picker swatch — the palette's mid-stop colour."""
    return _hex(_palette_mid_rgb(ALL[fid].get("palette")))


# swatch id scheme: 'grad_<structure>__<palette>' (palette 'spectrum' for the built-in-ramp ones).
def swatch_id(fid):
    d = ALL[fid]
    pal = d.get("palette") or "spectrum"
    return f"grad_{d['structure']}__{pal}"
