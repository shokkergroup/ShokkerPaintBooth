# -*- coding: utf-8 -*-
"""One isolated native-2048 Coral Cluster genealogy study.

SPB-WILDS, 2026-08-24, final bounded full-resolution art attempt.  The owner
rejected repeated cells, pavers, rows, stamps, noise, and picker-size judgment.
This module attempted to grow one connected reef genealogy from a single basal
junction through unequal primary, secondary, and tertiary orders.  Young
branches carry living polyps and axial mouths; old branches carry mineral
crests, erosion scars, and directly attached rubble.  Cross-lineage bridges
fuse back into the older skeleton, so the result is one colony rather than a
field of repeated coral glyphs.

No RNG, seed variation, noise, grain, stochastic jitter, grid, cell field,
wrapped source, or repeated stamp is used.  Curves are integrated from fixed
genealogical parameters, and every anatomical mark is located from branch
identity, order, tangent, and age.  M/R/Cc are independently authored from
mineral skeleton, erosion, and living tissue film.  This file is isolated and
has no production installer or registry side effect.  Native 2048 inspection
stopped the attempt: the radial basal junction and exposed branch hierarchy
read unmistakably as a tree diagram rather than a car-paint coral material.
The source and outputs remain negative-study evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Sequence, Tuple

import cv2
import numpy as np


_SIZE = 2048


@dataclass(frozen=True)
class Branch:
    points: np.ndarray
    order: int
    age: float
    lineage: int
    identity: int


@dataclass(frozen=True)
class CoralResult:
    paint: np.ndarray
    spec: np.ndarray
    marks: Tuple[str, ...]
    branch_counts: Tuple[int, int, int, int]


def _f32(value) -> np.ndarray:
    return np.clip(np.asarray(value, np.float32), 0.0, 1.0)


def _hex(token: str) -> Tuple[int, int, int]:
    text = token.lstrip("#")
    return int(text[:2], 16), int(text[2:4], 16), int(text[4:], 16)


@lru_cache(maxsize=16)
def _lut(tokens: Tuple[str, ...]) -> np.ndarray:
    colours = np.asarray([_hex(token) for token in tokens], np.float32)
    positions = np.linspace(0.0, 255.0, len(colours), dtype=np.float32)
    query = np.arange(256, dtype=np.float32)
    table = np.empty((256, 3), np.uint8)
    for channel in range(3):
        table[:, channel] = np.interp(query, positions, colours[:, channel]).astype(np.uint8)
    return table


def _colour(field: np.ndarray, palette: Sequence[str]) -> np.ndarray:
    index = np.clip(np.asarray(field, np.float32) * 255.0, 0, 255).astype(np.uint8)
    return _lut(tuple(palette))[index]


def _blend(base: np.ndarray, overlay: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = _f32(alpha)[..., None]
    b = np.asarray(base, np.float32)
    o = np.asarray(overlay, np.float32)
    return b + (o - b) * a


def _tiers(field: np.ndarray, values: Sequence[int]) -> np.ndarray:
    scale = _f32(field)
    bank = np.asarray(tuple(values), np.uint8)
    index = np.minimum((scale * len(bank)).astype(np.int16), len(bank) - 1)
    return bank[index]


def _curve(
    start: Tuple[float, float],
    heading: float,
    length: float,
    bend: float,
    phase: float,
    step: float = 10.0,
) -> np.ndarray:
    """Integrate a coherent branch from inherited heading and growth age."""
    count = max(3, int(math.ceil(length / step)))
    points = np.empty((count + 1, 2), np.float32)
    points[0] = start
    direction = float(heading)
    for index in range(1, count + 1):
        t = index / count
        # Unequal-order curvature is coherent along the branch, never jitter.
        direction += (
            bend * math.sin(math.pi * t + phase) / count
            + 0.16 * math.sin(3.0 * math.pi * t + 0.7 * phase) / count
            + 0.07 * math.sin(7.0 * math.pi * t - phase) / count
        )
        next_x = float(points[index - 1, 0]) + step * math.cos(direction)
        next_y = float(points[index - 1, 1]) + step * math.sin(direction)
        # Growth folds along the colony boundary instead of clipping into a
        # rectangular diagram. Reflection is deterministic and continuous.
        if next_x < 24.0 or next_x > _SIZE - 24.0:
            direction = math.pi - direction
            next_x = min(_SIZE - 24.0, max(24.0, next_x))
        if next_y < 24.0 or next_y > _SIZE - 24.0:
            direction = -direction
            next_y = min(_SIZE - 24.0, max(24.0, next_y))
        points[index] = (next_x, next_y)
    return points


def _tangent(points: np.ndarray, index: int) -> float:
    lo = max(0, index - 1)
    hi = min(len(points) - 1, index + 1)
    delta = points[hi] - points[lo]
    return math.atan2(float(delta[1]), float(delta[0]))


def _genealogy() -> Tuple[List[Branch], List[Branch]]:
    """Return connected growth branches and explicit cross-lineage fusions."""
    root = (1007.0, 1129.0)
    headings = (-2.92, -2.31, -1.58, -0.86, -0.18, 0.63, 1.37, 2.16)
    lengths = (1110.0, 870.0, 1040.0, 920.0, 1160.0, 790.0, 1080.0, 940.0)
    bends = (1.05, -0.72, 0.88, -1.18, 0.64, -0.96, 1.24, -0.58)
    branches: List[Branch] = []
    identity = 0

    primaries: List[Branch] = []
    for lineage, (heading, length, bend) in enumerate(zip(headings, lengths, bends)):
        points = _curve(root, heading, length, bend, 0.61 * lineage + 0.17)
        branch = Branch(points, 0, 0.91 - 0.035 * lineage, lineage, identity)
        identity += 1
        primaries.append(branch)
        branches.append(branch)

    secondaries: List[Branch] = []
    fractions = (0.14, 0.29, 0.47, 0.68, 0.84)
    for primary in primaries:
        for child_index, fraction in enumerate(fractions):
            warped_fraction = min(0.90, max(0.10, fraction + 0.035 * math.sin(primary.lineage * 1.17 + child_index * 0.83)))
            anchor_index = int(round(warped_fraction * (len(primary.points) - 1)))
            anchor = tuple(float(v) for v in primary.points[anchor_index])
            inherited = _tangent(primary.points, anchor_index)
            side = -1.0 if (primary.lineage + child_index) % 2 else 1.0
            divergence = side * (0.56 + 0.11 * child_index + 0.08 * math.sin(primary.lineage * 0.71))
            length = 255.0 + 48.0 * child_index + 61.0 * math.sin(primary.lineage * 0.79 + child_index * 1.31)
            points = _curve(anchor, inherited + divergence, length, side * (0.62 + 0.13 * child_index), 0.37 * identity)
            branch = Branch(points, 1, 0.60 - 0.042 * child_index + 0.016 * primary.lineage, primary.lineage, identity)
            identity += 1
            secondaries.append(branch)
            branches.append(branch)

    tertiaries: List[Branch] = []
    for secondary in secondaries:
        count = 2 + (secondary.identity % 3 == 0)
        for child_index in range(count):
            fraction = (0.34, 0.62, 0.80)[child_index]
            fraction += 0.035 * math.sin(secondary.identity * 0.49 + child_index)
            anchor_index = int(round(fraction * (len(secondary.points) - 1)))
            anchor = tuple(float(v) for v in secondary.points[anchor_index])
            inherited = _tangent(secondary.points, anchor_index)
            side = -1.0 if (secondary.identity + child_index) % 2 else 1.0
            divergence = side * (0.72 + 0.17 * math.sin(secondary.identity * 0.63 + child_index))
            length = 84.0 + 31.0 * child_index + 48.0 * (0.5 + 0.5 * math.sin(secondary.identity * 0.81))
            points = _curve(anchor, inherited + divergence, length, side * 0.44, 0.29 * secondary.identity + child_index)
            branch = Branch(points, 2, 0.24 + 0.06 * child_index, secondary.lineage, identity)
            identity += 1
            tertiaries.append(branch)
            branches.append(branch)

    # Fuse selected young tips to an older branch from a different lineage.
    older_samples = []
    for branch in primaries + secondaries:
        for point in branch.points[::4]:
            older_samples.append((float(point[0]), float(point[1]), branch.lineage, branch.identity))
    sample_array = np.asarray([(p[0], p[1]) for p in older_samples], np.float32)
    fusions: List[Branch] = []
    for terminal_index, branch in enumerate(tertiaries):
        if terminal_index % 3:
            continue
        endpoint = branch.points[-1]
        delta = sample_array - endpoint
        distance2 = np.sum(delta * delta, axis=1)
        valid = np.asarray([sample[2] != branch.lineage for sample in older_samples], bool)
        distance2[~valid] = np.inf
        nearest = int(np.argmin(distance2))
        distance = math.sqrt(float(distance2[nearest]))
        if not (38.0 <= distance <= 235.0):
            continue
        target = sample_array[nearest]
        heading = math.atan2(float(target[1] - endpoint[1]), float(target[0] - endpoint[0]))
        points = _curve(tuple(float(v) for v in endpoint), heading, distance, 0.36 * math.sin(branch.identity), 0.19 * branch.identity, 8.0)
        points[-1] = target
        fusion = Branch(points, 3, 0.42, branch.lineage, identity)
        identity += 1
        fusions.append(fusion)

    return branches, fusions


def _draw_polyline(mask: np.ndarray, points: np.ndarray, value: int, width: int) -> None:
    cv2.polylines(mask, [np.rint(points).astype(np.int32)], False, int(value), int(width), cv2.LINE_AA)


def _draw_age(mask: np.ndarray, branch: Branch, width: int) -> None:
    count = len(branch.points) - 1
    for index in range(count):
        age = branch.age * (1.0 - 0.34 * index / max(1, count))
        cv2.line(
            mask,
            tuple(np.rint(branch.points[index]).astype(int)),
            tuple(np.rint(branch.points[index + 1]).astype(int)),
            int(np.clip(32 + 220 * age, 0, 255)),
            width,
            cv2.LINE_AA,
        )


@lru_cache(maxsize=1)
def build_coral_genealogy() -> CoralResult:
    branches, fusions = _genealogy()
    skeleton = np.zeros((_SIZE, _SIZE), np.uint8)
    age_map = np.zeros_like(skeleton)
    axial = np.zeros_like(skeleton)
    fusion_mask = np.zeros_like(skeleton)
    scars = np.zeros_like(skeleton)
    rubble = np.zeros_like(skeleton)
    cup = np.zeros_like(skeleton)
    cup_floor = np.zeros_like(skeleton)
    mouth = np.zeros_like(skeleton)
    septa = np.zeros_like(skeleton)
    polyps = np.zeros_like(skeleton)
    tentacles = np.zeros_like(skeleton)

    widths = {0: 28, 1: 18, 2: 10}
    for branch in branches:
        width = widths[branch.order]
        _draw_polyline(skeleton, branch.points, 255, width)
        _draw_polyline(axial, branch.points, 205 - 35 * branch.order, max(2, 5 - branch.order))
        _draw_age(age_map, branch, width)

    for fusion in fusions:
        _draw_polyline(skeleton, fusion.points, 255, 9)
        _draw_polyline(fusion_mask, fusion.points, 235, 9)
        _draw_age(age_map, fusion, 9)

    # Old-branch erosion and rubble inherit age, tangent, and branch width.
    for branch in branches:
        if branch.order > 1 or branch.age < 0.44:
            continue
        scar_count = 2 + ((branch.identity + branch.lineage) % 3)
        for scar_index in range(scar_count):
            fraction = 0.20 + (scar_index + 1) / (scar_count + 2) * 0.62
            index = int(round(fraction * (len(branch.points) - 1)))
            centre = branch.points[index]
            angle = _tangent(branch.points, index)
            long_axis = 8 + (branch.identity + 3 * scar_index) % 7
            short_axis = 4 + (branch.lineage + scar_index) % 3
            cv2.ellipse(
                scars,
                tuple(np.rint(centre).astype(int)),
                (long_axis, short_axis),
                math.degrees(angle), 0, 360, 225, -1, cv2.LINE_AA,
            )
            normal = np.asarray((-math.sin(angle), math.cos(angle)), np.float32)
            side = -1.0 if (branch.identity + scar_index) % 2 else 1.0
            anchor = centre + normal * side * (widths[branch.order] * 0.46)
            tangent = np.asarray((math.cos(angle), math.sin(angle)), np.float32)
            fragment = np.asarray(
                [
                    anchor,
                    anchor + tangent * (7 + scar_index) + normal * side * 5,
                    anchor - tangent * (6 + branch.lineage % 4) + normal * side * 8,
                ],
                np.float32,
            )
            cv2.fillPoly(rubble, [np.rint(fragment).astype(np.int32)], 210, cv2.LINE_AA)

    # Young branch anatomy varies with identity, age, and inherited tangent.
    young_branches = [branch for branch in branches if branch.order == 2]
    for branch in young_branches:
        positions = (0.56, 0.82, 1.0) if branch.identity % 2 == 0 else (0.68, 1.0)
        for local_index, fraction in enumerate(positions):
            index = min(len(branch.points) - 1, int(round(fraction * (len(branch.points) - 1))))
            centre = branch.points[index]
            angle = _tangent(branch.points, index)
            major = 9 + (branch.identity + 2 * local_index) % 6
            minor = 7 + (branch.lineage + local_index) % 4
            centre_i = tuple(np.rint(centre).astype(int))
            cv2.ellipse(polyps, centre_i, (major + 2, minor + 2), math.degrees(angle), 0, 360, 175 + 12 * local_index, -1, cv2.LINE_AA)
            cv2.ellipse(cup_floor, centre_i, (major, minor), math.degrees(angle), 0, 360, 205, -1, cv2.LINE_AA)
            cv2.ellipse(cup, centre_i, (major, minor), math.degrees(angle), 0, 360, 245, 3, cv2.LINE_AA)
            cv2.ellipse(mouth, centre_i, (5 + branch.identity % 3, 2 + local_index), math.degrees(angle), 0, 360, 235, -1, cv2.LINE_AA)
            tooth_count = 5 + (branch.identity + local_index) % 5
            for tooth in range(tooth_count):
                tooth_angle = angle + 2.0 * math.pi * tooth / tooth_count + 0.09 * math.sin(branch.identity)
                inner = centre + np.asarray((math.cos(tooth_angle), math.sin(tooth_angle)), np.float32) * 5.0
                outer = centre + np.asarray((math.cos(tooth_angle), math.sin(tooth_angle)), np.float32) * (major - 1.0)
                cv2.line(septa, tuple(np.rint(inner).astype(int)), tuple(np.rint(outer).astype(int)), 220, 2, cv2.LINE_AA)
            if fraction >= 0.99:
                tentacle_count = 6 + branch.identity % 5
                for tentacle in range(tentacle_count):
                    tentacle_angle = angle + 2.0 * math.pi * tentacle / tentacle_count
                    start = centre + np.asarray((math.cos(tentacle_angle), math.sin(tentacle_angle)), np.float32) * (major - 1.0)
                    bend = centre + np.asarray((math.cos(tentacle_angle + 0.22), math.sin(tentacle_angle + 0.22)), np.float32) * (major + 6.0)
                    end = centre + np.asarray((math.cos(tentacle_angle + 0.08), math.sin(tentacle_angle + 0.08)), np.float32) * (major + 12.0)
                    curve = np.asarray([start, (start + bend) * 0.5, bend, (bend + end) * 0.5, end], np.float32)
                    _draw_polyline(tentacles, curve, 210, 2)

    skeleton_f = skeleton.astype(np.float32) / 255.0
    age_f = age_map.astype(np.float32) / 255.0
    axial_f = axial.astype(np.float32) / 255.0
    fusion_f = fusion_mask.astype(np.float32) / 255.0
    scar_f = scars.astype(np.float32) / 255.0
    rubble_f = rubble.astype(np.float32) / 255.0
    cup_f = cup.astype(np.float32) / 255.0
    floor_f = cup_floor.astype(np.float32) / 255.0
    mouth_f = mouth.astype(np.float32) / 255.0
    septa_f = septa.astype(np.float32) / 255.0
    polyp_f = polyps.astype(np.float32) / 255.0
    tentacle_f = tentacles.astype(np.float32) / 255.0

    binary = (skeleton > 16).astype(np.uint8)
    depth = _f32(cv2.distanceTransform(binary, cv2.DIST_L2, 3) / 14.0)
    eroded = cv2.erode(binary, np.ones((5, 5), np.uint8), iterations=1).astype(np.float32)
    mineral_crest = _f32(skeleton_f - eroded)
    reef_halo = _f32(cv2.GaussianBlur(skeleton_f, (0, 0), 7.0))
    living = np.maximum.reduce((floor_f, polyp_f, tentacle_f, cup_f * 0.55))

    base = _colour(
        _f32(0.08 + 0.30 * reef_halo + 0.16 * fusion_f),
        ("#010609", "#031018", "#071b22", "#0a2830", "#10242a", "#080d13"),
    ).astype(np.float32)
    skeleton_colour = _colour(
        _f32(0.08 + 0.43 * age_f + 0.24 * depth + 0.20 * mineral_crest + 0.12 * fusion_f),
        (
            "#260407", "#5a0b09", "#94170d", "#cc2d12", "#f04e1c", "#ff7830",
            "#ff9b45", "#ffc45f", "#ffe68c", "#ffb784", "#f56c73", "#d43b8d",
            "#9035aa", "#4942a6", "#e9a56d",
        ),
    )
    tissue_colour = _colour(
        _f32(0.10 + 0.38 * (1.0 - age_f) + 0.28 * living + 0.18 * septa_f + 0.13 * fusion_f),
        (
            "#031435", "#053c6b", "#006a8b", "#00999b", "#00c89b", "#42e77e",
            "#9bf05e", "#e2ef52", "#ffdf58", "#ff9d57", "#ff5c70", "#e7389b",
            "#9a34c2", "#533bc6", "#38cfd5",
        ),
    )
    paint = _blend(base, skeleton_colour, _f32(0.94 * skeleton_f))
    paint = _blend(paint, tissue_colour, _f32(0.88 * living + 0.42 * fusion_f))
    paint = _blend(paint, np.full_like(tissue_colour, (255, 225, 151)), _f32(0.48 * mineral_crest + 0.35 * axial_f + 0.32 * septa_f))
    paint = _blend(paint, np.full_like(tissue_colour, (63, 9, 16)), _f32(0.78 * scar_f + 0.88 * mouth_f))
    paint = _blend(paint, np.full_like(tissue_colour, (211, 134, 72)), _f32(0.78 * rubble_f))

    # Three independent material ancestries: mineral age/crest, destructive
    # erosion/rubble, and living film/cups. They cannot share one silhouette.
    metal_field = _f32(0.04 + 0.58 * skeleton_f * age_f + 0.48 * mineral_crest + 0.36 * fusion_f + 0.22 * axial_f - 0.28 * scar_f)
    rough_field = _f32(0.10 + 0.72 * scar_f + 0.62 * rubble_f + 0.30 * mineral_crest + 0.22 * axial_f - 0.38 * living + 0.14 * (1.0 - reef_halo))
    coat_field = _f32(0.05 + 0.72 * living + 0.52 * floor_f + 0.38 * cup_f + 0.28 * tentacle_f - 0.56 * mouth_f - 0.34 * rubble_f)
    spec = np.dstack(
        (
            _tiers(metal_field, (6, 22, 42, 66, 94, 128, 164, 204, 242)),
            _tiers(rough_field, (16, 34, 56, 82, 112, 146, 182, 218, 246)),
            _tiers(coat_field, (8, 26, 48, 74, 104, 140, 178, 218, 248)),
        )
    ).astype(np.uint8)
    marks = (
        "unequal_primary_ancestry", "secondary_growth_orders", "terminal_living_twigs",
        "cross_lineage_fused_bridges", "axial_mouths", "septal_cups",
        "living_polyp_films", "terminal_tentacles", "age_bound_erosion_scars",
        "scar_attached_rubble", "mineral_wall_crests",
    )
    return CoralResult(
        np.clip(paint, 0, 255).astype(np.uint8),
        spec,
        marks,
        (
            sum(branch.order == 0 for branch in branches),
            sum(branch.order == 1 for branch in branches),
            sum(branch.order == 2 for branch in branches),
            len(fusions),
        ),
    )


def clear_cache() -> None:
    build_coral_genealogy.cache_clear()


def angle_pair(result: CoralResult) -> Tuple[np.ndarray, np.ndarray]:
    paint = result.paint.astype(np.float32) / 255.0
    metal = result.spec[:, :, 0].astype(np.float32) / 255.0
    rough = result.spec[:, :, 1].astype(np.float32) / 255.0
    coat = result.spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.08 - 0.60 * rough, 0.22, 1.0)
    lobe_a = np.clip(0.20 + 1.16 * metal * aperture, 0.18, 1.34)
    lobe_b = np.clip(0.20 + 1.16 * coat * aperture, 0.18, 1.34)
    cool = np.asarray([0.012, 0.11, 0.18], np.float32)
    warm = np.asarray([0.20, 0.045, 0.01], np.float32)
    view_a = np.clip(paint * lobe_a[..., None] + cool * (metal * aperture)[..., None], 0, 1)
    view_b = np.clip(paint * lobe_b[..., None] + warm * (coat * aperture)[..., None], 0, 1)
    return (view_a * 255.0).astype(np.uint8), (view_b * 255.0).astype(np.uint8)


def _sha(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _write_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)):
        raise OSError(path)


def _write_gray(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(path)


def audit(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    clear_cache()
    started = time.perf_counter()
    first = build_coral_genealogy()
    first_seconds = time.perf_counter() - started
    paint_hash, spec_hash = _sha(first.paint), _sha(first.spec)
    clear_cache()
    repeat_started = time.perf_counter()
    repeat = build_coral_genealogy()
    repeat_seconds = time.perf_counter() - repeat_started
    deterministic = paint_hash == _sha(repeat.paint) and spec_hash == _sha(repeat.spec)
    view_a, view_b = angle_pair(first)

    _write_rgb(output / "FBL_CORAL_CLUSTER_PAINT_2048.png", first.paint)
    _write_gray(output / "FBL_CORAL_CLUSTER_M_2048.png", first.spec[:, :, 0])
    _write_gray(output / "FBL_CORAL_CLUSTER_R_2048.png", first.spec[:, :, 1])
    _write_gray(output / "FBL_CORAL_CLUSTER_CC_2048.png", first.spec[:, :, 2])
    _write_rgb(output / "FBL_CORAL_CLUSTER_ANGLE_A_2048.png", view_a)
    _write_rgb(output / "FBL_CORAL_CLUSTER_ANGLE_B_2048.png", view_b)
    _write_rgb(output / "FBL_CORAL_CLUSTER_DETAIL_1TO1_768.png", first.paint[640:1408, 640:1408])

    channels = {}
    for index, name in enumerate(("M", "R", "Cc")):
        channel = first.spec[:, :, index]
        channels[name] = {
            "range": [int(channel.min()), int(channel.max())],
            "std": round(float(channel.std()), 4),
            "tiers": int(np.unique(channel).size),
            "sha256": _sha(channel),
        }
    payload = {
        "schema": "spb-wilds-coral-genealogy-native2048/1",
        "status": "REJECT-TREE-DIAGRAM-DO-NOT-WIRE",
        "visual_verdict": "REJECT",
        "visual_reason": "radial basal junction and exposed branch hierarchy read unmistakably as a tree diagram, not a coral paint material",
        "id": "fbl_coral_cluster",
        "native_size": [2048, 2048],
        "process": "one connected unequal-order reef genealogy with cross-lineage fusions",
        "branch_counts_primary_secondary_tertiary_fusions": list(first.branch_counts),
        "marks": list(first.marks),
        "paint_sha256": paint_hash,
        "spec_sha256": spec_hash,
        "angle_a_sha256": _sha(view_a),
        "angle_b_sha256": _sha(view_b),
        "angle_flip_mean_abs_rgb": round(float(np.mean(np.abs(view_a.astype(np.int16) - view_b.astype(np.int16)))), 4),
        "render_seconds_uncached": round(first_seconds, 4),
        "repeat_seconds_uncached": round(repeat_seconds, 4),
        "render_budget_pass": bool(max(first_seconds, repeat_seconds) <= 3.0),
        "deterministic_repeat": bool(deterministic),
        "channels": channels,
        "forbidden_constructions_absent": ["cells", "paver", "grid", "rows", "glyph stamps", "rng", "noise", "grain"],
    }
    (output / "CORAL_GENEALOGY_AUDIT.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Coral Cluster native-2048 genealogy audit",
        "",
        "Status: **REJECT — TREE DIAGRAM**. Negative-study evidence only; isolated and never production-wired.",
        "",
        "The construction is one connected genealogy rather than a field of cells or stamps, but the native image fails the visual stop condition: its radial basal junction and exposed branch hierarchy read unmistakably as a tree diagram instead of a coral paint material. Mechanical causality does not rescue that failure.",
        "",
        f"Uncached native renders: {first_seconds:.4f}s / {repeat_seconds:.4f}s — {'PASS' if payload['render_budget_pass'] else 'FAIL'}  ",
        f"Deterministic repeat: {'PASS' if deterministic else 'FAIL'}  ",
        f"Branch counts (primary / secondary / tertiary / fusion): {' / '.join(str(v) for v in first.branch_counts)}  ",
        f"A/B angle mean absolute RGB change: {payload['angle_flip_mean_abs_rgb']:.4f}",
        "",
        "| Channel | Range | Std-dev | Authored tiers | SHA-256 |",
        "|---|---:|---:|---:|---|",
    ]
    for name in ("M", "R", "Cc"):
        channel = channels[name]
        report.append(f"| {name} | {channel['range'][0]}–{channel['range'][1]} | {channel['std']:.4f} | {channel['tiers']} | `{channel['sha256']}` |")
    report.extend([
        "",
        "## Stop boundary",
        "",
        "The native image reads as a tree diagram, so this attempt is REJECTED without rescue by recolouring or noise. Nothing in this module may be wired or counted as progress.",
        "",
    ])
    (output / "CORAL_GENEALOGY_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("_wilds_fullres_progress_20260824/coral_genealogy"))
    args = parser.parse_args()
    payload = audit(args.output)
    print(
        payload["id"],
        f"{payload['render_seconds_uncached']:.4f}s/{payload['repeat_seconds_uncached']:.4f}s",
        "budget=PASS" if payload["render_budget_pass"] else "budget=FAIL",
        "deterministic=PASS" if payload["deterministic_repeat"] else "deterministic=FAIL",
        "visual=REJECT-TREE-DIAGRAM",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Branch", "CoralResult", "build_coral_genealogy", "clear_cache", "angle_pair", "audit"]
