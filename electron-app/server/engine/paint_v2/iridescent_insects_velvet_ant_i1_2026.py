"""Velvet Ant Armor I1 — ultrablack lamellar plates with grooved warning pile.

IRIDESCENT INSECTS tick 33 / owner identity law 2026-09-02.
Not Bumble Velvet in red: Bombus nap packets are forbidden. This carrier is
hard armor first—overlapping rounded mutillid sclerites with stacked lamellae,
connective pillars, spines and stridulatory combs. Short flattened hollow setae
grow from plate edges in coherent warning bands; each carries a longitudinal
groove. The material contrast is ultrablack absorption against smooth hard
cuticle and pheomelanin orange-red pile.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "ant_velvet",
    "display_name": "Velvet Ant Armor",
    "promise": "Ultrablack hard armor interrupts directional orange-red grooved warning pile.",
    "reference_physics": {
        "mechanism": (
            "Female mutillid wasps combine a very hard rounded smooth exoskeleton with dense "
            "velvet-like pilosity, aposematic pheomelanin setae, spines and stridulation. "
            "Ultrablack cuticle uses sculpturing, stacked lamellae and hollow grooved flattened setae "
            "to increase scattering path length and absorption."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC11635292/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6010712/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5533327/",
        ],
    },
    "carrier_grammar": (
        "Offset capsule-like hard sclerites overlap in a complete armor sheet; coherent edge-born "
        "flattened setal fans bridge plates while sparse combs and spines interrupt the flow."
    ),
    "spec_grammar": (
        "Ultrablack plate wells, polished lamella lips, connective pillars, grooved setal bodies, "
        "spine burrs and stridulatory comb ribs own separate material states."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "armor_plate", "role": "forms the hard rounded ultrablack exoskeleton sheet"},
        {"name": "lamella_lip", "role": "shows stacked absorbing cuticle layers inside each plate"},
        {"name": "pillar_bar", "role": "connects adjacent lamellar levels as short hard bridges"},
        {"name": "flattened_seta", "role": "creates the directional aposematic velvet pile"},
        {"name": "setal_groove", "role": "reveals the hollow grooved structure of each seta"},
        {"name": "cuticle_spine", "role": "breaks the plate flow with a hard defensive point"},
        {"name": "stridulatory_comb", "role": "adds compact abdominal warning-sound rake ribs"},
    ],
    "material_binding": {
        "M": ["armor_plate", "lamella_lip", "pillar_bar", "cuticle_spine"],
        "R": ["armor_plate", "flattened_seta", "setal_groove", "stridulatory_comb"],
        "Cc": ["armor_plate", "lamella_lip", "cuticle_spine", "flattened_seta"],
    },
    "material_tiers": [
        "ultrablack absorber", "smooth hard shell", "lamellar satin", "pillar metal",
        "pheomelanin velvet", "black hollow seta", "chrome spine burr", "dry comb rib",
    ],
    "nearest_neighbors": [
        {
            "finish_id": "bumble_velvet",
            "difference": "hard overlapping armor plates lead; setae are attached edge fans, not free nap packets",
        },
        {
            "finish_id": "beetle_stag",
            "difference": "flattened grooved warning pile and lamellar lips replace bent ribs and spiral nodes",
        },
        {
            "finish_id": "wasp_warning",
            "difference": "rounded ultrablack capsules and setal fans replace nested signal chevrons",
        },
    ],
    "name_truth": {
        "visible_evidence": [
            "overlapping hard black armor capsules",
            "directional orange-red velvet fringes",
            "stacked lamella lips and warning combs",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "mutillid-overlap-armor-with-edge-born-grooved-setal-fans",
    "spec_key": "ultrablack-lamella-seta-groove-spine-comb-material-binding",
}


GEN = 640


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(array, shape):
    h, w = _hw(shape)
    array = np.asarray(array, np.float32)
    return array if array.shape[:2] == (h, w) else cv2.resize(array, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .98, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(colour, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _capsule_polygon(cx, cy, ux, uy, length, half_width):
    nx, ny = -uy, ux
    return np.rint(np.asarray([
        (cx - length * ux - .55 * half_width * nx, cy - length * uy - .55 * half_width * ny),
        (cx - .35 * length * ux - half_width * nx, cy - .35 * length * uy - half_width * ny),
        (cx + .72 * length * ux - .72 * half_width * nx, cy + .72 * length * uy - .72 * half_width * ny),
        (cx + length * ux, cy + length * uy),
        (cx + .72 * length * ux + .72 * half_width * nx, cy + .72 * length * uy + .72 * half_width * ny),
        (cx - .35 * length * ux + half_width * nx, cy - .35 * length * uy + half_width * ny),
    ], np.float32)).astype(np.int32)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0xA17E17)
    h = w = GEN
    plate = np.zeros((h, w), np.float32)
    lamella = np.zeros_like(plate)
    pillar = np.zeros_like(plate)
    seta_red = np.zeros_like(plate)
    seta_gold = np.zeros_like(plate)
    seta_black = np.zeros_like(plate)
    groove = np.zeros_like(plate)
    spine = np.zeros_like(plate)
    comb = np.zeros_like(plate)

    step_y, step_x = 8.7, 9.6
    plate_count = 0
    for row, y0 in enumerate(np.arange(-5.0, h + 6.0, step_y)):
        for col, x0 in enumerate(np.arange(-6.0, w + 7.0, step_x)):
            cx = x0 + (step_x * .46 if row % 2 else 0) + rng.uniform(-1.8, 1.8)
            cy = y0 + 1.4 * np.sin(col * .37 - row * .21) + rng.uniform(-1.5, 1.5)
            flow = .52 * np.sin(cx / 61.0 + cy / 97.0) + .31 * np.cos(cy / 43.0 - cx / 107.0)
            armor_zone = np.cos(cx / 83.0 - cy / 69.0 + np.sin((cx + cy) / 117.0)) > .48
            angle = .42 * flow + (.18 if row % 2 else -.14) + rng.uniform(-.18, .18)
            ux, uy = np.cos(angle), np.sin(angle)
            nx, ny = -uy, ux
            length = rng.uniform(3.2, 4.8)
            half_width = rng.uniform(2.0, 3.2)
            poly = _capsule_polygon(cx, cy, ux, uy, length, half_width)
            body = float(np.clip(.30 + .22 * flow + (.19 if armor_zone else 0.0)
                                 + rng.uniform(-.10, .18), .08, .88))
            cv2.fillConvexPoly(plate, poly, body, cv2.LINE_AA)

            # Two or three stacked lamella lips stay inside the hard capsule.
            for level in range(int(rng.integers(2, 4))):
                offset = (-1.1 + level * 1.15) * half_width / 2.0
                p0 = (round(cx - .72 * length * ux + offset * nx),
                      round(cy - .72 * length * uy + offset * ny))
                p1 = (round(cx + .58 * length * ux + offset * nx),
                      round(cy + .58 * length * uy + offset * ny))
                cv2.line(lamella, p0, p1, float(rng.uniform(.30, .94)), 1, cv2.LINE_AA)

            # Short connective bars bridge those lips—never free dots.
            for frac in (-.35, .28):
                if rng.random() < .68:
                    qx, qy = cx + frac * length * ux, cy + frac * length * uy
                    cv2.line(pillar, (round(qx - .9 * nx), round(qy - .9 * ny)),
                             (round(qx + .9 * nx), round(qy + .9 * ny)),
                             float(rng.uniform(.32, .91)), 1, cv2.LINE_AA)

            # Flattened hollow setae leave one plate edge in a coherent local fan.
            signal = .58 * np.sin(cx / 73.0 - cy / 89.0) + .42 * np.cos((cx + cy) / 121.0)
            seta_target = seta_red if signal < -.12 else seta_gold if signal < .48 else seta_black
            # I1 P3 after P2 88.7: coherent armor zones suppress most fringe
            # fans so stacked plates read as hard interruptions, not another
            # all-over nap field.
            fan_count = int(rng.integers(0, 2) if armor_zone else rng.integers(2, 5))
            for fan in range(fan_count):
                base_shift = (-.62 + 1.24 * fan / max(fan_count - 1, 1)) * half_width
                bx = cx + .72 * length * ux + base_shift * nx
                by = cy + .72 * length * uy + base_shift * ny
                seta_angle = angle + rng.uniform(-.42, .42)
                sux, suy = np.cos(seta_angle), np.sin(seta_angle)
                snx, sny = -suy, sux
                seta_len = rng.uniform(2.7, 5.7)
                width = rng.uniform(.55, 1.05)
                tipx, tipy = bx + seta_len * sux, by + seta_len * suy
                seta_poly = np.rint(np.asarray([
                    (bx - width * snx, by - width * sny),
                    (bx + width * snx, by + width * sny),
                    (tipx + .22 * width * snx, tipy + .22 * width * sny),
                    (tipx - .22 * width * snx, tipy - .22 * width * sny),
                ], np.float32)).astype(np.int32)
                cv2.fillConvexPoly(seta_target, seta_poly, float(rng.uniform(.32, .98)), cv2.LINE_AA)
                cv2.line(groove, (round(bx + .25 * seta_len * sux), round(by + .25 * seta_len * suy)),
                         (round(bx + .88 * seta_len * sux), round(by + .88 * seta_len * suy)),
                         float(rng.uniform(.25, .86)), 1, cv2.LINE_AA)

            # Defensive spines and stridulatory combs are rare plate-bound events.
            if rng.random() < (.24 if armor_zone else .10):
                sx, sy = cx - .70 * length * ux, cy - .70 * length * uy
                tip = (sx - rng.uniform(2.3, 4.2) * ux, sy - rng.uniform(2.3, 4.2) * uy)
                tri = np.rint(np.asarray([
                    (sx - 1.2 * nx, sy - 1.2 * ny),
                    (sx + 1.2 * nx, sy + 1.2 * ny),
                    tip,
                ], np.float32)).astype(np.int32)
                cv2.fillConvexPoly(spine, tri, float(rng.uniform(.35, .96)), cv2.LINE_AA)
            if ((plate_count % 23 == 0) or (armor_zone and plate_count % 11 == 0)) and rng.random() < .72:
                for rib in range(4):
                    qx = cx + (-1.8 + rib * 1.15) * ux
                    qy = cy + (-1.8 + rib * 1.15) * uy
                    cv2.line(comb, (round(qx - 1.8 * nx), round(qy - 1.8 * ny)),
                             (round(qx + 1.8 * nx), round(qy + 1.8 * ny)),
                             float(rng.uniform(.30, .90)), 1, cv2.LINE_AA)
            plate_count += 1

    arrays = (plate, lamella, pillar, seta_red, seta_gold, seta_black, groove, spine, comb)
    return tuple(cv2.GaussianBlur(array, (0, 0), .17).astype(np.float32) for array in arrays)


def paint_velvet_ant(paint, shape, mask, seed, pm, _base):
    plate, lamella, pillar, seta_red, seta_gold, seta_black, groove, spine, comb = _surface(seed + 33017)
    colour = np.zeros((*plate.shape, 3), np.float32)
    colour[:] = np.array([.006, .004, .006], np.float32)
    # I1 P2 after P1 63.1: lift the hard shell anatomy so "Armor" leads the
    # image instead of reading as another free-fur finish.
    colour += plate[..., None] * np.array([.145, .036, .043], np.float32)
    colour += lamella[..., None] * np.array([.48, .105, .073], np.float32) * .64
    colour += pillar[..., None] * np.array([.58, .19, .095], np.float32) * .59
    colour += seta_red[..., None] * np.array([.92, .055, .028], np.float32) * .92
    colour += seta_gold[..., None] * np.array([.96, .32, .035], np.float32) * .83
    colour += seta_black[..., None] * np.array([.055, .016, .025], np.float32) * .72
    colour += groove[..., None] * np.array([.17, .025, .025], np.float32) * .48
    colour += spine[..., None] * np.array([.74, .24, .10], np.float32) * .69
    colour += comb[..., None] * np.array([.42, .10, .055], np.float32) * .62
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_velvet_ant(shape, seed, sm, _base_m, _base_r):
    plate, lamella, pillar, seta_red, seta_gold, seta_black, groove, spine, comb = _surface(seed + 33017)
    # P1 independence .320 and spec-lively rank .825: overlapping every mark
    # into every channel made a generic correlated map. P2 assigns each
    # anatomical family a dominant material channel.
    m = 21 + 24 * plate + 41 * lamella + 174 * pillar + 28 * seta_red + 36 * seta_gold + 196 * spine + 151 * comb
    r = 31 + 58 * plate + 17 * lamella + 19 * pillar + 151 * seta_red + 128 * seta_gold + 174 * seta_black + 143 * groove + 62 * comb
    cc = 18 + 151 * plate + 194 * lamella + 67 * pillar + 24 * seta_red + 31 * seta_gold + 15 * seta_black + 188 * spine - 31 * groove
    m += pillar * 21 + spine * 26 + comb * 19 - seta_black * 8
    r += groove * 25 + seta_black * 18 - lamella * 17 - spine * 23
    cc += lamella * 27 + spine * 31 + plate * 16 - comb * 11

    def spread(array, low, high):
        p1, p99 = np.percentile(array, (1.0, 99.0))
        expanded = low + (array - p1) * ((high - low) / max(float(p99 - p1), 1e-5))
        return cv2.GaussianBlur(np.clip(expanded, low, high), (0, 0), 1.02)

    return (
        np.clip(_resize(spread(m, 14, 241) * sm, shape), 14, 241),
        np.clip(_resize(spread(r, 17, 238) * sm, shape), 17, 238),
        np.clip(_resize(spread(cc, 10, 246) * sm, shape), 10, 246),
    )
