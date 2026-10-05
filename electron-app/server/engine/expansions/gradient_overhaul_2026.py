"""Shipping Gradient overhaul — SPB-GRADIENT-OVERHAUL-2026-08-23.

Owner verdict (tick G-0): "the gradients are severely lacking across the
board" and the library needs "insane gradients ... with like 10 to 15 colors".

Measured before this renderer became final authority:
  * ``grad_*``: 125 finishes, M7 min 22.2 / mean 56.44, 112 below 85.
  * ``gradient_*`` material transitions: 10 finishes, M7 mean 50.41, 10 below 85.
  * the prior ``grad_*`` seed used Python ``hash(fid)`` and therefore changed
    rendered bytes between interpreter processes.
  * the 11 ``grd_*`` showcase finishes were not represented in the workbook.

Tick G-1 rebuild contract:
  * preserve every existing id and expand the existing 11-card ``🌈 GRADIENTS``
    shelf with a substantial 20-finish extreme set (no new light category);
  * 10-15 visible color stops on every ``grd_*`` showcase and new extreme;
    7-9 name-true stops on legacy two-color finishes;
  * deterministic BLAKE2 seeds, 30+ macro mechanisms, and parameter variation
    so suffix variants are designs rather than rotated clones;
  * six fine mark families at 8-32 px on a native 2048 canvas (grain, flecks,
    arcs, streaks, rings, petals) plus eight materially occupied shades in each
    of M/R/Cc;
  * work-grid cap 1024 and a two-entry field cache so a spec+paint pair remains
    inside the owner's 2-3 second native-2048 budget.

Final G-18 evidence (official promoted assets, not provisional renders):
  * exact census 166 = 125 legacy + 31 showcase/extreme + 10 material;
    62 topology families (36 single-finish families), with the former fan,
    triangle-vortex, accretion, waterfall, and Laser Jungle lookalike clusters
    split into visibly different mechanisms; a final owner-eye gate also split
    Topaz Vortex from Candy Frozen and restored Coral's rotational semantics;
  * official M7 moved from the measured baseline above to min 86.3 / mean
    92.277 / median 92.7 / max 94.4, 166/166 >= 85; M1 reports zero Gradient
    clone groups;
  * fail-closed production bake: 166/166 non-flat and exact-hash unique,
    minimum RGB std-dev 28.38978, minimum 14,693 unique RGB values, and
    minimum extreme-stop occupancy 3.007507%;
  * one cold native-2048 paint+spec representative from every one of the 62
    topology paths passed the owner's <3 second gate; the two final G-18 paths
    measured 1.229 s (Coral) and 1.455 s (Topaz).

Follow-on SPB-GRADIENT-MATH-2026-08-23 / tick GM-1 answers the owner's
reminder that the recent reusable pattern-math arsenal should become new
Gradients.  Twelve additive ``grd_*`` recipes compose two independently
authored scalar mechanisms apiece instead of recoloring a single existing
finish.

Final GM-7 evidence (official promoted assets, 2026-08-24):
  * census 178 = 125 legacy + 43 showcase/extreme/math + 10 material;
  * the twelve math cards moved from unregistered to official M7 90.6-93.6,
    12/12 >=85, with all M1/M2/M5/M6 components present;
  * the GM-8 fine-detail percentile ratchet restored the expanded shelf to
    178/178 >=85 (minimum 85.3);
  * all 178 paint cards are non-flat and exact-hash unique; all 15,753 look
    comparisons stay below 0.80 (maximum 0.587075), and the new12-versus-old166
    maximum is 0.409700;
  * every cold native-2048 paint+spec topology representative passed the
    owner's <3 second gate, and the full focused release matrix passed 22/22.
"""
from __future__ import annotations

import colorsys
import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import cv2
import numpy as np

from engine.expansions.color_monolithics import COLOR_PALETTE
from engine.expansions.gradient_math_wave_2026 import (
    MATH_DEPENDENCY_MODULES,
    MATH_TOPOLOGIES,
    build_math_field,
)
from engine.paint_v2.fable_collection import (
    _blend_paint,
    _mask2,
    _pack_spec,
    _shape2,
    _upscale,
)
from engine.paint_v2.gradient_math import oklab_ramp
from engine.recipe_kit import flow_grain, micro_scatter, ramp_apply, ramp_lut, ring_swarm


_WORK_CAP = 1024
_FIELD_CACHE_MAX = 2


