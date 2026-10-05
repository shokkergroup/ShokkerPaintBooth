"""FLAME SPEC-MAP RECIPES — the validated catalog of flame paint + spec finishes (2026-06-18).

This module is DATA-DRIVEN (AI-as-compiler): there is NO bespoke per-finish code. It is a single
RECIPES table — one row per VALIDATED (flame, mode, palette, params) combo — plus ONE generic helper
that turns a row into a finished (paint, spec) pair by calling:

  * engine.paint_v2.flame_math.FLAME_STRUCTURES[flame]((H,W), seed)  -> HxWx3 float albedo (PAINT)
  * engine.paint_v2.flame_spec.spec_{ignite,topo,dance}(paint, palette=..., **params) -> HxWx3 uint8 spec

Every recipe here PASSED its gates (spec_traces_paint >= 0.5, spec_iron_safe True, render < 3s @2048)
in the validated batch. The 6 topo@layers=3 recipes that only failed the >3s budget on the recording
machine were DROPPED here (they're machine-dependent; see regression test notes).

ADDITIVE ONLY — this module imports the existing flame_math + flame_spec and does not mutate them, nor
is it wired into the live catalog/picker (owner-gated). Nothing here registers a finish.

PUBLIC SURFACE:
  RECIPES                                  list[dict]  (flame, mode, palette, params, trace, recipe_id)
  MODES                                    ('ignite','topo','dance')
  recipe_id(flame, mode, palette)          -> "flame__mode__palette"
  get_recipe(recipe_id)                    -> dict | None
  render_flame_spec_finish(flame, mode, palette='classic', *, size=2048, seed=7, **params)
                                           -> (paint HxWx3 float 0..1, spec HxWx3 uint8 R=M,G=R,B=Cc)
  render_recipe(recipe, *, size=2048, seed=7)  -> (paint, spec)   convenience for a RECIPES row
"""
from __future__ import annotations

MODES = ("ignite", "topo", "dance")

