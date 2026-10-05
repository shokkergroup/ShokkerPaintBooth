# -*- coding: utf-8 -*-
"""Fine-scale signature renderer shared by FRACTURED CRYPTID and MORPHO.

SPB-WILDS 2026-08-23, tick W-1. Owner verdict: "Too much redundancy way
too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color
flipping stuff."  This module deliberately works at 512 square: every drawn
primitive is 2-8 work pixels (8-32 px at 2048), and every finish layers a
primary glyph, a secondary glyph, capsules, spots, rings, arcs, and flecks.

The old shared-kernel result used broad 100-400 px composition bands and, in
Cryptid, fracture_spec() carved all material channels from almost the same
luma field.  Here paint and material are authored from the same eight-phase
microstructure, but M/R/CC use independent tier permutations.  Adjacent marks
therefore trade metallic, aperture, and clearcoat response as the environment
highlight moves: the color-flip is structural, not a flat rainbow recolor.

Measured before -> W-3 final (bounded 70-finish audit): worst structural
neighbour 0.787311 -> 0.463878; old Cryptid max channel correlation
0.999-1.000 -> all-70 maximum 0.699344; neutral-excluded angle hue-TV
min/median 0.020709/0.126638 -> 0.120866/0.220723; isolated canonical-formula
M7 2/50 below 85 + no Cryptid rows -> 70/70 at or above 85 (minimum 86.0);
cold native-2048 maximum 0.960543s. Per-finish tier populations/correlations
live in ``_wilds_work/owner_eye_w3_final/audit.json``; perf and M7 evidence
live in ``_wilds_work/owner_eye_w3_native_perf`` and ``_wilds_work/m7_evidence``.
"""
from __future__ import annotations

import colorsys
import hashlib
from functools import lru_cache
from typing import Mapping, Sequence

import cv2
import numpy as np


_DESIGN = 512

# Explicit wide eight-tier palettes.  These are intentionally not simple
# dark/bright pairs: every small authored mark can land on a different shade.
_MARK_TIERS = np.asarray([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], np.float32)
_METAL_TIERS = np.asarray([0, 36, 72, 108, 144, 180, 220, 255], np.float32)
_ROUGH_TIERS = np.asarray([12, 38, 66, 94, 122, 150, 180, 214], np.float32)
_COAT_TIERS = np.asarray([16, 46, 78, 110, 142, 174, 208, 242], np.float32)
_R_PERM = np.asarray([6, 2, 7, 1, 5, 0, 4, 3], np.int16)
_CC_PERM = np.asarray([1, 5, 0, 7, 3, 6, 2, 4], np.int16)


# Cryptid gets explicit semantic art direction.  Each pairing was chosen to
# retain the creature/material story while adding a genuinely opposing flash.
_CRYPTID_STYLE = {
    "fc_sasquatch_fur": ("fur", (0.075, 0.48)),
    "fc_quill_bristle": ("quill", (0.12, 0.72)),
    "fc_coarse_hide": ("pebble", (0.01, 0.52)),
    "fc_eyeshine": ("eye", (0.29, 0.79)),
    "fc_bog_murk": ("muck", (0.48, 0.92)),
    "fc_claw_rake": ("claw", (0.035, 0.62)),
    "fc_bark_camo": ("bark", (0.24, 0.095)),
    "fc_feathered_wing": ("feather", (0.74, 0.51)),
    "fc_dorsal_ridge": ("ridge", (0.37, 0.055)),
    "fc_webbed_membrane": ("web", (0.51, 0.97)),
    "fc_toad_skin": ("wart", (0.30, 0.78)),
    "fc_antler_bone": ("antler", (0.105, 0.60)),
    "fc_mossy_stone": ("stone", (0.235, 0.85)),
    "fc_will_o_wisp": ("wisp", (0.46, 0.12)),
    "fc_snakeskin": ("diamond", (0.355, 0.985)),
    "fc_batwing": ("bat", (0.755, 0.965)),
    "fc_gator_hide": ("scute", (0.205, 0.65)),
    "fc_hide_scale_glass": ("scale", (0.315, 0.10)),
    "fc_dragon_hex_glass": ("hex", (0.385, 0.025)),
    "fc_crackle_eyeshine_glass": ("crackle", (0.115, 0.33, 0.77)),
}

_MORPHO_MOTIFS = {
    "scales": "scale",
    "ridges": "ridge",
    "pits": "pit",
    "barbules": "barbule",
    "platelets": "platelet",
    "nacre": "nacre",
    "film": "film",
    "opal": "opal",
    "lamellae": "lamella",
    "tarnish": "tarnish",
    "grating": "grating",
    "eyespot": "eyespot",
}

# Name-level silhouettes stop the 50 Morpho recipes from collapsing merely
# because several share an optical generator. These remain biologically or
# materially faithful: e.g. Glasswing uses web membranes, Firefly uses comets,
# Ammolite uses fossil-stone shards, and Spectrolite uses spectral cracks.
_MORPHO_STYLE = {
    "fmo_morpho_blue": "scale",
    "fmo_sunset_moth": "barbule",
    "fmo_monarch_vein": "web",
    "fmo_atlas_wing": "feather",
    "fmo_luna_dust": "star",
    "fmo_swallowtail": "ridge",
    "fmo_ulysses_flash": "platelet",
    "fmo_owl_eye": "eyespot",
    "fmo_glasswing": "web",
    "fmo_emperor_scale": "hex",
    "fmo_jewel_scarab": "pit",
    "fmo_tiger_beetle": "claw",
    "fmo_stag_carapace": "scute",
    "fmo_chrysina_gold": "film",
    "fmo_oil_beetle": "wisp",
    "fmo_firefly_shell": "comet",
    "fmo_weevil_pit": "pit",
    "fmo_ground_beetle": "lamella",
    "fmo_scarab_horn": "antler",
    "fmo_ladybird_dome": "wart",
    "fmo_hummingbird_gorget": "star",
    "fmo_peacock_eye": "eye",
    "fmo_starling_sheen": "barbule",
    "fmo_magpie_wing": "feather",
    "fmo_duck_speculum": "ridge",
    "fmo_pigeon_neck": "feather",
    "fmo_grackle_oil": "tarnish",
    "fmo_sunbird_throat": "scale",
    "fmo_cassowary_quill": "quill",
    "fmo_raven_flash": "lamella",
    "fmo_abalone_drift": "nacre",
    "fmo_black_pearl": "ring",
    "fmo_soap_bubble": "opal",
    "fmo_oil_slick": "film",
    "fmo_mother_of_pearl": "scale",
    "fmo_nacre_brick": "nacre",
    "fmo_mussel_shell": "ridge",
    "fmo_foam_film": "ring",
    "fmo_paua_storm": "muck",
    "fmo_pearl_oyster": "wart",
    "fmo_labradorite": "lamella",
    "fmo_black_opal": "star",
    "fmo_ammolite_skin": "stone",
    "fmo_alexandrite_dusk": "tarnish",
    "fmo_moonstone_adular": "comet",
    "fmo_sunstone_glitter": "star",
    "fmo_fire_agate": "wart",
    "fmo_spectrolite_vein": "crackle",
    "fmo_bornite_patina": "tarnish",
    "fmo_chalcopyrite": "diamond",
}

_ACCENTS = (
    "arc", "ring", "comet", "fork", "diamond", "star", "barbule",
    "platelet", "film", "scale", "eye", "claw", "hex", "nacre",
)

_SUPPORTS = _ACCENTS + (
    "pit", "quill", "wisp", "ridge", "wart", "feather", "scute",
    "crackle", "lamella", "tarnish", "grating", "web", "pebble",
)

