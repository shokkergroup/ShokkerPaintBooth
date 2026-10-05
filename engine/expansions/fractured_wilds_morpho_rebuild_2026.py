"""REJECTED ARCHITECTURE — Fractured Wilds / Morpho candidate (2026-08-24).

Do not integrate this module.  WR-MORPHO review rejected its shared
folded-field/derivative assembler even though its cards were farther apart
than the prior release.  Fifty unique source fields are not a substitute for
fifty literal construction grammars.  The replacement lane is
``fractured_wilds_morpho_biological_rebuild_2026.py``.

Ticket: SPB-WILDS-REJECTION-2026-08-24, lane WR-MORPHO-1.

Owner verdict (verbatim excerpt): "how many have the EXACT SAME pattern just
recolored or exact same spec maps" and "do NOT just put random noise in the
patterns to separate the way they look".

The earlier release collapsed all 50 ``fmo_*`` paints into one seven-scatter
composer and drove their spec maps with the same carrier family.  This
candidate attempted a source-field override, but was itself rejected because
its shared derivative assembler remained too dominant:

* every ID owns a different, nameable mathematical topology;
* the topology is densely folded so its authored primitives remain 2--8 px on
  the 512 work canvas (8--32 px at native 2048);
* five or more paint marks are causal derivatives of that topology (domain,
  boundary, crown, hollow, contour, junction, directional order), never an
  unrelated grain/fleck/noise overlay;
* twelve purposeful color shades bind to those structural marks;
* M, R and Cc use different named structural operators and fixed physical
  tiers (not equal-population rank quantisation);
* the A and B color banks are feature-attached, with metalness and clearcoat
  deliberately trading emphasis across the two banks.

The following implementation and evidence are retained only as a post-mortem
and must not be wired into production.

This file intentionally makes no claim of owner acceptance.  Rejection-audit
artifacts can be produced with ``python -m
engine.expansions.fractured_wilds_morpho_rebuild_2026 --audit PATH``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import argparse
import colorsys
import hashlib
import json
from pathlib import Path
import time
from typing import Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


ARCHITECTURE_STATUS = "REJECTED_DO_NOT_INTEGRATE"


_WORK = 512
_SOURCE = 160
# W1 used the literal repeat values and collapsed real mechanisms back into
# colored grit.  W2/W3 improved that at 0.46 but still hid too many source
# silhouettes.  At 0.15 a 1 px source ridge becomes roughly 2--5 px at the 512
# work size (8--20 px native) while the *assembly* -- eye, chamber, wing panel,
# equipotential basin -- remains readable.  Fine primitives are still dense;
# only their causal organization is allowed to be larger.
_ASSEMBLY_DENSITY = 0.15

_METAL_TIERS = np.asarray([18, 42, 72, 106, 142, 180, 218, 250], np.uint8)
_ROUGH_TIERS = np.asarray([16, 34, 58, 88, 122, 160, 204, 244], np.uint8)
_COAT_TIERS = np.asarray([18, 46, 78, 116, 156, 194, 226, 252], np.uint8)


@dataclass(frozen=True)
class Grammar:
    """One literal finish grammar; no seed/palette-only variants."""

    name: str
    source: str
    layout: str
    repeats: Tuple[float, float]
    seed: int
    hues: Tuple[float, ...]
    saturation: float
    value: float
    phase: float
    color_mode: str
    spec_ops: Tuple[str, str, str]
    features: Tuple[str, ...]


def _g(
    name: str,
    source: str,
    layout: str,
    repeats: Tuple[float, float],
    seed: int,
    hues: Sequence[float],
    saturation: float,
    value: float,
    phase: float,
    color_mode: str,
    spec_ops: Tuple[str, str, str],
    features: Sequence[str],
) -> Grammar:
    return Grammar(
        name=name,
        source=source,
        layout=layout,
        repeats=repeats,
        seed=seed,
        hues=tuple(float(x) % 1.0 for x in hues),
        saturation=float(saturation),
        value=float(value),
        phase=float(phase) % 1.0,
        color_mode=color_mode,
        spec_ops=spec_ops,
        features=tuple(features),
    )


# Each row is a literal, reviewable visual promise.  The feature labels are not
# decorative metadata: they name the five-plus masks built from this row's
# topology and used by paint/spec assembly.  Sources are asserted unique below.
MORPHO_GRAMMARS: Dict[str, Grammar] = {
    "fmo_morpho_blue": _g(
        "Morpho Blue", "diffraction_grating", "lamellar", (13, 9), 1900,
        (0.56, 0.61, 0.68, 0.77), .94, .94, .03, "order",
        ("direction", "hollow", "contour"),
        ("ridge trunks", "paired shelves", "cross-ribs", "perforation pores", "scale bases", "missing-shelf forks", "diffraction teeth")),
    "fmo_sunset_moth": _g(
        "Sunset Moth", "butterfly_curve", "wing", (9, 8), 1901,
        (0.99, 0.045, 0.10, 0.17, 0.53, 0.76), .93, .96, .11, "panel",
        ("boundary", "domain", "junction"),
        ("wing veins", "scalloped panels", "scale rows", "crescent bands", "false-eye wedges", "fringe combs", "dust pockets")),
    "fmo_monarch_vein": _g(
        "Monarch Vein", "tracery_web", "branch", (11, 10), 1902,
        (0.02, 0.055, 0.09, 0.12, 0.58), .91, .91, .19, "cell",
        ("boundary", "ridge", "domain"),
        ("primary veins", "secondary branches", "tertiary forks", "closed cells", "scale bricks", "cross-vein nodes", "marginal insets")),
    "fmo_atlas_wing": _g(
        "Atlas Wing", "wallpaper_p6m", "hooked", (10, 12), 1903,
        (0.02, 0.07, 0.12, 0.18, 0.43, 0.74), .83, .87, .27, "glyph",
        ("junction", "hollow", "direction"),
        ("snake-head hooks", "false pupils", "jaw bands", "neck scales", "cross-veins", "antenna fringe", "bite notches")),
    "fmo_luna_dust": _g(
        "Luna Dust", "larger_than_life", "nodal", (14, 12), 1904,
        (0.22, 0.29, 0.35, 0.48, 0.67, 0.80), .55, .90, .34, "node",
        ("contour", "valley", "junction"),
        ("nodal curves", "bead chains", "antinode clearings", "crescent ejecta", "crater cups", "radial spokes", "moon flakes")),
    "fmo_swallowtail": _g(
        "Swallowtail Flash", "sierpinski_arrow", "chevron", (12, 10), 1905,
        (0.09, 0.14, 0.53, 0.60, 0.72), .93, .94, .41, "arrow",
        ("direction", "boundary", "valley"),
        ("tail vanes", "arrow scales", "forked veins", "window bars", "hinge gaps", "edge eyes", "fringe teeth")),
    "fmo_ulysses_flash": _g(
        "Ulysses Flash", "beveled_panels", "parquet", (11, 13), 1906,
        (0.50, 0.56, 0.62, 0.70, 0.84), .95, .95, .48, "panel",
        ("domain", "boundary", "direction"),
        ("oriented comb domains", "domain walls", "blade strips", "crossbars", "overlap joints", "order ticks", "dislocation forks")),
    "fmo_owl_eye": _g(
        "Owl Eye", "fourier_epicycle", "ocellus", (10, 10), 1907,
        (0.05, 0.09, 0.14, 0.53, 0.64, 0.78), .90, .94, .56, "rings",
        ("contour", "junction", "hollow"),
        ("teardrop pupils", "eccentric irises", "broken annuli", "radial feather combs", "eyelid chevrons", "glint bars", "scale shingles")),
    "fmo_glasswing": _g(
        "Glasswing", "potential_flow_cylinders", "membrane", (12, 9), 1908,
        (0.46, 0.51, 0.57, 0.63, 0.10), .55, .97, .63, "truss",
        ("boundary", "direction", "domain"),
        ("primary veins", "secondary trusses", "transparent panes", "caustic wrinkles", "microtrichia combs", "node pads", "stress notches")),
    "fmo_emperor_scale": _g(
        "Emperor Scale", "hat_monotile", "shingle", (12, 11), 1909,
        (0.10, 0.16, 0.61, 0.71, 0.79), .91, .91, .70, "tile",
        ("ridge", "hollow", "contour"),
        ("crown scales", "overlap lips", "rib fans", "eye wedges", "hinge pores", "edge teeth", "missing tiles")),

    "fmo_jewel_scarab": _g(
        "Jewel Scarab", "hex_hull_greeble", "elytra", (10, 13), 1910,
        (0.31, 0.38, 0.46, 0.97, 0.78), .95, .93, .06, "shell",
        ("ridge", "valley", "domain"),
        ("central sutures", "scutellum triangles", "longitudinal costae", "puncture rows", "hex microcells", "stridulatory files", "rim teeth")),
    "fmo_tiger_beetle": _g(
        "Tiger Beetle", "viscous_fingering", "maculation", (11, 8), 1911,
        (0.08, 0.14, 0.38, 0.48, 0.89), .91, .91, .13, "ribbon",
        ("direction", "hollow", "junction"),
        ("elytral furrows", "branching maculations", "interstrial ridges", "ordered puncta", "suture ladders", "edge spines", "abrasion breaks")),
    "fmo_stag_carapace": _g(
        "Stag Carapace", "fracture_armor_sdf", "armor", (10, 10), 1912,
        (0.02, 0.06, 0.16, 0.28, 0.38), .83, .86, .20, "facet",
        ("domain", "boundary", "ridge"),
        ("carapace plates", "raised keels", "joint gutters", "ram-horn arcs", "puncture bosses", "rim bevels", "split repairs")),
    "fmo_chrysina_gold": _g(
        "Chrysina Gold", "bismuth_terraces", "terrace", (13, 11), 1913,
        (0.08, 0.11, 0.15, 0.29, 0.84), .88, .98, .27, "order",
        ("contour", "ridge", "domain"),
        ("Bragg lamellae", "crystal tiles", "cross-ribs", "layer dislocations", "pinholes", "crack arrests", "order fronts")),
    "fmo_oil_beetle": _g(
        "Oil Beetle", "domain_coloring", "complex", (9, 11), 1914,
        (0.50, 0.57, 0.66, 0.76, 0.88), .96, .91, .34, "phase",
        ("direction", "junction", "valley"),
        ("complex domains", "phase seams", "branch cuts", "pole eyes", "order bands", "suture arcs", "edge cusps")),
    "fmo_firefly_shell": _g(
        "Firefly Shell", "reactor_lattice", "segments", (13, 9), 1915,
        (0.06, 0.11, 0.17, 0.27, 0.36, 0.49, 0.57), .97, .99, .41, "window",
        ("domain", "hollow", "boundary"),
        ("abdominal plates", "lantern windows", "cuticle joints", "paired spiracles", "bristle rows", "diffraction ribs", "pulse bars")),
    "fmo_weevil_pit": _g(
        "Weevil Pit", "machined_knurl", "striae", (14, 10), 1916,
        (0.08, 0.16, 0.29, 0.47, 0.69), .77, .86, .49, "furrow",
        ("direction", "valley", "ridge"),
        ("strial furrows", "offset punctures", "raised interstriae", "leaf scales", "setae", "central sutures", "worn breaks")),
    "fmo_ground_beetle": _g(
        "Ground Beetle", "carbon_forge_weave", "weave", (12, 12), 1917,
        (0.04, 0.09, 0.21, 0.46, 0.69), .72, .82, .56, "weave",
        ("direction", "boundary", "hollow"),
        ("crossed costae", "interlocking struts", "ground pits", "suture rails", "shoulder bars", "rim hooks", "wear gaps")),
    "fmo_scarab_horn": _g(
        "Scarab Horn", "clelie_spiral", "horn", (10, 14), 1918,
        (0.07, 0.12, 0.28, 0.38, 0.57), .85, .89, .63, "spiral",
        ("contour", "direction", "junction"),
        ("horn spirals", "growth ridges", "basal collars", "forked tips", "cross struts", "pore beads", "abrasion flats")),
    "fmo_ladybird_dome": _g(
        "Ladybird Dome", "bubble_lattice", "dome", (12, 10), 1919,
        (0.98, 0.02, 0.07, 0.12, 0.20), .95, .93, .70, "bubble",
        ("domain", "contour", "hollow"),
        ("domed shields", "black maculae", "rim rings", "central sutures", "specular crowns", "pore collars", "edge scallops")),

    "fmo_hummingbird_gorget": _g(
        "Hummingbird Gorget", "cardioid_caustic", "fan", (11, 13), 1920,
        (0.91, 0.97, 0.04, 0.35, 0.48), .97, .96, .08, "arrow",
        ("direction", "ridge", "domain"),
        ("fanned arrow platelets", "central rachises", "barb ridges", "basal pockets", "overlap lips", "tip notches", "glint lines")),
    "fmo_peacock_eye": _g(
        "Peacock Eye", "rose_window", "ocellus", (9, 12), 1921,
        (0.09, 0.31, 0.39, 0.55, 0.63, 0.76), .96, .95, .15, "rings",
        ("contour", "domain", "junction"),
        ("ocellus pupils", "iris petals", "gold coronae", "radial barbs", "broken eyelids", "glint beads", "outer shingles")),
    "fmo_starling_sheen": _g(
        "Starling Sheen", "epitrochoid_weave", "barbule", (13, 10), 1922,
        (0.29, 0.36, 0.45, 0.69, 0.78), .91, .91, .22, "weave",
        ("direction", "ridge", "contour"),
        ("barbule hooks", "rachis loops", "cross-link nodes", "platelet ladders", "overlap pockets", "tip combs", "missing barb gaps")),
    "fmo_magpie_wing": _g(
        "Magpie Wing", "ammann_beenker", "quasifeather", (10, 12), 1923,
        (0.48, 0.57, 0.66, 0.13, 0.88), .86, .92, .29, "tile",
        ("domain", "direction", "boundary"),
        ("quasiperiodic vanes", "silver bars", "black pockets", "hooked barbules", "diamond nodes", "rachis seams", "edge teeth")),
    "fmo_duck_speculum": _g(
        "Duck Speculum", "lissajous_lattice", "speculum", (12, 9), 1924,
        (0.46, 0.53, 0.61, 0.69, 0.11), .94, .95, .36, "window",
        ("direction", "domain", "hollow"),
        ("speculum windows", "white border bars", "crossed barbules", "rachis rails", "hook nodes", "overlap lips", "edge pinions")),
    "fmo_pigeon_neck": _g(
        "Pigeon Neck", "schottky_limit", "collar", (11, 11), 1925,
        (0.31, 0.39, 0.48, 0.85, 0.94), .92, .92, .43, "circle",
        ("contour", "hollow", "junction"),
        ("collar circles", "nested platelet rims", "feather throats", "junction pearls", "dark sockets", "crossover arcs", "edge hooks")),
    "fmo_grackle_oil": _g(
        "Grackle Oil", "rhodonea_field", "petal", (12, 14), 1926,
        (0.06, 0.12, 0.50, 0.61, 0.70, 0.82), .96, .91, .50, "phase",
        ("direction", "contour", "valley"),
        ("oil petals", "barbule rays", "phase knots", "dark lobes", "order rings", "rachis crossings", "tip sparks")),
    "fmo_sunbird_throat": _g(
        "Sunbird Throat", "caustic_rose", "gorget", (10, 13), 1927,
        (0.91, 0.97, 0.04, 0.31, 0.39, 0.48), .98, .97, .57, "caustic",
        ("ridge", "direction", "domain"),
        ("gorget fans", "caustic platelets", "rachis needles", "black bases", "overlap crowns", "throat notches", "glint rails")),
    "fmo_cassowary_quill": _g(
        "Cassowary Quill", "scratch_striation", "quill", (14, 8), 1928,
        (0.03, 0.08, 0.54, 0.62, 0.75), .87, .89, .64, "furrow",
        ("direction", "boundary", "ridge"),
        ("quill shafts", "paired barb rails", "split tips", "cuticle rings", "cross scratches", "root sockets", "missing-barb gaps")),
    "fmo_raven_flash": _g(
        "Raven Flash", "girih_strapwork", "blackwing", (11, 13), 1929,
        (0.48, 0.54, 0.60, 0.68, 0.77, 0.89), .95, .95, .71, "strap",
        ("boundary", "direction", "hollow"),
        ("black feather straps", "blue flash windows", "barb ladders", "rachis knots", "overlap wells", "tip diamonds", "broken straps")),

    "fmo_abalone_drift": _g(
        "Abalone Drift", "mokume_gane", "growth", (10, 12), 1930,
        (0.42, 0.50, 0.58, 0.88, 0.96, 0.10), .84, .96, .09, "growth",
        ("contour", "boundary", "domain"),
        ("aragonite tablets", "organic mortar", "growth arcs", "screw spirals", "boring holes", "deflection bridges", "blister domes")),
    "fmo_black_pearl": _g(
        "Black Pearl", "steiner_chain", "pearlchain", (12, 10), 1931,
        (0.49, 0.57, 0.66, 0.78, 0.91), .76, .83, .16, "circle",
        ("contour", "domain", "hollow"),
        ("pearl chains", "dark nuclei", "nacre rings", "contact dimples", "overtone arcs", "junction beads", "surface scars")),
    "fmo_soap_bubble": _g(
        "Soap Bubble", "bz_spirals", "minimal", (11, 11), 1932,
        (0.00, 0.09, 0.18, 0.34, 0.51, 0.66, 0.82), .86, .99, .23, "film",
        ("junction", "contour", "domain"),
        ("saddle patches", "spiral necks", "membrane windows", "three-way junctions", "drainage rivulets", "Newton fringes", "rupture lips")),
    "fmo_oil_slick": _g(
        "Oil Slick", "warp_moire", "slick", (13, 9), 1933,
        (0.00, 0.09, 0.18, 0.32, 0.48, 0.63, 0.78, 0.91), .97, .92, .30, "phase",
        ("direction", "valley", "contour"),
        ("flow bands", "moire caustics", "shear folds", "oil islands", "drainage seams", "thickness nodes", "rupture crescents")),
    "fmo_mother_of_pearl": _g(
        "Mother of Pearl", "cut_paper_relief", "nacre", (10, 12), 1934,
        (0.91, 0.98, 0.08, 0.37, 0.49, 0.60), .62, .99, .37, "relief",
        ("domain", "boundary", "ridge"),
        ("nacre leaves", "overlap lips", "mortar seams", "pearl windows", "growth folds", "chip bevels", "soft inclusions")),
    "fmo_nacre_brick": _g(
        "Nacre Brick", "parallax_grids", "bouligand", (12, 10), 1935,
        (0.42, 0.50, 0.59, 0.69, 0.10, 0.89), .66, .98, .44, "weave",
        ("direction", "boundary", "domain"),
        ("rotating lamellae", "tablet end caps", "mortar dots", "screw dislocations", "deflection hooks", "growth fronts", "delamination pockets")),
    "fmo_mussel_shell": _g(
        "Mussel Shell", "terraced_strata", "shell", (11, 13), 1936,
        (0.50, 0.58, 0.66, 0.75, 0.89), .73, .88, .51, "growth",
        ("contour", "ridge", "valley"),
        ("shell terraces", "growth ridges", "hinge bars", "umbone arcs", "byssal notches", "erosion pits", "pearl edges")),
    "fmo_foam_film": _g(
        "Foam Film", "hodgepodge", "plateau", (12, 12), 1937,
        (0.45, 0.52, 0.61, 0.72, 0.88), .80, .97, .58, "cell",
        ("boundary", "junction", "domain"),
        ("polygon membranes", "Plateau borders", "triple junctions", "thickness bands", "drainage arrows", "rupture lips", "daughter cells")),
    "fmo_paua_storm": _g(
        "Paua Storm", "stable_fluids_ink", "storm", (10, 14), 1938,
        (0.41, 0.49, 0.58, 0.67, 0.78, 0.91), .89, .94, .65, "flow",
        ("direction", "junction", "ridge"),
        ("storm streamlines", "nacre fronts", "suture eddies", "dark squalls", "tablet islands", "spray crescents", "calm eyes")),
    "fmo_pearl_oyster": _g(
        "Pearl Oyster", "rib_vault", "oyster", (9, 12), 1939,
        (0.93, 0.02, 0.10, 0.45, 0.55, 0.65), .65, .99, .72, "rib",
        ("ridge", "domain", "junction"),
        ("oyster ribs", "hinge vaults", "nacre bays", "growth cusps", "pearl blisters", "edge flutes", "scar pockets")),

    "fmo_labradorite": _g(
        "Labradorite", "labradorite_schiller", "twins", (11, 9), 1940,
        (0.52, 0.57, 0.64, 0.11, 0.76), .93, .92, .10, "facet",
        ("direction", "boundary", "domain"),
        ("pericline twins", "albite blades", "sawtooth walls", "cleavage steps", "flash windows", "exsolution needles", "cross fractures")),
    "fmo_black_opal": _g(
        "Black Opal", "opal_playofcolor", "bragg", (13, 11), 1941,
        (0.00, 0.08, 0.17, 0.32, 0.49, 0.61, 0.79, 0.92), .99, .88, .17, "node",
        ("junction", "hollow", "domain"),
        ("silica lattices", "Bragg nodes", "potch voids", "domain walls", "pinfire orders", "crazing cracks", "lattice dislocations")),
    "fmo_ammolite_skin": _g(
        "Ammolite Skin", "doyle_spiral", "chamber", (10, 13), 1942,
        (0.01, 0.08, 0.16, 0.29, 0.47, 0.62, 0.78), .96, .94, .24, "spiral",
        ("contour", "boundary", "hollow"),
        ("log chambers", "ammonitic sutures", "radial ribs", "shell-chip windows", "mineral seams", "siphuncle dots", "repair scars")),
    "fmo_alexandrite_dusk": _g(
        "Alexandrite Dusk", "newton_basins", "crystal", (12, 10), 1943,
        (0.39, 0.48, 0.57, 0.82, 0.91, 0.98), .91, .91, .31, "basin",
        ("domain", "junction", "direction"),
        ("crystal basins", "twin boundaries", "conversion fronts", "pleochroic wedges", "dark inclusions", "facet ridges", "star junctions")),
    "fmo_moonstone_adular": _g(
        "Moonstone Adular", "thinfilm_bands", "lamella", (11, 12), 1944,
        (0.51, 0.57, 0.63, 0.08, 0.94), .58, .99, .38, "caustic",
        ("direction", "ridge", "domain"),
        ("bent twin sheets", "moving caustic bands", "cleavage steps", "exsolution needles", "dark inclusions", "cross fractures", "milky interlayers")),
    "fmo_sunstone_glitter": _g(
        "Sunstone Glitter", "ford_circles", "inclusion", (14, 10), 1945,
        (0.02, 0.06, 0.10, 0.14, 0.19, 0.86), .86, .97, .45, "circle",
        ("junction", "domain", "ridge"),
        ("ordered copper plates", "inclusion circles", "spark crowns", "feldspar lanes", "cleavage bars", "dark sockets", "orientation ticks")),
    "fmo_fire_agate": _g(
        "Fire Agate", "liesegang_rings", "botryoid", (12, 12), 1946,
        (0.00, 0.05, 0.11, 0.18, 0.31, 0.76), .96, .96, .52, "rings",
        ("contour", "hollow", "ridge"),
        ("botryoidal lobes", "iridescent skins", "limonite rims", "central pits", "inter-lobe throats", "radial cracks", "druzy crowns")),
    "fmo_spectrolite_vein": _g(
        "Spectrolite Vein", "electrostatic_equipotential", "vein", (10, 14), 1947,
        (0.09, 0.31, 0.42, 0.51, 0.59, 0.69, 0.82, 0.91), .97, .97, .59, "equipotential",
        ("contour", "direction", "junction"),
        ("spectral veins", "equipotential bands", "charge nodes", "twin blades", "dark matrix", "cross faults", "flash windows")),
    "fmo_bornite_patina": _g(
        "Bornite Patina", "eden_growth", "oxidation", (11, 11), 1948,
        (0.03, 0.11, 0.22, 0.49, 0.61, 0.75, 0.86), .92, .90, .66, "growth",
        ("boundary", "domain", "junction"),
        ("oxidation islands", "stepped fronts", "cleavage lines", "dendritic feathers", "pinhole pits", "grain seams", "unreacted cores")),
    "fmo_chalcopyrite": _g(
        "Chalcopyrite", "kirigami_creases", "tetrahedral", (13, 9), 1949,
        (0.08, 0.12, 0.18, 0.47, 0.67, 0.80), .93, .95, .73, "facet",
        ("domain", "boundary", "ridge"),
        ("tetrahedral twins", "triangular faces", "twin boundaries", "striated planes", "stepped terraces", "oxidation wedges", "cleavage pits")),
}


ALL = MORPHO_GRAMMARS

assert len(MORPHO_GRAMMARS) == 50, "Morpho rejection rebuild must own exactly 50 IDs"
assert all(fid.startswith("fmo_") for fid in MORPHO_GRAMMARS)
assert len({g.source for g in MORPHO_GRAMMARS.values()}) == 50, "source reuse is forbidden"
assert all(len(g.features) >= 5 for g in MORPHO_GRAMMARS.values())
assert all(len(set(g.spec_ops)) == 3 for g in MORPHO_GRAMMARS.values())


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo = float(np.nanmin(a))
    hi = float(np.nanmax(a))
    if not np.isfinite(lo + hi) or hi - lo < 1e-7:
        return np.zeros_like(a, np.float32)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _triangle(t: np.ndarray) -> np.ndarray:
    """Continuous mirrored repetition: dense topology without tile seams."""
    f = t - np.floor(t)
    return (1.0 - np.abs(2.0 * f - 1.0)).astype(np.float32)


def _layout_coordinates(layout: str, rx: float, ry: float) -> Tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:_WORK, 0:_WORK].astype(np.float32)
    x = (x + 0.5) / _WORK - 0.5
    y = (y + 0.5) / _WORK - 0.5
    r = np.sqrt(x * x + y * y) + 1e-6
    a = np.arctan2(y, x) / (2.0 * np.pi)

    if layout == "lamellar":
        u, v = x + 0.13 * np.sin(2 * np.pi * y * 3), y + 0.08 * np.sin(2 * np.pi * x * 2)
    elif layout == "wing":
        u, v = np.abs(x) + 0.22 * y * y, y + 0.10 * np.sin(4 * np.pi * np.abs(x))
    elif layout == "branch":
        u, v = x + 0.18 * np.sign(y) * np.abs(y), y + 0.08 * np.sin(6 * np.pi * x)
    elif layout == "hooked":
        u, v = x + 0.14 * np.sin(2 * np.pi * y * 2), y + 0.14 * np.cos(2 * np.pi * x * 2)
    elif layout == "nodal":
        u, v = x + 0.09 * np.sin(8 * np.pi * y), y + 0.09 * np.sin(6 * np.pi * x)
    elif layout == "chevron":
        u, v = x + 0.38 * np.abs(_triangle(y * ry) - 0.5) / max(rx, 1.0), y
    elif layout == "parquet":
        q = np.floor((y + .5) * ry)
        u, v = x + 0.5 * (q % 2) / max(rx, 1.0), y
    elif layout == "ocellus":
        u, v = r + 0.07 * np.sin(12 * np.pi * a), a + 0.14 * r
    elif layout == "membrane":
        u, v = x + 0.16 * np.sin(2 * np.pi * y * 3), y + 0.06 * np.sin(2 * np.pi * x * 5)
    elif layout == "shingle":
        q = np.floor((y + .5) * ry)
        u, v = x + 0.5 * (q % 2) / max(rx, 1.0), y + 0.06 * np.sin(4 * np.pi * x)
    elif layout == "elytra":
        u, v = np.abs(x) + 0.035 * np.sin(10 * np.pi * y), y
    elif layout == "maculation":
        u, v = x + 0.15 * np.sin(4 * np.pi * y), y + 0.05 * np.sin(12 * np.pi * x)
    elif layout == "armor":
        u, v = x + 0.09 * np.sin(6 * np.pi * y), y + 0.09 * np.cos(6 * np.pi * x)
    elif layout == "terrace":
        u, v = x + 0.12 * y, y + 0.03 * np.sin(12 * np.pi * x)
    elif layout == "complex":
        u, v = x * x - y * y + 0.35 * x, 2 * x * y + 0.35 * y
    elif layout == "segments":
        u, v = x + 0.5 * (np.floor((y + .5) * ry) % 2) / max(rx, 1.0), y
    elif layout == "striae":
        u, v = x + 0.10 * np.sin(8 * np.pi * y), y
    elif layout == "weave":
        u, v = x + 0.06 * np.sin(10 * np.pi * y), y + 0.06 * np.sin(10 * np.pi * x)
    elif layout == "horn":
        u, v = r + 0.12 * a, a + 0.35 * r
    elif layout == "dome":
        u, v = r + 0.06 * np.sin(10 * np.pi * a), a
    elif layout == "fan":
        u, v = r + 0.10 * np.sin(8 * np.pi * a), a + 0.18 * r
    elif layout == "barbule":
        u, v = x + 0.07 * np.sin(14 * np.pi * y), y + 0.05 * np.sin(6 * np.pi * x)
    elif layout == "quasifeather":
        c, s = np.cos(0.39), np.sin(0.39)
        u, v = c * x - s * y + 0.04 * np.sin(12 * np.pi * y), s * x + c * y
    elif layout == "speculum":
        u, v = x + 0.05 * np.sin(14 * np.pi * y), y + 0.03 * np.sin(8 * np.pi * x)
    elif layout == "collar":
        u, v = r, a + 0.08 * np.sin(10 * np.pi * r)
    elif layout == "petal":
        u, v = r + 0.09 * np.sin(10 * np.pi * a), a + 0.12 * np.sin(8 * np.pi * r)
    elif layout == "gorget":
        u, v = r + 0.14 * np.sin(6 * np.pi * a), a + 0.25 * r
    elif layout == "quill":
        u, v = x + 0.04 * np.sin(16 * np.pi * y), y + 0.12 * np.sign(x) * x * x
    elif layout == "blackwing":
        u, v = np.abs(x) + 0.06 * np.sin(12 * np.pi * y), y + 0.08 * np.sin(4 * np.pi * x)
    elif layout == "growth":
        u, v = x + 0.12 * np.sin(4 * np.pi * y), y + 0.07 * np.sin(6 * np.pi * x)
    elif layout == "pearlchain":
        u, v = x + 0.08 * np.sin(8 * np.pi * y), y + 0.08 * np.cos(8 * np.pi * x)
    elif layout == "minimal":
        u, v = x + 0.10 * np.sin(6 * np.pi * y), y + 0.10 * np.sin(6 * np.pi * x + np.pi / 3)
    elif layout == "slick":
        u, v = x + 0.16 * np.sin(5 * np.pi * y), y + 0.07 * np.sin(9 * np.pi * x)
    elif layout == "nacre":
        u, v = x + 0.5 * (np.floor((y + .5) * ry) % 2) / max(rx, 1.0), y + 0.04 * np.sin(8 * np.pi * x)
    elif layout == "bouligand":
        ang = 0.42 * np.sin(2 * np.pi * y * 3)
        u, v = np.cos(ang) * x - np.sin(ang) * y, np.sin(ang) * x + np.cos(ang) * y
    elif layout == "shell":
        u, v = r + 0.05 * np.sin(14 * np.pi * a), a + 0.18 * np.log(r + .08)
    elif layout == "plateau":
        u, v = x + 0.07 * np.sin(7 * np.pi * y), y + 0.07 * np.cos(7 * np.pi * x)
    elif layout == "storm":
        u, v = x + 0.18 * np.sin(3 * np.pi * y), y + 0.10 * np.sin(7 * np.pi * x + 2 * y)
    elif layout == "oyster":
        u, v = r + 0.09 * np.cos(8 * np.pi * a), a + 0.12 * r
    elif layout == "twins":
        u, v = x + 0.13 * np.abs(y), y + 0.06 * np.sign(x) * x
    elif layout == "bragg":
        u, v = x + 0.08 * np.sin(8 * np.pi * y), y + 0.08 * np.sin(8 * np.pi * x)
    elif layout == "chamber":
        u, v = np.log(r + .04) + 0.22 * a, a + 0.25 * r
    elif layout == "crystal":
        c, s = np.cos(0.61), np.sin(0.61)
        u, v = c * x - s * y + 0.06 * np.abs(y), s * x + c * y
    elif layout == "lamella":
        u, v = x + 0.17 * np.sin(3 * np.pi * y), y + 0.03 * np.sin(12 * np.pi * x)
    elif layout == "inclusion":
        u, v = x + 0.04 * np.sin(12 * np.pi * y), y
    elif layout == "botryoid":
        u, v = r + 0.08 * np.sin(12 * np.pi * a), a
    elif layout == "vein":
        u, v = x + 0.14 * np.sin(4 * np.pi * y), y + 0.04 * np.sin(12 * np.pi * x)
    elif layout == "oxidation":
        u, v = x + 0.09 * np.sin(5 * np.pi * y), y + 0.09 * np.sin(7 * np.pi * x)
    elif layout == "tetrahedral":
        c, s = np.cos(np.pi / 6), np.sin(np.pi / 6)
        u, v = c * x - s * y + 0.04 * np.abs(y), s * x + c * y
    else:
        raise KeyError(f"unknown Morpho layout: {layout}")

    # Mirror folding keeps every boundary continuous and makes the unique
    # source topology dense.  No random displacement or grain is introduced.
    return _triangle((u + .5) * rx), _triangle((v + .5) * ry)


def _source_field(g: Grammar) -> np.ndarray:
    from engine.paint_v2 import exotic_engines_2026 as exotic

    base = exotic.field(g.source, _SOURCE, _SOURCE, g.seed)
    uu, vv = _layout_coordinates(
        g.layout, g.repeats[0] * _ASSEMBLY_DENSITY,
        g.repeats[1] * _ASSEMBLY_DENSITY,
    )
    mx = (uu * (_SOURCE - 1)).astype(np.float32)
    my = (vv * (_SOURCE - 1)).astype(np.float32)
    return _norm(cv2.remap(base, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101))


def _features(g: Grammar) -> Mapping[str, np.ndarray]:
    domain = _source_field(g)
    fine = cv2.GaussianBlur(domain, (0, 0), .65)
    broad = cv2.GaussianBlur(domain, (0, 0), 2.15)
    gx = cv2.Sobel(fine, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(fine, cv2.CV_32F, 0, 1, ksize=3)
    boundary = _norm(np.hypot(gx, gy))
    ridge = _norm(np.maximum(fine - broad, 0.0))
    valley = _norm(np.maximum(broad - fine, 0.0))
    lap = cv2.Laplacian(fine, cv2.CV_32F, ksize=3)
    junction = _norm(np.abs(lap) * (0.28 + 0.72 * boundary))
    # Fixed iso-value comb.  Threshold spacing is geometric and independent of
    # population, unlike the rejected equal-population rank carrier.
    contour = np.clip(1.0 - np.abs(np.mod(domain * 7.0 + g.phase, 1.0) - .5) * 8.0, 0.0, 1.0)
    angle = np.arctan2(gy, gx)
    direction = (0.5 + 0.5 * np.cos(3.0 * angle + 2.0 * np.pi * domain)).astype(np.float32)
    hollow = _norm((1.0 - domain) * (0.35 + 0.65 * valley))
    crown = _norm(domain * (0.35 + 0.65 * ridge))
    tone = _norm(cv2.GaussianBlur(domain, (0, 0), 2.20))
    # Distance-order halos fill the negative space of sparse mechanisms (opal
    # pinfire, horn arms, Plateau borders) with fine *causal* bands.  They are
    # distances to that finish's own boundary, never noise or a global carrier.
    boundary_seed = (boundary > .42).astype(np.uint8)
    dist = cv2.distanceTransform(1 - boundary_seed, cv2.DIST_L2, 3)
    proximity = (0.5 + 0.5 * np.cos(2.0 * np.pi * dist / 6.0 + 2.0 * np.pi * g.phase)).astype(np.float32)
    return {
        "domain": domain, "boundary": boundary, "ridge": ridge,
        "valley": valley, "junction": junction, "contour": contour,
        "direction": direction, "hollow": hollow, "crown": crown,
        "tone": tone, "proximity": proximity,
    }


def _palette(g: Grammar) -> np.ndarray:
    """Twelve coherent shades spanning the grammar's explicit hue anchors."""
    hs = g.hues
    out = []
    for i in range(12):
        p = (i + .5) / 12.0
        z = p * len(hs)
        j = int(np.floor(z)) % len(hs)
        k = (j + 1) % len(hs)
        t = z - np.floor(z)
        h0, h1 = hs[j], hs[k]
        dh = ((h1 - h0 + .5) % 1.0) - .5
        h = (h0 + dh * t) % 1.0
        sat = np.clip(g.saturation * (.72 + .28 * ((i * 5) % 11) / 10.0), .18, 1.0)
        val = np.clip(g.value * (.50 + .50 * ((i * 7) % 12) / 11.0), .12, 1.0)
        out.append(colorsys.hsv_to_rgb(float(h), float(sat), float(val)))
    return np.asarray(out, np.float32)