# ---------------------------------------------------------------------------------------------------
# THE CATALOG. Each row is a validated finish. `params` are the spec_* kwargs (frac/strength/layers);
# `trace` is the spec_traces_paint score recorded + independently re-verified at 2048². AI-as-compiler:
# adding a finish = adding a row, never new code.
# ---------------------------------------------------------------------------------------------------
RECIPES = [
    dict(flame='tongues', mode='ignite', palette='classic', params={'frac': 'auto', 'strength': 1.0}, trace=0.907),
    dict(flame='tongues', mode='topo', palette='classic', params={'layers': 2}, trace=0.868),
    dict(flame='tongues', mode='dance', palette='classic', params={}, trace=0.902),
    dict(flame='cellular_embers', mode='ignite', palette='classic', params={'frac': 'auto', 'strength': 1.0}, trace=0.974),
    dict(flame='cellular_embers', mode='dance', palette='classic', params={}, trace=0.953),
    dict(flame='curl_streamers', mode='ignite', palette='blue', params={'frac': 'auto', 'strength': 1.0}, trace=0.986),
    dict(flame='curl_streamers', mode='topo', palette='violet', params={'layers': 2}, trace=0.864),
    dict(flame='curl_streamers', mode='dance', palette='blue', params={}, trace=0.945),
    dict(flame='radial', mode='ignite', palette='spectral', params={'frac': 'auto', 'strength': 1.0}, trace=0.905),
    dict(flame='radial', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.79),
    dict(flame='radial', mode='dance', palette='spectral', params={}, trace=0.875),
    dict(flame='vortex_spiral', mode='ignite', palette='blue', params={'frac': 'auto', 'strength': 1.0}, trace=0.985),
    dict(flame='vortex_spiral', mode='topo', palette='blue', params={'layers': 2}, trace=0.855),
    dict(flame='vortex_spiral', mode='dance', palette='blue', params={}, trace=0.965),
    dict(flame='dragon_jet', mode='ignite', palette='classic', params={'frac': 'auto', 'strength': 1.0}, trace=0.987),
    dict(flame='dragon_jet', mode='topo', palette='classic', params={'layers': 2}, trace=0.847),
    dict(flame='dragon_jet', mode='dance', palette='classic', params={}, trace=0.963),
    dict(flame='interference_wisps', mode='ignite', palette='blue', params={'frac': 'auto', 'strength': 1.0}, trace=0.899),
    dict(flame='interference_wisps', mode='topo', palette='blue', params={'layers': 2}, trace=0.688),
    dict(flame='interference_wisps', mode='dance', palette='blue', params={}, trace=0.771),
    dict(flame='metaball_plumes', mode='ignite', palette='classic', params={'frac': 'auto', 'strength': 1.0}, trace=0.938),
    dict(flame='metaball_plumes', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.831),
    dict(flame='metaball_plumes', mode='dance', palette='white_hot', params={}, trace=0.904),
    dict(flame='candle', mode='ignite', palette='white_hot', params={'frac': 'auto', 'strength': 1.0}, trace=0.979),
    dict(flame='candle', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.966),
    dict(flame='candle', mode='dance', palette='white_hot', params={}, trace=0.932),
    dict(flame='ember_storm', mode='ignite', palette='spectral', params={'frac': 'auto', 'strength': 1.0}, trace=0.951),
    dict(flame='ember_storm', mode='topo', palette='spectral', params={'layers': 2}, trace=0.797),
    dict(flame='ember_storm', mode='dance', palette='spectral', params={}, trace=0.942),
    dict(flame='will_o_wisp', mode='ignite', palette='violet', params={'frac': 'auto', 'strength': 1.0}, trace=0.993),
    dict(flame='will_o_wisp', mode='topo', palette='violet', params={'layers': 2}, trace=0.83),
    dict(flame='will_o_wisp', mode='dance', palette='violet', params={}, trace=0.981),
    dict(flame='reaction_diffusion', mode='ignite', palette='green_toxic', params={'frac': 'auto', 'strength': 1.0}, trace=0.67),
    dict(flame='reaction_diffusion', mode='topo', palette='blue', params={'layers': 2}, trace=0.617),
    dict(flame='reaction_diffusion', mode='dance', palette='white_hot', params={}, trace=0.61),
    dict(flame='gas_ring', mode='ignite', palette='blue', params={'frac': 'auto', 'strength': 1.0}, trace=0.961),
    dict(flame='gas_ring', mode='topo', palette='blue', params={'layers': 2}, trace=0.904),
    dict(flame='gas_ring', mode='dance', palette='blue', params={}, trace=0.9),
    dict(flame='plasma_arc', mode='ignite', palette='white_hot', params={'frac': 'auto', 'strength': 1.0}, trace=0.87),
    dict(flame='plasma_arc', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.857),
    dict(flame='solar_flare', mode='ignite', palette='white_hot', params={'frac': 'auto', 'strength': 1.0}, trace=0.985),
    dict(flame='solar_flare', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.748),
    dict(flame='solar_flare', mode='dance', palette='white_hot', params={}, trace=0.926),
    dict(flame='lava_flow', mode='ignite', palette='classic', params={'frac': 'auto', 'strength': 1.0}, trace=0.98),
    dict(flame='lava_flow', mode='topo', palette='classic', params={'layers': 2}, trace=0.959),
    dict(flame='lava_flow', mode='dance', palette='classic', params={}, trace=0.964),
    dict(flame='ferro_spikes', mode='ignite', palette='violet', params={'frac': 'auto', 'strength': 1.0}, trace=0.986),
    dict(flame='ferro_spikes', mode='topo', palette='blue', params={'layers': 2}, trace=0.968),
    dict(flame='ferro_spikes', mode='dance', palette='violet', params={}, trace=0.957),
    dict(flame='backdraft_rings', mode='ignite', palette='green_toxic', params={'frac': 'auto', 'strength': 1.0}, trace=0.866),
    dict(flame='backdraft_rings', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.783),
    dict(flame='backdraft_rings', mode='dance', palette='blue', params={}, trace=0.823),
    dict(flame='spark_fountain', mode='ignite', palette='white_hot', params={'frac': 'auto', 'strength': 1.0}, trace=0.949),
    dict(flame='spark_fountain', mode='dance', palette='white_hot', params={}, trace=0.829),
    dict(flame='corona_rays', mode='ignite', palette='white_hot', params={'strength': 1.15}, trace=0.942),
    dict(flame='corona_rays', mode='dance', palette='white_hot', params={}, trace=0.795),
    dict(flame='votive_field', mode='ignite', palette='white_hot', params={'frac': 0.18, 'strength': 1.1}, trace=0.992),
    dict(flame='votive_field', mode='dance', palette='white_hot', params={}, trace=0.967),
    dict(flame='meteor_shower', mode='ignite', palette='white_hot', params={'frac': 0.18, 'strength': 1.1}, trace=0.986),
    dict(flame='meteor_shower', mode='topo', palette='spectral', params={'layers': 3}, trace=0.983),
    dict(flame='meteor_shower', mode='dance', palette='white_hot', params={}, trace=0.97),
    dict(flame='smoke_billow', mode='ignite', palette='blue', params={'strength': 1.15}, trace=0.988),
    dict(flame='smoke_billow', mode='dance', palette='violet', params={}, trace=0.965),
    dict(flame='pahoehoe_rope', mode='ignite', palette='classic', params={}, trace=0.837),
    dict(flame='pahoehoe_rope', mode='dance', palette='classic', params={}, trace=0.658),
    dict(flame='napalm_drips', mode='ignite', palette='classic', params={'frac': 0.18, 'strength': 1.1}, trace=0.977),
    dict(flame='napalm_drips', mode='dance', palette='classic', params={}, trace=0.931),
    dict(flame='magma_bubbles', mode='ignite', palette='classic', params={}, trace=0.609),
    dict(flame='magma_bubbles', mode='topo', palette='white_hot', params={'layers': 3}, trace=0.588),
    dict(flame='marble_swirl', mode='ignite', palette='blue', params={}, trace=0.884),
    dict(flame='marble_swirl', mode='topo', palette='blue', params={'layers': 3}, trace=0.723),
    dict(flame='marble_swirl', mode='dance', palette='blue', params={}, trace=0.786),
    dict(flame='dragon_scale', mode='ignite', palette='classic', params={'frac': 0.24, 'strength': 1.0}, trace=0.866),
    dict(flame='dragon_scale', mode='topo', palette='violet', params={'layers': 2}, trace=0.804),
    dict(flame='dragon_scale', mode='dance', palette='classic', params={}, trace=0.847),
    dict(flame='caustic_web', mode='ignite', palette='blue', params={'frac': 0.18, 'strength': 1.1}, trace=0.657),
    dict(flame='caustic_web', mode='dance', palette='white_hot', params={}, trace=0.682),
    dict(flame='obsidian_fracture', mode='ignite', palette='white_hot', params={'frac': 0.2, 'strength': 1.1}, trace=0.972),
    dict(flame='obsidian_fracture', mode='dance', palette='violet', params={}, trace=0.946),
    dict(flame='basalt_columns', mode='ignite', palette='classic', params={'frac': 0.22, 'strength': 1.0}, trace=0.814),
    dict(flame='basalt_columns', mode='topo', palette='classic', params={'layers': 2}, trace=0.738),
    dict(flame='basalt_columns', mode='dance', palette='green_toxic', params={}, trace=0.746),
    dict(flame='eruption_column', mode='ignite', palette='classic', params={'frac': 0.26, 'strength': 1.05}, trace=0.972),
    dict(flame='eruption_column', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.84),
    dict(flame='eruption_column', mode='dance', palette='classic', params={}, trace=0.959),
    dict(flame='heat_mirage', mode='ignite', palette='spectral', params={'frac': 0.22, 'strength': 1.15}, trace=0.714),
    dict(flame='heat_mirage', mode='dance', palette='spectral', params={}, trace=0.67),
    dict(flame='spiral_galaxy', mode='ignite', palette='violet', params={'frac': 0.2, 'strength': 1.1}, trace=0.967),
    dict(flame='spiral_galaxy', mode='topo', palette='violet', params={'layers': 2}, trace=0.762),
    dict(flame='spiral_galaxy', mode='dance', palette='blue', params={}, trace=0.946),
    dict(flame='aurora_drape', mode='ignite', palette='green_toxic', params={'frac': 0.24, 'strength': 1.0}, trace=0.921),
    dict(flame='aurora_drape', mode='topo', palette='green_toxic', params={'layers': 2}, trace=0.771),
    dict(flame='aurora_drape', mode='dance', palette='green_toxic', params={}, trace=0.875),
    dict(flame='kaleidoscope', mode='ignite', palette='spectral', params={'frac': 0.16, 'strength': 1.05}, trace=0.857),
    dict(flame='kaleidoscope', mode='topo', palette='spectral', params={'layers': 2}, trace=0.793),
    dict(flame='kaleidoscope', mode='dance', palette='violet', params={}, trace=0.898),
    dict(flame='basket_weave', mode='ignite', palette='classic', params={'frac': 0.3, 'strength': 1.2}, trace=0.955),
    dict(flame='basket_weave', mode='topo', palette='classic', params={'layers': 2}, trace=0.857),
    dict(flame='basket_weave', mode='dance', palette='classic', params={}, trace=0.931),
    dict(flame='lightning_storm', mode='ignite', palette='blue', params={'frac': 'auto', 'strength': 1.0}, trace=0.989),
    dict(flame='lightning_storm', mode='topo', palette='blue', params={'layers': 2}, trace=0.975),
    dict(flame='lightning_storm', mode='dance', palette='blue', params={}, trace=0.974),
    dict(flame='fire_rose', mode='ignite', palette='classic', params={'frac': 0.22, 'strength': 1.15}, trace=0.97),
    dict(flame='fire_rose', mode='topo', palette='classic', params={'layers': 2}, trace=0.838),
    dict(flame='fire_rose', mode='dance', palette='classic', params={}, trace=0.899),
    dict(flame='mammatus', mode='ignite', palette='white_hot', params={'frac': 0.3, 'strength': 1.2}, trace=0.973),
    dict(flame='mammatus', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.786),
    dict(flame='mammatus', mode='dance', palette='white_hot', params={}, trace=0.902),
    dict(flame='spider_web', mode='ignite', palette='violet', params={'frac': 0.3, 'strength': 1.2}, trace=0.978),
    dict(flame='spider_web', mode='topo', palette='violet', params={'layers': 2}, trace=0.856),
    dict(flame='spider_web', mode='dance', palette='violet', params={}, trace=0.942),
    dict(flame='mach_cone', mode='ignite', palette='spectral', params={'frac': 'auto', 'strength': 1.0}, trace=0.931),
    dict(flame='mach_cone', mode='topo', palette='spectral', params={'layers': 2}, trace=0.838),
    dict(flame='mach_cone', mode='dance', palette='spectral', params={}, trace=0.889),
    dict(flame='quasicrystal', mode='ignite', palette='green_toxic', params={'frac': 'auto', 'strength': 1.0}, trace=0.936),
    dict(flame='quasicrystal', mode='topo', palette='green_toxic', params={'layers': 2}, trace=0.811),
    dict(flame='quasicrystal', mode='dance', palette='green_toxic', params={}, trace=0.904),
    dict(flame='crackle_glaze', mode='ignite', palette='white_hot', params={'frac': 0.3, 'strength': 1.2}, trace=0.81),
    dict(flame='crackle_glaze', mode='topo', palette='white_hot', params={'layers': 2}, trace=0.581),
    dict(flame='crackle_glaze', mode='dance', palette='white_hot', params={}, trace=0.627),
    dict(flame='chevron_herringbone', mode='ignite', palette='spectral', params={'frac': 'auto', 'strength': 1.0}, trace=0.917),
    dict(flame='chevron_herringbone', mode='topo', palette='spectral', params={'layers': 2}, trace=0.826),
    dict(flame='chevron_herringbone', mode='dance', palette='spectral', params={}, trace=0.895),
    dict(flame='fire_tornado', mode='ignite', palette='white_hot', params={'frac': 0.28, 'strength': 1.0}, trace=0.99),
    dict(flame='fire_tornado', mode='dance', palette='white_hot', params={}, trace=0.954),
    dict(flame='quilted_diamond', mode='ignite', palette='blue', params={'frac': 'auto', 'strength': 1.0}, trace=0.971),
    dict(flame='quilted_diamond', mode='dance', palette='blue', params={}, trace=0.934),
    dict(flame='vortex_street', mode='ignite', palette='white_hot', params={'frac': 0.28, 'strength': 1.0}, trace=0.988),
    dict(flame='vortex_street', mode='dance', palette='white_hot', params={}, trace=0.965),
    dict(flame='leopard_rd', mode='ignite', palette='classic', params={'frac': 'auto', 'strength': 1.0}, trace=0.918),
    dict(flame='leopard_rd', mode='dance', palette='spectral', params={}, trace=0.82),
    dict(flame='pele_strands', mode='ignite', palette='white_hot', params={'frac': 0.28, 'strength': 1.0}, trace=0.974),
    dict(flame='pele_strands', mode='dance', palette='violet', params={}, trace=0.934),
    dict(flame='tessellated_triangles', mode='ignite', palette='violet', params={'frac': 0.28, 'strength': 1.0}, trace=0.929),
    dict(flame='tessellated_triangles', mode='dance', palette='spectral', params={}, trace=0.897),
]