def _hexes(*values: str) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        tuple(int(value[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
        for value in values
    )


@dataclass(frozen=True)
class GradientRecipe:
    finish_id: str
    family: str
    topology: str
    palette: tuple[tuple[float, float, float], ...]
    stop_count: int
    variant: int
    material_profile: str = "spectral_gloss"
    orientation: str = "free"
    color_space: str = "srgb"


# The new finishes intentionally live in Gradient Extended.  Each concept has
# a unique macro mechanism and 10-15 genuinely different interpolated stops;
# they are not a cross-product of one structure and many palettes.
EXTREME_SPECS = {
    "grd_hyperprism_supernova": (
        "Hyperprism Supernova", "kaleidoscope", 15,
        _hexes("#120024", "#5B00D6", "#006CFF", "#00F5FF", "#00FF7A", "#D8FF00", "#FFF4A8", "#FF8A00", "#FF1744", "#FF00A8", "#F6E7FF"),
    ),
    "grd_aurora_reactor": (
        "Aurora Reactor", "aurora_reactor", 14,
        _hexes("#02051C", "#003C7A", "#00A6D6", "#00FFD0", "#7CFF6B", "#C6FF00", "#8C3CFF", "#FF37C7", "#E7F8FF"),
    ),
    "grd_toxic_candy_nebula": (
        "Toxic Candy Nebula", "nebula", 12,
        _hexes("#090014", "#7A00FF", "#FF00B8", "#FF477E", "#FF9F1C", "#E8FF00", "#39FF14", "#00FFD5", "#B8F2FF"),
    ),
    "grd_ultraviolet_solarstorm": (
        "Ultraviolet Solarstorm", "solar_shockwave", 13,
        _hexes("#070018", "#3B00A4", "#8A00FF", "#FF00D4", "#FF2849", "#FF6A00", "#FFD000", "#00C8FF", "#F4F0FF"),
    ),
    "grd_chromatic_faultline": (
        "Chromatic Faultline", "chromatic_faultline", 15,
        _hexes("#02030A", "#FF1744", "#FF9100", "#FFF000", "#3DFF00", "#00FFD5", "#00A2FF", "#4A3CFF", "#B400FF", "#FF2BB5", "#F2F7FF"),
    ),
    "grd_kaleidoscope_overdrive": (
        "Kaleidoscope Overdrive", "mirror_wedges", 12,
        _hexes("#16002C", "#5A189A", "#4361EE", "#00B4D8", "#06D6A0", "#A7C957", "#FFD166", "#F77F00", "#EF476F", "#FF99C8"),
    ),
    "grd_spectrum_dragonfire": (
        "Spectrum Dragonfire", "flame_braid", 14,
        _hexes("#090014", "#3D0066", "#B000FF", "#FF006E", "#FF2D00", "#FF7A00", "#FFD000", "#E8FF9A", "#00F5D4", "#00A8FF", "#FFF0D8"),
    ),
    "grd_digital_acid_rain": (
        "Digital Acid Rain", "acid_rain", 11,
        _hexes("#020B08", "#004D2C", "#00A65A", "#20FF00", "#C8FF00", "#FFF600", "#00E5FF", "#005BFF", "#E0FFEA"),
    ),
    "grd_quantum_carnival": (
        "Quantum Carnival", "quantum_nodes", 15,
        _hexes("#050014", "#3400A8", "#0068FF", "#00E5FF", "#00FF85", "#B7FF00", "#FFE600", "#FF8800", "#FF1744", "#FF00C8", "#B14CFF", "#F7F2FF"),
    ),
    "grd_holographic_maelstrom": (
        "Holographic Maelstrom", "triple_maelstrom", 13,
        _hexes("#050714", "#003C8F", "#008DFF", "#00FFF0", "#6DFFB0", "#F5FF75", "#FFB000", "#FF4A6E", "#F000FF", "#824DFF", "#EAFBFF"),
    ),
    "grd_electric_coral_rift": (
        "Electric Coral Rift", "rift", 10,
        _hexes("#07152A", "#004B78", "#00C2D1", "#45F0DF", "#FF8A80", "#FF5A5F", "#FF1744", "#A8004F", "#FFE0D6"),
    ),
    "grd_neon_cathedral": (
        "Neon Cathedral", "neon_rose_window", 12,
        _hexes("#050014", "#301050", "#7A00FF", "#E000FF", "#FF007A", "#FF5C00", "#FFD500", "#00D8FF", "#A8F4FF", "#FFF4DE"),
    ),
    "grd_plasma_oilspill": (
        "Plasma Oilspill", "plasma_cells", 15,
        _hexes("#010408", "#10204F", "#004C9A", "#00B4D8", "#00E6A8", "#75FF5B", "#E4FF00", "#FF9E00", "#FF365D", "#D500B8", "#6B2DFF", "#C9F8FF"),
    ),
    "grd_candy_quasar": (
        "Candy Quasar", "twin_jet_quasar", 11,
        _hexes("#140024", "#5B008A", "#C600FF", "#FF00A8", "#FF4F9A", "#FF8A00", "#FFE45E", "#48E5C2", "#6EC5FF", "#FFF0FA"),
    ),
    "grd_laser_jungle": (
        "Laser Jungle", "laser_network", 13,
        _hexes("#02140D", "#005C36", "#00B85A", "#40FF00", "#D0FF00", "#00FFD5", "#00A8FF", "#6C3CFF", "#FF00A8", "#FF5A00", "#E9FFE5"),
    ),
    "grd_infrared_glacier": (
        "Infrared Glacier", "ice_crevasses", 10,
        _hexes("#001229", "#005E9A", "#35C9FF", "#C8F5FF", "#FFF7E8", "#FFB36B", "#FF4A2D", "#A90C1B", "#2A0010"),
    ),
    "grd_prismatic_thunderhead": (
        "Prismatic Thunderhead", "lightning", 14,
        _hexes("#03050F", "#171F4A", "#3040A8", "#825BFF", "#F000FF", "#FF277A", "#FF7A00", "#FFF000", "#00FFB8", "#00B8FF", "#EAF3FF"),
    ),
    "grd_solar_reef": (
        "Solar Reef", "reaction_branches", 12,
        _hexes("#071B38", "#004A7A", "#00A6B2", "#00E0C6", "#6DFFB0", "#FFF06A", "#FFB000", "#FF6F61", "#FF2D7A", "#8E44AD", "#E8FBFF"),
    ),
    "grd_velvet_spectrum_crash": (
        "Velvet Spectrum Crash", "torn_ribbons", 15,
        _hexes("#08000F", "#2E063D", "#6500A8", "#A600FF", "#F000A8", "#FF1744", "#FF7200", "#FFD000", "#66FF00", "#00E5C8", "#008DFF", "#CDB4FF"),
    ),
    "grd_cosmic_heatmap": (
        "Cosmic Heatmap", "topographic_heat", 11,
        _hexes("#020414", "#15145A", "#0047AB", "#00B4D8", "#24E07A", "#C8F000", "#FFE600", "#FF7900", "#E00032", "#F4E8FF"),
    ),
}


# SPB-GRADIENT-MATH-2026-08-23 / GM-1.  These are deliberately not a
# full-rainbow cross-product.  The Morpho owner review found that unrestricted
# spectral travel made unlike structures "run together, no wow"; each palette
# below therefore has its own mineral/neon geography and each topology composes
# two independent fields from the public math arsenal.  All entries are new, so
# metric movement is unregistered -> official M7 90.6-93.6 after the
# fail-closed GM-7 release bake (12/12 >=85).
MATH_SPECS = {
    "grd_domain_coloring_singularity": (
        "Domain Coloring Singularity", "domain_singularity", 15,
        _hexes("#02000A", "#24004A", "#6A00C8", "#1747FF", "#00C8FF", "#D9FAFF", "#073A2C", "#00C97A", "#D7F23A", "#61420A", "#FFB52E", "#D53B1F", "#8B123E", "#FF4CB4", "#E7D8FF"),
    ),
    "grd_nebulabrot_ionstorm": (
        "Nebulabrot Ionstorm", "nebulabrot_ionstorm", 14,
        _hexes("#01030A", "#0C1640", "#2436A5", "#5C51E6", "#D7E3FF", "#003A58", "#008DB5", "#76E6E0", "#153015", "#5CA62E", "#D9E756", "#D86B27", "#79143F", "#F4D8EE"),
    ),
    "grd_superformula_starforge": (
        "Superformula Starforge", "superformula_starforge", 13,
        _hexes("#08020D", "#3B0D4A", "#8B2475", "#E35088", "#FFD1A8", "#594000", "#D0A92F", "#F7F4C0", "#063C43", "#00A3A0", "#6CE1C0", "#303081", "#BA8FFF"),
    ),
    "grd_bismuth_colorquake": (
        "Bismuth Colorquake", "bismuth_chladni", 12,
        _hexes("#07090F", "#29323D", "#627385", "#BEC7D0", "#F8F5E9", "#C39342", "#725E18", "#163F34", "#279B7F", "#3A5FA8", "#7E3C8C", "#D988BA"),
    ),
    "grd_stable_ink_supercurrent": (
        "Stable Ink Supercurrent", "stable_ink_caustics", 15,
        _hexes("#01070B", "#023248", "#006F8E", "#24C1C8", "#C9F7F2", "#143125", "#3A805B", "#A8D866", "#EFF59A", "#704A13", "#CF7A20", "#F2B36D", "#612030", "#B23D70", "#B8A7FF"),
    ),
    "grd_electrostatic_candy_wells": (
        "Electrostatic Candy Wells", "electrostatic_ridges", 11,
        _hexes("#05000D", "#3C006A", "#9C19D2", "#FF4BA8", "#FFD3EA", "#163A72", "#16A0D4", "#7AF1EF", "#EAF45B", "#FF8E31", "#5B1028"),
    ),
    "grd_ferrofluid_spectrum_crown": (
        "Ferrofluid Spectrum Crown", "ferrofluid_gyroid", 14,
        _hexes("#010305", "#141C22", "#34404A", "#77858F", "#EAF4F7", "#153B32", "#00A987", "#A2E84A", "#F8DF54", "#AC6C1D", "#E33F3D", "#A20E6E", "#532EA5", "#90A4FF"),
    ),
    "grd_viscous_prism_fingers": (
        "Viscous Prism Fingers", "viscous_schlieren", 13,
        _hexes("#08020B", "#33103E", "#713061", "#BC5A7B", "#F1B6A2", "#F7E7BD", "#6A6525", "#94C85D", "#1D8065", "#28D7C7", "#1A608A", "#383C91", "#C5A4FF"),
    ),
    "grd_scarab_shingle_cascade": (
        "Scarab Shingle Cascade", "scarab_cascade", 12,
        _hexes("#020608", "#082B31", "#006D78", "#22D4C4", "#C7FFF2", "#22451C", "#7BBE2E", "#E4E657", "#C98525", "#9B2A37", "#6D258E", "#D8CBFF"),
    ),
    "grd_nacre_brickwave": (
        "Nacre Brickwave", "nacre_filament", 12,
        _hexes("#080B12", "#283746", "#4F7780", "#91C7BE", "#D5EFDA", "#FFF5DD", "#DAB883", "#BE7E9D", "#9A80C8", "#6374AC", "#B8DDF1", "#FFF9FF"),
    ),
    "grd_singularity_loom": (
        "Singularity Loom", "singularity_loom", 15,
        _hexes("#020008", "#190026", "#43006F", "#7300A6", "#1B1F60", "#006A9C", "#58E8E2", "#D4FFF4", "#254B1D", "#C7F138", "#FFE4A1", "#C34C17", "#5B0719", "#F12BA6", "#8872FF"),
    ),
    "grd_harmonic_cathedral": (
        "Harmonic Cathedral", "harmonic_cathedral", 14,
        _hexes("#030713", "#16285A", "#315BC1", "#83B8FF", "#EDF6FF", "#163E37", "#38A889", "#C2E08A", "#6B5323", "#D6A64A", "#F1D8A1", "#7B2D58", "#C05AAE", "#9B8DFF"),
    ),
}


# The original 11 showcase ids are all upgraded to 10-15 colors too.  Their
# established semantic identity remains intact while their renderer is replaced.
_GRD_SPECS = {
    "grd_oklab_flow": ("flow", 12, _hexes("#21002F", "#6A0572", "#AB0E86", "#F03A6E", "#FF7A3D", "#FFD166", "#34D1BF", "#2878C8")),
    "grd_iridescent": ("oil_marble", 15, _hexes("#05050A", "#4200A8", "#004DFF", "#00D8FF", "#00FF87", "#D0FF00", "#FFE600", "#FF7200", "#FF1744", "#F000FF", "#F4FBFF")),
    "grd_ridged_contour": ("contour_ridges", 10, _hexes("#010914", "#022B4F", "#005C78", "#008C95", "#00C2B8", "#6DE2C6", "#B2C9FF", "#5749A8")),
    "grd_mesh_bleed": ("spline_pools", 14, _hexes("#07142C", "#006994", "#00C2B8", "#53FFB8", "#B8FF60", "#FFD166", "#FF5E7A", "#C63BFA", "#EFFBFF")),
    "grd_duotone_grain": ("braided_flow", 10, _hexes("#280018", "#7A003F", "#C21868", "#F54291", "#FF9AC8", "#E4E9FF", "#8CA3C7", "#36496B")),
    "grd_chromatic_aberration": ("rgb_aberration", 15, _hexes("#070014", "#6100FF", "#006CFF", "#00ECFF", "#00FF70", "#E8FF00", "#FF8A00", "#FF1744", "#FF00B8", "#F3F7FF")),
    "grd_spectral_sweep": ("spectral_sweep", 15, _hexes("#3A0012", "#E0002B", "#FF5A00", "#FFD000", "#80FF00", "#00E67A", "#00D8FF", "#0050FF", "#5A00D6", "#D000FF", "#FF70D0")),
    "grd_liquid_marble": ("oil_marble", 13, _hexes("#12001F", "#430078", "#8700B8", "#D000A8", "#FF3D7A", "#FF8A50", "#00B4C8", "#183D8F", "#E8D8FF")),
    "grd_moire_interference": ("moire_phase", 12, _hexes("#07131F", "#193B5A", "#2C6F9B", "#4EB5D9", "#A8F0F5", "#D9E5FF", "#8D80C9", "#473968")),
    "grd_holo_foil": ("holo_lattice", 15, _hexes("#050511", "#4C00A8", "#0064FF", "#00E5FF", "#00FF8A", "#D8FF00", "#FFE600", "#FF7A00", "#FF1744", "#FF00C8", "#FFFFFF")),
    "grd_radial_burst": ("radial_burst", 14, _hexes("#210007", "#770012", "#D71C00", "#FF5A00", "#FFA800", "#FFE066", "#F4FFB8", "#FF2D7A", "#7A00A8")),
}


_MATERIAL_SPECS = {
    "gradient_chrome_matte": ("directional_prism", "chrome_matte", _hexes("#10151C", "#3E4A59", "#8B9AAA", "#E8F2FA", "#FFFFFF", "#9DA3A8", "#424448")),
    "gradient_candy_frozen": ("dendritic_crystal", "candy_frozen", _hexes("#41001E", "#A0004E", "#FF287F", "#FF9BC7", "#E8FBFF", "#77D8FF", "#1B55B8")),
    "gradient_pearl_chrome": ("pearl_folds", "pearl_chrome", _hexes("#36283D", "#8C7199", "#EADCF2", "#FFF9FF", "#B8CAD8", "#637786")),
    "gradient_metallic_satin": ("crosscurrent", "metallic_satin", _hexes("#1E2630", "#526070", "#9AA9B8", "#D8E3EC", "#8F8790", "#514B55")),
    "gradient_obsidian_mirror": ("shockwave", "obsidian_mirror", _hexes("#010104", "#080A12", "#171D2A", "#43516A", "#A7B9C8", "#F5FBFF")),
    "gradient_candy_matte": ("flow", "candy_matte", _hexes("#240014", "#72003C", "#D3166B", "#FF6FA8", "#B45C78", "#523342")),
    "gradient_anodized_gloss": ("anodized_ripples", "anodized_gloss", _hexes("#11151A", "#4B2D7A", "#006E9A", "#00A878", "#B5A642", "#D67935", "#F7E8FF")),
    "gradient_ember_ice": ("thermal_fracture", "ember_ice", _hexes("#220005", "#B31212", "#FF5A00", "#FFD36A", "#F8FCFF", "#61D6FF", "#063B8C")),
    "gradient_carbon_chrome": ("braided_flow", "carbon_chrome", _hexes("#030405", "#111820", "#263543", "#6A7D8F", "#C8D7E2", "#FFFFFF")),
    "gradient_spectraflame_void": ("spectra_vortex", "spectra_void", _hexes("#000002", "#0B0025", "#5200A8", "#006CFF", "#00F5FF", "#38FF68", "#FFE600", "#FF5A00", "#FF005D")),
}


_STANDARD_DIRECTIONAL = (
    "flow", "directional_wave", "directional_prism", "braided_flow",
    "crosscurrent", "waterfall", "ribbon_fold", "fan_burst",
)
_STANDARD_VORTEX = (
    "spiral", "cyclone_cells", "shockwave", "vortex_lattice", "oil_whorl",
    "accretion", "dual_vortex", "petal_whirl", "broken_rotor", "tidal_vortex",
)

# GM-5: the first math owner-eye sheet proved that full histogram equalization
# forced unrelated natural distributions into the same neon contour grammar.
# Retain enough CDF influence for all 10-15 authored colors to remain visible,
# but let each imported field keep its void/core/face/edge geography. Existing
# 166 Gradients stay on the exact historical equalized path below.
_MATH_EQUALIZE_BLEND = {
    "domain_singularity": 0.35,
    # Preserve ~18% true fractal black while balancing the occupied orbit
    # filaments across all fourteen authored colors.
    "nebulabrot_ionstorm": 0.75,
    "superformula_starforge": 0.30,
    "bismuth_chladni": 0.40,
    "stable_ink_caustics": 0.70,
    "electrostatic_ridges": 0.35,
    "ferrofluid_gyroid": 0.32,
    # The irregular multi-injection field intentionally leaves ~78% dark
    # solvent; equalize only the nonzero growth ranks so all 13 prism colors
    # still appear along the fingers.
    "viscous_schlieren": 0.85,
    "scarab_cascade": 0.45,
    "nacre_filament": 0.65,
    "singularity_loom": 0.30,
    "harmonic_cathedral": 0.40,
}

# G-8 visual audit: exact hashes were unique, but ten legacy cards still read
# as the same triangle-lattice spiral and two other pairs exceeded the 0.95
# morphology review line. Keep only three intentional lattice variants and give
# the rest different vortex physics. IDs stay stable for saved projects.
_LEGACY_TOPOLOGY_OVERRIDES = {
    "grad_aqua_drift": "aqua_current",
    # G-17 final visual sweep: remove the seven oversized center-fan cards.
    # Each now gets a name-appropriate dense mechanism rather than a palette
    # swap over the same giant sectors (morphology max had remained 0.93943).
    "grad_black_gold": "micro_constellation",
    "grad_copper_flame": "flame_braid",
    "grad_fire_fade": "acid_rain",
    "grad_ocean_depths_diag": "aqua_current",
    "grad_plum_dawn": "aurora_reactor",
    "grad_rose_gold": "pearl_folds",
    "grad_twilight_diag": "rgb_aberration",
    # G-18 owner-eye correction: the first G-17 split removed the numerical
    # collision but made Coral a flat triangle field and made Topaz an obvious
    # palette twin of material Candy Frozen's seven-point crystal.  Give both
    # literal, name-true small-feature vortex mechanisms.
    "grad_coral_vortex": "coral_cell_vortex",
    "grad_topaz_vortex": "topaz_shard_vortex",
    # Split the blush/champagne/peach accretion-pinwheel cluster.
    "grad_champagne_vortex": "vortex_bubbles",
    "grad_peach_vortex": "whirlpool_rift",
    # Break the secondary Waterfall morphology cluster.
    "grad_chrome_wave": "anodized_ripples",
    "grad_lavender_dusk": "nebula",
    "grad_pewter_vortex": "vortex_ribbons",
    "grad_emerald_vortex": "eddy_chain",
    "grad_green_vortex": "logarithmic_shells",
    "grad_honey_vortex": "vortex_bubbles",
    "grad_lavender_vortex": "pinwheel_shards",
    "grad_rose_vortex": "whirlpool_rift",
    "grad_shadow_vortex": "turbine_blades",
    "grad_slate_vortex": "countercurrent_vortex",
}


def _stable_int(value: str) -> int:
    return int.from_bytes(hashlib.blake2s(value.encode("utf-8"), digest_size=8).digest(), "big")


def _seed_for(finish_id: str, seed: int) -> int:
    return (_stable_int(finish_id) ^ (int(seed) & 0x7FFFFFFF)) & 0x7FFFFFFF


def _rgb_tuple(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(float(np.clip(v, 0.0, 1.0)) for v in value)


def _resample_anchors(
    anchors: tuple[tuple[float, float, float], ...], count: int
) -> tuple[tuple[float, float, float], ...]:
    """Resample curated anchors in HSV along the shortest hue route.

    The resulting entries are actual ramp stops, not a LUT density claim.  A
    15-stop recipe therefore contains 15 separately addressable colors.
    """
    if len(anchors) == count:
        return tuple(_rgb_tuple(c) for c in anchors)
    hsv = [colorsys.rgb_to_hsv(*_rgb_tuple(c)) for c in anchors]
    out: list[tuple[float, float, float]] = []
    for pos in np.linspace(0.0, len(anchors) - 1, count):
        i0 = min(int(np.floor(pos)), len(anchors) - 1)
        i1 = min(i0 + 1, len(anchors) - 1)
        f = float(pos - i0)
        h0, s0, v0 = hsv[i0]
        h1, s1, v1 = hsv[i1]
        dh = ((h1 - h0 + 0.5) % 1.0) - 0.5
        h = (h0 + dh * f) % 1.0
        s = s0 * (1.0 - f) + s1 * f
        v = v0 * (1.0 - f) + v1 * f
        out.append(_rgb_tuple(colorsys.hsv_to_rgb(h, s, v)))
    return tuple(out)


def _legacy_palette(
    c1: tuple[float, float, float],
    c2: tuple[float, float, float],
    count: int,
    variant: int,
) -> tuple[tuple[float, float, float], ...]:
    """Expand two catalog endpoints into a name-true 7-9 color story.

    Grayscale/near-black pairs borrow a stable chromatic undertone, while vivid
    pairs bend through nearby companions.  Endpoints remain exact.
    """
    a = np.asarray(c1, np.float32)
    b = np.asarray(c2, np.float32)
    ah, ass, av = colorsys.rgb_to_hsv(*_rgb_tuple(a))
    bh, bss, bv = colorsys.rgb_to_hsv(*_rgb_tuple(b))
    hero_h = ah if ass >= bss else bh
    if max(ass, bss) < 0.12:
        hero_h = ((variant % 19) / 19.0 + 0.54) % 1.0
    excursion = (22.0 + float(variant % 37)) / 360.0
    mid_h = (hero_h + (excursion if variant & 1 else -excursion)) % 1.0
    mid2_h = (hero_h - excursion * 0.65) % 1.0
    mid_v = float(np.clip(max(av, bv) * 0.92 + 0.08, 0.18, 1.0))
    mid_s = float(np.clip(max(ass, bss) * 0.92 + 0.24, 0.28, 1.0))
    dark = _rgb_tuple(np.clip(a * 0.38 + b * 0.08, 0.0, 1.0))
    light = _rgb_tuple(np.clip(b * 0.84 + np.float32([0.16, 0.16, 0.16]), 0.0, 1.0))
    anchors = (
        dark,
        _rgb_tuple(a),
        _rgb_tuple(colorsys.hsv_to_rgb(mid_h, mid_s, mid_v)),
        _rgb_tuple((a + b) * 0.5),
        _rgb_tuple(colorsys.hsv_to_rgb(mid2_h, min(1.0, mid_s * 0.9), mid_v)),
        _rgb_tuple(b),
        light,
    )
    return _resample_anchors(anchors, count)


def _work_dims(shape) -> tuple[int, int, int, int]:
    fh, fw = _shape2(shape)
    m = max(fh, fw)
    if m <= _WORK_CAP:
        return int(fh), int(fw), int(fh), int(fw)
    scale = _WORK_CAP / float(m)
    return max(64, int(round(fh * scale))), max(64, int(round(fw * scale))), int(fh), int(fw)


def _norm(field: np.ndarray) -> np.ndarray:
    field = np.asarray(field, np.float32)
    lo = float(field.min())
    span = float(np.ptp(field))
    if span < 1e-8:
        return np.zeros_like(field, np.float32)
    return ((field - lo) / span).astype(np.float32)


def _smooth_noise(h: int, w: int, seed: int, cells: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    gh = max(3, int(round(cells * h / max(h, w))))
    gw = max(3, int(round(cells * w / max(h, w))))
    small = rng.random((gh, gw), dtype=np.float32)
    return _norm(cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC))


def _coords(h: int, w: int):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = xx / max(w - 1, 1) * 2.0 - 1.0
    y = yy / max(h - 1, 1) * 2.0 - 1.0
    return yy, xx, y, x


def _hex_field(x: np.ndarray, y: np.ndarray, freq: float) -> np.ndarray:
    q = np.abs(np.sin(x * freq * 2.7207))
    r = np.abs(np.sin((x * 0.5 + y * 0.8660254) * freq * 2.7207))
    s = np.abs(np.sin((-x * 0.5 + y * 0.8660254) * freq * 2.7207))
    return _norm(np.minimum(np.minimum(q, r), s))


from engine.expansions import gradient_designs_2026 as _GD


def _macro_fields(recipe: GradientRecipe, h: int, w: int, seed: int):
    _, _, y, x = _coords(h, w)
    rng = np.random.default_rng(seed)
    angle = rng.uniform(0.0, np.pi)
    # Legacy suffixes are a rendering contract, not decoration.  The rejected
    # v2 stripped these suffixes and round-robined every id through unrelated
    # structures, leaving 18/18 H/Diag names directionally false.
    if recipe.family == "legacy" and not recipe.finish_id.endswith("_vortex"):
        if recipe.finish_id.endswith("_h"):
            angle = 0.0
        elif recipe.finish_id.endswith("_diag"):
            angle = np.pi * 0.25
        else:
            angle = np.pi * 0.5  # catalog contract: unsuffixed default is vertical
    ca, sa = np.cos(angle), np.sin(angle)
    u = x * ca + y * sa
    v = -x * sa + y * ca
    n1 = _smooth_noise(h, w, seed ^ 0x191, 5 + seed % 5)
    n2 = _smooth_noise(h, w, seed ^ 0x2A7, 11 + seed % 8)
    warp = (n1 - 0.5) * (0.34 + (seed % 13) * 0.009) + (n2 - 0.5) * 0.12
    freq = 3.2 + (seed % 17) * 0.23
    cx = x - rng.uniform(-0.24, 0.24)
    cy = y - rng.uniform(-0.24, 0.24)
    rad = np.hypot(cx, cy) + 1e-5
    theta = np.arctan2(cy, cx)
    mode = recipe.topology

    if recipe.finish_id in _GD.DESIGNS:
        # 2026-09-02 owner: "way too many repeating patterns ... make them all good".
        # One authored construction per finish (gradient_designs_2026), blended with
        # this finish's own carrier so the colour sweep and the H/Diag/vortex
        # contracts survive. Spec composition below is unchanged.
        raw = _GD.raw_field(recipe.finish_id, seed, h, w, u, rad, theta, recipe.orientation)
    elif mode in MATH_TOPOLOGIES:
        # GM-1 owner verdict: reuse the recent procedural-math arsenal to make
        # structures that are not palette variants of the original Gradient
        # fleet. The helper composes two independent fields and stays on the
        # bounded work grid; the common CDF and fine-detail stack below remain
        # the shipping occupancy/material contract.
        raw = build_math_field(mode, h, w, seed)
    elif mode == "flow":
        raw = u * 0.72 + warp + np.sin(v * np.pi * freq + n1 * 4.0) * 0.17
    elif mode == "directional_wave":
        raw = u * 0.38 + np.sin((v + warp) * np.pi * freq) * 0.48 + n2 * 0.18
    elif mode == "directional_prism":
        z = (u + warp) * (3.0 + (seed % 5))
        raw = 1.0 - np.abs(np.mod(z, 2.0) - 1.0) + v * 0.13
    elif mode == "braided_flow":
        raw = np.sin((u + np.sin(v * 4.0) * 0.19 + warp) * np.pi * freq) + np.sin((v - u * 0.28) * np.pi * (freq + 1.7)) * 0.55
    elif mode == "crosscurrent":
        raw = np.sin((u + warp) * np.pi * freq) * np.cos((v - warp) * np.pi * (freq * 0.73)) + n1 * 0.38
    elif mode == "waterfall":
        raw = y * 0.65 + np.sin((x + warp) * np.pi * (freq + 2.0)) * 0.20 + n2 * 0.34
    elif mode == "ribbon_fold":
        raw = np.abs(np.mod((u + warp) * (3.0 + seed % 4), 2.0) - 1.0) + np.sin(v * 5.0) * 0.17
    elif mode == "fan_burst":
        raw = theta / np.pi + rad * 0.42 + np.sin(theta * (4 + seed % 6)) * 0.26 + warp
    elif mode == "spiral":
        raw = np.sin(theta * (3 + seed % 6) + np.log(rad) * (5.0 + seed % 5) + n1 * 2.0)
    elif mode == "cyclone_cells":
        spiral = np.sin(theta * (4 + seed % 5) + rad * np.pi * (6 + seed % 5) + warp * 4.0)
        raw = spiral * 0.68 + _hex_field(x + warp * 0.2, y - warp * 0.2, 6 + seed % 5) * 0.52
    elif mode in {"shockwave", "solar_shockwave"}:
        raw = np.sin(rad * np.pi * (7 + seed % 8) + theta * (1 + seed % 3) + warp * 3.0) + (1.0 - rad) * 0.35
    elif mode in {"vortex_lattice", "holo_lattice"}:
        spiral = np.sin(theta * (5 + seed % 5) + rad * np.pi * (5 + seed % 6))
        raw = spiral * 0.55 + _hex_field(x, y, 7 + seed % 6) * 0.72
    elif mode in {"oil_whorl", "oil_marble"}:
        raw = np.sin((u + n1 * 0.76 + np.sin(v * 3.0) * 0.22) * np.pi * (freq + 1.0)) + n2 * 0.62
    elif mode == "accretion":
        raw = rad * 0.62 + np.sin(theta * (5 + seed % 8) + rad * 13.0) * 0.34 + warp
    elif mode == "dual_vortex":
        th2 = np.arctan2(y + 0.35, x - 0.38)
        r2 = np.hypot(y + 0.35, x - 0.38)
        raw = np.sin(theta * 4.0 + rad * 14.0) + np.cos(th2 * 5.0 - r2 * 12.0) * 0.78 + warp
    elif mode == "petal_whirl":
        raw = np.cos(theta * (6 + seed % 7) + rad * (9 + seed % 8)) * (1.1 - np.clip(rad, 0, 1)) + rad * 0.35
    elif mode == "broken_rotor":
        sectors = np.floor((theta + np.pi) / (2 * np.pi) * (7 + seed % 7))
        raw = sectors * 0.21 + np.sin(rad * np.pi * (5 + seed % 6) + sectors) + warp
    elif mode == "tidal_vortex":
        raw = theta * 0.22 + rad * 0.72 + np.sin((theta + rad * 5.0) * 4.0) * 0.28 + n1 * 0.34
    elif mode == "kaleidoscope":
        wedge = np.abs(np.cos(theta * (5 + seed % 8)))
        raw = wedge * (1.1 - np.clip(rad, 0, 1)) + np.sin(rad * np.pi * (7 + seed % 6)) * 0.48 + warp
    elif mode == "aurora_reactor":
        curtains = np.sin((x + n1 * 0.36) * np.pi * (4 + seed % 5)) * (0.25 + (1.0 - np.abs(y)) * 0.4)
        raw = y * 0.58 + curtains + n2 * 0.32
    elif mode == "nebula":
        raw = n1 * 0.62 + n2 * 0.34 + np.sin(theta * 3.0 + rad * 9.0) * 0.24 - rad * 0.16
    elif mode == "faultline":
        fault = np.abs(u + warp * 0.92)
        raw = np.floor((v + n1 * 0.2 + 1.0) * (4 + seed % 4)) * 0.22 + np.exp(-fault * (9 + seed % 8)) * 0.9
    elif mode == "stained_glass":
        cells = _hex_field(x + warp * 0.16, y - warp * 0.12, 5 + seed % 6)
        raw = cells * 0.58 + n1 * 0.52 + np.sin(theta * (3 + seed % 5)) * 0.14
    elif mode == "flame_braid":
        tongues = np.sin((u + np.sin(v * 5.0 + n1 * 2.0) * 0.22) * np.pi * (freq + 1.0))
        raw = tongues * 0.58 + (1.0 - (y + 1.0) * 0.5) * 0.52 + n2 * 0.34
    elif mode == "acid_rain":
        drops = np.sin((x + n1 * 0.12) * np.pi * (10 + seed % 8))
        raw = y * 0.55 + drops * 0.21 + np.floor(n2 * (5 + seed % 4)) * 0.17
    elif mode == "quasicrystal":
        raw = np.zeros((h, w), np.float32)
        for k in range(5):
            a = k * np.pi / 5.0 + angle * 0.17
            raw += np.cos((x * np.cos(a) + y * np.sin(a)) * np.pi * (4.0 + k * 0.71 + seed % 3))
        raw = raw + warp * 1.2
    elif mode == "micro_constellation":
        # G-17 Black/Gold rescue: dense 8-24 px star clusters and short links
        # replace the rejected full-panel fan sectors.
        raw = _norm(u * 0.34 + (n1 - 0.5) * 0.28)
        stars = np.zeros((h, w), np.float32)
        area = (h * w) / float(_WORK_CAP * _WORK_CAP)
        count = max(70, int((190 + seed % 61) * area))
        px_scale = max(0.5, min(h, w) / float(_WORK_CAP))
        points = np.stack((rng.integers(0, w, count), rng.integers(0, h, count)), axis=1)
        for i, (sx, sy) in enumerate(points):
            radius = max(2, int(round((4.0 + (i % 7)) * px_scale)))
            value = float((i % 13) / 12.0)
            cv2.circle(stars, (int(sx), int(sy)), radius, value, -1, cv2.LINE_AA)
            if i and i % 3 == 0:
                px0, py0 = points[i - 1]
                cv2.line(stars, (int(px0), int(py0)), (int(sx), int(sy)), value, max(1, int(round(2 * px_scale))), cv2.LINE_AA)
        mask_star = np.clip(stars * 2.2, 0.0, 1.0)
        raw = raw * (1.0 - mask_star) + stars * mask_star
    elif mode == "rift":
        cleft = np.exp(-np.abs(u + warp * 0.8) * (10 + seed % 10))
        raw = np.sign(u + warp * 0.8) * 0.55 + cleft * 1.2 + np.sin(v * 8.0 + n2 * 3.0) * 0.22
    elif mode == "cathedral":
        bay = np.mod((x + 1.0) * (3 + seed % 4), 2.0) - 1.0
        arch = np.hypot(bay, np.maximum(0.0, y + 0.1))
        raw = np.cos(arch * np.pi * (3.5 + seed % 3)) + n1 * 0.42 + y * 0.22
    elif mode == "quasar":
        rays = np.cos(theta * (8 + seed % 9)) * np.exp(-rad * 0.75)
        raw = rays * 0.82 + np.sin(rad * np.pi * (8 + seed % 7)) * 0.46 + warp
    elif mode == "laser_vines":
        raw = np.sin((y + np.sin(x * (4 + seed % 4) + n1 * 2.0) * 0.28) * np.pi * (5 + seed % 5)) + n2 * 0.55
    elif mode == "laser_network":
        # G-17: edge-to-edge laser vines with junction branches.  The former
        # periodic sine ribbons were an owner-eye twin of Spectrum Dragonfire.
        background = _norm((n1 - 0.5) * 0.38 + u * 0.34 + v * 0.16)
        raw = background * 0.18
        lane = np.zeros((h, w), np.float32)
        lane_mask = np.zeros((h, w), np.float32)
        tau = np.linspace(0.0, 1.0, 30, dtype=np.float32)[:, None]
        bern = np.concatenate(((1-tau)**3, 3*(1-tau)**2*tau, 3*(1-tau)*tau**2, tau**3), axis=1)
        vine_count = 15 + seed % 5
        halo_w = max(4, int(round(min(h, w) * 0.0095)))
        core_w = max(2, int(round(min(h, w) * 0.0042)))
        for i in range(vine_count):
            side = i % 4
            if side == 0:
                p0, p3 = (rng.uniform(0, w), -5.0), (rng.uniform(0, w), h + 5.0)
            elif side == 1:
                p0, p3 = (-5.0, rng.uniform(0, h)), (w + 5.0, rng.uniform(0, h))
            elif side == 2:
                p0, p3 = (rng.uniform(0, w), h + 5.0), (w + 5.0, rng.uniform(0, h))
            else:
                p0, p3 = (w + 5.0, rng.uniform(0, h)), (rng.uniform(0, w), -5.0)
            controls = np.asarray((
                p0,
                (rng.uniform(0.08*w, 0.92*w), rng.uniform(0.08*h, 0.92*h)),
                (rng.uniform(0.08*w, 0.92*w), rng.uniform(0.08*h, 0.92*h)),
                p3,
            ), np.float32)
            points = np.rint(bern @ controls).astype(np.int32).reshape(-1, 1, 2)
            value = float((i + 0.45) / (vine_count + 0.1))
            cv2.polylines(lane_mask, [points], False, 1.0, halo_w, cv2.LINE_AA)
            cv2.polylines(lane, [points], False, value, halo_w, cv2.LINE_AA)
            cv2.polylines(lane, [points], False, float(np.mod(value + 0.19, 1.0)), core_w, cv2.LINE_AA)
            if i % 3 == 0:
                junction = points[len(points) // 2, 0]
                endpoint = np.asarray((
                    np.clip(junction[0] + rng.uniform(-0.32*w, 0.32*w), -5, w + 5),
                    np.clip(junction[1] + rng.uniform(-0.32*h, 0.32*h), -5, h + 5),
                ), np.int32)
                branch = np.asarray((junction, endpoint), np.int32).reshape(-1, 1, 2)
                cv2.polylines(lane_mask, [branch], False, 1.0, halo_w, cv2.LINE_AA)
                cv2.polylines(lane, [branch], False, float(np.mod(value + 0.31, 1.0)), core_w, cv2.LINE_AA)
        blend = np.clip(lane_mask, 0.0, 1.0)
        raw = raw * (1.0 - blend) + lane * blend
    elif mode == "glacier_facets":
        facets = _hex_field(x + warp * 0.12, y, 5 + seed % 5)
        raw = facets * 0.72 + np.abs(u) * 0.22 + n1 * 0.36
    elif mode == "lightning":
        ridge = 1.0 - np.clip(np.abs(n1 - n2) * (3.5 + seed % 3), 0.0, 1.0)
        raw = ridge * 0.78 + u * 0.24 + np.sin(v * 8.0) * 0.16
    elif mode == "coral_cell_vortex":
        # G-18: dense 8-30 px Voronoi polyps are physically advected around an
        # off-center whirl. G-17's regular triangle lattice was collision-free
        # but semantically flat; the first G-18 dotted-arm prototype was too
        # sparse on the car. Density now carries the design, never larger cells.
        area = max(0.12, (h * w) / float(_WORK_CAP * _WORK_CAP))
        point_count = max(480, int(7000 * area))
        source = np.full((h, w), 255, np.uint8)
        source[rng.integers(0, h, point_count), rng.integers(0, w, point_count)] = 0
        _distance, labels = cv2.distanceTransformWithLabels(
            source, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
        )
        boundary = np.zeros((h, w), np.float32)
        boundary[:, 1:] = np.maximum(boundary[:, 1:], labels[:, 1:] != labels[:, :-1])
        boundary[1:, :] = np.maximum(boundary[1:, :], labels[1:, :] != labels[:-1, :])
        boundary = cv2.GaussianBlur(boundary, (0, 0), 0.78)
        cell_phase = np.mod(labels.astype(np.float32) * 0.61803398875, 1.0)

        vx = x - 0.08
        vy = y + 0.06
        vrad = np.hypot(vx, vy) + 1e-5
        vtheta = np.arctan2(vy, vx)
        twist = 2.75 * np.exp(-vrad * 0.92)
        ct, st = np.cos(twist), np.sin(twist)
        sample_x = vx * ct - vy * st + 0.08
        sample_y = vx * st + vy * ct - 0.06
        map_x = np.clip((sample_x + 1.0) * 0.5 * (w - 1), 0, w - 1).astype(np.float32)
        map_y = np.clip((sample_y + 1.0) * 0.5 * (h - 1), 0, h - 1).astype(np.float32)
        cells = cv2.remap(cell_phase, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        membranes = cv2.remap(boundary, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        circulation = 0.5 + 0.5 * np.sin(vtheta * 5.0 + vrad * 19.0)
        raw = cells * 0.70 + membranes * 0.30 + circulation * 0.18
    elif mode == "torn_ribbons":
        ribbons = np.abs(np.mod((u + warp) * (4 + seed % 5), 2.0) - 1.0)
        tears = np.floor((v + n2 * 0.35 + 1.0) * (5 + seed % 4)) * 0.18
        raw = ribbons * 0.78 + tears
    elif mode == "topographic_heat":
        topo = np.floor((n1 * 0.65 + n2 * 0.35) * (8 + seed % 5))
        raw = topo + u * 0.42
    elif mode == "spectral_sweep":
        raw = u * 0.72 + np.sin(v * 3.0 + n1 * 3.0) * 0.26 + warp
    elif mode == "mirror_wedges":
        segments = 7 + seed % 7
        folded = np.abs(np.mod((theta + np.pi) / np.pi * segments, 2.0) - 1.0)
        raw = folded * 0.82 + np.sin(rad * np.pi * (5 + seed % 5) + folded * 3.0) * 0.38 + warp
    elif mode == "quantum_nodes":
        waves = np.zeros((h, w), np.float32)
        for k in range(4):
            a = angle * 0.23 + k * np.pi / 4.0
            waves += np.cos((x * np.cos(a) + y * np.sin(a)) * np.pi * (3.2 + k * 0.83))
        raw = np.sin(waves * 1.72 + theta * 1.4 + n1 * 2.3) + (1.0 - rad) * 0.24
    elif mode == "triple_maelstrom":
        raw = np.zeros((h, w), np.float32)
        for ox, oy, direction in ((-0.42, -0.18, 1.0), (0.38, -0.12, -1.0), (0.02, 0.43, 1.0)):
            rr = np.hypot(x - ox, y - oy) + 1e-4
            tt = np.arctan2(y - oy, x - ox)
            raw += np.sin(tt * (3.0 + seed % 3) * direction + rr * (10.0 + seed % 5)) / (0.72 + rr)
        raw = raw + warp * 0.9
    elif mode == "neon_rose_window":
        petals2 = np.cos(theta * (8 + seed % 7) + rad * 3.2)
        tracery = np.cos(rad * np.pi * (5 + seed % 5) + petals2 * 1.8)
        raw = tracery * 0.68 + petals2 * (1.0 - np.clip(rad, 0, 1.2)) * 0.56 + n1 * 0.25
    elif mode == "plasma_cells":
        membrane = np.sin((n1 - n2) * np.pi * (8 + seed % 5) + u * 4.0)
        plasma = np.cos((n1 + n2) * np.pi * (5 + seed % 4) - v * 3.0)
        raw = membrane * 0.62 + plasma * 0.45 + n1 * 0.28
    elif mode == "twin_jet_quasar":
        r_left = np.hypot(x + 0.36, y) + 1e-4
        r_right = np.hypot(x - 0.36, y) + 1e-4
        t_left = np.arctan2(y, x + 0.36)
        t_right = np.arctan2(y, x - 0.36)
        jets = np.cos(t_left * 5.0 + r_left * 13.0) / (0.55 + r_left)
        jets -= np.cos(t_right * 6.0 - r_right * 12.0) / (0.55 + r_right)
        raw = jets + np.exp(-np.abs(y + warp * 0.4) * 12.0) * 0.9
    elif mode == "ice_crevasses":
        # G-12: actual angular ice plates.  The rejected sine/noise level sets
        # read as the same amoeba contours used by Reef and Mesh Bleed.
        point_count = 48 + seed % 31
        source = np.full((h, w), 255, np.uint8)
        py = rng.integers(0, h, point_count)
        px = rng.integers(0, w, point_count)
        source[py, px] = 0
        _distance, labels = cv2.distanceTransformWithLabels(
            source, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
        )
        boundary = np.zeros((h, w), np.float32)
        boundary[:, 1:] = np.maximum(boundary[:, 1:], labels[:, 1:] != labels[:, :-1])
        boundary[1:, :] = np.maximum(boundary[1:, :], labels[1:, :] != labels[:-1, :])
        boundary = cv2.GaussianBlur(boundary, (0, 0), 1.05)
        plate_phase = np.mod(labels.astype(np.float32) * 0.61803398875, 1.0)
        raw = np.clip(plate_phase * 0.86 + boundary * 0.22 + (n1 - 0.5) * 0.05, 0.0, 1.0)
    elif mode == "reaction_branches":
        # G-12: coral trunks + forked tendrils, drawn in bounded OpenCV calls.
        # This is directional branching geometry, not another periodic noise
        # contour pretending to be organic growth.
        background = _norm(u * 0.58 + (n1 - 0.5) * 0.42)
        raw = background * 0.22
        halo = np.zeros((h, w), np.float32)
        core = np.zeros((h, w), np.float32)
        trunks = 7 + seed % 4
        trunk_paths: list[np.ndarray] = []
        child_paths: list[np.ndarray] = []
        trunk_values: list[float] = []
        child_values: list[float] = []
        for i in range(trunks):
            x0 = float((i + 0.45 + rng.uniform(-0.22, 0.22)) * w / trunks)
            pts = [(x0, float(h + 2))]
            heading = -np.pi * 0.5 + rng.uniform(-0.24, 0.24)
            step = h / float(5.2 + rng.uniform(-0.35, 0.35))
            for _ in range(6):
                heading += rng.uniform(-0.23, 0.23)
                nx = np.clip(pts[-1][0] + np.cos(heading) * step, -8, w + 8)
                ny = pts[-1][1] + np.sin(heading) * step
                pts.append((float(nx), float(ny)))
            trunk = np.rint(pts).astype(np.int32).reshape(-1, 1, 2)
            trunk_paths.append(trunk)
            trunk_values.append(float((i + 0.65) / (trunks + 0.3)))
            for fork_index, direction in ((2, -1.0), (3, 1.0), (4, -1.0 if i & 1 else 1.0)):
                fx, fy = pts[fork_index]
                child = [(fx, fy)]
                branch_heading = heading + direction * rng.uniform(0.62, 1.03)
                branch_step = step * rng.uniform(0.44, 0.62)
                for _ in range(3):
                    branch_heading += rng.uniform(-0.18, 0.18)
                    child.append((
                        float(np.clip(child[-1][0] + np.cos(branch_heading) * branch_step, -8, w + 8)),
                        float(child[-1][1] + np.sin(branch_heading) * branch_step),
                    ))
                child_paths.append(np.rint(child).astype(np.int32).reshape(-1, 1, 2))
                child_values.append(float(np.mod(trunk_values[-1] + direction * 0.17, 1.0)))
        halo_w = max(4, int(round(min(h, w) * 0.012)))
        core_w = max(2, int(round(min(h, w) * 0.0048)))
        for path, value in zip(trunk_paths + child_paths, trunk_values + child_values):
            cv2.polylines(halo, [path], False, float(value), halo_w, cv2.LINE_AA)
            cv2.polylines(core, [path], False, float(np.mod(value + 0.16, 1.0)), core_w, cv2.LINE_AA)
        branch_mask = np.clip(halo * 2.8, 0.0, 1.0)
        raw = raw * (1.0 - branch_mask) + halo * branch_mask
        raw = np.where(core > 0.0, core, raw).astype(np.float32)
    elif mode == "contour_ridges":
        contour = np.floor((n1 * 0.76 + n2 * 0.24 + u * 0.10) * (12 + seed % 5))
        raw = contour + np.sin((v + warp) * np.pi * (3 + seed % 3)) * 0.22
    elif mode == "spline_pools":
        # G-12: named spline pools now contain literal cubic Bezier ribbons.
        # Twelve-to-sixteen lanes remain 8-30 px at native 2048 and are drawn
        # from ~500 broadcast sample points, keeping the renderer vectorized.
        background = _norm(u * 0.42 + v * 0.18 + (n1 - 0.5) * 0.40)
        raw = background * 0.24
        lane = np.zeros((h, w), np.float32)
        lane_mask = np.zeros((h, w), np.float32)
        tau = np.linspace(0.0, 1.0, 34, dtype=np.float32)[:, None]
        bern = np.concatenate(((1-tau)**3, 3*(1-tau)**2*tau, 3*(1-tau)*tau**2, tau**3), axis=1)
        spline_count = 12 + seed % 5
        halo_w = max(4, int(round(min(h, w) * 0.011)))
        core_w = max(2, int(round(min(h, w) * 0.0045)))
        for i in range(spline_count):
            p = np.stack((rng.uniform(-0.12*w, 1.12*w, 4), rng.uniform(-0.12*h, 1.12*h, 4)), axis=1).astype(np.float32)
            pts = np.rint(bern @ p).astype(np.int32).reshape(-1, 1, 2)
            value = float((i + 0.55) / (spline_count + 0.2))
            cv2.polylines(lane_mask, [pts], False, 1.0, halo_w, cv2.LINE_AA)
            cv2.polylines(lane, [pts], False, value, halo_w, cv2.LINE_AA)
            cv2.polylines(lane, [pts], False, float(np.mod(value + 0.14, 1.0)), core_w, cv2.LINE_AA)
        blend = np.clip(lane_mask, 0.0, 1.0)
        raw = raw * (1.0 - blend) + lane * blend
    elif mode == "rgb_aberration":
        red_route = np.sin((u + warp * 0.72) * np.pi * (4.2 + seed % 3))
        cyan_route = np.cos((v - warp * 0.55) * np.pi * (5.7 + seed % 4))
        split_route = np.sin((u + v) * np.pi * 3.3 + n1 * 4.0)
        raw = red_route * 0.58 + cyan_route * 0.47 + split_route * 0.31
    elif mode == "chromatic_faultline":
        seam1 = np.exp(-np.abs(u + warp * 0.82) * (11 + seed % 7))
        seam2 = np.exp(-np.abs(v - 0.34 + (n2 - 0.5) * 0.28) * (13 + seed % 5))
        plates = np.floor((n1 * 0.62 + n2 * 0.38) * (6 + seed % 4))
        raw = plates * 0.23 + seam1 * 1.2 - seam2 * 0.84 + np.sign(u) * 0.28
    elif mode == "moire_phase":
        a1 = angle * 0.19 + 0.17
        a2 = a1 + 0.11 + (seed % 5) * 0.012
        q1 = np.sin((x * np.cos(a1) + y * np.sin(a1)) * np.pi * (10 + seed % 5))
        q2 = np.sin((x * np.cos(a2) + y * np.sin(a2)) * np.pi * (10.7 + seed % 5))
        raw = q1 * q2 + np.sin((u + v) * np.pi * 2.2) * 0.24
    elif mode == "radial_burst":
        rays = np.abs(np.cos(theta * (11 + seed % 9) + warp * 2.0))
        raw = rays * (1.18 - np.clip(rad, 0, 1.15)) + rad * 0.26 + n2 * 0.19
    elif mode == "dendritic_crystal":
        sixfold = np.abs(np.cos(theta * 3.0 + n1 * 0.7))
        branches = np.cos(rad * np.pi * (9 + seed % 6) + sixfold * 4.0)
        raw = branches * 0.62 + sixfold * 0.56 + (n2 - 0.5) * 0.28
    elif mode == "topaz_shard_vortex":
        # G-18: dense gem-cut shards follow five logarithmic arms.  This keeps
        # Topaz unmistakably rotational while eliminating the concentric
        # seven-point star it shared with Candy Frozen.  Every diamond is
        # 8-24 px on the native 2048 canvas.
        # A narrow ground lets the dense gem shards own the form; the rejected
        # first pass was visually a broad smooth whirlpool with a few dots.
        raw = (0.30 + u * 0.018 + v * 0.012).astype(np.float32)
        shards = np.zeros((h, w), np.float32)
        shard_mask = np.zeros((h, w), np.float32)
        px_scale = max(0.5, min(h, w) / float(_WORK_CAP))
        center_x = w * 0.54
        center_y = h * 0.46
        phase = (seed % 720) * np.pi / 360.0
        arms = 5
        tracks = 7
        per_track = 40
        for arm in range(arms):
            for track in range(tracks):
                for index in range(per_track):
                    radius = 0.035 + index * 0.024
                    track_offset = (track - 3) * (0.052 + radius * 0.015)
                    a = phase + arm * (2.0 * np.pi / arms) + radius * 9.7 + track_offset
                    sx = center_x + np.cos(a) * radius * w * 0.44
                    sy = center_y + np.sin(a) * radius * h * 0.44
                    tangent = a + np.pi * 0.5 + 0.30
                    tx, ty = np.cos(tangent), np.sin(tangent)
                    nx, ny = -ty, tx
                    long_axis = max(2.0, (4.0 + (index + track + 2 * arm) % 5) * px_scale)
                    short_axis = max(2.0, (2.0 + (2 * index + track + arm) % 3) * px_scale)
                    polygon = np.rint(np.asarray((
                        (sx + tx * long_axis, sy + ty * long_axis),
                        (sx + nx * short_axis, sy + ny * short_axis),
                        (sx - tx * long_axis, sy - ty * long_axis),
                        (sx - nx * short_axis, sy - ny * short_axis),
                    ), np.float32)).astype(np.int32)
                    value = float(np.mod(index * 0.083 + arm * 0.19 + track * 0.11, 1.0))
                    cv2.fillConvexPoly(shard_mask, polygon, 1.0, cv2.LINE_AA)
                    cv2.fillConvexPoly(shards, polygon, value, cv2.LINE_AA)
                    cv2.polylines(shards, [polygon.reshape(-1, 1, 2)], True, float(np.mod(value + 0.24, 1.0)), max(1, int(round(1.5 * px_scale))), cv2.LINE_AA)
        # Independent short facet-glints keep the coil from becoming a lazy
        # single-mark finish. They are bounded 16-32 px arcs at native 2048,
        # never another macro ring or a larger hero feature.
        area = max(0.12, (h * w) / float(_WORK_CAP * _WORK_CAP))
        arc_count = max(50, int(150 * area))
        arc_width = max(1, int(round(4.0 * px_scale)))
        for index in range(arc_count):
            sx = int(rng.integers(0, w))
            sy = int(rng.integers(0, h))
            radius = max(2, int(round((4.0 + index % 5) * px_scale)))
            axes = (radius, max(2, int(round(radius * 0.62))))
            tilt = float(rng.uniform(0.0, 180.0))
            start = float(rng.uniform(0.0, 360.0))
            end = start + float(rng.uniform(40.0, 105.0))
            value = float(np.mod(index * 0.137 + 0.17, 1.0))
            cv2.ellipse(shard_mask, (sx, sy), axes, tilt, start, end, 1.0, arc_width, cv2.LINE_AA)
            cv2.ellipse(shards, (sx, sy), axes, tilt, start, end, value, arc_width, cv2.LINE_AA)
        blend = np.clip(shard_mask, 0.0, 1.0)
        raw = raw * (1.0 - blend) + shards * blend
    elif mode == "pearl_folds":
        fold_a = np.sin((u + n1 * 0.42) * np.pi * (4 + seed % 4))
        fold_b = np.cos((v - n2 * 0.31) * np.pi * (3 + seed % 3))
        raw = np.abs(fold_a * 0.72 + fold_b * 0.44) + (n1 - n2) * 0.22
    elif mode == "anodized_ripples":
        r2 = np.hypot(x - 0.43, y + 0.31)
        r3 = np.hypot(x + 0.48, y - 0.27)
        raw = np.sin(rad * np.pi * (7 + seed % 5)) + np.cos(r2 * np.pi * 9.0) * 0.58 + np.sin(r3 * np.pi * 8.0) * 0.42
    elif mode == "thermal_fracture":
        heat = np.sign(u + warp * 0.72)
        crack = 1.0 - np.clip(np.abs(n1 - n2) * (7 + seed % 5), 0.0, 1.0)
        raw = heat * 0.64 + crack * 0.88 + np.sin(v * 7.0 + n2 * 2.0) * 0.23
    elif mode == "spectra_vortex":
        shell = theta + np.log(rad) * (2.8 + (seed % 5) * 0.25)
        raw = np.sin(shell * (3 + seed % 4)) + np.cos(rad * np.pi * (6 + seed % 6)) * 0.34 + warp
    elif mode == "aqua_current":
        current = np.sin((y + n1 * 0.52) * np.pi * (3 + seed % 4))
        cross = np.cos((x - n2 * 0.31) * np.pi * (5 + seed % 3))
        raw = y * 0.44 + current * 0.43 + cross * 0.27
    elif mode == "eddy_chain":
        raw = np.zeros((h, w), np.float32)
        for ox, oy, direction in ((-0.52, -0.38, 1.0), (0.0, 0.0, -1.0), (0.48, 0.40, 1.0)):
            rr = np.hypot(x - ox, y - oy) + 1e-4
            tt = np.arctan2(y - oy, x - ox)
            raw += np.sin(tt * 4.0 * direction + rr * 11.0) / (0.8 + rr)
    elif mode == "logarithmic_shells":
        raw = np.mod(theta / (2.0 * np.pi) + np.log(rad) * (1.2 + (seed % 5) * 0.13), 1.0) + n1 * 0.18
    elif mode == "vortex_bubbles":
        bubbles = np.sin(rad * np.pi * (8 + seed % 7) + theta * 3.0)
        raw = bubbles * 0.52 + np.cos(theta * (5 + seed % 5) - rad * 9.0) * 0.42 + n2 * 0.36
    elif mode == "pinwheel_shards":
        sectors = 9 + seed % 8
        shard = np.floor((theta + np.pi + rad * 2.4) / (2.0 * np.pi) * sectors)
        raw = shard * 0.19 + np.sin(rad * np.pi * (4 + seed % 5) + shard * 0.8) + warp
    elif mode == "whirlpool_rift":
        seam = np.exp(-np.abs(np.sin(theta + rad * (4.5 + seed % 4))) * (6 + seed % 5))
        raw = np.sin(theta * 3.0 + rad * 14.0) * 0.48 + seam * 1.05 + n1 * 0.26
    elif mode == "turbine_blades":
        blades = np.mod((theta + rad * (3.1 + seed % 4)) / (2.0 * np.pi) * (8 + seed % 7), 1.0)
        raw = blades + np.cos(rad * np.pi * (5 + seed % 4)) * 0.28 + warp
    elif mode == "countercurrent_vortex":
        raw = np.sin(theta * (4 + seed % 4) + rad * 13.0) + np.cos(-theta * (6 + seed % 5) + rad * 8.0) * 0.67 + warp
    elif mode == "vortex_ribbons":
        ribbons = np.abs(np.mod((theta + rad * (5.0 + seed % 4)) / np.pi * (3 + seed % 4), 2.0) - 1.0)
        raw = ribbons * 0.82 + np.sin(rad * np.pi * (4 + seed % 4)) * 0.31 + n1 * 0.22
    else:
        raw = u + warp

    # Palette occupancy is a shipping contract for the 10-15-color designs.
    # Extrema-only normalization left some end colors on <0.05% of the panel;
    # equalizing the scalar route keeps the same topology/order while ensuring
    # every authored stop owns meaningful visible area.
    raw_norm = _norm(raw)
    t0 = np.clip(raw_norm * 255.0, 0, 255).astype(np.uint8)
    equalized = cv2.equalizeHist(t0).astype(np.float32) / 255.0
    # G-12: CDF remapping is monotonic, so it preserves the newly authored
    # ribbons/plates/branches while guaranteeing that even a 15-stop extreme
    # actually shows its endpoint colors.  The former visual convergence came
    # from shared periodic geometry and wrapped micro-phase, not this ordering.
    if mode in MATH_TOPOLOGIES:
        equalize_mix = _MATH_EQUALIZE_BLEND[mode]
        t = _norm(raw_norm * (1.0 - equalize_mix) + equalized * equalize_mix)
    else:
        t = equalized.astype(np.float32)
    blur = cv2.GaussianBlur(t, (0, 0), 1.2)
    gy, gx = np.gradient(blur)
    hero = _norm(np.hypot(gx, gy))
    relief = np.clip(1.0 + gx * 3.0 - gy * 2.2, 0.74, 1.26).astype(np.float32)
    return t, hero, relief


def _fine_fields(h: int, w: int, seed: int):
    """Six local mark types, all 4-16 px on the 1024 work grid.

    At a native 2048 render that is 8-32 px, matching the owner's finish
    doctrine.  Counts scale by area, not mark size.
    """
    area = max(0.12, (h * w) / float(_WORK_CAP * _WORK_CAP))
    px_scale = max(0.5, min(h, w) / float(_WORK_CAP))
    # G-7 owner-eye/M7 iteration: the first v3 pass kept the correct 8-32 px
    # scale but its low mark counts and 10-16% blends made the detail disappear
    # on the car (512 audit paintFineEnergy 0.0008-0.0288, all below the 0.055
    # catalog P60). Increase density, never feature size, per owner doctrine.
    # G-10 owner-eye correction: a fixed four-axis carrier produced the same
    # neon triangle/star lattice over otherwise unrelated glaciers, reefs,
    # spline pools, and kaleidoscopes.  Varying axis count, pitch, and warp by
    # the stable recipe seed keeps the required fine energy without turning a
    # shared helper into the visible identity of every finish.
    grain_axes = 1 + (seed % 4)
    grain_pitch = (4.5 + ((seed >> 3) % 8) * 0.78) * px_scale
    grain_warp = 0.36 + ((seed >> 7) % 6) * 0.075
    grain = flow_grain(
        h, w, seed ^ 0x410, axes=grain_axes,
        freq_px=grain_pitch, warp=grain_warp,
    )
    flecks = micro_scatter(h, w, seed ^ 0x421, max(360, int(1500 * area)), 4.2 * px_scale, kind="dot", amp=(0.32, 1.0))
    arcs = micro_scatter(h, w, seed ^ 0x432, max(150, int(620 * area)), 8.0 * px_scale, kind="arc", amp=(0.38, 1.0))
    streaks = micro_scatter(h, w, seed ^ 0x443, max(210, int(860 * area)), 3.8 * px_scale, kind="streak", amp=(0.34, 0.96), len_px=13.0 * px_scale)
    rings = ring_swarm(h, w, seed ^ 0x454, max(95, int(390 * area)), 12.0 * px_scale, pitch_px=3.8 * px_scale)
    petals = micro_scatter(h, w, seed ^ 0x465, max(150, int(610 * area)), 7.0 * px_scale, kind="petal", amp=(0.34, 0.94))
    return tuple(np.clip(a, 0.0, 1.0).astype(np.float32) for a in (grain, flecks, arcs, streaks, rings, petals))


_FIELD_CACHE: OrderedDict[tuple[str, int, int, int], tuple[np.ndarray, ...]] = OrderedDict()

# G-14 measured quiet-tail correction at the fixed 512 audit/car-sampling
# scale.  These semantically dark or near-isoluminant palettes hid otherwise
# valid 8-32 px marks. Targets normalize local contrast only for the measured
# laggards; every other finish keeps the restrained shared relief gain.
_FINE_LOCAL_STD_TARGETS = {
    "grad_ultraviolet": 0.60,
    "grad_maroon_vortex": 0.18,
    "grad_plum_vortex": 0.15,
    "grad_ember_ash": 0.14,
    "grad_graphite_vortex": 0.14,
    "gradient_obsidian_mirror": 0.14,
    "grd_digital_acid_rain": 0.14,
    "grad_pink_vortex": 0.14,
    "grad_fire_fade_h": 0.14,
    "grad_crimson_vortex": 0.14,
    "grad_rose_gold_h": 0.14,
    "grad_pewter_rose": 0.14,
    # G-16 provisional M7 tail: each of these missed only the catalog's HI
    # fine-energy rank (M6 5/6) after every color/spec axis passed. Density and
    # 8-32 px pitch stay unchanged; normalize local contrast to the same floor.
    "grad_midnight_ember": 0.14,
    "grad_teal_vortex": 0.14,
    "grad_ruby_vortex": 0.14,
    "grad_neon_violet": 0.14,
    "grad_patriot": 0.14,
    "grad_magma": 0.14,
    "grad_patriot_h": 0.14,
    "grad_magma_h": 0.14,
    "grad_sapphire_vortex": 0.14,
    "grad_lavender_dusk": 0.14,
    "grad_aqua_vortex": 0.14,
    "grad_electric_lime": 0.14,
    "grad_coral_sea": 0.14,
    "gradient_chrome_matte": 0.14,
    "grd_velvet_spectrum_crash": 0.14,
    "grad_champagne_vortex": 0.14,
    "grad_frostbite": 0.14,
    "grd_cosmic_heatmap": 0.14,
    "grad_twilight_h": 0.14,
    "grad_chocolate_vortex": 0.14,
    "grad_ivory_cobalt": 0.14,
    "grd_iridescent": 0.14,
    # G-17 contact-sheet weak-detail tail: contrast/density only, never size.
    "grd_spectral_sweep": 0.18,
    "grd_oklab_flow": 0.16,
    # GM-8 percentile-boundary ratchet after adding the twelve math cards.
    # These three already-shipping extreme Gradients were visually accepted,
    # but the enlarged 178-card workbook moved their HIGH fine-energy cutoff
    # just above the unchanged paint bytes (M7 84.3/84.8/84.6).  Lift only the
    # contrast of their existing dense 8-32 px carrier, never its size or
    # topology. Metric movement: M7 84.3/84.8/84.6 -> 93.0/92.3/93.8;
    # the expanded shelf returns to 178/178 >=85.
    "grd_hyperprism_supernova": 0.11,
    "grd_neon_cathedral": 0.11,
    "grd_ultraviolet_solarstorm": 0.11,
    "grad_ocean_depths": 0.14,
    "grad_twilight_diag": 0.14,
    "grad_ocean_depths_diag": 0.14,
    "grad_wine_silk": 0.14,
    "gradient_candy_matte": 0.14,
    "grad_storm_front": 0.14,
}


def clear_gradient_cache() -> None:
    _FIELD_CACHE.clear()
    _lut.cache_clear()
    _oklab_lut.cache_clear()


def _fields(recipe: GradientRecipe, h: int, w: int, seed: int):
    key = (recipe.finish_id, int(h), int(w), int(seed))
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        _FIELD_CACHE.move_to_end(key)
        return cached
    fine = list(_fine_fields(h, w, seed))
    if recipe.finish_id in _GD.DESIGNS:
        fine[0] = _GD.fine_field(recipe.finish_id, seed, h, w)   # design-keyed grain, not the shelf-wide screen
    out = (*_macro_fields(recipe, h, w, seed), *fine)
    _FIELD_CACHE[key] = out
    _FIELD_CACHE.move_to_end(key)
    while len(_FIELD_CACHE) > _FIELD_CACHE_MAX:
        _FIELD_CACHE.popitem(last=False)
    return out


@lru_cache(maxsize=256)
def _lut(palette: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    return np.asarray(ramp_lut(palette, flatten=0.34, n=1537), np.float32)


@lru_cache(maxsize=64)
def _oklab_lut(palette: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    """Perceptual LUT for the math wave, using the June Gradient Math API.

    Calling the existing ``oklab_ramp`` on a one-row coordinate builds the LUT
    once; full-resolution renders remain a gather through ``ramp_apply``. This
    preserves clean 10-15-stop travel without changing any pre-GM recipe bytes.
    """
    positions = np.linspace(0.0, 1.0, len(palette), dtype=np.float32)
    stops = [(float(pos), tuple(float(channel) for channel in color))
             for pos, color in zip(positions, palette)]
    route = np.linspace(0.0, 1.0, 1537, dtype=np.float32)[None, :]
    return np.asarray(oklab_ramp(route, stops, lut_n=1537)[0], np.float32)


def _paint_work(recipe: GradientRecipe, h: int, w: int, seed: int) -> np.ndarray:
    t, hero, relief, grain, flecks, arcs, streaks, rings, petals = _fields(recipe, h, w, seed)
    lut = _oklab_lut(recipe.palette) if recipe.color_space == "oklab" else _lut(recipe.palette)
    col = np.asarray(ramp_apply(t, lut), np.float32)
    if recipe.family == "math":
        # SPB-GRADIENT-MATH-2026-08-23 / GM-4 owner-eye bake correction.
        # Verdict: the initial twelve were exact-hash unique but eight read as
        # the same RGB-confetti surface.  Keep all six 8-32 px mark families,
        # but make them material accents instead of a seventh shared topology;
        # the composed math field must own the silhouette. Metric movement:
        # unregistered -> official M7 90.6-93.6 after owner-eye promotion.
        phase = np.clip(
            t
            + (grain - 0.50) * 0.018
            + (arcs - rings) * 0.010
            + (streaks - petals) * 0.007,
            0.0, 1.0,
        )
        companion = np.asarray(ramp_apply(phase, lut), np.float32)
        col = col * (0.86 + relief[..., None] * 0.14)
        marks = np.maximum.reduce((
            flecks, arcs * 0.88, streaks * 0.82, rings * 0.84, petals * 0.86,
        ))
        detail_mix = np.clip(0.035 * grain + 0.075 * marks, 0.01, 0.10).astype(np.float32)
        col = col * (1.0 - detail_mix[..., None]) + companion * detail_mix[..., None]
        col += flecks[..., None] * np.float32(recipe.palette[-1])[None, None, :] * 0.070
        col += arcs[..., None] * np.float32(recipe.palette[max(1, len(recipe.palette) // 3)])[None, None, :] * 0.055
        col -= streaks[..., None] * np.float32([0.042, 0.035, 0.028])[None, None, :]
        col += rings[..., None] * np.float32(recipe.palette[(2 * len(recipe.palette)) // 3])[None, None, :] * 0.052
        col += petals[..., None] * np.float32(recipe.palette[len(recipe.palette) // 2])[None, None, :] * 0.055
        grain_local = grain - cv2.GaussianBlur(grain, (0, 0), 0.90)
        # SPB-GRADIENT-MATH-2026-08-23 / GM-7, owner doctrine: Viscous Prism's
        # accepted multi-injection fingers still measured too quiet between the
        # branches at the fixed 512 audit scale.  Raise contrast on the existing
        # dense 8-32 px carrier (never its pitch or primitive size) so the fine
        # detail survives a car-panel preview.  Metric movement: official M7
        # 79.5 -> 93.6; paintFineEnergy 0.028196 -> 0.077577.
        grain_gain = 0.70 if recipe.topology == "viscous_schlieren" else 0.18
        signed_relief = (
            grain_local * grain_gain
            + (flecks - arcs) * 0.045
            + (rings - petals) * 0.040
            + (streaks - 0.38 * flecks) * 0.030
        ).astype(np.float32)
        col += signed_relief[..., None]
        col += hero[..., None] * np.float32(recipe.palette[-1])[None, None, :] * 0.065
        return np.clip((col - 0.5) * 1.045 + 0.5, 0.0, 1.0).astype(np.float32)

    # G-11 owner-eye correction: wrapping by as much as 0.50 sent a local
    # micro mark across 3-7 authored stops and made every 10-15-color recipe
    # read as the same rainbow contour textile.  Fine marks now perturb within
    # roughly one stop and reflect at the ramp ends instead of joining them.
    phase = np.clip(
        t
        + (grain - 0.50) * 0.055
        + (arcs - rings) * 0.030
        + (streaks - petals) * 0.018,
        0.0, 1.0,
    )
    companion = np.asarray(ramp_apply(phase, lut), np.float32)
    col = col * (0.80 + relief[..., None] * 0.20)
    # Dense chromatic micro-carrier: every one of the six mark families changes
    # either hue or value, while the macro field remains legible underneath.
    marks = np.maximum.reduce((flecks, arcs * 0.88, streaks * 0.82, rings * 0.84, petals * 0.86))
    detail_mix = np.clip(0.11 * grain + 0.24 * marks, 0.03, 0.31).astype(np.float32)
    col = col * (1.0 - detail_mix[..., None]) + companion * detail_mix[..., None]
    col += flecks[..., None] * np.float32(recipe.palette[-1])[None, None, :] * 0.23
    col += arcs[..., None] * np.float32(recipe.palette[max(1, len(recipe.palette) // 3)])[None, None, :] * 0.20
    col -= streaks[..., None] * np.float32([0.13, 0.105, 0.08])[None, None, :]
    col += rings[..., None] * np.float32(recipe.palette[(2 * len(recipe.palette)) // 3])[None, None, :] * 0.18
    col += petals[..., None] * np.float32(recipe.palette[len(recipe.palette) // 2])[None, None, :] * 0.19
    # Absolute (not merely multiplicative) fine relief keeps dark, chrome, and
    # obsidian recipes detailed too. Flow-grain pitch is 8-20 px at native 2048.
    # G-9 lifted the fine-detail tail, but its 0.84 universal carrier became a
    # visual topology of its own.  G-10 returns the carrier to relief scale and
    # gives the five sparse mark families more influence; fine energy now comes
    # from dense 8-32 px detail rather than a single repeated lattice.
    grain_local = grain - cv2.GaussianBlur(grain, (0, 0), 0.90)
    # Normalize only the measured quiet tail. Applying one high target to all
    # 166 made already-strong spline/kaleidoscope cards read as black textile.
    # The stable seed still owns axis count, direction, pitch, and topology.
    target_std = _FINE_LOCAL_STD_TARGETS.get(recipe.finish_id)
    grain_gain = 0.58 if target_std is None else float(
        np.clip(target_std / max(float(grain_local.std()), 1e-4), 0.58, 7.40)
    )
    signed_relief = (
        grain_local * grain_gain
        + (flecks - arcs) * 0.15
        + (rings - petals) * 0.13
        + (streaks - 0.38 * flecks) * 0.085
    ).astype(np.float32)
    col += signed_relief[..., None]
    col += hero[..., None] * np.float32(recipe.palette[-1])[None, None, :] * 0.10
    return np.clip((col - 0.5) * 1.07 + 0.5, 0.0, 1.0).astype(np.float32)


_M_TIERS = np.float32([2, 28, 56, 88, 124, 164, 210, 252])
_R_TIERS = np.float32([16, 38, 64, 92, 124, 158, 198, 236])
_C_TIERS = np.float32([16, 40, 68, 98, 130, 166, 210, 248])


def _tier(field: np.ndarray, palette: np.ndarray) -> np.ndarray:
    # Equalize occupancy before quantization.  Merely normalizing extrema left
    # calm directional recipes with six nominal tiers but almost every pixel in
    # two middle shades (tick G-1 native probe: M std 16.34).  Equalization keeps
    # the geometry intact while making all eight authored material shades carry
    # real surface area, as the owner's spec-color doctrine requires.
    u8 = np.clip(_norm(field) * 255.0, 0, 255).astype(np.uint8)
    balanced = cv2.equalizeHist(u8)
    index = np.minimum((balanced.astype(np.int32) // 32), 7)
    return palette[index]


def _spec_work(recipe: GradientRecipe, h: int, w: int, seed: int):
    t, hero, relief, grain, flecks, arcs, streaks, rings, petals = _fields(recipe, h, w, seed)
    broad_m = _smooth_noise(h, w, seed ^ 0x5C1, 7)
    broad_r = _smooth_noise(h, w, seed ^ 0x6D2, 9)
    broad_c = _smooth_noise(h, w, seed ^ 0x7E3, 11)
    if recipe.family == "math":
        # GM-6 owner-eye spec correction: the first wave had rich numeric tiers
        # but all twelve cards read as the same magenta/green/blue static because
        # generic decor marks outweighed the authored topology.  Faces, ridges,
        # flow age and weave relief now own most of M/R/Cc; independent broad and
        # micro terms preserve eight decorrelated shades per channel. Metric
        # movement: unregistered -> official M7 90.6-93.6 (12/12 >=85).
        slope = _norm(np.abs(relief - 1.0))
        if recipe.topology in {
            "bismuth_chladni", "ferrofluid_gyroid", "scarab_cascade", "nacre_filament",
        }:
            m_field = t * 0.46 + hero * 0.25 + flecks * 0.09 + broad_m * 0.20
            r_field = (1.0 - t) * 0.34 + slope * 0.22 + streaks * 0.13 + broad_r * 0.31
            c_field = hero * 0.36 + t * 0.20 + rings * 0.13 + petals * 0.09 + broad_c * 0.22
        elif recipe.topology in {"stable_ink_caustics", "nebulabrot_ionstorm"}:
            # GM-7: the first official workbook pass found the three material
            # channels too correlated even though each already carried eight
            # shades (Nebulabrot M7 81.7; Stable Ink 83.9).  Give M, R, and Cc
            # different semantic views of the same math source -- occupied
            # faces, flow-age slope, and ion/caustic ridges -- plus independent
            # fine marks and broad modulation.  This preserves the accepted
            # paint topology while making angle response genuinely different;
            # final M7 moved to 91.7 and 93.0 respectively.
            m_field = t * 0.38 + arcs * 0.22 + broad_m * 0.40
            r_field = slope * 0.38 + grain * 0.22 + broad_r * 0.40
            c_field = hero * 0.38 + rings * 0.12 + petals * 0.10 + broad_c * 0.40
        elif recipe.topology == "viscous_schlieren":
            m_field = t * 0.38 + slope * 0.18 + arcs * 0.13 + broad_m * 0.31
            r_field = (1.0 - t) * 0.39 + grain * 0.15 + streaks * 0.12 + broad_r * 0.34
            c_field = hero * 0.34 + t * 0.25 + rings * 0.12 + petals * 0.10 + broad_c * 0.19
        else:
            m_field = hero * 0.38 + t * 0.24 + flecks * 0.12 + broad_m * 0.26
            r_field = (1.0 - t) * 0.31 + slope * 0.21 + streaks * 0.13 + broad_r * 0.35
            c_field = t * 0.33 + hero * 0.24 + arcs * 0.11 + petals * 0.10 + broad_c * 0.22
        m_out = _tier(m_field, _M_TIERS)
        r_out = _tier(r_field, _R_TIERS)
        c_out = _tier(c_field, _C_TIERS)
        if recipe.topology == "nebulabrot_ionstorm":
            # GM-7 owner-eye follow-up: decorrelation alone made the spec read
            # like an unrelated full-frame cloud.  Preserve the Nebulabrot's
            # defining unoccupied orbit basin as a shared low-response void;
            # the surrounding face/slope/ridge channels remain independently
            # tiered and keep their wide 8-shade ranges.
            orbit_void = t < 0.08
            m_out = np.where(orbit_void, _M_TIERS[0], m_out)
            r_out = np.where(orbit_void, _R_TIERS[0], r_out)
            c_out = np.where(orbit_void, _C_TIERS[0], c_out)
        return m_out, r_out, c_out

    # Each channel traces the color field but owns a different fine-mark mix.
    # Eight tiers are deliberately broad and exact; no dark-base/bright-peak shortcut.
    if recipe.finish_id in _GD.DESIGNS:
        # 2026-09-02: same eight-tier, six-mark material composition the owner called
        # "legitimately impressive", but its geography now traces THIS finish's design
        # (the Uniqueness Law: the spec mirrors the paint's structure). grain is already
        # design-keyed (see _fields).
        d = _GD.design_field(recipe.finish_id, seed, h, w)
        # three different views of the same design so the eight tiers stay multi-hued:
        # M = the design's tone, R = its keyed grain (inverse), Cc = its edges.
        m_field = d * 0.34 + hero * 0.12 + flecks * 0.16 + arcs * 0.12 + petals * 0.10 + broad_m * 0.16
        r_field = grain * 0.24 + (1.0 - d) * 0.24 + streaks * 0.16 + rings * 0.12 + (1.0 - t) * 0.10 + broad_r * 0.14
        c_field = d * 0.22 + hero * 0.18 + arcs * 0.13 + rings * 0.14 + petals * 0.12 + t * 0.08 + broad_c * 0.13
        return _tier(m_field, _M_TIERS), _tier(r_field, _R_TIERS), _tier(c_field, _C_TIERS)
    m_field = hero * 0.33 + flecks * 0.20 + arcs * 0.18 + petals * 0.11 + broad_m * 0.18
    r_field = grain * 0.29 + streaks * 0.23 + rings * 0.18 + (1.0 - t) * 0.13 + broad_r * 0.17
    c_field = hero * 0.18 + arcs * 0.18 + rings * 0.20 + petals * 0.19 + t * 0.10 + broad_c * 0.15
    return _tier(m_field, _M_TIERS), _tier(r_field, _R_TIERS), _tier(c_field, _C_TIERS)


def _make_pair(recipe: GradientRecipe):
    def spec_fn(shape, mask, seed, sm, _recipe=recipe):
        h, w, fh, fw = _work_dims(shape)
        local_seed = _seed_for(_recipe.finish_id, seed)
        m, r, cc = _spec_work(_recipe, h, w, local_seed)
        m, r, cc = (_upscale(a.astype(np.float32), fh, fw) for a in (m, r, cc))
        return _pack_spec(m, r, cc, _mask2(mask, fh, fw), sm, fh, fw)

    def paint_fn(paint, shape, mask, seed, pm, bb, _recipe=recipe):
        h, w, fh, fw = _work_dims(shape)
        local_seed = _seed_for(_recipe.finish_id, seed)
        effect = _upscale(_paint_work(_recipe, h, w, local_seed), fh, fw)
        return _blend_paint(paint, effect, _mask2(mask, fh, fw), pm)

    spec_fn.__name__ = f"spec_{recipe.finish_id}"
    paint_fn.__name__ = f"paint_{recipe.finish_id}"
    spec_fn._spb_gradient_recipe = recipe  # type: ignore[attr-defined]
    paint_fn._spb_gradient_recipe = recipe  # type: ignore[attr-defined]
    if recipe.family == "math":
        # GM-2 buyer-cache truth: factory wrapper bytecode does not change when
        # an imported field engine changes. Declare the exact shared sources on
        # only the 12 math recipes so server hashing can invalidate those cards
        # without rebaking the other 166 Gradients.
        dependencies = (
            "engine.expansions.gradient_math_wave_2026",
            "engine.paint_v2.gradient_math",
            *MATH_DEPENDENCY_MODULES,
        )
        spec_fn._spb_picker_dependency_modules = dependencies  # type: ignore[attr-defined]
        paint_fn._spb_picker_dependency_modules = dependencies  # type: ignore[attr-defined]
    return spec_fn, paint_fn


def _make_base_pair(recipe: GradientRecipe):
    spec_fn, paint_fn = _make_pair(recipe)

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, **_kwargs):
        h, w, fh, fw = _work_dims(shape)
        local_seed = _seed_for(recipe.finish_id, seed)
        m, r, cc = _spec_work(recipe, h, w, local_seed)
        return tuple(_upscale(a.astype(np.float32), fh, fw) for a in (m, r, cc))

    base_spec_fn.__name__ = f"base_spec_{recipe.finish_id}"
    base_spec_fn._spb_gradient_recipe = recipe  # type: ignore[attr-defined]
    return base_spec_fn, paint_fn


def _catalog_gradient_rows():
    try:
        from engine.expansions.owner_review_gradients import _read_gradient_defs

        return list(_read_gradient_defs())
    except Exception:
        return []


def _build_recipes(mono_reg, fusion_reg=None) -> dict[str, GradientRecipe]:
    recipes: dict[str, GradientRecipe] = {}
    for finish_id, name, c1_name, c2_name in _catalog_gradient_rows():
        if finish_id in EXTREME_SPECS:
            continue
        variant = _stable_int(finish_id) & 0x7FFFFFFF
        if finish_id.endswith("_vortex") or "vortex" in name.lower():
            topology = _STANDARD_VORTEX[variant % len(_STANDARD_VORTEX)]
            orientation = "vortex"
        elif finish_id.endswith("_h"):
            topology = ("braided_flow", "crosscurrent", "ribbon_fold", "directional_wave")[variant % 4]
            orientation = "horizontal"
        elif finish_id.endswith("_diag"):
            topology = ("directional_prism", "fan_burst", "flow", "waterfall")[variant % 4]
            orientation = "diagonal"
        else:
            topology = _STANDARD_DIRECTIONAL[variant % len(_STANDARD_DIRECTIONAL)]
            orientation = "vertical"
        topology = _LEGACY_TOPOLOGY_OVERRIDES.get(finish_id, topology)
        count = 7 + variant % 3
        palette = _legacy_palette(COLOR_PALETTE[c1_name], COLOR_PALETTE[c2_name], count, variant)
        recipes[finish_id] = GradientRecipe(
            finish_id, "legacy", topology, palette, count, variant, orientation=orientation
        )

    for finish_id, (_name, topology, count, anchors) in EXTREME_SPECS.items():
        variant = _stable_int(finish_id) & 0x7FFFFFFF
        recipes[finish_id] = GradientRecipe(
            finish_id, "extreme", topology, _resample_anchors(anchors, count), count, variant, "hyperchromatic"
        )

    for finish_id, (_name, topology, count, anchors) in MATH_SPECS.items():
        variant = _stable_int(finish_id) & 0x7FFFFFFF
        recipes[finish_id] = GradientRecipe(
            finish_id=finish_id,
            family="math",
            topology=topology,
            palette=_resample_anchors(anchors, count),
            stop_count=count,
            variant=variant,
            material_profile="math_hyperchromatic",
            orientation="free",
            color_space="oklab",
        )

    for finish_id, (topology, count, anchors) in _GRD_SPECS.items():
        # Register unconditionally.  engine.registry historically omitted this
        # entire 11-card family even while the legacy registry and picker showed
        # it, so the production zone validator rejected every grd_* id.
        variant = _stable_int(finish_id) & 0x7FFFFFFF
        recipes[finish_id] = GradientRecipe(
            finish_id, "showcase", topology, _resample_anchors(anchors, count), count, variant, "hyperchromatic"
        )

    material_ids = set(k for k in mono_reg if k.startswith("gradient_"))
    if fusion_reg:
        material_ids.update(k for k in fusion_reg if k.startswith("gradient_"))
    for finish_id in sorted(material_ids):
        if finish_id not in _MATERIAL_SPECS:
            continue
        topology, profile, anchors = _MATERIAL_SPECS[finish_id]
        variant = _stable_int(finish_id) & 0x7FFFFFFF
        count = 8 + variant % 3
        recipes[finish_id] = GradientRecipe(
            finish_id, "material", topology, _resample_anchors(anchors, count), count, variant, profile
        )
    return recipes


_RECIPE_BY_ID: dict[str, GradientRecipe] = {}


def gradient_recipe(finish_id: str) -> GradientRecipe | None:
    return _RECIPE_BY_ID.get(finish_id)


def gradient_palette_occupancy(finish_id: str, size: int = 256, seed: int = 7301) -> tuple[float, ...]:
    """Fraction of the routed color field owned by each authored stop.

    This is deliberately measured before relief/glints alter RGB, because it
    answers the release question that matters: are all claimed 10-15 colors
    actually routed onto the surface, or are some decorative dead entries?
    """
    recipe = _RECIPE_BY_ID.get(finish_id)
    if recipe is None:
        return ()
    local_seed = _seed_for(recipe.finish_id, seed)
    t = _fields(recipe, int(size), int(size), local_seed)[0]
    index = np.clip(np.rint(t * (recipe.stop_count - 1)), 0, recipe.stop_count - 1).astype(np.int32)
    counts = np.bincount(index.ravel(), minlength=recipe.stop_count).astype(np.float64)
    counts /= max(float(counts.sum()), 1.0)
    return tuple(float(value) for value in counts)


def install_gradient_overhaul(mono_reg, base_reg=None, fusion_reg=None) -> dict[str, int]:
    """Install the overhaul as final authority over all shipping Gradient ids."""
    recipes = _build_recipes(mono_reg, fusion_reg)
    _RECIPE_BY_ID.clear()
    _RECIPE_BY_ID.update(recipes)
    counts = {"legacy": 0, "extreme": 0, "math": 0, "showcase": 0, "material": 0}

    for finish_id, recipe in recipes.items():
        pair = _make_pair(recipe)
        mono_reg[finish_id] = pair
        if fusion_reg is not None and finish_id.startswith("gradient_"):
            fusion_reg[finish_id] = pair
        if base_reg is not None:
            entry = base_reg.get(finish_id)
            if isinstance(entry, dict) and "base_spec_fn" in entry:
                entry["base_spec_fn"], entry["paint_fn"] = _make_base_pair(recipe)
        counts[recipe.family] += 1
    return counts


__all__ = [
    "EXTREME_SPECS",
    "MATH_SPECS",
    "GradientRecipe",
    "clear_gradient_cache",
    "gradient_palette_occupancy",
    "gradient_recipe",
    "install_gradient_overhaul",
]