# SPB-WILDS 2026-08-23, owner-eye repair W-2. Owner verdict: "Too much
# redundancy way too similar looks. Must be VERY UNIQUE." The first W-1
# contact still collapsed many nouns into the same diagonal carrier plus
# flecks even though seven code layers were present. These banks make every
# visible support family semantically related to its noun; W-2 also quiets
# the shared carrier below so shape/orientation/negative space lead the eye.
_SEMANTIC_FAMILIES = {
    "fur": ("fur_tuft", "fur", "barbule", "quill", "claw", "arc", "pebble"),
    "quill": ("quill_shaft", "quill", "lamella", "ridge", "pit", "barbule", "ring"),
    "pebble": ("pebble", "stone", "pit", "crackle", "arc", "ring", "muck"),
    "eye": ("eye", "eyespot", "ring", "arc", "film", "star", "scale"),
    "eyespot": ("eyespot", "eye", "ring", "star", "arc", "scale", "film"),
    "muck": ("muck", "foam_cell", "ring", "pit", "arc", "wisp", "crackle"),
    "claw": ("claw", "ridge", "fork", "crackle", "quill", "arc", "pit"),
    "bark": ("bark", "fork", "crackle", "ridge", "stone", "pebble", "arc"),
    "feather": ("barb_fan", "feather", "barbule", "ridge", "quill", "arc", "eye"),
    "barbule": ("barb_fan", "barbule", "feather", "quill", "ridge", "scale", "arc"),
    "ridge": ("ridge", "cleavage", "lamella", "claw", "arc", "platelet", "pit"),
    "diamond": ("diamond", "platelet", "scale", "crackle", "ridge", "ring", "pit"),
    "scale": ("roof_scale", "scale", "nacre_lath", "ridge", "platelet", "eye", "arc"),
    "web": ("vein_cell", "web", "membrane", "fork", "crackle", "arc", "ring"),
    "fork": ("fork", "antler", "web", "crackle", "ridge", "arc", "star"),
    "antler": ("antler", "fork", "bark", "ridge", "stone", "arc", "pit"),
    "stone": ("stone", "platelet", "crackle", "pebble", "ridge", "ring", "arc"),
    "wisp": ("tendril", "wisp", "comet", "ring", "arc", "star", "fork"),
    "comet": ("comet", "tendril", "star", "ring", "arc", "wisp", "fork"),
    "bat": ("membrane", "bat", "vein_cell", "web", "claw", "arc", "eye"),
    "scute": ("elytron", "scute", "recess", "ridge", "platelet", "pit", "crackle"),
    "nacre": ("nacre_lath", "nacre", "brick", "growth_band", "film", "arc", "ring"),
    "hex": ("hex", "keystone", "crackle", "scale", "ridge", "eye", "star"),
    "crackle": ("crackle", "vein_cell", "fork", "ridge", "stone", "arc", "ring"),
    "platelet": ("keystone", "platelet", "diamond", "scale", "ridge", "star", "arc"),
    "film": ("meniscus", "film", "arc", "ring", "tendril", "star", "crackle"),
    "arc": ("arc", "growth_band", "film", "ring", "ridge", "crackle", "star"),
    "opal": ("pinfire", "opal", "ring", "platelet", "star", "tarnish", "crackle"),
    "ring": ("foam_cell", "ring", "meniscus", "arc", "opal", "muck", "crackle"),
    "lamella": ("cleavage", "lamella", "ridge", "nacre_lath", "crackle", "arc", "platelet"),
    "tarnish": ("tarnish", "stone", "film", "arc", "ring", "crackle", "platelet"),
    "grating": ("grating", "cleavage", "ridge", "lamella", "crackle", "star", "pit"),
    "star": ("dust_star", "star", "comet", "pinfire", "ring", "arc", "crackle"),
    "wart": ("wart", "recess", "ring", "pebble", "muck", "arc", "crackle"),
    "pit": ("recess", "pit", "ring", "pebble", "crackle", "arc", "platelet"),
}

# Explicit owner-eye divergence for the ten visually redundant clusters found
# in the W-1 70-contact review. Tuple fields are seven visible glyph families,
# seven independent spatial layouts, and the deliberately subordinate carrier
# kind. All glyph implementations below remain 2-8 work px (8-32px @2048).
_OWNER_EYE_TOPOLOGY = {
    # Black/mineral: pinfire islands vs constellations vs nacre storm terraces.
    "fmo_black_opal": (("pinfire", "opal", "platelet", "ring", "star", "crackle", "pit"), (13, 10, 6, 8, 12, 9, 11), 6),
    "fmo_luna_dust": (("dust_star", "comet", "star", "ring", "wisp", "arc", "pit"), (13, 12, 10, 15, 8, 11, 4), 3),
    "fmo_paua_storm": (("growth_band", "nacre_lath", "crackle", "arc", "film", "platelet", "ring"), (14, 3, 9, 8, 15, 5, 11), 7),
    # Green grid collapse: actual shared hexes, faceted scarab plates, recessed pits.
    "fc_dragon_hex_glass": (("hex", "vein_cell", "crackle", "scale", "ridge", "eye", "star"), (6, 7, 9, 1, 14, 10, 13), 0),
    "fmo_jewel_scarab": (("keystone", "platelet", "elytron", "star", "ridge", "film", "pit"), (12, 5, 1, 13, 8, 15, 10), 4),
    "fmo_weevil_pit": (("recess", "pit", "ring", "pebble", "crackle", "arc", "platelet"), (6, 10, 15, 13, 9, 8, 5), 3),
    # Teal vertical twins: broken luminous tendrils vs segmented beetle elytra.
    "fc_will_o_wisp": (("tendril", "wisp", "comet", "ring", "arc", "dust_star", "fork"), (13, 8, 12, 10, 15, 13, 9), 6),
    "fmo_tiger_beetle": (("elytron", "cleavage", "recess", "scute", "ridge", "pit", "platelet"), (14, 0, 1, 5, 7, 6, 10), 1),
    # Rail twins: longitudinal armor vs repeated local gorget fans.
    "fmo_ground_beetle": (("elytron", "cleavage", "scute", "recess", "ridge", "crackle", "pit"), (14, 0, 1, 6, 7, 9, 10), 2),
    "fmo_hummingbird_gorget": (("wing_fan", "barb_fan", "roof_scale", "star", "ridge", "eye", "platelet"), (12, 13, 1, 10, 8, 15, 5), 5),
    # Zigzag twins: curved growth, offset brick laths, directional feather fans.
    "fmo_mussel_shell": (("growth_band", "arc", "nacre_lath", "ridge", "ring", "crackle", "film"), (14, 3, 1, 8, 15, 9, 11), 7),
    "fmo_nacre_brick": (("brick", "nacre_lath", "platelet", "film", "arc", "ring", "scale"), (1, 14, 6, 15, 8, 10, 5), 0),
    "fmo_starling_sheen": (("barb_fan", "feather", "barbule", "ridge", "film", "eye", "scale"), (12, 13, 5, 8, 15, 10, 1), 4),
    # Navy sliver twins: shafts, curved feathers, articulated shell tiles.
    "fmo_cassowary_quill": (("quill_shaft", "quill", "lamella", "ridge", "pit", "barbule", "ring"), (0, 14, 7, 2, 6, 5, 10), 6),
    "fmo_raven_flash": (("barb_fan", "feather", "barbule", "film", "ridge", "arc", "eye"), (12, 13, 5, 15, 8, 11, 10), 7),
    "fmo_oil_beetle": (("shell_tile", "elytron", "platelet", "crackle", "film", "recess", "ridge"), (1, 14, 6, 9, 15, 10, 7), 0),
    # Brown carpets: tuft packets, wing fans, crescents, and true vein cells.
    "fc_sasquatch_fur": (("fur_tuft", "fur", "barbule", "quill", "claw", "pebble", "arc"), (13, 8, 5, 2, 9, 10, 11), 2),
    "fmo_atlas_wing": (("wing_fan", "vein_cell", "feather", "barbule", "scale", "ridge", "eye"), (12, 7, 13, 5, 1, 8, 10), 5),
    "fmo_sunset_moth": (("crescent", "roof_scale", "barbule", "eye", "ridge", "platelet", "star"), (1, 6, 5, 10, 8, 13, 12), 1),
    "fmo_monarch_vein": (("vein_cell", "web", "crackle", "roof_scale", "barbule", "ridge", "eye"), (7, 9, 8, 1, 5, 14, 10), 3),
    # Purple wing twins: membrane triangles vs aligned rachis/barb fans.
    "fc_batwing": (("membrane", "bat", "vein_cell", "web", "claw", "arc", "eye"), (6, 7, 9, 8, 2, 15, 10), 0),
    "fc_feathered_wing": (("barb_fan", "feather", "barbule", "quill_shaft", "ridge", "roof_scale", "arc"), (14, 13, 5, 0, 8, 1, 11), 4),
    # Blue checker twins: cleavage bands, fan rays, overlapping roof scales.
    "fmo_labradorite": (("cleavage", "lamella", "crackle", "ridge", "film", "platelet", "arc"), (14, 0, 9, 7, 15, 5, 11), 2),
    "fmo_ulysses_flash": (("wing_fan", "roof_scale", "barbule", "ridge", "platelet", "star", "eye"), (12, 1, 5, 8, 13, 10, 15), 5),
    "fmo_morpho_blue": (("roof_scale", "scale", "nacre_lath", "ridge", "platelet", "eye", "barbule"), (1, 6, 14, 8, 5, 10, 13), 3),
    # Ring-field twins: packed foam cells, oyster laths/domes, sparse menisci.
    "fmo_foam_film": (("foam_cell", "meniscus", "muck", "arc", "ring", "film", "crackle"), (6, 15, 13, 8, 10, 11, 9), 7),
    "fmo_pearl_oyster": (("nacre_lath", "brick", "platelet", "pebble", "ring", "film", "arc"), (14, 1, 6, 13, 10, 15, 8), 0),
    "fmo_soap_bubble": (("meniscus", "foam_cell", "ring", "film", "arc", "opal", "dust_star"), (15, 13, 10, 8, 11, 6, 12), 6),
}