def recipe_id(flame, mode, palette):
    """Stable id for a finish: 'flame__mode__palette'."""
    return f"{flame}__{mode}__{palette}"


# attach the id to each row once at import (still pure data)
for _r in RECIPES:
    _r.setdefault("recipe_id", recipe_id(_r["flame"], _r["mode"], _r["palette"]))
del _r

_BY_ID = {r["recipe_id"]: r for r in RECIPES}


def get_recipe(rid):
    """Look up a recipe row by its recipe_id, or None."""
    return _BY_ID.get(rid)


# ---------------------------------------------------------------------------------------------------
# THE ONE GENERIC RENDERER. flame_math makes the PAINT; flame_spec turns it into the SPEC. No
# per-finish branching beyond dispatching the spec MODE (the three documented spec functions).
# ---------------------------------------------------------------------------------------------------
def render_flame_spec_finish(flame, mode, palette="classic", *, size=2048, seed=7, **params):
    """Render one flame finish -> (paint, spec).

    paint : HxWx3 float32 0..1 albedo, from flame_math.FLAME_STRUCTURES[flame]((size,size), seed).
            flame_math is NEVER mutated here; we only read its structures.
    spec  : HxWx3 uint8 (R=Metallic, G=Roughness, B=Clearcoat), from the matching flame_spec mode:
              ignite -> flame_spec.spec_ignite(paint, palette=..., frac=..., strength=...)
              topo   -> flame_spec.spec_topo  (paint, palette=..., layers=...)
              dance  -> flame_spec.spec_dance (paint, palette=...)

    `params` overrides the per-mode spec kwargs (frac/strength for ignite, layers for topo). Unknown
    kwargs for a mode are dropped so a RECIPES row can carry a superset safely.
    """
    import numpy as np
    from engine.paint_v2 import flame_math as fm
    from engine.paint_v2 import flame_spec as fs

    if flame not in fm.FLAME_STRUCTURES:
        raise KeyError(f"unknown flame structure {flame!r}")
    if mode not in MODES:
        raise ValueError(f"unknown spec mode {mode!r}; expected one of {MODES}")

    paint = np.asarray(fm.FLAME_STRUCTURES[flame]((int(size), int(size)), int(seed)), np.float32)

    if mode == "ignite":
        kw = {k: params[k] for k in ("frac", "strength") if k in params}
        spec = fs.spec_ignite(paint, palette=palette, **kw)
    elif mode == "topo":
        kw = {k: params[k] for k in ("layers",) if k in params}
        spec = fs.spec_topo(paint, palette=palette, **kw)
    else:  # dance
        spec = fs.spec_dance(paint, palette=palette)
    return paint, spec


def render_recipe(recipe, *, size=2048, seed=7):
    """Render a RECIPES row (a dict with flame/mode/palette/params) -> (paint, spec)."""
    return render_flame_spec_finish(
        recipe["flame"], recipe["mode"], recipe.get("palette", "classic"),
        size=size, seed=seed, **dict(recipe.get("params", {})))
