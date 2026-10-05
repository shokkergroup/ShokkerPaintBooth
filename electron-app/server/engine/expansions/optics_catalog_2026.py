"""LIGHT & OPTICS catalog (2026-06-19) — ADDITIVE expansion registering the 8 reworked optics
finishes (engine/paint_v2/optics_math.OPTICS_STRUCTURES) into the monolithic registry. Total rework
of the old Light-Waves / Spectral-Reactive colour swaps -> 8 physically-grounded optical PHENOMENA
(diffraction spiral / thin-film oil / refractive caustics / Newton's rings / prism dispersion /
moire interference / aurora veil / soap-bubble froth) on a real wavelength->sRGB spectral engine.

Mirrors neon_catalog_2026 / anime_catalog_2026: (spec_fn, paint_fn) per fid; PAINT = optics
structure blended via mask; SPEC = the assigned flame_spec mode (dance=flash / ignite=glossy /
topo=depth), iron-safe + masked. ADDITIVE ONLY — shared-file edits (finish-data.js /
shokker_engine_v2) happen separately.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.optics_math as opm
import engine.paint_v2.flame_spec as fs

_WORK = 1152
GROUP = "★ LIGHT & OPTICS"

# fid -> (structure, spec mode, display name, swatch hex, description)
OPTICS_FINISHES = {
    "optics2_dvd":      ("diffraction_dvd",     "dance",  "Diffraction Spiral",  "#ff2fa0", "A CD/DVD micro-grating spun into a log-spiral that splits white light into a spectral swirl."),
    "optics2_thinfilm": ("thin_film_oil",       "ignite", "Thin-Film Oil Slick", "#36d0ff", "Thin-film interference over a flowing film — oil-on-water iridescence, glossy and shifting."),
    "optics2_caustics": ("caustics_pool",       "topo",   "Refractive Caustics", "#7af0ff", "The bright cyan caustic web focused on a sunlit pool floor, rippling over deep teal water."),
    "optics2_newton":   ("newton_rings",        "ignite", "Newton's Rings",      "#c86cff", "Scattered lens-contact interference rings (phase proportional to r^2) overlapping into a spectral quilt."),
    "optics2_prism":    ("prism_dispersion",    "dance",  "Prism Dispersion",    "#ffd11a", "White light shot through scattered prisms, fanning into crossing spectral shafts with fine fingering."),
    "optics2_moire":    ("moire_interference",  "topo",   "Moire Interference",  "#2fff7a", "Warped line-gratings beating into organic full-spectrum moire fringes over a fine line micro-texture."),
    "optics2_aurora":   ("aurora_veil",         "dance",  "Aurora Veil",         "#34ffa0", "Flowing auroral curtains — luminous draped sheets climbing green to violet with fine ray striations."),
    "optics2_bubbles":  ("soap_bubble_cluster", "ignite", "Soap-Bubble Froth",   "#b0e8ff", "A froth of translucent soap bubbles — thin-film spheres with specular glints and bright Fresnel rims."),
    "optics2_fiber":    ("fiber_optic",         "dance",  "Fiber-Optic Bundle",  "#ff5ad0", "A bundle of glowing optical fibres — thin curl-flow strands blazing into bright point tips."),
    "optics2_holo":     ("holographic_foil",    "ignite", "Holographic Foil",    "#46ffd0", "Embossed holo-glitter foil — a fine diamond mosaic where each cell flashes its own spectral hue."),
    "optics2_lenticular":("lenticular_flip",    "ignite", "Lenticular Flip",     "#ffd14a", "A lenticular lens sheet — wavy cylindrical lenslets flipping spectral parallax bands with bright crowns."),
}


@lru_cache(maxsize=16)
def _art_work_cached(fid):
    structure = OPTICS_FINISHES[fid][0]
    art = np.asarray(opm.OPTICS_STRUCTURES[structure]((_WORK, _WORK), 7), np.float32)
    if art.ndim == 2:
        art = np.repeat(art[..., None], 3, axis=2)
    art = art[:, :, :3]
    if art.size and art.max() > 1.5:
        art = art / 255.0
    return np.clip(art, 0.0, 1.0)


def _mask2d(mask, fh, fw):
    m2 = np.asarray(mask, np.float32)
    if m2.ndim == 3:
        m2 = m2[:, :, 0]
    if m2.shape[:2] != (fh, fw):
        m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
    return m2


def _mk(fid):
    mode = OPTICS_FINISHES[fid][1]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = _mask2d(mask, fh, fw)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        out = src * (1.0 - kk) + art * kk
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = _mask2d(mask, fh, fw)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        if mode == "ignite":
            spec = fs.spec_ignite(art)
        elif mode == "topo":
            spec = fs.spec_topo(art)
        else:
            spec = fs.spec_dance(art)
        spec = np.asarray(spec, np.uint8)
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (spec.astype(np.float32) * mm).clip(0, 255).astype(np.uint8)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register every optics finish into the monolithic + FUSION registries (mirrors neon_catalog)."""
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
    for fid in OPTICS_FINISHES:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    return f"light-and-optics: {n} reworked optics finishes live"
