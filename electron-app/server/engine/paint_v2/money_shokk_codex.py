"""
engine/paint_v2/money_shokk_codex.py - MONEY SHOKK (Codex bake-off entry)
============================================================================

Codex entry in the 2026-05-27 MONEY SHOKK bake-off.

SPB-CCB / Codex 2026-05-27
Owner verdict snippet: "We STRIVE to get color changing finishes in SPB. I may
have accidentally stumbled onto something... YOUR 10 best MONEY SHOKK finishes."
Metric movement: V1 owner ratings logged in COLOR_CHANGE_BREAKTHROUGH.html.
M7 rows still unavailable until the generated scorecard includes MONEY SHOKK.
V2 rebuilds keep the two owner-approved Codex winners and move the eight
REBUILD entries into the blue/indigo + colored flare window proven by V1.

Design thesis:
  * This is not a coverage set. It is a trophy set.
  * Reuse the strongest overlays when they are the best fit. Customers do not
    care whether an overlay was already used in another AI entry; they care
    whether the truck visibly changes color in sunlight.
  * Keep scale tight (0.30x-0.38x), hue rotation decisive, and brightness
    positive (+10 to +14 on rebuilds) so highlights tint instead of whitewashing.
"""
from __future__ import annotations

from engine.paint_v2.money_shokk import _make_money_shokk

__all__ = ["MONEY_SHOKK_CODEX_BASE_REGISTRY"]

_SEED_BASE = 9820


_MSHX_ROWS = [
    dict(
        id="mshx_blueprint_jackpot",
        seed_off=_SEED_BASE,
        pf_id="pf_bright_canary_glass",
        spec_id="coffin_nail_rust",
        hue_deg=-160.0,
        spec_scale=0.30,
        sat_adj=10.0,
        bri_adj=12.0,
        desc=(
            "MONEY SHOKK Blueprint Jackpot V2 - owner V1 3/REBUILD 'fairly weak'; "
            "tighter coffin gates, stronger blue-indigo landing, and brighter lavender/pink flare."
        ),
    ),
    dict(
        id="mshx_venom_cashmere",
        seed_off=_SEED_BASE + 1,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="tiger_fang_fracture",
        hue_deg=100.0,
        spec_scale=0.31,
        sat_adj=8.0,
        bri_adj=14.0,
        desc=(
            "MONEY SHOKK Venom Cashmere V2 - owner V1 4/REBUILD white flashes; "
            "ice-blue/purple body with colored fang glints instead of gray glare."
        ),
    ),
    dict(
        id="mshx_glacier_pinkslip",
        seed_off=_SEED_BASE + 2,
        pf_id="pf_bright_magenta_arc",
        spec_id="sharkbite_riptide",
        hue_deg=-118.0,
        spec_scale=0.32,
        sat_adj=8.0,
        bri_adj=12.0,
        desc=(
            "MONEY SHOKK Glacier Pinkslip V2 - owner V1 3/REBUILD dull transition; "
            "Prism Tipjar-derived sapphire body with sharkbite pink/ice flare."
        ),
    ),
    dict(
        id="mshx_lime_afterburner",
        seed_off=_SEED_BASE + 3,
        pf_id="pf_bright_lime_voltage",
        spec_id="scorpion_ember_hex",
        hue_deg=-160.0,
        spec_scale=0.30,
        sat_adj=10.0,
        bri_adj=12.0,
        desc=(
            "MONEY SHOKK Lime Afterburner V2 - owner V1 5/REBUILD had hotspots but weaker; "
            "deeper blue-purple landing with denser copper ember cells."
        ),
    ),
    dict(
        id="mshx_miami_blacklight",
        seed_off=_SEED_BASE + 4,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="widow_web_venom",
        hue_deg=96.0,
        spec_scale=0.31,
        sat_adj=8.0,
        bri_adj=14.0,
        desc=(
            "MONEY SHOKK Miami Blacklight V2 - owner V1 3/REBUILD no real color coming through; "
            "neon-ice substrate with magenta widow-web flare baked in."
        ),
    ),
    dict(
        id="mshx_royal_sunstroke",
        seed_off=_SEED_BASE + 5,
        pf_id="pf_bright_canary_glass",
        spec_id="kyoto_lantern_filigree",
        hue_deg=-160.0,
        spec_scale=0.31,
        sat_adj=10.0,
        bri_adj=12.0,
        desc=(
            "MONEY SHOKK Royal Sunstroke V2 - owner V1 3/REBUILD boring; "
            "canary-to-indigo base with champagne/pink Kyoto pin bloom."
        ),
    ),
    dict(
        id="mshx_kintsugi_ransom",
        seed_off=_SEED_BASE + 6,
        pf_id="pf_bright_orchid_pulse",
        spec_id="kintsugi_rift",
        hue_deg=-145.0,
        spec_scale=0.33,
        sat_adj=0.0,
        bri_adj=6.0,
        desc=(
            "MONEY SHOKK Kintsugi Ransom - orchid energy becomes teal-night "
            "paint with pale-gold fracture flashes that read expensive fast."
        ),
    ),
    dict(
        id="mshx_coral_sharkskin",
        seed_off=_SEED_BASE + 7,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="piranha_frenzy_current",
        hue_deg=96.0,
        spec_scale=0.32,
        sat_adj=8.0,
        bri_adj=14.0,
        desc=(
            "MONEY SHOKK Coral Sharkskin V2 - owner V1 3/REBUILD weak reveal; "
            "owner-proven blue-base direction with hot piranha current scratches."
        ),
    ),
    dict(
        id="mshx_dover_jackpot",
        seed_off=_SEED_BASE + 8,
        pf_id="pf_bright_solar_daffodil",
        spec_id="bayou_smoke_script",
        hue_deg=-160.0,
        spec_scale=0.30,
        sat_adj=10.0,
        bri_adj=12.0,
        desc=(
            "MONEY SHOKK Dover Jackpot V2 - owner V1 3/REBUILD not much shifting; "
            "darker indigo Dover body with tighter violet/pink smoke-script payout."
        ),
    ),
    dict(
        id="mshx_prism_tipjar",
        seed_off=_SEED_BASE + 9,
        pf_id="pf_bright_magenta_arc",
        spec_id="rising_sun_prismwave",
        hue_deg=-118.0,
        spec_scale=0.38,
        sat_adj=0.0,
        bri_adj=5.0,
        desc=(
            "MONEY SHOKK Prism Tipjar - magenta arc becomes sapphire-teal, then "
            "tips warm orange/pink from prismwave micro-crowns in motion."
        ),
    ),
]


MONEY_SHOKK_CODEX_BASE_REGISTRY: dict[str, dict] = {}
for _row in _MSHX_ROWS:
    _fid = _row["id"]
    _cfg = {k: v for k, v in _row.items() if k != "id"}
    _cfg["finish_id"] = _fid
    _paint, _spec = _make_money_shokk(**_cfg)
    MONEY_SHOKK_CODEX_BASE_REGISTRY[_fid] = {
        "base_spec_fn": _spec,
        "M": 180,
        "R": 80,
        "CC": 60,
        "paint_fn": _paint,
        "desc": _row["desc"],
    }

assert len(MONEY_SHOKK_CODEX_BASE_REGISTRY) == 10
