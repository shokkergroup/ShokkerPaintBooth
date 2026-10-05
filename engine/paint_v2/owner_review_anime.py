"""Owner-review Anime Inspired base renderers.

HISTORY OF THIS FILE:
- SPB-30: replaced the stock anime pack (oversized cells, sparse decals, simple radial math)
  with scaled-down bespoke renderers. Those scored M7 55.9–72.3 — every one below the 75 floor.
- [SPB ANIME OVERHAUL 2026-08-25] owner mandate "expand the 19 we have to 25 designs and make
  them mind melting… NO REPEATS, NO LAZINESS": the whole category was rebuilt as 25 married
  paint+spec structures in engine/paint_v2/anime_math.py (ledger: docs/ANIME_OVERHAUL_2026-08-25.md).
  engine/paint_v2/anime_style.py now wraps those structures under the original function names,
  so this override module simply re-exports the current generation. It must NOT keep frozen
  copies — that is exactly how the previous generation kept shipping after its rebuild (the
  "[Regular Base V2]" boot pass installs THESE fns over the registry, silently bypassing
  anime_style edits).

The OWNER_REVIEW_ANIME_OVERRIDES dict shape (fid -> (paint_fn, spec_fn)) is consumed by two
install sites in shokker_engine_v2.py (~15150 and ~15230).
"""

from __future__ import annotations

from engine.paint_v2.anime_style import (
    paint_anime_cel_shade_chrome, spec_anime_cel_shade_chrome,
    paint_anime_speed_lines, spec_anime_speed_lines,
    paint_anime_sparkle_burst, spec_anime_sparkle_burst,
    paint_anime_gradient_hair, spec_anime_gradient_hair,
    paint_anime_mecha_plate, spec_anime_mecha_plate,
    paint_anime_sakura_scatter, spec_anime_sakura_scatter,
    paint_anime_energy_aura, spec_anime_energy_aura,
    paint_anime_comic_halftone, spec_anime_comic_halftone,
    paint_anime_neon_outline, spec_anime_neon_outline,
    paint_anime_crystal_facet, spec_anime_crystal_facet,
)

OWNER_REVIEW_ANIME_OVERRIDES = {
    "anime_cel_shade_chrome": (paint_anime_cel_shade_chrome, spec_anime_cel_shade_chrome),
    "anime_speed_lines": (paint_anime_speed_lines, spec_anime_speed_lines),
    "anime_sparkle_burst": (paint_anime_sparkle_burst, spec_anime_sparkle_burst),
    "anime_gradient_hair": (paint_anime_gradient_hair, spec_anime_gradient_hair),
    "anime_mecha_plate": (paint_anime_mecha_plate, spec_anime_mecha_plate),
    "anime_sakura_scatter": (paint_anime_sakura_scatter, spec_anime_sakura_scatter),
    "anime_energy_aura": (paint_anime_energy_aura, spec_anime_energy_aura),
    "anime_comic_halftone": (paint_anime_comic_halftone, spec_anime_comic_halftone),
    "anime_neon_outline": (paint_anime_neon_outline, spec_anime_neon_outline),
    "anime_crystal_facet": (paint_anime_crystal_facet, spec_anime_crystal_facet),
}
