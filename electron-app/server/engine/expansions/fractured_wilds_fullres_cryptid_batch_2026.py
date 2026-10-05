# -*- coding: utf-8 -*-
"""Native-2048 Fractured Wilds Cryptid rebuild, full-resolution batch C1.

This module is deliberately isolated and unwired.  It answers the owner's
2026-08-24 correction that Fractured Wilds must be judged as 2048x2048 art,
not as picker thumbnails.  The four builders below share only raster utility
primitives; every finish owns a different causal topology, paint composition,
and M/R/Cc material construction.  There is no RNG, sampled noise, grain, or
decorative perturbation used to manufacture uniqueness.

SPB-WILDS-C1, tick 1, 2026-08-24.  Owner verdict addressed: "the biggest
cardinal sin PERIOD ... LAZY" and "2048x2048 canvas size images ... that's
what I care where they look."  Prior M7 is not applicable because these are
new isolated candidates; native render timing and full-resolution evidence are
written by :func:`render_fullres_evidence`.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time
from typing import Callable, Mapping

import cv2
import numpy as np


S = 2048
CALM_SPEC = np.asarray((12, 218, 10), np.float32)
TIERS = (76, 96, 116, 138, 160, 184, 216, 248)


@dataclass(frozen=True)
class FullresGrammar:
    """One full-resolution authored material and its auditable anatomy."""

    marks: tuple[tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    explicit_spec: tuple[np.ndarray, np.ndarray, np.ndarray]
    topology: str
    primitive_px: tuple[int, int]


def _mask() -> np.ndarray:
    return np.zeros((S, S), np.uint8)


def _p(point) -> tuple[int, int]:
    return int(round(float(point[0]))), int(round(float(point[1])))


def _line(dst, a, b, width, value) -> None:
    cv2.line(dst, _p(a), _p(b), int(value), int(width), cv2.LINE_AA)


def _polyline(dst, points, width, value, closed=False) -> None:
    pts = np.asarray([_p(point) for point in points], np.int32).reshape((-1, 1, 2))
    cv2.polylines(dst, [pts], bool(closed), int(value), int(width), cv2.LINE_AA)


def _poly(dst, points, value) -> None:
    pts = np.asarray([_p(point) for point in points], np.int32)
    cv2.fillConvexPoly(dst, pts, int(value), cv2.LINE_AA)


def _ellipse(dst, center, axes, angle, value, width=-1, start=0, end=360) -> None:
    cv2.ellipse(
        dst, _p(center), (max(1, int(round(axes[0]))), max(1, int(round(axes[1])))),
        float(angle), float(start), float(end), int(value), int(width), cv2.LINE_AA,
    )


def _rot(center, angle_deg, points):
    """Map local (cross-axis, along-axis) coordinates into image space."""
    theta = np.deg2rad(float(angle_deg))
    cross = np.asarray((np.cos(theta), np.sin(theta)), np.float32)
    along = np.asarray((-np.sin(theta), np.cos(theta)), np.float32)
    origin = np.asarray(center, np.float32)
    return tuple(origin + float(u) * cross + float(v) * along for u, v in points)


def _tier(*indices: int) -> int:
    return TIERS[sum(indices) % len(TIERS)]


def _paint_layers(base_hex: str, layers) -> np.ndarray:
    base = np.asarray(tuple(int(base_hex[i:i + 2], 16) for i in (1, 3, 5)), np.float32) / 255.0
    out = np.broadcast_to(base, (S, S, 3)).copy()
    for mask, colour_hex, opacity in layers:
        colour = np.asarray(tuple(int(colour_hex[i:i + 2], 16) for i in (1, 3, 5)), np.float32) / 255.0
        active = mask > 0
        if not np.any(active):
            continue
        strength = mask[active].astype(np.float32) / 255.0
        alpha = np.clip(float(opacity) * (.31 + .69 * strength), 0.0, 1.0)
        out[active] = out[active] * (1.0 - alpha[:, None]) + colour * alpha[:, None]
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _spec_channel(base: int, layers) -> np.ndarray:
    """Compose an authored channel; tier-valued masks create many real shades."""
    out = np.full((S, S), int(base), np.uint8)
    for mask, lo, hi in layers:
        active = mask > 0
        if not np.any(active):
            continue
        strength = mask[active].astype(np.float32) / 255.0
        values = float(lo) + (float(hi) - float(lo)) * strength
        out[active] = np.clip(values, 0, 255).astype(np.uint8)
    return out


def _marks_dict(marks):
    return {name: mask for name, mask, _bank in marks}


def _assert_grammar(grammar: FullresGrammar) -> None:
    names = [name for name, _mask_value, _bank in grammar.marks]
    if len(names) < 5 or len(names) != len(set(names)):
        raise ValueError("a full-resolution grammar needs at least five unique causal marks")
    banks = {bank for _name, _mask_value, bank in grammar.marks}
    if not {"A", "B"}.issubset(banks):
        raise ValueError("opposed A/B material ownership is mandatory")
    if grammar.paint.shape != (S, S, 3):
        raise ValueError("paint must be authored natively at 2048x2048")
    for channel in grammar.explicit_spec:
        if channel.shape != (S, S) or channel.dtype != np.uint8:
            raise ValueError("each explicit spec channel must be native uint8 2048x2048")
        channel_std = float(channel.std())
        channel_range = int(channel.max()) - int(channel.min())
        if channel_std < 20.0 or channel_range < 180:
            raise ValueError(
                "a full-resolution spec channel lacks authored range: "
                f"std={channel_std:.3f}, range={channel_range}, "
                f"min={int(channel.min())}, max={int(channel.max())}"
            )
    for name, mark, _bank in grammar.marks:
        if float(np.mean(mark > 0)) < .001:
            raise ValueError(f"causal mark {name!r} is too sparse")


def _build_fc_quill_bristle() -> FullresGrammar:
    """Interlocked quill zippers: paired roots physically close every chain."""
    collars = _mask()
    rigid_shafts = _mask()
    hollow_slits = _mask()
    alternating_barbs = _mask()
    zipper_bridges = _mask()
    taper_breaks = _mask()
    lee_lips = _mask()
    root_sutures = _mask()
    fracture_nicks = _mask()
    terminal_glints = _mask()

    # Sixty-seven continuous quill trains are integrated through an analytic
    # vector field.  The visible object is a flowing zipper fabric, not a grid
    # of repeated feather glyphs.  Every curve is still made from 15--19 px
    # causal shaft segments and 7--12 px attachments.
    trains = []
    for train, x_seed in enumerate(range(-10, S + 22, 31)):
        point = np.asarray((float(x_seed), -18.0), np.float32)
        points = [point.copy()]
        for step in range(126):
            angle = (10.0 * np.sin(point[1] / 137.0 + train * .19)
                     + 8.0 * np.sin(point[0] / 193.0 - point[1] / 311.0)
                     + 4.0 * np.cos(train * .37 + step * .11))
            length = 16.0 + 2.5 * np.sin(train * .29 + step * .47)
            delta = np.asarray((np.sin(np.deg2rad(angle)) * length,
                                np.cos(np.deg2rad(angle)) * length), np.float32)
            point = point + delta
            points.append(point.copy())
        trains.append(points)

    for train, points in enumerate(trains):
        handed = -1 if train & 1 else 1
        for step, (root, tip) in enumerate(zip(points, points[1:])):
            delta = tip - root
            length = max(1e-4, float(np.linalg.norm(delta)))
            along = delta / length
            cross = np.asarray((along[1], -along[0]), np.float32)
            mid = (root + tip) * .5
            angle = float(np.degrees(np.arctan2(along[1], along[0])))
            value = _tier(train * 5, step * 3, train * step)
            _line(rigid_shafts, root, tip, 4, value)

            slit_a = mid - along * 5.0
            slit_b = mid + along * 5.0
            _line(hollow_slits, slit_a, slit_b, 2, _tier(train, step, 4))
            side = handed if step & 1 else -handed
            barb_root = mid + along * 1.5
            barb_tip = barb_root + cross * side * (8.0 + (step % 3)) + along * 4.0
            _line(alternating_barbs, barb_root, barb_tip, 2, _tier(train, step, 1))
            lee_a = root - cross * side * 4.0
            lee_b = mid - cross * side * 4.0
            _line(lee_lips, lee_a, lee_b, 2, _tier(train, step, 6))

            if step % 4 == 0:
                _ellipse(collars, root, (6, 3), angle, value, 2)
                _line(root_sutures, root - cross * 6, root + cross * 6, 2,
                      _tier(train, step, 2))
            if step % 5 == 2:
                _line(taper_breaks, mid - cross * 4, mid + cross * 4, 2,
                      _tier(train, step, 7))
            if step % 7 == 3:
                _line(fracture_nicks, mid, mid + cross * handed * 7 + along * 3,
                      2, _tier(train, step, 5))
            if step % 9 == 6:
                _ellipse(terminal_glints, tip, (4, 4), angle,
                         _tier(train, step, 3), -1)

    # Adjacent trains close into a true zipper at irregular analytic intervals.
    # Only gaps <=32 px are bridged, so no macro connector enters the design.
    for train in range(len(trains) - 1):
        for step in range(3 + train % 4, 125, 8 + train % 3):
            a, b = trains[train][step], trains[train + 1][step]
            if float(np.linalg.norm(b - a)) <= 32.0:
                mid = (a + b) * .5
                _polyline(zipper_bridges, (a, mid + np.asarray((0, 3), np.float32), b),
                          2, _tier(train, step, 3))

    marks = (
        ("root_collar_cups", collars, "A"),
        ("paired_rigid_shafts", rigid_shafts, "A"),
        ("hollow_core_slits", hollow_slits, "B"),
        ("alternating_hook_barbs", alternating_barbs, "B"),
        ("interlock_zipper_bridges", zipper_bridges, "A"),
        ("taper_breaks", taper_breaks, "B"),
        ("lee_side_lips", lee_lips, "A"),
        ("root_socket_sutures", root_sutures, "A"),
        ("fracture_nicks", fracture_nicks, "B"),
        ("terminal_quill_glints", terminal_glints, "B"),
    )
    m = _marks_dict(marks)
    paint = _paint_layers("#080811", (
        (m["interlock_zipper_bridges"], "#3b164f", .78),
        (m["root_socket_sutures"], "#6d253b", .88),
        (m["root_collar_cups"], "#da6428", .94),
        (m["paired_rigid_shafts"], "#ffb23d", .98),
        (m["lee_side_lips"], "#a84cff", .91),
        (m["hollow_core_slits"], "#041725", .99),
        (m["alternating_hook_barbs"], "#25e2ff", .98),
        (m["taper_breaks"], "#f542dd", .96),
        (m["fracture_nicks"], "#6fffd0", .96),
        (m["terminal_quill_glints"], "#fff4b5", .99),
    ))
    metal = _spec_channel(6, (
        (collars, 118, 236), (rigid_shafts, 154, 252), (root_sutures, 82, 214),
        (zipper_bridges, 44, 188), (lee_lips, 92, 224), (hollow_slits, 10, 76),
        (alternating_barbs, 34, 142), (taper_breaks, 112, 246),
        (fracture_nicks, 52, 202), (terminal_glints, 176, 255),
    ))
    rough = _spec_channel(246, (
        (collars, 66, 166), (rigid_shafts, 22, 126), (root_sutures, 112, 220),
        (zipper_bridges, 136, 232), (lee_lips, 74, 190), (hollow_slits, 184, 250),
        (alternating_barbs, 38, 148), (taper_breaks, 88, 214),
        (fracture_nicks, 124, 238), (terminal_glints, 0, 30),
        (hollow_slits, 210, 252),
    ))
    coat = _spec_channel(4, (
        (collars, 44, 166), (rigid_shafts, 62, 188), (root_sutures, 24, 128),
        (zipper_bridges, 18, 114), (lee_lips, 132, 242), (hollow_slits, 96, 206),
        (alternating_barbs, 152, 252), (taper_breaks, 118, 238),
        (fracture_nicks, 146, 250), (terminal_glints, 202, 255),
    ))
    result = FullresGrammar(marks, paint, (metal, rough, coat),
                            "interlocked root-collar quill zipper fabric", (8, 29))
    _assert_grammar(result)
    return result


def _build_fc_toad_skin() -> FullresGrammar:
    """A connected poison-gland hydraulic organ, never a wart stamp field."""
    valve_chambers = _mask()
    pore_horseshoes = _mask()
    capillary_feeds = _mask()
    saddle_wrinkles = _mask()
    mucus_rivulets = _mask()
    dry_collars = _mask()
    paired_pressure_slits = _mask()
    release_creases = _mask()
    valve_hinges = _mask()
    overflow_droplets = _mask()

    # Forty-eight horizontally anastomosing capillaries carry valves only at
    # curvature extrema.  That makes a continuous hydraulic skin instead of
    # bead-like vertical gland columns.
    networks = []
    for track, y_seed in enumerate(range(-8, S + 30, 43)):
        points = []
        for step, x in enumerate(range(-16, S + 35, 27)):
            y = (y_seed + 11.0 * np.sin(x / 83.0 + track * .61)
                 + 6.0 * np.sin(x / 211.0 - track * .37)
                 + 3.0 * np.cos(step * .79 + track * .13))
            points.append(np.asarray((float(x), float(y)), np.float32))
        networks.append(points)
        for step, (a, b) in enumerate(zip(points, points[1:])):
            value = _tier(track * 5, step * 3, track * step)
            _line(capillary_feeds, a, b, 3, value)
            mid = (a + b) * .5
            tangent = b - a
            length = max(1e-4, float(np.linalg.norm(tangent)))
            along = tangent / length
            normal = np.asarray((-along[1], along[0]), np.float32)
            side = -1 if (track + step) & 1 else 1
            angle = float(np.degrees(np.arctan2(tangent[1], tangent[0]))) + 90.0

            # A valve event occurs every 3--5 segments, with deterministic
            # phase gaps so no repeated bead cadence owns the canvas.
            if (step + 2 * track) % (3 + track % 3) != 0:
                if step % 4 == 1:
                    _line(saddle_wrinkles, mid - normal * 5, mid + normal * 5,
                          2, _tier(track, step, 1))
                continue

            center = mid + normal * side * 10.0
            valve = _rot(center, angle, (
                (0, -12), (-7, -9), (-10, -3), (-7, 2), (-9, 7),
                (0, 12), (9, 7), (7, 2), (10, -3), (7, -9),
            ))
            _poly(valve_chambers, valve, value)
            neck_a, neck_b = center - normal * side * 8, mid
            _line(valve_hinges, neck_a, neck_b, 3, _tier(track, step, 4))

            pore_center = center + normal * side * 3
            _ellipse(pore_horseshoes, pore_center, (6, 4), angle,
                     _tier(track, step, 2), 2, 22, 318)
            saddle_a, saddle_b = center - along * 7, center + along * 7
            _line(saddle_wrinkles, saddle_a, saddle_b, 2, _tier(track, step, 1))
            for slit_side in (-1, 1):
                slit_root = center + along * slit_side * 4 + normal * side * 4
                slit_tip = slit_root + along * slit_side * 3 + normal * side * 3
                _line(paired_pressure_slits, slit_root, slit_tip, 2,
                      _tier(track, step, slit_side))

            rivulet_mid = center + normal * side * 8 + along * 5
            rivulet_end = center + normal * side * 13 + along * 9
            _polyline(mucus_rivulets, (pore_center, rivulet_mid, rivulet_end), 3,
                      _tier(track, step, 5))
            _ellipse(dry_collars, center, (12, 9), angle,
                     _tier(track, step, 6), 2, 205, 335)
            crease = (center - along * 11 + normal * side * 7,
                      center - along * 4 + normal * side * 12,
                      center + along * 5 + normal * side * 11)
            _polyline(release_creases, crease, 2, _tier(track, step, 7))
            drop_center = rivulet_end + normal * side * 3
            _ellipse(overflow_droplets, drop_center, (3, 5), angle + side * 18,
                     _tier(track, step, 3), -1)

    # Short diagonal cross-feeds create branch hydraulics without closing into
    # a paver or foam mesh.
    for track in range(len(networks) - 1):
        for step in range(2 + track % 5, len(networks[track]) - 1, 11):
            a = networks[track][step]
            b = networks[track + 1][min(step + 1, len(networks[track + 1]) - 1)]
            delta = b - a
            if float(np.linalg.norm(delta)) > 32.0:
                b = a + delta / max(float(np.linalg.norm(delta)), 1e-4) * 29.0
            _line(release_creases, a, b, 2, _tier(track, step, 6))

    marks = (
        ("lobed_gland_valves", valve_chambers, "A"),
        ("annular_poison_horseshoes", pore_horseshoes, "B"),
        ("capillary_feed_trunks", capillary_feeds, "A"),
        ("saddle_pressure_wrinkles", saddle_wrinkles, "A"),
        ("mucus_return_rivulets", mucus_rivulets, "B"),
        ("dry_crack_collars", dry_collars, "A"),
        ("paired_pressure_slits", paired_pressure_slits, "B"),
        ("pressure_release_creases", release_creases, "B"),
        ("valve_feed_hinges", valve_hinges, "A"),
        ("overflow_poison_droplets", overflow_droplets, "B"),
    )
    m = _marks_dict(marks)
    paint = _paint_layers("#07100c", (
        (m["capillary_feed_trunks"], "#315b1f", .86),
        (m["lobed_gland_valves"], "#789b24", .88),
        (m["dry_crack_collars"], "#d4c73d", .92),
        (m["saddle_pressure_wrinkles"], "#302218", .94),
        (m["valve_feed_hinges"], "#ffa32b", .96),
        (m["annular_poison_horseshoes"], "#ff4b1f", .98),
        (m["paired_pressure_slits"], "#7b24ff", .97),
        (m["pressure_release_creases"], "#d02aff", .95),
        (m["mucus_return_rivulets"], "#32ffd5", .99),
        (m["overflow_poison_droplets"], "#e7ff71", .99),
    ))
    metal = _spec_channel(4, (
        (valve_chambers, 24, 122), (pore_horseshoes, 98, 226),
        (capillary_feeds, 118, 248), (saddle_wrinkles, 12, 82),
        (mucus_rivulets, 166, 255), (dry_collars, 36, 148),
        (paired_pressure_slits, 72, 210), (release_creases, 92, 232),
        (valve_hinges, 132, 244), (overflow_droplets, 186, 255),
    ))
    rough = _spec_channel(252, (
        (valve_chambers, 102, 224), (pore_horseshoes, 44, 162),
        (capillary_feeds, 34, 138), (saddle_wrinkles, 154, 246),
        (mucus_rivulets, 6, 74), (dry_collars, 172, 250),
        (paired_pressure_slits, 94, 220), (release_creases, 116, 236),
        (valve_hinges, 62, 184), (overflow_droplets, 4, 68),
    ))
    coat = _spec_channel(3, (
        (valve_chambers, 52, 174), (pore_horseshoes, 164, 250),
        (capillary_feeds, 92, 226), (saddle_wrinkles, 18, 104),
        (mucus_rivulets, 198, 255), (dry_collars, 28, 134),
        (paired_pressure_slits, 136, 242), (release_creases, 108, 234),
        (valve_hinges, 74, 196), (overflow_droplets, 214, 255),
    ))
    result = FullresGrammar(marks, paint, (metal, rough, coat),
                            "connected poison-gland hydraulic organ", (8, 29))
    _assert_grammar(result)
    return result


def _build_fc_gator_hide() -> FullresGrammar:
    """Open osteoderm crowns carried by sensory canals, not closed cell paving."""
    crown_keels = _mask()
    growth_steps = _mask()
    pressure_pits = _mask()
    seam_teeth = _mask()
    canal_sluices = _mask()
    scar_ramps = _mask()
    porous_face_ribs = _mask()
    brow_ridges = _mask()
    hinge_notches = _mask()
    worn_tip_glints = _mask()

    # Sinuous armor courses remain open: the face is described by internal
    # ribs and crown anatomy, never a closed Voronoi/polygon/pebble boundary.
    for course, y0 in enumerate(range(-18, S + 44, 42)):
        phase = course * .39
        for unit, x0 in enumerate(range(-24, S + 46, 41)):
            cx = x0 + (20.5 if course & 1 else 0) + 5.5 * np.sin(phase + unit * .47)
            cy = y0 + 5.0 * np.sin(unit * .31 + course * .57)
            angle = -6.0 + 14.0 * np.sin(unit * .19 - course * .23)
            value = _tier(course * 7, unit * 3, course * unit)
            length = 25.0 + 3.0 * ((course + unit) % 3)

            root, crown, tip = _rot((cx, cy), angle, ((0, -length / 2), (0, 0), (0, length / 2)))
            _line(crown_keels, root, tip, 3, value)
            _ellipse(worn_tip_glints, tip, (4, 2), angle, _tier(course, unit, 6), -1)

            # Three open, nested growth chevrons wrap the central keel.
            for ring, along in enumerate((-5.5, 1.0, 7.0)):
                left, apex, right = _rot((cx, cy), angle, (
                    (-11 + ring * 1.5, along - 3), (0, along + 3),
                    (11 - ring * 1.5, along - 3),
                ))
                _polyline(growth_steps, (left, apex, right), 2,
                          _tier(course, unit, ring))

            # Sensory canal and paired pit are physically attached to the
            # crown root, not dots sprinkled over a face.
            canal_a, canal_b = _rot((cx, cy), angle, ((-9, -10), (9, -10)))
            _line(canal_sluices, canal_a, canal_b, 3, _tier(course, unit, 2))
            for side in (-1, 1):
                pit = _rot((cx, cy), angle, ((side * 7, -7),))[0]
                _ellipse(pressure_pits, pit, (4, 3), angle, _tier(course, unit, side), 2)

            # Interlocking teeth alternate course handedness along the open
            # seam and are kept within the 8--14 px feature span.
            handed = -1 if (course + unit) & 1 else 1
            for tooth_index, along in enumerate((-8, 0, 8)):
                tooth = _rot((cx, cy), angle, (
                    (handed * 10, along - 3), (handed * 14, along),
                    (handed * 10, along + 3),
                ))
                _poly(seam_teeth, tooth, _tier(course, unit, tooth_index + 3))

            # Porous face is a radial rib stack, not a filled tile.
            for rib in (-1, 0, 1):
                a, b = _rot((cx, cy), angle, ((rib * 5 - 3, -2), (rib * 5 + 3, 5)))
                _line(porous_face_ribs, a, b, 2, _tier(course, unit, rib + 5))

            brow_a, brow_mid, brow_b = _rot((cx, cy), angle, ((-10, 9), (0, 12), (10, 9)))
            _polyline(brow_ridges, (brow_a, brow_mid, brow_b), 3,
                      _tier(course, unit, 7))
            notch_a, notch_b = _rot((cx, cy), angle, ((-3, -13), (3, -13)))
            _line(hinge_notches, notch_a, notch_b, 3, _tier(course, unit, 1))

            if (course * 3 + unit) % 7 in (0, 3):
                scar = _rot((cx, cy), angle, ((-10, -1), (-3, 4), (5, 1), (11, 6)))
                _polyline(scar_ramps, scar, 2, _tier(course, unit, 4))

    marks = (
        ("raised_osteoderm_keels", crown_keels, "B"),
        ("open_growth_chevrons", growth_steps, "A"),
        ("paired_sensory_pressure_pits", pressure_pits, "B"),
        ("interlocking_seam_teeth", seam_teeth, "A"),
        ("rooted_canal_sluices", canal_sluices, "B"),
        ("healed_scar_ramps", scar_ramps, "A"),
        ("porous_face_rib_stacks", porous_face_ribs, "A"),
        ("crown_brow_ridges", brow_ridges, "B"),
        ("hinge_notches", hinge_notches, "A"),
        ("worn_keel_tip_glints", worn_tip_glints, "B"),
    )
    m = _marks_dict(marks)
    paint = _paint_layers("#090c08", (
        (m["open_growth_chevrons"], "#68732a", .88),
        (m["porous_face_rib_stacks"], "#9a7334", .91),
        (m["interlocking_seam_teeth"], "#d46a25", .96),
        (m["hinge_notches"], "#f0bb52", .96),
        (m["healed_scar_ramps"], "#e8442f", .95),
        (m["rooted_canal_sluices"], "#126f6b", .91),
        (m["paired_sensory_pressure_pits"], "#1cc7a4", .95),
        (m["raised_osteoderm_keels"], "#91c35b", .93),
        (m["crown_brow_ridges"], "#3ea4b5", .92),
        (m["worn_keel_tip_glints"], "#fff0ac", .99),
    ))
    metal = _spec_channel(5, (
        (growth_steps, 54, 176), (porous_face_ribs, 22, 132),
        (seam_teeth, 116, 238), (hinge_notches, 84, 214),
        (scar_ramps, 148, 250), (canal_sluices, 62, 196),
        (pressure_pits, 96, 228), (crown_keels, 168, 255),
        (brow_ridges, 132, 246), (worn_tip_glints, 218, 255),
    ))
    rough = _spec_channel(250, (
        (growth_steps, 96, 214), (porous_face_ribs, 146, 244),
        (seam_teeth, 54, 172), (hinge_notches, 112, 226),
        (scar_ramps, 76, 196), (canal_sluices, 26, 136),
        (pressure_pits, 128, 236), (crown_keels, 12, 104),
        (brow_ridges, 42, 158), (worn_tip_glints, 4, 66),
    ))
    coat = _spec_channel(3, (
        (growth_steps, 44, 166), (porous_face_ribs, 18, 118),
        (seam_teeth, 88, 216), (hinge_notches, 70, 198),
        (scar_ramps, 106, 234), (canal_sluices, 142, 250),
        (pressure_pits, 178, 255), (crown_keels, 152, 252),
        (brow_ridges, 190, 255), (worn_tip_glints, 224, 255),
    ))
    result = FullresGrammar(marks, paint, (metal, rough, coat),
                            "open sensory-canal osteoderm crown terrain", (8, 31))
    _assert_grammar(result)
    return result


def _build_fc_crackle_eyeshine_glass() -> FullresGrammar:
    """Non-cellular crack relays with attached retroreflective optical organs."""
    relay_spines = _mask()
    caustic_slits = _mask()
    iris_bars = _mask()
    bevel_brackets = _mask()
    glint_squares = _mask()
    backing_wedges = _mask()
    arrest_forks = _mask()
    edge_echoes = _mask()
    flash_filaments = _mask()
    compression_hinges = _mask()

    # Segmented oblique relay tracks replace a generic crack graph.  Optical
    # organs occur only at coded relay events and vary orientation/anatomy, so
    # the canvas is not a repeated eye-stamp field.
    for track, start_x in enumerate(range(-50, S + 80, 76)):
        points = []
        for step in range(-2, 78):
            y = step * 28.0
            x = start_x + .23 * y + 13.0 * np.sin(step * .41 + track * .67)
            points.append(np.asarray((x, y), np.float32))
        for step in range(len(points) - 1):
            a, b = points[step], points[step + 1]
            value = _tier(track * 5, step * 3, track * step)
            _line(relay_spines, a, b, 3, value)
            mid = (a + b) * .5
            tangent = b - a
            angle = float(np.degrees(np.arctan2(tangent[1], tangent[0])))

            if (step + 2 * track) % 4 == 0:
                # Asymmetric cat-eye caustic: a slit, three iris bars, one
                # backing wedge and a relay bracket all share the same hinge.
                slit_angle = angle + 27.0 * np.sin(step * .37 + track)
                _ellipse(caustic_slits, mid, (11 + (step % 3), 3), slit_angle,
                         _tier(track, step, 4), -1)
                for bar_index, offset in enumerate((-7, 0, 7)):
                    bar_a, bar_b = _rot(mid, slit_angle, ((offset, -5), (offset, 5)))
                    _line(iris_bars, bar_a, bar_b, 2,
                          _tier(track, step, bar_index + 1))
                bracket = _rot(mid, slit_angle, ((-13, -6), (-15, 0), (-13, 6)))
                _polyline(bevel_brackets, bracket, 2, _tier(track, step, 5))
                wedge = _rot(mid, slit_angle, ((5, 5), (14, 0), (5, -5)))
                _poly(backing_wedges, wedge, _tier(track, step, 6))

            elif (step + track) % 4 == 1:
                square = _rot(mid, angle, ((-4, -4), (4, -4), (4, 4), (-4, 4)))
                _polyline(glint_squares, square, 2, _tier(track, step, 2), True)
                echo_a, echo_b = _rot(mid, angle, ((-10, -5), (10, 5)))
                _line(edge_echoes, echo_a, echo_b, 2, _tier(track, step, 3))

            elif (step + 3 * track) % 5 == 2:
                fork = _rot(mid, angle, ((0, 0), (-8, 9), (0, 0), (9, 8)))
                _polyline(arrest_forks, fork, 2, _tier(track, step, 7))
                hinge_a, hinge_b = _rot(mid, angle, ((-6, -3), (6, -3)))
                _line(compression_hinges, hinge_a, hinge_b, 3,
                      _tier(track, step, 1))

            filament_a, filament_b = _rot(mid, angle + 90, ((-5, 0), (5, 0)))
            _line(flash_filaments, filament_a, filament_b, 1,
                  _tier(track, step, 6))

    # Sparse opposing relays cross the first family, but remain deterministic
    # 24--30 px segments and never form enclosed crackle cells.
    for band, y0 in enumerate(range(18, S + 40, 91)):
        for step, x0 in enumerate(range(-20, S + 35, 29)):
            a = (x0, y0 + 9.0 * np.sin(step * .53 + band * .31))
            b = (x0 + 27, y0 + 9.0 * np.sin((step + 1) * .53 + band * .31))
            _line(edge_echoes, a, b, 2, _tier(band, step, 4))
            if (band + step) % 6 == 0:
                _ellipse(glint_squares, b, (3, 3), 45, _tier(band, step, 6), -1)

    marks = (
        ("segmented_relay_crack_spines", relay_spines, "A"),
        ("cat_eye_caustic_slits", caustic_slits, "B"),
        ("attached_iris_diffraction_bars", iris_bars, "A"),
        ("bevel_relay_brackets", bevel_brackets, "B"),
        ("square_glint_relays", glint_squares, "A"),
        ("dark_backing_wedges", backing_wedges, "B"),
        ("fracture_arrest_forks", arrest_forks, "A"),
        ("vitreous_edge_echoes", edge_echoes, "B"),
        ("tapetum_flash_filaments", flash_filaments, "B"),
        ("compression_hinges", compression_hinges, "A"),
    )
    m = _marks_dict(marks)
    paint = _paint_layers("#03050d", (
        (m["dark_backing_wedges"], "#26052e", .90),
        (m["segmented_relay_crack_spines"], "#b88719", .92),
        (m["attached_iris_diffraction_bars"], "#65dd35", .95),
        (m["square_glint_relays"], "#fff177", .98),
        (m["compression_hinges"], "#ff8a2b", .96),
        (m["bevel_relay_brackets"], "#315cff", .96),
        (m["vitreous_edge_echoes"], "#2145a8", .93),
        (m["cat_eye_caustic_slits"], "#ff31c8", .99),
        (m["fracture_arrest_forks"], "#42f1ff", .97),
        (m["tapetum_flash_filaments"], "#e9ffff", .99),
    ))
    metal = _spec_channel(4, (
        (relay_spines, 116, 246), (caustic_slits, 178, 255),
        (iris_bars, 82, 218), (bevel_brackets, 148, 252),
        (glint_squares, 212, 255), (backing_wedges, 10, 94),
        (arrest_forks, 62, 204), (edge_echoes, 36, 174),
        (flash_filaments, 198, 255), (compression_hinges, 96, 232),
    ))
    rough = _spec_channel(252, (
        (relay_spines, 72, 190), (caustic_slits, 4, 76),
        (iris_bars, 42, 162), (bevel_brackets, 18, 118),
        (glint_squares, 2, 52), (backing_wedges, 178, 248),
        (arrest_forks, 104, 224), (edge_echoes, 126, 238),
        (flash_filaments, 6, 64), (compression_hinges, 84, 208),
    ))
    coat = _spec_channel(2, (
        (relay_spines, 72, 196), (caustic_slits, 206, 255),
        (iris_bars, 132, 244), (bevel_brackets, 184, 255),
        (glint_squares, 224, 255), (backing_wedges, 18, 106),
        (arrest_forks, 112, 234), (edge_echoes, 152, 250),
        (flash_filaments, 218, 255), (compression_hinges, 94, 222),
    ))
    result = FullresGrammar(marks, paint, (metal, rough, coat),
                            "non-cellular retroreflective crack-relay lattice", (8, 30))
    _assert_grammar(result)
    return result


BUILDERS: Mapping[str, Callable[[], FullresGrammar]] = {
    "fc_quill_bristle": _build_fc_quill_bristle,
    "fc_toad_skin": _build_fc_toad_skin,
    "fc_gator_hide": _build_fc_gator_hide,
    "fc_crackle_eyeshine_glass": _build_fc_crackle_eyeshine_glass,
}
CRYPTID_FULLRES_IDS = tuple(BUILDERS)
HUES = {
    "fc_quill_bristle": (.105, .75),
    "fc_toad_skin": (.24, .91),
    "fc_gator_hide": (.22, .54),
    "fc_crackle_eyeshine_glass": (.135, .67),
}


@lru_cache(maxsize=1)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2)


def clear_cache() -> None:
    _authored.cache_clear()


def debug_grammar(fid: str) -> FullresGrammar:
    return BUILDERS[fid]()


def owner_unions(grammar: FullresGrammar):
    unions = {"A": np.zeros((S, S), np.uint8), "B": np.zeros((S, S), np.uint8)}
    for _name, mask, bank in grammar.marks:
        unions[bank] = np.maximum(unions[bank], mask)
    return {bank: value.astype(np.float32) / 255.0 for bank, value in unions.items()}


def debug_angle_pair(fid: str):
    """Simulate the opposed A/B ownership flip with different material lobes."""
    grammar = BUILDERS[fid]()
    owners = owner_unions(grammar)
    metal, rough, coat = (channel.astype(np.float32) / 255.0 for channel in grammar.explicit_spec)
    aperture = np.clip(1.0 - .58 * rough, .18, 1.0)
    a_owner, b_owner = owners["A"], owners["B"]
    # A is metal/copper-green dominant at one angle; B is clearcoat/cyan-violet
    # dominant at the other.  The opposed terms make this a real ownership flip,
    # not a global brightness change.
    gain_a = np.clip(.30 + 1.18 * metal * aperture + .46 * a_owner - .28 * b_owner, .08, 1.42)
    gain_b = np.clip(.30 + 1.18 * coat * aperture + .46 * b_owner - .28 * a_owner, .08, 1.42)
    warm = np.asarray((.30, .095, .015), np.float32)
    cool = np.asarray((.025, .09, .34), np.float32)
    angle_a = grammar.paint * gain_a[..., None] + warm * (a_owner * aperture)[..., None]
    angle_a += .035 * cool * (b_owner * aperture)[..., None]
    angle_b = grammar.paint * gain_b[..., None] + cool * (b_owner * aperture)[..., None]
    angle_b += .035 * warm * (a_owner * aperture)[..., None]
    return (np.clip(angle_a, 0, 1).astype(np.float32),
            np.clip(angle_b, 0, 1).astype(np.float32),
            np.abs(np.clip(angle_a, 0, 1) - np.clip(angle_b, 0, 1)).astype(np.float32))


def _paint_runtime(fid, paint, shape, mask, seed, pm, bb):
    h, w = int(shape[0]), int(shape[1])
    source = np.asarray(paint, np.float32)
    if source.ndim != 3 or source.shape[2] < 3:
        source = np.zeros((h, w, 3), np.float32)
    else:
        source = source[:, :, :3]
        if source.size and float(source.max()) > 1.5:
            source = source / 255.0
        if source.shape[:2] != (h, w):
            source = cv2.resize(source, (w, h), interpolation=cv2.INTER_LINEAR)
    zone = np.asarray(mask, np.float32)
    if zone.ndim == 3:
        zone = zone[:, :, 0]
    if zone.shape != (h, w):
        zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
    authored, _spec = _authored(fid)
    if (h, w) != (S, S):
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_AREA)
    alpha = np.clip(zone * max(0.0, float(pm)), 0, 1)[..., None]
    return np.clip(source * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)


def _spec_runtime(fid, shape, mask, seed, sm):
    h, w = int(shape[0]), int(shape[1])
    zone = np.asarray(mask, np.float32)
    if zone.ndim == 3:
        zone = zone[:, :, 0]
    if zone.shape != (h, w):
        zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
    _paint, authored = _authored(fid)
    if (h, w) != (S, S):
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST)
    authored = authored.astype(np.float32)
    active = np.clip(CALM_SPEC + (authored - CALM_SPEC) * max(0.0, float(sm)), 0, 255)
    alpha = np.clip(zone, 0, 1)[..., None]
    out = np.empty((h, w, 4), np.uint8)
    out[:, :, :3] = np.clip(active * alpha + CALM_SPEC * (1.0 - alpha), 0, 255).astype(np.uint8)
    out[:, :, 3] = 255
    return out


# Explicit module-level callables keep each candidate individually inspectable.
def paint_fc_quill_bristle(paint, shape, mask, seed, pm, bb):
    return _paint_runtime("fc_quill_bristle", paint, shape, mask, seed, pm, bb)


def spec_fc_quill_bristle(shape, mask, seed, sm):
    return _spec_runtime("fc_quill_bristle", shape, mask, seed, sm)


def paint_fc_toad_skin(paint, shape, mask, seed, pm, bb):
    return _paint_runtime("fc_toad_skin", paint, shape, mask, seed, pm, bb)


def spec_fc_toad_skin(shape, mask, seed, sm):
    return _spec_runtime("fc_toad_skin", shape, mask, seed, sm)


def paint_fc_gator_hide(paint, shape, mask, seed, pm, bb):
    return _paint_runtime("fc_gator_hide", paint, shape, mask, seed, pm, bb)


def spec_fc_gator_hide(shape, mask, seed, sm):
    return _spec_runtime("fc_gator_hide", shape, mask, seed, sm)


def paint_fc_crackle_eyeshine_glass(paint, shape, mask, seed, pm, bb):
    return _paint_runtime("fc_crackle_eyeshine_glass", paint, shape, mask, seed, pm, bb)


def spec_fc_crackle_eyeshine_glass(shape, mask, seed, sm):
    return _spec_runtime("fc_crackle_eyeshine_glass", shape, mask, seed, sm)


RENDERERS = {
    "fc_quill_bristle": (spec_fc_quill_bristle, paint_fc_quill_bristle),
    "fc_toad_skin": (spec_fc_toad_skin, paint_fc_toad_skin),
    "fc_gator_hide": (spec_fc_gator_hide, paint_fc_gator_hide),
    "fc_crackle_eyeshine_glass": (spec_fc_crackle_eyeshine_glass,
                                   paint_fc_crackle_eyeshine_glass),
}


def install_into_engine(registry, base_registry=None):
    """Optional isolated install hook; this module is not wired by this batch."""
    for fid, renderer in RENDERERS.items():
        registry[fid] = renderer
    return "fractured-wilds-fullres-cryptid-c1: 4 isolated candidates"


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    image = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)):
        raise OSError(f"failed to write {path}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_fullres_evidence(output_dir: str | Path) -> dict:
    """Render native paint/spec/A-B proof and a compact evidence manifest."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "spb-wilds-fullres-cryptid-c1/1",
        "native_size": [S, S],
        "acceptance_target": "full 2048x2048 only; picker size deliberately ignored",
        "determinism": "analytic geometry only; no RNG, sampled noise, or grain",
        "finishes": {},
    }
    for fid in CRYPTID_FULLRES_IDS:
        clear_cache()
        start = time.perf_counter()
        grammar = BUILDERS[fid]()
        elapsed = time.perf_counter() - start
        angle_a, angle_b, angle_delta = debug_angle_pair(fid)
        files = {}
        paint_path = output / f"{fid}_paint_2048.png"
        _write_rgb(paint_path, grammar.paint)
        files["paint"] = paint_path
        for label, channel in zip(("M", "R", "Cc"), grammar.explicit_spec):
            path = output / f"{fid}_{label}_2048.png"
            if not cv2.imwrite(str(path), channel):
                raise OSError(f"failed to write {path}")
            files[label] = path
        for label, image in (("angle_A", angle_a), ("angle_B", angle_b),
                             ("angle_delta", angle_delta)):
            path = output / f"{fid}_{label}_2048.png"
            _write_rgb(path, image)
            files[label] = path

        owners = owner_unions(grammar)
        stats = {}
        for label, channel in zip(("M", "R", "Cc"), grammar.explicit_spec):
            stats[label] = {
                "min": int(channel.min()), "max": int(channel.max()),
                "std": round(float(channel.std()), 6),
                "unique_values": int(np.unique(channel).size),
            }
        manifest["finishes"][fid] = {
            "topology": grammar.topology,
            "primitive_px": list(grammar.primitive_px),
            "causal_marks": [
                {"name": name, "bank": bank,
                 "coverage": round(float(np.mean(mask > 0)), 6)}
                for name, mask, bank in grammar.marks
            ],
            "owner_coverage": {
                "A": round(float(np.mean(owners["A"] > 0)), 6),
                "B": round(float(np.mean(owners["B"] > 0)), 6),
                "angle_delta_mean": round(float(angle_delta.mean()), 6),
                "angle_delta_p95": round(float(np.percentile(angle_delta, 95)), 6),
            },
            "native_builder_seconds": round(elapsed, 6),
            "within_3_second_budget": bool(elapsed <= 3.0),
            "spec_stats": stats,
            "files": {
                key: {"path": path.name, "sha256": _sha256(path)}
                for key, path in files.items()
            },
        }
        del grammar, angle_a, angle_b, angle_delta
    manifest_path = output / "fullres_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    render_fullres_evidence(
        Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "cryptid"
    )


__all__ = [
    "BUILDERS", "CRYPTID_FULLRES_IDS", "HUES", "RENDERERS", "S", "_authored",
    "clear_cache", "debug_angle_pair", "debug_grammar", "install_into_engine",
    "owner_unions", "render_fullres_evidence",
]