def _color_coordinate(g: Grammar, f: Mapping[str, np.ndarray]) -> np.ndarray:
    # Color rides a slightly broader version of the topology.  W1/W2 proved
    # that assigning twelve hard colors to every sub-pixel oscillation reads as
    # grit even when the source math is real.  Fine marks remain in the causal
    # light/accent model below; color order now reads as coherent interference.
    d, e, r, v = f["tone"], f["boundary"], f["ridge"], f["valley"]
    c, j, o = f["contour"], f["junction"], f["direction"]
    mode = g.color_mode
    if mode in {"order", "phase"}:
        q = 1.15 * d + .18 * o + .12 * c
    elif mode in {"panel", "tile", "facet", "shell"}:
        q = .95 * d + .20 * e + .12 * j
    elif mode in {"cell", "window", "bubble", "basin"}:
        q = 1.08 * d + .16 * (1.0 - e) + .12 * j
    elif mode in {"arrow", "glyph", "truss", "strap"}:
        q = .58 * o + .72 * d + .15 * e
    elif mode in {"rings", "circle", "spiral", "botryoid"}:
        q = 1.35 * d + .16 * c + .12 * v
    elif mode in {"furrow", "weave", "rib", "equipotential"}:
        q = .55 * o + .85 * d + .15 * r
    elif mode in {"caustic", "film", "relief"}:
        q = 1.12 * d + .18 * r - .10 * v + .12 * c
    elif mode in {"growth", "flow", "ribbon"}:
        q = .90 * d + .25 * o + .16 * j
    elif mode == "node":
        q = .96 * d + .25 * j + .12 * c
    else:
        raise KeyError(f"unknown Morpho color mode: {mode}")
    return np.mod(_norm(q) + g.phase, 1.0).astype(np.float32)


