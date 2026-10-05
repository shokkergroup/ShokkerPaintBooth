"""GRADIENT finishes expansion (2026-06-18) — 🌈 GRADIENTS group, 11 finishes.

ADDITIVE expansion (mirrors fractured_themes_2026): registers the gradient finishes
(engine.paint_v2.gradient_math.GRADIENT_STRUCTURES x ONE curated palette each) into the monolithic
registry + both FUSION registries.

FINISH SET = 11 finishes = the 11 GRADIENT_STRUCTURES, one curated palette per structure (NOT the
11x11 = 121 cross product). HARD reason: scripts/spb_uniqueness_gate.py is COLOR-INDEPENDENT (luma
pHash + structural descriptor), so the same structure under a different palette = same luma layout =
>80% similar = FAIL. gradient_math.gradient_similarity is colour-AWARE (same-structure / diff-palette
~0.6, distinct) but that gate does NOT run at booth runtime — the catalog uniqueness gate is the
ship gate and it is colour-blind. One palette per structure therefore guarantees zero intra-group
structural collisions (and 11 is the clean count to eyeball-test the engine without near-dup clutter).

CURATED structure->palette pairings (max visual spread; the two warped-diagonal lookalikes —
oklab_flow & chromatic_aberration — get different palettes so they don't read as a pair):
  oklab_flow->sunset_drift, iridescent->oilslick, ridged_contour->deep_sea, mesh_bleed->aurora,
  duotone_grain->candy_chrome, chromatic_aberration->miami, spectral_sweep->(built-in _SPECTRUM),
  liquid_marble->royal, moire_interference->chrome_ice, holo_foil->(built-in _SPECTRUM),
  radial_burst->molten. (spectral_sweep & holo_foil take no palette kwarg — called without palette.)

paint_fn renders the structure blended via mask*pm; spec_fn returns the clean glossy GRADIENT DEFAULT
SPEC (fracture_spec at ignition=0.7, decorrelation=0.15 — a clearcoat sheen that follows the
gradient's bright bands with calm matte troughs). Recipe schema + install mirror the themed pattern.

The implementation lives in gradients_catalog_2026 (the _mk / install_into_engine machine); this
module is the stable public expansion entry that re-exports it (parity with fractured_themes_2026).
"""
from __future__ import annotations

from engine.expansions.gradients_catalog_2026 import (  # noqa: F401  (re-exported public API)
    ALL,
    GRAD_FINISHES,
    GROUP,
    GROUPS,
    install_into_engine,
    swatch_hex,
    swatch_id,
)

__all__ = [
    "ALL",
    "GRAD_FINISHES",
    "GROUP",
    "GROUPS",
    "install_into_engine",
    "swatch_hex",
    "swatch_id",
]
