"""ANIME INSPIRED catalog — the ★ ANIME INSPIRED monolithic specials.

[SPB ANIME OVERHAUL 2026-08-25] Owner mandate: 19 → 25 mind-melting distinct designs. This
catalog carries the 15 monolithic ids (8 rebuilt concepts + 7 NEW); the other 10 live in
BASE_REGISTRY via engine/paint_v2/anime_style.py. Concept ledger + collision watchlist:
docs/ANIME_OVERHAUL_2026-08-25.md.

Changes vs the 2026-06-19 generation it replaces:
  - structures render at NATIVE resolution (the old _WORK=1152 upscale softened everything);
  - specs are MARRIED to the paint (same-geometry M/R/CC built in one pass in anime_math),
    replacing the recycled flame_spec dance/ignite/topo modes;
  - the 8 old fids keep their ids but get genuinely different rebuilt concepts so they no
    longer collide with the 10 base-registry anime finishes (e.g. anime2_crystal is now an
    anime-eye iris field, not a second voronoi crystal).

ADDITIVE ONLY — shared-file edits (finish-data.js / shokker_engine_v2) happen separately.
"""
from __future__ import annotations

import cv2
import numpy as np

import engine.paint_v2.anime_math as am

GROUP = "★ ANIME INSPIRED"
_SEED = 7   # fixed: keeps paint+spec married and lets am.build's cache serve both channels

# fid -> (anime_math structure key, display name, swatch hex, description)
ANIME_FINISHES = {
    "anime2_cel_shade":     ("cel_cloud_sea",   "Cel Cloud Sea",      "#7fb6f2", "A Ghibli sky-sea — stratified cel-shaded cloud decks with ink rims, sun stipple and tiny birds."),
    "anime2_screentone":    ("impact_frames",   "Impact Frames",      "#1a1a1a", "Manga impact-burst cells — jagged spike outlines, B/W flash sectors, halftone interiors, yellow flashes."),
    "anime2_sakura":        ("hanami_night",    "Hanami Night",       "#ff9e5e", "Festival night — glowing ribbed paper lanterns on strings, firefly bokeh, branch silhouettes, drifting petals."),
    "anime2_mecha":         ("mecha_hologrid",  "Mecha Hologrid",     "#22d4e8", "Holographic CAD space — depth-faded grids, wireframe primitives, targeting reticles, scan sweep."),
    "anime2_speed_lines":   ("shuriken_storm",  "Shuriken Storm",     "#aab4c4", "A blade blizzard — concave 4-point shuriken with spin trails, kunai, embed cracks, crimson ribbons."),
    "anime2_energy_aura":   ("raiton_lightning","Raiton Lightning",   "#54d8ff", "A dendritic lightning nest — stepped zigzag bolts, white-hot cores in cyan sheaths, mauve echo strikes."),
    "anime2_crystal":       ("iris_gem_field",  "Iris Gem Field",     "#9b5cff", "A field of anime-eye irises — radial fibers, limbal rings, jewel heterochromia, window catchlights."),
    "anime2_gradient_hair": ("holo_idol_foil",  "Holo Idol Foil",     "#d24cff", "Idol-sticker holo foil — warped rainbow interference, micro-prism facets, star and heart confetti."),
    "anime2_kanji_rain":    ("kanji_rain",      "Kanji Rain",         "#b8332a", "Columns of brush-stroke glyphs raining down washi — sumi ink, vermillion accents, hanko seals."),
    "anime2_onomatopoeia":  ("onomatopoeia",    "Onomatopoeia Riot",  "#ffd91a", "A comic sound-effect riot — jagged double-outline bursts, halftone shading, slash marks, action dashes."),
    "anime2_glitch":        ("cyber_glitch",    "Cyber Glitch",       "#ff1aa6", "Digital dissolve — displaced RGB-split slices, pixel-sort streaks, corrupted neon block mosaics."),
    "anime2_broadcast":     ("retro_broadcast", "Retro Broadcast",    "#e8734a", "A CRT transmission — phosphor triads, scanlines, interlace jitter, ghosting, static bursts, test bars."),
    "anime2_blood_moon":    ("blood_moon",      "Blood Moon Eclipse", "#a61e14", "A sky multiplied with eclipse moons — cel-banded craters, bright rim arcs, crossing cloud wisps, flocks."),
    "anime2_oni_sumi":      ("oni_sumi",        "Oni Sumi-e",         "#2b2226", "Demon-mask brushwork — dry-bristle horn and fang strokes, enso rings, ink mist, vermillion hanko."),
    "anime2_manga_page":    ("manga_page",      "Manga Page Chaos",   "#f2f0e8", "An exploded manga spread — recursive panels, ink gutters, every panel a different screentone story."),
}


def _mask2d(mask, fh, fw):
    m2 = np.asarray(mask, np.float32)
    if m2.ndim == 3:
        m2 = m2[:, :, 0]
    if m2.shape[:2] != (fh, fw):
        m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
    return m2


def _mk(fid):
    key = ANIME_FINISHES[fid][0]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = _mask2d(mask, fh, fw)
        art = am.build(key, (fh, fw), _SEED)["rgb"]
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        out = src * (1.0 - kk) + art * kk
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = _mask2d(mask, fh, fw)
        spec = am.build(key, (fh, fw), _SEED)["spec"]
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (spec * mm).clip(0, 255).astype(np.uint8)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register every anime finish into the monolithic + FUSION registries (mirrors neon_catalog)."""
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
    for fid in ANIME_FINISHES:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    return f"anime-inspired: {n} overhauled anime finishes live (2026-08-25 gen)"