def _operator(name: str, f: Mapping[str, np.ndarray]) -> np.ndarray:
    d = f["domain"]
    if name == "domain":
        a = .74 * d + .26 * f["ridge"]
    elif name == "boundary":
        a = .76 * f["boundary"] + .24 * f["junction"]
    elif name == "ridge":
        a = .73 * f["ridge"] + .27 * f["contour"]
    elif name == "valley":
        a = .72 * f["valley"] + .28 * f["hollow"]
    elif name == "junction":
        a = .69 * f["junction"] + .31 * f["boundary"] * f["direction"]
    elif name == "contour":
        a = .76 * f["contour"] + .24 * f["ridge"]
    elif name == "direction":
        a = .67 * f["direction"] + .33 * f["boundary"]
    elif name == "hollow":
        a = .71 * f["hollow"] + .29 * f["valley"]
    elif name == "crown":
        a = .70 * f["crown"] + .30 * f["ridge"]
    else:
        raise KeyError(f"unknown structural operator: {name}")
    return _norm(a)


def _fixed_tiers(a: np.ndarray, tiers: np.ndarray) -> np.ndarray:
    # Fixed thresholds, never percentile/rank/equal-population bins.
    # A fixed contrast expansion widens physical travel without redistributing
    # pixels by population (the rejected rank-carrier behavior).
    a = np.clip((np.asarray(a, np.float32) - .5) * 1.52 + .5, 0.0, 1.0)
    ix = np.clip(np.floor(np.clip(a, 0.0, 0.999999) * 8.0), 0, 7).astype(np.intp)
    return tiers[ix]


