"""
engine/paint_v2/money_shokk_antigravity.py — ★ MONEY SHOKK (Antigravity bake-off entry)
=================================================================================
Antigravity entry in the 2026-05-27 four-way MONEY SHOKK bake-off.

V2 rebuild pass: applies the V1 rating post-mortem doctrine.
- Green bases and dead white-flashes are replaced by deep, highly saturated
  blue/indigo/sapphire albedo bases.
- Spatial frequency is tightened (0.30x–0.34x scale) to remain below the human visual resolution floor.
- Large saturation and brightness adjustments (+8.0 sat, +10.0 bri) are added as a reserve
  to prevent spec highlights from turning into dead white/grey glare.
- Fuji Neon Crest applies the owner's exact doctored values (hue 96.0, brightness 23.0).
- Keeps canary_gris_gris (7) and cherry_blossom_flux (7) exactly as-is.
"""
from __future__ import annotations

from engine.paint_v2.money_shokk import _make_money_shokk

__all__ = ["MONEY_SHOKK_ANTIGRAVITY_BASE_REGISTRY"]

_SEED_BASE = 9800

_MSHA_ROWS = [
    dict(
        id="msha_canary_gris_gris",
        seed_off=_SEED_BASE,
        pf_id="pf_bright_canary_glass",
        spec_id="midnight_gris_gris",
        hue_deg=-155.0,
        spec_scale=0.35,
        sat_adj=0.0,
        bri_adj=5.0,
        desc="MONEY SHOKK Canary Gris-Gris — electric indigo-blue base with soft pearlescent amethyst crystal shift. (V1 KEEP: rated 7)",
    ),
    dict(
        id="msha_emerald_brocade",
        seed_off=_SEED_BASE + 1,
        pf_id="pf_bright_canary_glass",
        spec_id="shogun_scale_brocade",
        hue_deg=-167.0,
        spec_scale=0.32,
        sat_adj=8.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Emerald Brocade V2 — electric blue body, vibrant gold-coral samurai-armor scale reveal under Direct Sun. (V1 REBUILD: rated 3)",
    ),
    dict(
        id="msha_fuji_neon_crest",
        seed_off=_SEED_BASE + 2,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="fuji_frost_crest",
        hue_deg=96.0,
        spec_scale=0.33,
        sat_adj=6.0,
        bri_adj=23.0,
        desc="MONEY SHOKK Fuji Neon Crest V2 — ice-blue body with electric ice-blue and soft purple cloud transitions. (V1 REBUILD: rated 7, owner doctored)",
    ),
    dict(
        id="msha_volcanic_croc",
        seed_off=_SEED_BASE + 3,
        pf_id="pf_bright_canary_glass",
        spec_id="croc_delta_armor",
        hue_deg=-165.0,
        spec_scale=0.33,
        sat_adj=8.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Volcanic Croc V2 — sapphire-blue body shifting to molten lava gold plates under glancing angles. (V1 REBUILD: rated 5)",
    ),
    dict(
        id="msha_cherry_blossom_flux",
        seed_off=_SEED_BASE + 4,
        pf_id="pf_bright_magenta_arc",
        spec_id="sakura_static",
        hue_deg=-125.0,
        spec_scale=0.36,
        sat_adj=0.0,
        bri_adj=5.0,
        desc="MONEY SHOKK Cherry Blossom Flux — intense sky-teal body blooming cherry-blossom pink under direct solar rays. (V1 KEEP: rated 7)",
    ),
    dict(
        id="msha_waxen_voodoo",
        seed_off=_SEED_BASE + 5,
        pf_id="pf_bright_magenta_arc",
        spec_id="candle_wax_veve",
        hue_deg=-135.0,
        spec_scale=0.32,
        sat_adj=8.0,
        bri_adj=11.0,
        desc="MONEY SHOKK Waxen Voodoo V2 — royal indigo body, shimmering gold waxen veve highlights under solar glare. (V1 REBUILD: rated 4)",
    ),
    dict(
        id="msha_hyperpink_threads",
        seed_off=_SEED_BASE + 6,
        pf_id="pf_bright_magenta_arc",
        spec_id="pins_and_thread",
        hue_deg=-120.0,
        spec_scale=0.32,
        sat_adj=8.0,
        bri_adj=12.0,
        desc="MONEY SHOKK Hyperpink Threads V2 — sapphire-blue body with golden micro-thread grid reveals that sparkle under motion. (V1 REBUILD: rated 3)",
    ),
    dict(
        id="msha_peach_burlap",
        seed_off=_SEED_BASE + 7,
        pf_id="pf_bright_canary_glass",
        spec_id="bayou_hex_burlap",
        hue_deg=-160.0,
        spec_scale=0.33,
        sat_adj=8.0,
        bri_adj=11.0,
        desc="MONEY SHOKK Peach Burlap V2 — deep royal indigo body, shifting copper-gold hex burlap weave under glancing light. (V1 REBUILD: rated 4)",
    ),
    dict(
        id="msha_seafoam_charm",
        seed_off=_SEED_BASE + 8,
        pf_id="pf_bright_cerulean_pop",
        spec_id="swamp_charm_patina",
        hue_deg=-140.0,
        spec_scale=0.32,
        sat_adj=8.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Seafoam Charm V2 — royal blue-indigo body, shifting emerald-patina charms under glancing sunlight. (V1 REBUILD: rated 5)",
    ),
    dict(
        id="msha_solar_moss",
        seed_off=_SEED_BASE + 9,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="spanish_moss_static",
        hue_deg=100.0,
        spec_scale=0.31,
        sat_adj=8.0,
        bri_adj=12.0,
        desc="MONEY SHOKK Solar Moss V2 — deep blue-violet base shifting to glowing neon-green moss sparkles (neon ground-effect). (V1 REBUILD: rated 4)",
    ),
]

MONEY_SHOKK_ANTIGRAVITY_BASE_REGISTRY: dict[str, dict] = {}
for _row in _MSHA_ROWS:
    _fid = _row["id"]
    _cfg = {k: v for k, v in _row.items() if k != "id"}
    _cfg["finish_id"] = _fid
    _paint, _spec = _make_money_shokk(**_cfg)
    MONEY_SHOKK_ANTIGRAVITY_BASE_REGISTRY[_fid] = {
        "base_spec_fn": _spec,
        "M": 180,
        "R": 80,
        "CC": 60,
        "paint_fn": _paint,
        "desc": _row["desc"],
    }

assert len(MONEY_SHOKK_ANTIGRAVITY_BASE_REGISTRY) == 10