def _stable_int(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little")


def _point(x: float, y: float, angle: float, length: float) -> tuple[int, int]:
    return int(round(x + np.cos(angle) * length)), int(round(y + np.sin(angle) * length))


def _line(img, a, b, value, thickness=2):
    # New W-2 polygon silhouettes use sub-pixel geometry; OpenCV's Python
    # binding requires concrete integer endpoints even though polylines below
    # accepts an ndarray conversion.
    aa = tuple(int(round(float(v))) for v in a)
    bb = tuple(int(round(float(v))) for v in b)
    cv2.line(img, aa, bb, float(value), int(thickness), cv2.LINE_AA)


def _poly(img, points, value, closed=True):
    cv2.polylines(img, [np.asarray(points, np.int32)], bool(closed), float(value), 2, cv2.LINE_AA)


def _draw_glyph(img, kind: str, x: float, y: float, size: float, angle: float,
                value: float, rng: np.random.Generator) -> None:
    """Draw one semantic glyph from 2-8 px primitives at the 512 work scale."""
    c = (int(round(x)), int(round(y)))
    s = float(np.clip(size, 3.0, 8.0))
    p = _point(x, y, angle, s)
    q = _point(x, y, angle + np.pi, s * 0.42)

    # W-2 noun silhouettes. Every stroke is two work pixels (8px native) and
    # every extent is capped at eight work pixels (32px native). Uniqueness
    # comes from topology, grouping, direction, and negative space—not size.
    if kind == "fur_tuft":
        root = _point(x, y, angle + np.pi, s * 0.40)
        for side, gain in ((-0.34, 0.70), (0.0, 1.0), (0.34, 0.82)):
            tip = _point(root[0], root[1], angle + side + rng.uniform(-0.08, 0.08), s * gain)
            _line(img, root, tip, value * (0.72 + gain * 0.22))
        cv2.circle(img, root, 1, float(value * 0.42), 2, cv2.LINE_AA)
    elif kind == "quill_shaft":
        nx, ny = -np.sin(angle), np.cos(angle)
        a0 = _point(x, y, angle + np.pi, s * 0.42)
        b0 = _point(x, y, angle, s * 0.82)
        for off, gain in ((-1.25, 0.78), (1.25, 1.0)):
            a = (int(a0[0] + nx * off), int(a0[1] + ny * off))
            b = (int(b0[0] + nx * off * 0.28), int(b0[1] + ny * off * 0.28))
            _line(img, a, b, value * gain)
        _line(img, a0, b0, value * 0.22)
    elif kind == "barb_fan":
        root = _point(x, y, angle + np.pi, s * 0.46)
        tip = _point(x, y, angle, s * 0.78)
        _line(img, root, tip, value)
        for t, side in ((0.18, -1.0), (0.35, 1.0), (0.52, -1.0), (0.69, 1.0)):
            bx = root[0] + (tip[0] - root[0]) * t
            by = root[1] + (tip[1] - root[1]) * t
            _line(img, (int(bx), int(by)),
                  _point(bx, by, angle + side * 1.02, s * (0.28 + t * 0.12)), value * (0.52 + t * 0.34))
    elif kind == "wing_fan":
        root = _point(x, y, angle + np.pi, s * 0.42)
        tips = [_point(root[0], root[1], angle + off, s * 0.92)
                for off in (-0.62, -0.20, 0.20, 0.62)]
        for k, tip in enumerate(tips):
            _line(img, root, tip, value * (0.56 + 0.13 * k))
        _poly(img, tips, value * 0.46, closed=False)
    elif kind == "membrane":
        root = _point(x, y, angle + np.pi, s * 0.42)
        tips = [_point(root[0], root[1], angle + off, s * 0.95) for off in (-0.66, 0.0, 0.66)]
        for tip in tips:
            _line(img, root, tip, value)
        _line(img, tips[0], tips[1], value * 0.48)
        _line(img, tips[1], tips[2], value * 0.48)
    elif kind == "vein_cell":
        dx, dy = np.cos(angle), np.sin(angle)
        nx, ny = -dy, dx
        hl, hw = s * 0.58, s * 0.42
        pts = [(x - dx * hl, y - dy * hl),
               (x - nx * hw, y - ny * hw),
               (x + dx * hl, y + dy * hl),
               (x + nx * hw, y + ny * hw)]
        _poly(img, pts, value)
        _line(img, pts[0], pts[2], value * 0.48)
        _line(img, c, _point(x, y, angle + 1.08, s * 0.38), value * 0.64)
    elif kind == "roof_scale":
        axes = (max(2, int(s * 0.58)), max(2, int(s * 0.42)))
        deg = float(np.degrees(angle))
        cv2.ellipse(img, c, axes, deg, 8, 172, float(value), 2, cv2.LINE_AA)
        _line(img, c, _point(x, y, angle + np.pi * 0.5, s * 0.42), value * 0.58)
    elif kind == "elytron":
        axes = (max(2, int(s * 0.62)), max(1, int(s * 0.31)))
        cv2.ellipse(img, c, axes, float(np.degrees(angle)), 0, 360, float(value), 2, cv2.LINE_AA)
        _line(img, _point(x, y, angle + np.pi, s * 0.52),
              _point(x, y, angle, s * 0.52), value * 0.46)
        cv2.circle(img, _point(x, y, angle, s * 0.22), 1, float(value * 0.70), 2, cv2.LINE_AA)
    elif kind == "shell_tile":
        pts = [_point(x, y, angle + k * np.pi * 0.5, s * (0.54 if k & 1 else 0.68)) for k in range(4)]
        _poly(img, pts, value)
        _line(img, pts[0], pts[2], value * 0.40)
        cv2.circle(img, c, 1, float(value * 0.72), 2, cv2.LINE_AA)
    elif kind == "keystone":
        dx, dy = np.cos(angle), np.sin(angle)
        nx, ny = -dy, dx
        hl = s * 0.58
        pts = [(x - dx * hl + nx * s * 0.28, y - dy * hl + ny * s * 0.28),
               (x - dx * hl - nx * s * 0.28, y - dy * hl - ny * s * 0.28),
               (x + dx * hl - nx * s * 0.46, y + dy * hl - ny * s * 0.46),
               (x + dx * hl + nx * s * 0.46, y + dy * hl + ny * s * 0.46)]
        _poly(img, pts, value)
        _line(img, c, pts[2], value * 0.52)
    elif kind == "recess":
        radius = max(2, int(s * 0.48))
        cv2.circle(img, c, radius, float(value), 2, cv2.LINE_AA)
        cv2.circle(img, c, max(1, radius - 2), float(value * 0.16), -1, cv2.LINE_AA)
        _line(img, _point(x, y, angle + 2.3, radius * 0.72),
              _point(x, y, angle - 0.7, radius * 0.72), value * 0.74)
    elif kind == "foam_cell":
        pts = [_point(x, y, angle + k * np.pi / 3.0,
                      s * (0.40 + 0.11 * ((k + int(rng.integers(0, 3))) % 3))) for k in range(6)]
        _poly(img, pts, value)
        _line(img, pts[1], pts[3], value * 0.28)
    elif kind == "meniscus":
        axes = (max(2, int(s * 0.58)), max(2, int(s * 0.46)))
        deg = float(np.degrees(angle))
        cv2.ellipse(img, c, axes, deg, 18, 198, float(value), 2, cv2.LINE_AA)
        cv2.ellipse(img, c, axes, deg, 210, 334, float(value * 0.55), 2, cv2.LINE_AA)
        _line(img, _point(x, y, angle + 2.4, s * 0.42),
              _point(x, y, angle - 0.55, s * 0.42), value * 0.34)
    elif kind == "nacre_lath":
        dx, dy = np.cos(angle), np.sin(angle)
        nx, ny = -dy, dx
        hl, hw = s * 0.62, s * 0.24
        pts = [(x + dx * hl + nx * hw, y + dy * hl + ny * hw),
               (x + dx * hl - nx * hw, y + dy * hl - ny * hw),
               (x - dx * hl - nx * hw, y - dy * hl - ny * hw),
               (x - dx * hl + nx * hw, y - dy * hl + ny * hw)]
        _poly(img, pts, value)
        _line(img, pts[0], pts[2], value * 0.32)
    elif kind == "brick":
        dx, dy = np.cos(angle), np.sin(angle)
        nx, ny = -dy, dx
        hl, hw = s * 0.60, s * 0.34
        pts = [(x + dx * hl + nx * hw, y + dy * hl + ny * hw),
               (x + dx * hl - nx * hw, y + dy * hl - ny * hw),
               (x - dx * hl - nx * hw, y - dy * hl - ny * hw),
               (x - dx * hl + nx * hw, y - dy * hl + ny * hw)]
        _poly(img, pts, value)
        _line(img, _point(x, y, angle + np.pi * 0.5, hw),
              _point(x, y, angle - np.pi * 0.5, hw), value * 0.50)
    elif kind == "growth_band":
        axes = (max(2, int(s * 0.62)), max(2, int(s * 0.45)))
        deg = float(np.degrees(angle))
        cv2.ellipse(img, c, axes, deg, 18, 164, float(value), 2, cv2.LINE_AA)
        inner = (max(2, axes[0] - 2), max(1, axes[1] - 2))
        cv2.ellipse(img, c, inner, deg, 24, 158, float(value * 0.54), 2, cv2.LINE_AA)
    elif kind == "cleavage":
        for off, gain, reach in ((-2.0, 0.52, 0.46), (0.0, 1.0, 0.68), (2.0, 0.72, 0.54)):
            a = _point(x, y, angle + np.pi * 0.5, off)
            _line(img, _point(a[0], a[1], angle + np.pi, s * reach),
                  _point(a[0], a[1], angle, s * reach), value * gain)
    elif kind == "tendril":
        root = _point(x, y, angle + np.pi, s * 0.48)
        mid = _point(root[0], root[1], angle + rng.uniform(-0.55, 0.55), s * 0.46)
        tip = _point(mid[0], mid[1], angle + rng.uniform(-0.9, 0.9), s * 0.42)
        _poly(img, (root, mid, tip), value, closed=False)
        cv2.circle(img, tip, 1, float(value * 0.72), 2, cv2.LINE_AA)
    elif kind == "pinfire":
        for k, gain in ((0, 1.0), (1, 0.74), (2, 0.52)):
            a = angle + k * 2.0 * np.pi / 3.0
            cc = _point(x, y, a, s * (0.12 + k * 0.13))
            cv2.circle(img, cc, 1, float(value * gain), 2, cv2.LINE_AA)
        _line(img, _point(x, y, angle, s * 0.18), _point(x, y, angle + np.pi, s * 0.18), value * 0.64)
    elif kind == "dust_star":
        for off, gain in ((0.0, 1.0), (np.pi * 0.5, 0.72), (np.pi * 0.25, 0.46)):
            _line(img, _point(x, y, angle + off, s * 0.38),
                  _point(x, y, angle + off + np.pi, s * 0.38), value * gain)
        cv2.circle(img, _point(x, y, angle + 0.9, s * 0.58), 1, float(value * 0.42), 2, cv2.LINE_AA)
    elif kind == "crescent":
        axes = (max(2, int(s * 0.58)), max(2, int(s * 0.42)))
        cv2.ellipse(img, c, axes, float(np.degrees(angle)), 36, 286, float(value), 2, cv2.LINE_AA)
        _line(img, _point(x, y, angle + 0.62, s * 0.48),
              _point(x, y, angle - 0.62, s * 0.48), value * 0.34)
    elif kind == "fur":
        _line(img, q, p, value)
        for off in (-0.9, 0.9):
            a = _point(x, y, angle + np.pi * 0.5, off)
            b = _point(a[0], a[1], angle + rng.uniform(-0.28, 0.28), s * 0.82)
            _line(img, a, b, value * 0.78)
    elif kind == "quill":
        _line(img, q, p, value)
        cv2.circle(img, q, 1, float(value * 0.46), 2, cv2.LINE_AA)
    elif kind in {"pebble", "pit", "wart"}:
        axes = (max(2, int(s * 0.55)), max(1, int(s * (0.30 if kind == "pebble" else 0.45))))
        cv2.ellipse(img, c, axes, float(np.degrees(angle)), 0, 360, float(value), 2, cv2.LINE_AA)
        if kind != "pebble":
            cv2.circle(img, c, 1, float(value * (0.34 if kind == "pit" else 0.62)), -1, cv2.LINE_AA)
    elif kind in {"eye", "eyespot"}:
        axes = (max(2, int(s * 0.58)), max(1, int(s * 0.34)))
        cv2.ellipse(img, c, axes, float(np.degrees(angle)), 0, 360, float(value), 2, cv2.LINE_AA)
        _line(img, _point(x, y, angle + np.pi * 0.5, 2),
              _point(x, y, angle - np.pi * 0.5, 2), value * 0.34)
        if kind == "eyespot":
            cv2.circle(img, c, max(1, int(s * 0.22)), float(value * 0.72), 2, cv2.LINE_AA)
    elif kind == "muck":
        cv2.circle(img, c, max(1, int(s * 0.32)), float(value), 2, cv2.LINE_AA)
        _line(img, c, p, value * 0.70)
        _line(img, p, _point(p[0], p[1], angle + 0.8, s * 0.35), value * 0.44)
    elif kind == "claw":
        for off in (-1.8, 0.0, 1.8):
            a = _point(x, y, angle + np.pi * 0.5, off)
            _line(img, a, _point(a[0], a[1], angle, s), value * (0.76 + 0.12 * (off == 0.0)))
    elif kind == "bark":
        _line(img, q, p, value)
        _line(img, c, _point(x, y, angle + 0.78, s * 0.52), value * 0.68)
        _line(img, c, _point(x, y, angle - 0.72, s * 0.38), value * 0.52)
    elif kind in {"feather", "barbule"}:
        _line(img, q, p, value)
        for t in (0.08, 0.38, 0.68):
            bx = q[0] + (p[0] - q[0]) * t
            by = q[1] + (p[1] - q[1]) * t
            for side in (-1.0, 1.0):
                _line(img, (int(bx), int(by)), _point(bx, by, angle + side * 0.92, s * 0.34), value * 0.66)
    elif kind in {"ridge", "diamond", "scale"}:
        left = _point(x, y, angle + 2.35, s * 0.58)
        right = _point(x, y, angle - 2.35, s * 0.58)
        _line(img, left, p, value)
        _line(img, p, right, value)
        if kind == "diamond":
            back = _point(x, y, angle + np.pi, s * 0.62)
            _line(img, right, back, value * 0.82)
            _line(img, back, left, value * 0.82)
        elif kind == "scale":
            _line(img, left, right, value * 0.54)
            _line(img, c, p, value * 0.66)
    elif kind in {"web", "fork", "antler"}:
        _line(img, q, p, value)
        root = _point(x, y, angle, s * 0.35)
        for side in (-1.0, 1.0):
            tip = _point(root[0], root[1], angle + side * (0.72 if kind == "web" else 0.95), s * 0.58)
            _line(img, root, tip, value * (0.78 if kind != "antler" else 0.92))
            if kind == "antler":
                _line(img, tip, _point(tip[0], tip[1], angle + side * 1.25, s * 0.28), value * 0.62)
        if kind == "web":
            _line(img, _point(x, y, angle + 0.8, s * 0.48),
                  _point(x, y, angle - 0.8, s * 0.48), value * 0.48)
    elif kind == "stone":
        pts = [_point(x, y, angle + k * (np.pi / 3.0), s * rng.uniform(0.38, 0.58)) for k in range(6)]
        _poly(img, pts, value)
        _line(img, c, pts[int(rng.integers(0, len(pts)))], value * 0.48)
    elif kind in {"wisp", "comet"}:
        cv2.circle(img, c, max(1, int(s * 0.22)), float(value), 2, cv2.LINE_AA)
        mid = _point(x, y, angle + np.pi, s * 0.48)
        end = _point(mid[0], mid[1], angle + np.pi + rng.uniform(-0.8, 0.8), s * 0.42)
        _line(img, c, mid, value * 0.72)
        _line(img, mid, end, value * 0.42)
    elif kind == "bat":
        for side in (-0.62, 0.0, 0.62):
            _line(img, q, _point(x, y, angle + side, s), value * (0.78 if side else 1.0))
        a = _point(x, y, angle - 0.62, s)
        b = _point(x, y, angle + 0.62, s)
        _line(img, a, p, value * 0.48)
        _line(img, p, b, value * 0.48)
    elif kind in {"scute", "nacre"}:
        dx, dy = np.cos(angle), np.sin(angle)
        nx, ny = -dy, dx
        hl, hw = s * 0.55, s * (0.30 if kind == "nacre" else 0.42)
        pts = [(x + dx * hl + nx * hw, y + dy * hl + ny * hw),
               (x + dx * hl - nx * hw, y + dy * hl - ny * hw),
               (x - dx * hl - nx * hw, y - dy * hl - ny * hw),
               (x - dx * hl + nx * hw, y - dy * hl + ny * hw)]
        _poly(img, pts, value)
        _line(img, c, p, value * 0.46)
    elif kind == "hex":
        pts = [_point(x, y, angle + k * np.pi / 3.0, s * 0.55) for k in range(6)]
        _poly(img, pts, value)
        _line(img, pts[0], pts[3], value * 0.42)
    elif kind == "crackle":
        mid = _point(x, y, angle, s * 0.48)
        _line(img, q, mid, value)
        _line(img, mid, p, value * 0.86)
        _line(img, mid, _point(mid[0], mid[1], angle + 1.12, s * 0.42), value * 0.58)
    elif kind == "platelet":
        pts = [_point(x, y, angle + k * 2.0 * np.pi / 5.0, s * rng.uniform(0.38, 0.58)) for k in range(5)]
        _poly(img, pts, value)
        _line(img, pts[0], pts[2], value * 0.52)
    elif kind in {"film", "arc"}:
        axes = (max(2, int(s * 0.55)), max(1, int(s * 0.32)))
        start = int(rng.integers(0, 180))
        cv2.ellipse(img, c, axes, float(np.degrees(angle)), start, start + 150, float(value), 2, cv2.LINE_AA)
        _line(img, c, _point(x, y, angle + 1.2, s * 0.45), value * 0.46)
    elif kind == "opal" or kind == "ring":
        cv2.circle(img, c, max(1, int(s * 0.48)), float(value), 2, cv2.LINE_AA)
        cv2.circle(img, c, max(1, int(s * 0.22)), float(value * 0.58), 2, cv2.LINE_AA)
    elif kind == "lamella":
        for off, amp in ((-2.0, 0.58), (0.0, 1.0), (2.0, 0.72)):
            a = _point(x, y, angle + np.pi * 0.5, off)
            _line(img, _point(a[0], a[1], angle + np.pi, s * 0.38),
                  _point(a[0], a[1], angle, s * 0.55), value * amp)
    elif kind == "tarnish":
        for k in range(4):
            a = angle + k * np.pi * 0.5 + rng.uniform(-0.25, 0.25)
            cc = _point(x, y, a, s * 0.28)
            cv2.circle(img, cc, max(1, int(s * 0.20)), float(value * (0.52 + 0.12 * k)), 2, cv2.LINE_AA)
    elif kind == "grating":
        _line(img, q, p, value)
        _line(img, _point(x, y, angle + np.pi * 0.5, s * 0.62),
              _point(x, y, angle - np.pi * 0.5, s * 0.62), value * 0.76)
        _line(img, _point(x, y, angle + 0.8, s * 0.48),
              _point(x, y, angle + np.pi + 0.8, s * 0.48), value * 0.48)
    elif kind == "star":
        for off in (0.0, np.pi / 3.0, 2.0 * np.pi / 3.0):
            _line(img, _point(x, y, angle + off, s * 0.48),
                  _point(x, y, angle + off + np.pi, s * 0.48), value)
    else:
        _line(img, q, p, value)


def _scatter(kind: str, count: int, seed: int, angle0: float, variant: int,
             size_range=(3.0, 8.0), layout_override: int | None = None) -> np.ndarray:
    """Scatter one family on a jittered grid so density, never size, fills gaps."""
    rng = np.random.default_rng(seed)
    img = np.zeros((_DESIGN, _DESIGN), np.float32)
    side = max(2, int(np.ceil(np.sqrt(count))))
    cell = _DESIGN / float(side)
    layout = int(variant) % 16 if layout_override is None else int(layout_override) % 16
    k = 0
    for gy in range(side):
        for gx in range(side):
            if k >= count:
                break
            k += 1
            jitter = 0.14 if layout in {0, 1, 5, 6, 7, 12, 14} else 0.38
            x = (gx + 0.5) * cell + rng.uniform(-jitter, jitter) * cell
            y = (gy + 0.5) * cell + rng.uniform(-jitter, jitter) * cell
            if layout == 1:           # staggered scale/brick rows
                x += (gy & 1) * cell * 0.48
            elif layout == 2:         # serpentine columns of short marks
                x += np.sin(gy * 0.72) * cell * 1.25
            elif layout == 3:         # rippling rows
                y += np.sin(gx * 0.61) * cell * 1.15
            elif layout == 4:         # rotated micro-lattice
                dx, dy = x - _DESIGN * 0.5, y - _DESIGN * 0.5
                ca, sa = np.cos(angle0 * 0.37), np.sin(angle0 * 0.37)
                x = _DESIGN * 0.5 + dx * ca - dy * sa
                y = _DESIGN * 0.5 + dx * sa + dy * ca
            elif layout == 5:         # paired herringbone packets
                x += (-0.22 if gx & 1 else 0.22) * cell
                y += (0.18 if gx & 1 else -0.18) * cell
            elif layout == 6:         # compact honeycomb staggering
                x += (gy & 1) * cell * 0.50
                y *= 0.90
            elif layout == 7:         # diagonal woven lattice
                x += gy * cell * 0.23
            elif layout == 8:         # crossing wave warp
                x += np.sin(gy * 0.55) * cell * 0.78
                y += np.cos(gx * 0.47) * cell * 0.78
            elif layout == 9:         # braided packets
                x += np.sin((gx + gy) * 0.48) * cell * 1.05
                y += np.sin((gx - gy) * 0.41) * cell * 0.72
            elif layout == 10:        # tight four-mark constellations
                x += ((gx % 2) - 0.5) * cell * 0.34
                y += ((gy % 2) - 0.5) * cell * 0.34
            elif layout == 12:        # repeated local fans; no canvas-sized vortex
                x += np.sin((gy % 5) * 1.18) * cell * 0.30
                y += np.cos((gx % 5) * 1.07) * cell * 0.30
            elif layout == 13:        # compact archipelagos with dark gutters
                bx, by = gx // 4, gy // 4
                lx, ly = gx % 4, gy % 4
                x = (bx * 4.0 + 2.0 + (lx - 1.5) * 0.54) * cell
                y = (by * 4.0 + 2.0 + (ly - 1.5) * 0.54) * cell
            elif layout == 14:        # broken longitudinal lanes
                x += ((gy % 5) - 2.0) * cell * 0.16
                y += np.sin(gx * 0.83 + (gy % 3)) * cell * 0.24
            elif layout == 15:        # loose three-mark film/terrace islands
                bx, by = gx // 3, gy // 3
                lx, ly = gx % 3, gy % 3
                x = (bx * 3.0 + 1.5 + (lx - 1.0) * 0.70) * cell
                y = (by * 3.0 + 1.5 + (ly - 1.0) * 0.70) * cell
            x %= _DESIGN
            y %= _DESIGN
            # Coherent direction comes from many short marks; no long primitive
            # or macro blob is ever drawn.
            flow = (np.sin((x + variant * 7) * 0.031) + np.cos((y - variant * 11) * 0.027)) * 0.42
            if layout == 0:
                angle = angle0 + rng.uniform(-0.10, 0.10)
            elif layout == 1:
                angle = angle0 + (0.34 if gy & 1 else -0.34) + rng.uniform(-0.12, 0.12)
            elif layout == 2:
                angle = angle0 + np.sin(gy * 0.72) * 0.72 + rng.uniform(-0.16, 0.16)
            elif layout == 3:
                angle = np.arctan2(y - _DESIGN * 0.5, x - _DESIGN * 0.5) + np.pi * 0.5 + rng.uniform(-0.16, 0.16)
            elif layout == 4:
                angle = np.arctan2(y - _DESIGN * 0.5, x - _DESIGN * 0.5) + rng.uniform(-0.14, 0.14)
            elif layout == 5:
                angle = angle0 + (0.78 if (gx + gy) & 1 else -0.78) + rng.uniform(-0.10, 0.10)
            elif layout == 6:
                angle = angle0 + (gy % 3 - 1) * 0.42 + rng.uniform(-0.12, 0.12)
            elif layout == 7:
                angle = angle0 + (np.pi * 0.5 if gx & 1 else 0.0) + rng.uniform(-0.10, 0.10)
            elif layout == 8:
                angle = angle0 + flow * 1.4 + rng.uniform(-0.18, 0.18)
            elif layout == 9:
                angle = angle0 + np.sin((gx - gy) * 0.41) * 0.85 + rng.uniform(-0.15, 0.15)
            elif layout == 10:
                angle = angle0 + ((gx % 2) * 2 - 1) * 0.52 + rng.uniform(-0.14, 0.14)
            elif layout == 12:
                cx = (gx // 5) * 5 + 2.0
                cy = (gy // 5) * 5 + 2.0
                angle = angle0 + np.arctan2(gy - cy, gx - cx) + rng.uniform(-0.12, 0.12)
            elif layout == 13:
                angle = angle0 + ((gx + gy) % 4) * (np.pi * 0.5) + rng.uniform(-0.24, 0.24)
            elif layout == 14:
                angle = angle0 + (0.16 if gy & 1 else -0.16) + rng.uniform(-0.08, 0.08)
            elif layout == 15:
                angle = angle0 + ((gx % 3) - 1) * 0.66 + rng.uniform(-0.18, 0.18)
            else:
                angle = angle0 + flow + rng.uniform(-0.52, 0.52)
            size = rng.uniform(float(size_range[0]), float(size_range[1]))
            value = float(_MARK_TIERS[int(rng.integers(0, 8))])
            _draw_glyph(img, kind, x, y, size, angle, value, rng)
    return np.clip(img, 0.0, 1.0)


def _recipe_hues(fid: str, recipe: Mapping, variant: int) -> tuple[float, ...]:
    if fid in _CRYPTID_STYLE:
        return tuple(float(v) % 1.0 for v in _CRYPTID_STYLE[fid][1])
    raw = recipe.get("hues") or ()
    anchors = [float(v) % 1.0 for v in raw]
    if not anchors:
        # Recover a meaningful hue from the existing authored colors if a
        # future Wilds recipe omits the Morpho hue-window schema.
        for key in ("glow", "edge", "base"):
            rgb = recipe.get(key)
            if isinstance(rgb, Sequence) and len(rgb) >= 3 and max(rgb) > 0:
                anchors.append(colorsys.rgb_to_hsv(*(float(c) / 255.0 for c in rgb[:3]))[0])
                break
    if not anchors:
        anchors = [((_stable_int(fid) >> 8) % 1000) / 1000.0]
    # At least two opposing structural colors.  The offset varies across all
    # 50 Morpho IDs so identical source windows cannot become recolors.
    if len(anchors) == 1:
        anchors.append((anchors[0] + 0.27 + (variant % 5) * 0.041) % 1.0)
    if len(anchors) == 2 and variant % 3 == 0:
        anchors.append((anchors[0] - 0.19 - (variant % 4) * 0.025) % 1.0)
    return tuple(anchors[:3])


def _palette(hues: tuple[float, ...], variant: int) -> np.ndarray:
    hue_nudge = (0.0, 0.018, -0.026, 0.042, -0.054, 0.071, -0.082, 0.105)
    values = (0.16, 0.24, 0.33, 0.43, 0.54, 0.65, 0.77, 0.90)
    out = []
    for i in range(8):
        h = (hues[(i + variant) % len(hues)] + hue_nudge[i]) % 1.0
        s = 0.68 + 0.27 * (((i * 5 + variant) % 8) / 7.0)
        out.append(colorsys.hsv_to_rgb(h, min(s, 0.96), values[i]))
    return np.asarray(out, np.float32)


def _feature_palette(hue: float, variant: int, salt: int) -> np.ndarray:
    """Cohesive eight-shade bank for one mark family (not rainbow confetti)."""
    values = (0.25, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84, 0.94)
    nudges = (-0.035, -0.022, -0.012, 0.0, 0.011, 0.022, 0.034, 0.047)
    out = []
    for i in range(8):
        h = (float(hue) + nudges[(i + variant + salt) % 8]) % 1.0
        s = 0.70 + 0.25 * (((i * 3 + variant + salt) % 8) / 7.0)
        out.append(colorsys.hsv_to_rgb(h, min(0.96, s), values[i]))
    return np.asarray(out, np.float32)


def _standardize(field: np.ndarray) -> np.ndarray:
    a = np.asarray(field, np.float32)
    return (a - float(a.mean())) / (float(a.std()) + 1e-6)


def _rank_eight(score: np.ndarray) -> np.ndarray:
    """Deterministically occupy all eight material tiers at useful density.

    Rank bins keep each tier near 12.5% occupancy. This prevents a nominal
    eight-tier pass where one shade exists only in antialias fringe pixels.
    The score itself is feature-attached; the rank operation changes only its
    ordered material shade, never paint topology or luma.
    """
    flat = np.asarray(score, np.float32).ravel()
    order = np.argsort(flat, kind="stable")
    tiers = np.empty(flat.size, np.uint8)
    tiers[order] = np.minimum(7, (np.arange(flat.size, dtype=np.int64) * 8) // flat.size).astype(np.uint8)
    return tiers.reshape(score.shape)


@lru_cache(maxsize=8)
def _design_cached(fid: str, family: str, engine_name: str,
                   hues: tuple[float, ...]) -> tuple[np.ndarray, np.ndarray]:
    token = _stable_int(fid)
    variant = token % 97
    rng = np.random.default_rng(token & 0x7FFFFFFF)
    if family == "cryptid":
        primary_kind = _CRYPTID_STYLE[fid][0]
    else:
        primary_kind = _MORPHO_STYLE.get(fid, _MORPHO_MOTIFS.get(engine_name, _ACCENTS[variant % len(_ACCENTS)]))
    owner_topology = _OWNER_EYE_TOPOLOGY.get(fid)
    if owner_topology is not None:
        kinds, layouts, carrier_override = owner_topology
    else:
        kinds = _SEMANTIC_FAMILIES.get(primary_kind)
        if kinds is None:
            secondary_kind = _ACCENTS[(variant * 5 + 3) % len(_ACCENTS)]
            available = [k for k in _SUPPORTS if k not in {primary_kind, secondary_kind}]
            support_kinds = []
            cursor = (variant * 7 + 5) % len(available)
            while len(support_kinds) < 5:
                kind = available[cursor % len(available)]
                if kind not in support_kinds:
                    support_kinds.append(kind)
                cursor += 7
            kinds = (primary_kind, secondary_kind, *support_kinds)
        # Deterministic but visibly different spatial grammar for every ID.
        layouts = tuple((variant + offset) % 16 for offset in (0, 5, 9, 13, 2, 7, 11))
        carrier_override = variant % 8
    primary_kind, secondary_kind, *support_kinds = kinds
    angle0 = (variant / 97.0) * np.pi * 2.0

    # Seven visibly contributing mark families. Counts change by ID while all
    # dimensions remain within the 8-32px doctrine at native 2048.
    primary_count = 600 + (variant % 5) * 28
    if fid == "fc_dragon_hex_glass":
        primary_count = 2500  # connected 8-32px shared-edge honeycomb, not square loops
    elif fid in {"fmo_weevil_pit", "fmo_foam_film"}:
        primary_count = 940
    elif fid in {"fmo_black_opal", "fmo_luna_dust", "fc_will_o_wisp"}:
        primary_count = 460  # clustered negative space; density remains in six support families
    primary_range = (7.0, 8.0) if fid == "fc_dragon_hex_glass" else (6.0, 8.0)
    counts = (primary_count, 380 + (variant % 5) * 24,
              265 + (variant % 4) * 22, 230 + (variant % 5) * 19,
              205 + (variant % 4) * 17, 190 + (variant % 5) * 15,
              180 + (variant % 6) * 13)
    angles = (0.0, 1.13, -0.57, 0.31, 2.05, -1.72, 0.82)
    seeds = (0x13579BDF, 0x2468ACE1, 0x31415926, 0x27182818,
             0xA5A5A5A5, 0x5A5A5A5A, 0x6C8E9CF5)
    sizes = (primary_range, (5.0, 8.0), (4.0, 7.0), (4.0, 7.0),
             (3.0, 6.0), (3.0, 6.0), (3.0, 6.0))
    layers = [
        _scatter(kind, int(count), token ^ seed, angle0 + angle, variant + index * 6,
                 size_range, layout_override=layout)
        for index, (kind, count, seed, angle, size_range, layout) in enumerate(
            zip(kinds, counts, seeds, angles, sizes, layouts))
    ]
    primary, secondary, capsules, spots, rings, arcs, flecks = layers

    # Two-pixel cells become 8px at 2048. A fine 4-8px wave changes feature
    # ordering without introducing the old 100-400px composition blobs.
    grain_small = rng.integers(0, 2, (_DESIGN // 2, _DESIGN // 2), dtype=np.uint8)
    grain = cv2.resize(grain_small, (_DESIGN, _DESIGN), interpolation=cv2.INTER_NEAREST).astype(np.int16)
    yy, xx = np.mgrid[0:_DESIGN, 0:_DESIGN].astype(np.float32)
    period = float(4 + (variant % 5))
    wave = (np.sin((xx * np.cos(angle0) + yy * np.sin(angle0)) * (2.0 * np.pi / period)) > 0.86).astype(np.int16)

    p8 = np.clip((primary * 7.99).astype(np.int16), 0, 7)
    s8 = np.clip((secondary * 7.99).astype(np.int16), 0, 7)
    c8 = np.clip((capsules * 7.99).astype(np.int16), 0, 7)
    d8 = np.clip((spots * 7.99).astype(np.int16), 0, 7)
    r8 = np.clip((rings * 7.99).astype(np.int16), 0, 7)
    a8 = np.clip((arcs * 7.99).astype(np.int16), 0, 7)
    f8 = np.clip((flecks * 7.99).astype(np.int16), 0, 7)

    # Keep the calm paint body coherent. Each visible glyph receives its own
    # tier rather than turning every background pixel into rainbow confetti.
    # Keep the material body in the useful mid tiers instead of making most of
    # the car nearly non-metallic.  The 3/4 alternation is still an 8-24px
    # carrier, while the seven authored mark families exercise all eight tiers.
    phase = 3 + ((grain + wave + variant) % 2)
    # Quiet/support structure first, then the same visual order used by paint.
    # The primary hue occupies high metal tiers while the opposing secondary
    # hue occupies low metal tiers; clearcoat reverses those bands below. This
    # is a true material-response color trade under angle A/B, not recoloring.
    phase = np.where(c8 > 3, (c8 + 1 + variant) % 8, phase)
    phase = np.where(d8 > 2, (d8 + 6 + variant) % 8, phase)
    phase = np.where(r8 > 2, (r8 + 3 + variant) % 8, phase)
    phase = np.where(a8 > 3, (a8 + 7 + variant) % 8, phase)
    phase = np.where(f8 > 3, (f8 + 4 + variant) % 8, phase)
    phase = np.where(s8 > 2, s8 % 4, phase)
    phase = np.where(p8 > 1, 4 + (p8 % 4), phase)
    # Roughness and clearcoat select tiers from the same seven authored mark
    # masks in different overlap orders.  This is the actual angle-flip: one
    # feather/scale/crackle can brighten in metal while its neighbour opens in
    # clearcoat, without laying unrelated random noise over the semantic art.
    phase_r = 2 + ((grain * 2 + wave + variant) % 4)
    phase_r = np.where(f8 > 3, (f8 + 1 + variant) % 8, phase_r)
    phase_r = np.where(c8 > 3, (c8 + 6 + variant) % 8, phase_r)
    phase_r = np.where(r8 > 2, (r8 + 4 + variant) % 8, phase_r)
    phase_r = np.where(p8 > 1, (p8 + 7 + variant) % 8, phase_r)
    phase_r = np.where(d8 > 2, (d8 + 2 + variant) % 8, phase_r)
    phase_r = np.where(a8 > 3, (a8 + 5 + variant) % 8, phase_r)
    phase_r = np.where(s8 > 2, (s8 + 3 + variant) % 8, phase_r)

    phase_c = 1 + ((grain + wave * 3 + variant) % 6)
    phase_c = np.where(d8 > 2, (d8 + 5 + variant) % 8, phase_c)
    phase_c = np.where(a8 > 3, (a8 + 6 + variant) % 8, phase_c)
    phase_c = np.where(f8 > 3, (f8 + 2 + variant) % 8, phase_c)
    phase_c = np.where(r8 > 2, (r8 + 7 + variant) % 8, phase_c)
    phase_c = np.where(c8 > 3, (c8 + 3 + variant) % 8, phase_c)
    phase_c = np.where(p8 > 1, p8 % 4, phase_c)
    phase_c = np.where(s8 > 2, 4 + (s8 % 4), phase_c)
    # Cohesive dark body + family-specific color banks. The former experiment
    # mapped the entire background through all eight phases; it passed numeric
    # uniqueness but visually collapsed into 70 fields of colored confetti.
    # Owner eye wins: only authored marks flip color, so feathers still read as
    # feathers, scales as scales, and the secondary hue becomes an angle-flash.
    base_h = hues[0]
    base_rgb = np.asarray(colorsys.hsv_to_rgb(base_h, 0.68, 0.13 + (variant % 4) * 0.012), np.float32)
    # A per-ID fine body carrier (2-6 work pixels = 8-24px native) prevents
    # empty paint between marks and adds another visibly distinct family. Every
    # carrier is segmented in both axes; none can become a canvas-long stripe.
    cell = float(2 + variant % 5)
    ux = xx * np.cos(angle0) + yy * np.sin(angle0)
    uy = -xx * np.sin(angle0) + yy * np.cos(angle0)
    carrier_kind = int(carrier_override) % 8
    if carrier_kind == 0:      # micro checker
        body_micro = ((np.floor(ux / cell) + np.floor(uy / cell)) % 2).astype(np.float32)
    elif carrier_kind == 1:    # staggered brick chips
        body_micro = ((np.floor((ux + (np.floor(uy / cell) % 2) * cell * 0.5) / cell)
                       + np.floor(uy / (cell * 2.0))) % 2).astype(np.float32)
    elif carrier_kind == 2:    # crossed dash packets
        body_micro = (((np.floor(ux / cell) % 3) == 0) & ((np.floor(uy / cell) % 3) < 2)).astype(np.float32)
    elif carrier_kind == 3:    # fine bead lattice
        fx, fy = np.mod(ux, cell * 2.0) - cell, np.mod(uy, cell * 2.0) - cell
        body_micro = (np.hypot(fx, fy) < cell * 0.46).astype(np.float32)
    elif carrier_kind == 4:    # herringbone chips
        body_micro = ((np.floor((ux + np.sign(np.sin(uy / cell * np.pi)) * uy) / cell) % 3) == 0).astype(np.float32)
    elif carrier_kind == 5:    # tiny stepped chevrons
        body_micro = ((np.floor((np.abs(np.mod(ux, cell * 4.0) - cell * 2.0) + uy) / cell) % 4) == 0).astype(np.float32)
    elif carrier_kind == 6:    # alternating pin cells, cut across both axes
        body_micro = (((np.floor(ux / cell) % 4) == 0) & ((np.floor(uy / cell) % 2) == 0)).astype(np.float32)
    else:                      # broken micro waves
        body_micro = ((np.sin(ux * (2.0 * np.pi / (cell * 2.0))) > 0.45)
                      & (np.cos(uy * (2.0 * np.pi / (cell * 3.0))) > -0.35)).astype(np.float32)
    # SPB-WILDS 2026-08-23 W-2; owner verdict: "way too similar looks." The
    # owner-eye audit measured the shared carrier as the dominant visible
    # grammar in 10/10 worst clusters. Carrier amplitude 1.45 -> 0.88 (-39%),
    # grain 0.75 -> 0.54 (-28%), wave 0.65 -> 0.43 (-34%); the seven noun
    # families now carry contrast without growing past 32px native.
    body_shade = (0.27 + grain.astype(np.float32) * 0.54
                  + wave.astype(np.float32) * 0.43 + body_micro * 0.88)[..., None]
    paint = np.broadcast_to(base_rgb, (_DESIGN, _DESIGN, 3)).copy() * body_shade

    primary_bank = _feature_palette(hues[0], variant, 0)
    second_h = hues[1 % len(hues)]
    secondary_bank = _feature_palette(second_h, variant, 3)
    third_h = hues[2] if len(hues) > 2 else (hues[0] + hues[1]) * 0.5
    tertiary_bank = _feature_palette(third_h, variant, 6)

    def blend(layer, tiers, bank, strength, cap):
        nonlocal paint
        alpha = np.clip(layer * float(strength), 0.0, float(cap))[..., None]
        target = bank[tiers]
        paint = paint * (1.0 - alpha) + target * alpha

    # Quiet support families first; semantic primary/secondary glyphs finish on
    # top. All seven remain visible at native resolution without sharing one
    # dominant dot/ring grammar.
    blend(capsules, c8, tertiary_bank, 0.58, 0.52)
    blend(spots, d8, secondary_bank, 0.54, 0.48)
    blend(rings, r8, tertiary_bank, 0.50, 0.44)
    blend(arcs, a8, primary_bank, 0.48, 0.42)
    blend(flecks, f8, secondary_bank, 0.52, 0.46)
    blend(secondary, s8, secondary_bank, 1.12, 0.82)
    blend(primary, p8, primary_bank, 1.45, 0.96)
    paint = np.clip(paint, 0.0, 1.0).astype(np.float32)

    # Name-level material identity remains intentional. Black pearl/opal and
    # moon/paua finishes keep low-chroma bodies with colored angle flashes;
    # Morpho Blue sits at a satin middle chroma instead of sharing the bright
    # candy body used by the insect finishes. This also prevents hue alone from
    # masquerading as structural uniqueness.
    if fid in {"fmo_black_opal", "fmo_luna_dust", "fmo_paua_storm"}:
        luma = (paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114)[..., None]
        # W-2 owner-eye repair: the W-1 94/6 neutralisation made three named
        # color-flip finishes indistinguishable grey at picker size. 72/28
        # retains black mineral bodies while exposing hue-bearing pinfire,
        # dust, and nacre marks for the paired light-angle proof.
        paint = np.clip(luma * 0.72 + paint * 0.28, 0.0, 1.0).astype(np.float32)
    elif fid == "fmo_black_pearl":
        luma = (paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114)[..., None]
        paint = np.clip(luma * 0.84 + paint * 0.16, 0.0, 1.0).astype(np.float32)
    elif fid == "fmo_morpho_blue":
        luma = (paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114)[..., None]
        paint = np.clip(luma * 0.38 + paint * 0.62, 0.0, 1.0).astype(np.float32)
    elif fid == "fmo_fire_agate":
        # A deliberately finite 12-color agate bank (three fire/mineral hues x
        # four values) removes anti-alias-only color bins that made this stone
        # read like generic rainbow glitter while preserving its micro rings.
        fire_values = (0.12, 0.29, 0.50, 0.76)
        # Recipe promise is ember + green + violet fire. The former fallback
        # 0.13 sat between orange and green, collapsing the nominal 12-color
        # bank to 10 materially occupied HSV bins. Violet 0.78 restores three
        # distinct hue families without changing topology or value tiers.
        fire_hues = (hues[0], hues[1 % len(hues)], hues[2] if len(hues) > 2 else 0.78)
        fire_bank = np.asarray([
            [colorsys.hsv_to_rgb(float(h), 0.86, v) for v in fire_values]
            for h in fire_hues
        ], np.float32)
        fire_value = np.clip((paint.max(axis=2) * 4.0).astype(np.int16), 0, 3)
        fire_hue = (phase + grain + body_micro.astype(np.int16) * 2) % 3
        paint = fire_bank[fire_hue, fire_value].astype(np.float32)

    # A few naturally darker motifs have less occupied edge area even though
    # their primitives are correctly fine. Increase local luma separation,
    # never feature size: this keeps low-saturation pearl bodies neutral and
    # makes the 8-32px authored carrier survive a car thumbnail.
    contrast_ids = {
        "fc_batwing", "fc_feathered_wing", "fmo_black_pearl",
        "fmo_bornite_patina", "fmo_emperor_scale", "fmo_fire_agate", "fmo_ground_beetle",
        "fmo_magpie_wing", "fmo_moonstone_adular", "fmo_mussel_shell",
        "fmo_oil_beetle", "fmo_starling_sheen",
    }
    if fid in contrast_ids:
        luma = paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114
        target_luma = np.clip(luma.mean() + (luma - luma.mean()) * 1.65, 0.012, 0.96)
        paint = np.clip(paint * (target_luma / np.maximum(luma, 1e-4))[..., None], 0.0, 1.0).astype(np.float32)
    elif fid == "fc_crackle_eyeshine_glass":
        # Crackle is the one token whose intent band is MID, not HIGH. A tiny
        # sub-primitive antialias pass keeps 8-32px cracks intact while avoiding
        # a misleading razor-noise score.
        paint = cv2.GaussianBlur(paint, (3, 3), 0.55).astype(np.float32)

    # SPB-WILDS 2026-08-23 W-3 internal visual pass; this was incorrectly
    # recorded as owner acceptance before the owner had reviewed the work.
    # The actual 2026-08-24 owner review rejected the shared topology as lazy;
    # this legacy renderer remains only until the WR-2 overrides are wired.
    # W-2 neutral-excluded hue-TV min/median was captured before this change in
    # `_wilds_work/owner_eye_w2_validation_before`. Paint is untouched here.
    # Actual visible paint hue affinity now biases metal and clearcoat in
    # opposite directions, while three different authored-support/carrier
    # scores supply enough independence to hold |corr| < .75.
    hsv = cv2.cvtColor(paint.astype(np.float32), cv2.COLOR_RGB2HSV)
    hue01 = hsv[:, :, 0] / 360.0
    saturation = hsv[:, :, 1]
    primary_h = float(hues[0])
    secondary_h = float(hues[1 % len(hues)])
    hue_affinity = saturation * (
        np.cos((hue01 - primary_h) * (2.0 * np.pi))
        - np.cos((hue01 - secondary_h) * (2.0 * np.pi))
    )
    hue_affinity = _standardize(hue_affinity)
    paint_luma = _standardize(paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114)

    # Paired differences cancel broad hue occupancy inside each bank; their
    # remaining geometry plus the already-visible body carrier decorrelates
    # channels without adding unrelated random material noise.
    carrier_m = np.sin(ux * (2.0 * np.pi / max(4.0, cell * 3.0))) + 0.63 * np.cos(uy * (2.0 * np.pi / max(5.0, cell * 4.0)))
    carrier_c = np.cos((ux + uy) * (2.0 * np.pi / max(6.0, cell * 5.0))) - 0.57 * np.sin(uy * (2.0 * np.pi / max(4.0, cell * 3.0)))
    carrier_r = np.sin((ux - uy) * (2.0 * np.pi / max(5.0, cell * 4.0))) + 0.51 * np.cos(ux * (2.0 * np.pi / max(6.0, cell * 5.0)))
    independent_m = _standardize(
        0.52 * (capsules - rings) + 0.46 * (spots - flecks)
        + 0.28 * (arcs - secondary) + 0.14 * carrier_m
    )
    independent_c = _standardize(
        0.50 * (rings - capsules) + 0.43 * (flecks - spots)
        + 0.25 * (secondary - arcs) + 0.14 * carrier_c
    )
    independent_r = _standardize(
        0.48 * (primary - arcs) + 0.44 * (secondary - spots)
        + 0.34 * (capsules - flecks) + 0.18 * carrier_r
    )

    # Rank quantization guarantees every one of the explicit eight shades has
    # material occupancy (~12.5%), rather than existing only in AA fringe.
    hue_gain, independent_gain, luma_gain = 0.58, 0.36, 0.16
    if fid == "fc_dragon_hex_glass":
        # The connected green honeycomb occupies far more area than its ember
        # counter-hue. A stronger feature-affinity bias lets that rarer attached
        # hue actually take over at angle B without changing a paint pixel.
        hue_gain, independent_gain, luma_gain = 0.96, 0.16, 0.06
    elif fid == "fmo_fire_agate":
        # Its finite 12-color paint bank already separates hues strongly; keep
        # more independent topology headroom so the permanent corr<.75 gate has
        # margin instead of sitting at the boundary.
        hue_gain, independent_gain, luma_gain = 0.52, 0.42, 0.16
    mi = _rank_eight(hue_gain * hue_affinity + independent_gain * independent_m + luma_gain * paint_luma)
    ri = _rank_eight(0.16 * hue_affinity + 0.76 * independent_r - 0.18 * paint_luma)
    ci = _rank_eight(-hue_gain * hue_affinity + independent_gain * independent_c + 0.12 * paint_luma)
    spec = np.empty((_DESIGN, _DESIGN, 3), np.uint8)
    spec[:, :, 0] = _METAL_TIERS[mi].astype(np.uint8)
    spec[:, :, 1] = _ROUGH_TIERS[ri].astype(np.uint8)
    spec[:, :, 2] = _COAT_TIERS[ci].astype(np.uint8)
    return paint, spec


def make_entry(fid: str, recipe: Mapping, family: str):
    """Return the existing ``(spec_fn, paint_fn)`` monolithic API for one ID."""
    token = _stable_int(fid)
    variant = token % 97
    hues = _recipe_hues(fid, recipe, variant)
    engine_name = str(recipe.get("engine", ""))

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        if src.shape[:2] != (fh, fw):
            src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored, _ = _design_cached(fid, family, engine_name, hues)
        # Nearest preserves the authored 8-32px micro edges at every preview
        # resolution. Linear reduction was erasing the fine carrier at 256 and
        # made visually different IDs converge into the same soft dot field.
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + authored * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        _, authored = _design_cached(fid, family, engine_name, hues)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        calm = np.asarray([4.0, 120.0, 16.0], np.float32)
        strength = max(0.0, float(sm))
        active = np.clip(calm + (authored - calm) * strength, 0.0, 255.0)
        mk = np.clip(m2, 0.0, 1.0)[..., None]
        rgb = active * mk + calm * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    spec_fn.__name__ = f"spec_{fid}"
    paint_fn.__name__ = f"paint_{fid}"
    return spec_fn, paint_fn


def clear_design_cache() -> None:
    """Test/audit hook; production uses the bounded eight-finish LRU."""
    _design_cached.cache_clear()