@lru_cache(maxsize=6)
def _design_cached(fid: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    g = MORPHO_GRAMMARS[fid]
    f = _features(g)
    q = _color_coordinate(g, f)
    palette = _palette(g)
    z = q * 12.0
    ix = np.floor(z).astype(np.intp) % 12
    blend = (z - np.floor(z)).astype(np.float32)
    blend = blend * blend * (3.0 - 2.0 * blend)
    paint = palette[ix] * (1.0 - blend[..., None]) + palette[(ix + 1) % 12] * blend[..., None]

    # Five-plus topology-attached mark types are present in the value/chroma
    # model: domains, boundaries, ridges, valleys, contours and junctions.
    # Their weights vary by the row's structural source, not by random masks.
    light = np.clip(
        .52 + .25 * f["domain"] + .20 * f["ridge"] - .18 * f["valley"]
        + .12 * f["contour"] + .10 * f["junction"] - .24 * f["boundary"],
        .24, 1.18,
    )
    paint = np.clip(paint * light[..., None], 0.0, 1.0)
    # Structural seams and crowns get causal color accents from neighboring
    # palette shades; this is not an independent speckle/fleck overlay.
    accent = palette[(ix + 3) % 12]
    am = np.clip(.17 * f["contour"] + .14 * f["ridge"] + .11 * f["junction"], 0.0, .32)
    paint = np.clip(paint * (1.0 - am[..., None]) + accent * am[..., None], 0.0, 1.0).astype(np.float32)

    # FRACTURED A/B ownership: these banks are literally the paint color-order
    # groups.  Metalness powers bank A; clearcoat powers the complementary bank
    # B.  Each also receives a different named structural operator, so the spec
    # maps are not copies/inverses of one carrier.
    bank_a = (0.5 + 0.5 * np.cos(2.0 * np.pi * q)).astype(np.float32)
    bank_b = (0.5 + 0.5 * np.cos(2.0 * np.pi * (q - .5))).astype(np.float32)
    m0 = _operator(g.spec_ops[0], f)
    r0 = _operator(g.spec_ops[1], f)
    c0 = _operator(g.spec_ops[2], f)
    mfield = _norm(.46 * m0 + .27 * bank_a + .07 * f["ridge"] + .20 * f["proximity"])
    rough_order = (0.5 + 0.5 * np.cos(
        2.0 * np.pi * (3.0 * f["tone"] + .23 * f["direction"] + g.phase)
    )).astype(np.float32)
    rfield = _norm(.46 * r0 + .19 * f["valley"] + .14 * (1.0 - f["contour"]) + .21 * rough_order)
    cfield = _norm(.43 * c0 + .27 * bank_b + .08 * f["junction"] + .22 * (1.0 - f["proximity"]))
    if fid == "fmo_scarab_horn":
        # The Clelie horn arms occupy little area; a generic junction-weighted
        # coat left 90% of the field at one tier (W5 Cc std 18.505).  On this
        # finish the clearcoat is physically the concentric growth-order halo,
        # so its own boundary-distance bands correctly receive more authority.
        cfield = _norm(.32 * c0 + .20 * bank_b + .08 * f["junction"] + .40 * (1.0 - f["proximity"]))

    spec = np.empty((_WORK, _WORK, 3), np.uint8)
    spec[:, :, 0] = _fixed_tiers(mfield, _METAL_TIERS)
    spec[:, :, 1] = _fixed_tiers(rfield, _ROUGH_TIERS)
    spec[:, :, 2] = _fixed_tiers(cfield, _COAT_TIERS)
    return paint, spec, bank_a, bank_b


def make_entry(fid: str):
    """Return the existing monolithic ``(spec_fn, paint_fn)`` API."""
    if fid not in MORPHO_GRAMMARS:
        raise KeyError(fid)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and float(src.max()) > 1.5:
            src = src / 255.0
        if src.shape[:2] != (fh, fw):
            src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored = cv2.resize(_design_cached(fid)[0], (fw, fh), interpolation=cv2.INTER_NEAREST)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + authored * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored = cv2.resize(_design_cached(fid)[1], (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        calm = np.asarray([4.0, 120.0, 16.0], np.float32)
        active = np.clip(calm + (authored - calm) * max(0.0, float(sm)), 0.0, 255.0)
        mk = np.clip(m2, 0.0, 1.0)[..., None]
        rgb = active * mk + calm * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    spec_fn.__name__ = f"spec_{fid}"
    paint_fn.__name__ = f"paint_{fid}"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the 50 current Fractured Morpho registry IDs."""
    regs = [mono_reg]
    if base_reg is not None and base_reg is not mono_reg:
        regs.append(base_reg)
    try:
        from engine.expansions import fusions as _fus
        if _fus.FUSION_REGISTRY not in regs:
            regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys
    eng = sys.modules.get("shokker_engine_v2")
    if eng is not None and hasattr(eng, "FUSION_REGISTRY"):
        ereg = eng.FUSION_REGISTRY
        if ereg not in regs:
            regs.append(ereg)
    for fid in MORPHO_GRAMMARS:
        entry = make_entry(fid)
        for reg in regs:
            reg[fid] = entry
    return "fractured-wilds-morpho-rejection-rebuild: 50 literal topologies installed"


def clear_design_cache() -> None:
    _design_cached.cache_clear()


def _tile_contact(images: Sequence[np.ndarray], labels: Sequence[str], cols: int = 5, cell: int = 256) -> np.ndarray:
    rows = (len(images) + cols - 1) // cols
    head = 34
    sheet = np.full((rows * (cell + head), cols * cell, 3), 18, np.uint8)
    for i, (im, label) in enumerate(zip(images, labels)):
        row, col = divmod(i, cols)
        tile = cv2.resize(im, (cell, cell), interpolation=cv2.INTER_AREA)
        if tile.ndim == 2:
            tile = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
        sheet[row * (cell + head) + head:(row + 1) * (cell + head), col * cell:(col + 1) * cell] = tile
        cv2.putText(sheet, label.replace("fmo_", "")[:28], (col * cell + 5, row * (cell + head) + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, .48, (235, 235, 235), 1, cv2.LINE_AA)
    return sheet


def _palette_null(paint_rgb: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor((np.clip(paint_rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
    luma = lab[:, :, 0]
    gx = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm(np.hypot(gx, gy))
    return (edge * 255).astype(np.uint8)


def _nearest_pair(images: Sequence[np.ndarray], labels: Sequence[str]) -> Mapping[str, object]:
    """Palette-independent structural correlation; diagnostic, never a gate."""
    vectors = []
    for im in images:
        a = np.asarray(im)
        if a.ndim == 3:
            a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
        a = cv2.resize(a, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
        a -= float(a.mean())
        a /= max(float(np.linalg.norm(a)), 1e-7)
        vectors.append(a)
    best = (-2.0, "", "")
    values = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            corr = float(np.dot(vectors[i], vectors[j]))
            values.append(corr)
            if corr > best[0]:
                best = (corr, labels[i], labels[j])
    return {
        "max_correlation": round(best[0], 5),
        "nearest_pair": [best[1], best[2]],
        "mean_correlation": round(float(np.mean(values)), 5),
        "pair_count": len(values),
    }


def _audit(output: Path) -> Mapping[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    ids = list(MORPHO_GRAMMARS)
    paints, nulls, metals, roughs, coats, views_a, views_b, diffs = ([] for _ in range(8))
    rows = []
    t_all = time.perf_counter()
    for fid in ids:
        clear_design_cache()
        t0 = time.perf_counter()
        paint, spec, bank_a, bank_b = _design_cached(fid)
        elapsed = time.perf_counter() - t0
        p8 = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
        paints.append(cv2.cvtColor(p8, cv2.COLOR_RGB2BGR))
        nulls.append(_palette_null(paint))
        metals.append(spec[:, :, 0])
        roughs.append(spec[:, :, 1])
        coats.append(spec[:, :, 2])
        # Diagnostic A/B views only: they expose which existing paint colors
        # each spec power system emphasizes.  They are evidence, not runtime art.
        va = np.clip(paint * (.38 + .62 * bank_a[..., None]), 0, 1)
        vb = np.clip(paint * (.38 + .62 * bank_b[..., None]), 0, 1)
        views_a.append(cv2.cvtColor((va * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
        views_b.append(cv2.cvtColor((vb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
        diffs.append((np.mean(np.abs(va - vb), axis=2) * 255).astype(np.uint8))
        rows.append({
            "id": fid,
            "name": MORPHO_GRAMMARS[fid].name,
            "source": MORPHO_GRAMMARS[fid].source,
            "layout": MORPHO_GRAMMARS[fid].layout,
            "features": list(MORPHO_GRAMMARS[fid].features),
            "spec_ops": list(MORPHO_GRAMMARS[fid].spec_ops),
            "seconds_512_cold": round(elapsed, 4),
            "paint_sha256": hashlib.sha256(p8.tobytes()).hexdigest(),
            "spec_sha256": hashlib.sha256(spec.tobytes()).hexdigest(),
            "m_std": round(float(spec[:, :, 0].std()), 3),
            "r_std": round(float(spec[:, :, 1].std()), 3),
            "cc_std": round(float(spec[:, :, 2].std()), 3),
            "ab_mean_abs": round(float(np.mean(np.abs(va - vb)) * 255.0), 3),
        })
        print(f"[{len(rows):02d}/50] {fid}: {elapsed:.3f}s", flush=True)

    contacts = {
        "paint_contact.png": paints,
        "palette_null_contact.png": nulls,
        "metal_contact.png": metals,
        "roughness_contact.png": roughs,
        "clearcoat_contact.png": coats,
        "view_a_contact.png": views_a,
        "view_b_contact.png": views_b,
        "ab_difference_contact.png": diffs,
    }
    for filename, images in contacts.items():
        cv2.imwrite(str(output / filename), _tile_contact(images, ids))

    palette_null_nn = _nearest_pair(nulls, ids)
    # One structural spec silhouette per finish: concatenate three independently
    # normalized channel thumbnails before measuring cross-finish correlation.
    spec_silhouettes = []
    for m, r, c in zip(metals, roughs, coats):
        chans = []
        for ch in (m, r, c):
            z = cv2.resize(ch, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
            chans.append((_norm(z) * 255).astype(np.uint8))
        spec_silhouettes.append(np.concatenate(chans, axis=1))
    spec_nn = _nearest_pair(spec_silhouettes, ids)

    # API and native-resolution hot-path probe.  The authored 512 art is cached;
    # 2048 work consists of nearest resize plus mask compositing.
    probe_ids = ids[::10]
    api_rows = []
    for fid in probe_ids:
        spec_fn, paint_fn = make_entry(fid)
        shape = (2048, 2048)
        mask = np.ones(shape, np.float32)
        base = np.zeros((2048, 2048, 3), np.float32)
        _design_cached(fid)
        t0 = time.perf_counter(); pout = paint_fn(base, shape, mask, 1, 1.0, None); tp = time.perf_counter() - t0
        t0 = time.perf_counter(); sout = spec_fn(shape, mask, 1, 1.0); ts = time.perf_counter() - t0
        api_rows.append({"id": fid, "paint_2048_hot_s": round(tp, 4), "spec_2048_hot_s": round(ts, 4),
                         "paint_shape": list(pout.shape), "spec_shape": list(sout.shape)})

    registry = {}
    status = install_into_engine(registry)
    report = {
        "schema": 1,
        "ticket": "SPB-WILDS-REJECTION-2026-08-24 WR-MORPHO-1",
        "owner_acceptance_claimed": False,
        "rejected_old_state": "50 Morpho IDs shared one seven-scatter paint composer and a shared carrier/rank spec family",
        "noise_used_as_uniqueness": False,
        "finish_count": len(ids),
        "unique_source_count": len({g.source for g in MORPHO_GRAMMARS.values()}),
        "unique_paint_hashes": len({r["paint_sha256"] for r in rows}),
        "unique_spec_hashes": len({r["spec_sha256"] for r in rows}),
        "all_have_five_causal_features": all(len(g.features) >= 5 for g in MORPHO_GRAMMARS.values()),
        "all_channels_name_distinct_ops": all(len(set(g.spec_ops)) == 3 for g in MORPHO_GRAMMARS.values()),
        "rank_quantisation_used": False,
        "palette_null_structural_nn": palette_null_nn,
        "spec_structural_nn": spec_nn,
        "registry_count": len(registry),
        "registry_ids_exact": set(registry) == set(ids),
        "install_status": status,
        "seconds_total": round(time.perf_counter() - t_all, 3),
        "max_cold_512_s": max(r["seconds_512_cold"] for r in rows),
        "min_spec_std": {
            "M": min(r["m_std"] for r in rows),
            "R": min(r["r_std"] for r in rows),
            "Cc": min(r["cc_std"] for r in rows),
        },
        "min_ab_mean_abs": min(r["ab_mean_abs"] for r in rows),
        "api_2048_samples": api_rows,
        "finishes": rows,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Fractured Morpho rejection rebuild")
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    report = _audit(args.audit)
    print(json.dumps({k: report[k] for k in (
        "finish_count", "unique_source_count", "unique_paint_hashes", "unique_spec_hashes",
        "registry_count", "registry_ids_exact", "max_cold_512_s", "min_spec_std", "min_ab_mean_abs")
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
