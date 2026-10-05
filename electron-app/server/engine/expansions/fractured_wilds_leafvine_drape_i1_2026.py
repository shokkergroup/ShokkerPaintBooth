# -*- coding: utf-8 -*-
"""Isolated native-2048 Leafvine Drape botanical-tapestry study.

Fourteen unequal off-canvas vines climb a warped, incomplete trellis. Every
leaf, tendril, pod, thorn, collar and wound is attached to that shared growth
history; there is no RNG, noise, grain, stamp atlas, particle scatter, graph
layout or reused Wilds composer.

SPB-WILDS-LEAFVINE-I1 / SPB-105, 2026-08-24. Native verdict: REJECT. The
canvas reads as sparse vertical rails decorated with tiny repeated leaf glyphs
and horizontal trellis lines. No density, palette, scale or spec repair is
authorized. Installer remains fail-closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time
from typing import Dict, Tuple

import cv2
import numpy as np


ID = "fbl_leafvine_drape"
WORK = 512


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]
    topology: str


def _f(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def _mask() -> np.ndarray:
    return np.zeros((WORK, WORK), np.uint8)


def _line(dst: np.ndarray, pts: np.ndarray, width: int = 1) -> None:
    cv2.polylines(dst, [np.rint(pts).astype(np.int32)], False, 255,
                  width, cv2.LINE_AA)


def _poly(dst: np.ndarray, pts: np.ndarray) -> None:
    cv2.fillPoly(dst, [np.rint(pts).astype(np.int32)], 255, cv2.LINE_AA)


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    lo, hi = np.percentile(field, (3.0, 97.0))
    spread = _f((field - float(lo)) / max(float(hi - lo), 1e-5))
    idx = np.clip(np.floor(spread * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _vine_xy(index: int, t: np.ndarray | float) -> Tuple[np.ndarray, np.ndarray]:
    t = np.asarray(t, np.float32)
    phase = (index * 0.61803398875) % 1.0
    lane = (index + 0.47) * WORK / 14.0
    drift = (8.0 + 7.0 * np.sin(index * 1.73)) * (t - 0.5)
    x = (lane + drift
         + (11.0 + 4.0 * np.sin(index * 2.17))
         * np.sin(2.0 * np.pi * ((1.12 + 0.07 * index) * t + phase))
         + 5.0 * np.sin(2.0 * np.pi * (3.17 * t + phase * 0.41)))
    y = t * (WORK - 1)
    return x, y


def _leaf_polygon(center: np.ndarray, direction: np.ndarray,
                  length: float, width: float, phase: float) -> np.ndarray:
    direction = direction / max(float(np.linalg.norm(direction)), 1e-6)
    normal = np.asarray((-direction[1], direction[0]), np.float32)
    pts = []
    steps = 6
    for side in (1.0, -1.0):
        order = range(steps + 1) if side > 0 else range(steps, -1, -1)
        for k in order:
            s = k / steps
            axial = (s - 0.42) * length
            envelope = np.sin(np.pi * s) ** 0.78
            serration = 1.0 + 0.19 * np.sin((k * 2.0 + phase * 7.0) * np.pi)
            asym = 1.0 + side * 0.13 * np.sin(phase * 11.0 + s * 5.0)
            p = center + direction * axial + normal * side * width * envelope * serration * asym
            pts.append(p)
    return np.asarray(pts, np.float32)


@lru_cache(maxsize=1)
def _build() -> Grammar:
    trellis = _mask()
    stem = _mask()
    branch = _mask()
    lamina_a = _mask()
    lamina_b = _mask()
    margin = _mask()
    midrib = _mask()
    tendril = _mask()
    thorn = _mask()
    pod = _mask()
    collar = _mask()
    wound = _mask()

    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    base_phase = np.mod(0.013 * xx + 0.009 * yy
                        + 0.12 * np.sin(xx / 43.0 + yy / 67.0), 1.0)
    paint = np.empty((WORK, WORK, 3), np.float32)
    paint[..., 0] = 0.018 + 0.018 * base_phase
    paint[..., 1] = 0.025 + 0.026 * (1.0 - base_phase)
    paint[..., 2] = 0.065 + 0.030 * base_phase

    palette = np.asarray([
        (0.06, 0.72, 0.54), (0.10, 0.91, 0.78), (0.22, 0.64, 0.96),
        (0.42, 0.26, 0.91), (0.73, 0.16, 0.88), (0.96, 0.19, 0.63),
        (0.98, 0.38, 0.34), (0.99, 0.67, 0.19), (0.83, 0.89, 0.24),
        (0.43, 0.84, 0.24), (0.06, 0.58, 0.38), (0.04, 0.46, 0.70),
    ], np.float32)

    # Incomplete warped trellis: no regular grid and no identical rail spacing.
    for k in range(9):
        s = np.linspace(-0.08, 1.08, 190, dtype=np.float32)
        x = s * (WORK - 1)
        y = ((k + 0.65) * WORK / 9.0
             + 12.0 * np.sin(2.0 * np.pi * (s * (0.63 + 0.037 * k) + k * 0.17))
             + (k - 4.0) * 7.0 * (s - 0.5))
        keep = ~(((np.arange(s.size) + 17 * k) % (43 + k)) < (5 + k % 4))
        runs = np.split(np.column_stack((x, y))[keep],
                        np.where(np.diff(np.flatnonzero(keep)) > 1)[0] + 1)
        for run in runs:
            if len(run) > 2:
                _line(trellis, run, 1 + (k % 3 == 0))
                cv2.polylines(paint, [np.rint(run).astype(np.int32)], False,
                              (0.22, 0.13, 0.08), 1 + (k % 3 == 0), cv2.LINE_AA)

    tline = np.linspace(-0.08, 1.08, 420, dtype=np.float32)
    for i in range(14):
        vx, vy = _vine_xy(i, tline)
        vine_pts = np.column_stack((vx, vy))
        sw = 2 + (i % 4 == 0)
        _line(stem, vine_pts, sw)
        stem_color = tuple(float(v) for v in palette[(i * 5 + 9) % 12] * 0.48)
        cv2.polylines(paint, [np.rint(vine_pts).astype(np.int32)], False,
                      stem_color, sw, cv2.LINE_AA)

        for j in range(20):
            phase = (i * 0.61803398875 + j * 0.41421356237) % 1.0
            tn = (j + 0.30 + 0.24 * np.sin(i * 1.31 + j * 2.07)) / 20.0
            px, py = _vine_xy(i, tn)
            xa, ya = _vine_xy(i, tn - 0.002)
            xb, yb = _vine_xy(i, tn + 0.002)
            tangent = np.asarray((float(xb - xa), float(yb - ya)), np.float32)
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1.0 if (i + j) % 2 else 1.0
            origin = np.asarray((float(px), float(py)), np.float32)
            branch_len = 3.0 + 3.4 * ((phase * 1.73) % 1.0)
            bend = tangent * (1.1 * np.sin(phase * 9.0))
            tip = origin + normal * side * branch_len + bend
            bpts = np.asarray((origin, origin * 0.55 + tip * 0.45 + tangent * 1.2, tip))
            _line(branch, bpts, 1)
            cv2.polylines(paint, [np.rint(bpts).astype(np.int32)], False,
                          tuple(float(v) for v in palette[(i * 3 + j + 10) % 12] * 0.42),
                          1, cv2.LINE_AA)

            leaf_dir = normal * side + tangent * (0.42 * np.sin(phase * 13.0))
            leaf_len = 4.2 + 3.5 * ((phase * 2.31) % 1.0)
            leaf_w = 1.55 + 1.35 * ((phase * 3.17) % 1.0)
            center = tip + leaf_dir * (leaf_len * 0.35)
            leaf = _leaf_polygon(center, leaf_dir, leaf_len, leaf_w, phase)
            bank_a = ((i * 7 + j * 3) % 11) < 5
            _poly(lamina_a if bank_a else lamina_b, leaf)
            _line(margin, np.vstack((leaf, leaf[0])), 1)
            leaf_color = palette[(i * 5 + j * 7) % 12]
            shade = 0.66 + 0.31 * ((phase * 5.83) % 1.0)
            cv2.fillPoly(paint, [np.rint(leaf).astype(np.int32)],
                         tuple(float(v) for v in leaf_color * shade), cv2.LINE_AA)
            cv2.polylines(paint, [np.rint(np.vstack((leaf, leaf[0]))).astype(np.int32)],
                          False, tuple(float(v) for v in np.clip(leaf_color * 1.18, 0, 1)),
                          1, cv2.LINE_AA)
            rib0 = center - leaf_dir * leaf_len * 0.40
            rib1 = center + leaf_dir * leaf_len * 0.52
            _line(midrib, np.asarray((rib0, rib1)), 1)
            cv2.line(paint, tuple(np.rint(rib0).astype(int)), tuple(np.rint(rib1).astype(int)),
                     tuple(float(v) for v in np.clip(leaf_color * 1.32, 0, 1)), 1, cv2.LINE_AA)

            if (i + 2 * j) % 4 == 0:
                ang = np.linspace(0.0, 1.7 * np.pi, 28, dtype=np.float32)
                radius = np.linspace(0.6, 3.3 + 1.2 * phase, ang.size)
                c = origin - normal * side * 1.3
                spiral = c + np.column_stack((np.cos(ang + phase * 4.0),
                                               np.sin(ang + phase * 4.0))) * radius[:, None]
                _line(tendril, spiral, 1)
                cv2.polylines(paint, [np.rint(spiral).astype(np.int32)], False,
                              tuple(float(v) for v in palette[(i + j + 1) % 12]), 1, cv2.LINE_AA)

            if (3 * i + j) % 9 == 0:
                pdir = tangent * (2.0 + phase) + normal * side * 1.5
                pc = origin + pdir
                axes = (2 + (j % 2), 1 + (i % 2))
                cv2.ellipse(pod, tuple(np.rint(pc).astype(int)), axes,
                            float(np.degrees(np.arctan2(pdir[1], pdir[0]))), 0, 360,
                            255, -1, cv2.LINE_AA)
                cv2.ellipse(paint, tuple(np.rint(pc).astype(int)), axes,
                            float(np.degrees(np.arctan2(pdir[1], pdir[0]))), 0, 360,
                            tuple(float(v) for v in palette[(i * 2 + j + 4) % 12]), -1, cv2.LINE_AA)

            if (i + j) % 5 == 0:
                thorn_tip = origin - normal * side * (2.0 + phase)
                _line(thorn, np.asarray((origin, thorn_tip)), 1)
                cv2.line(paint, tuple(np.rint(origin).astype(int)),
                         tuple(np.rint(thorn_tip).astype(int)), (0.96, 0.50, 0.18), 1, cv2.LINE_AA)

            if (2 * i + j) % 11 == 0:
                cv2.ellipse(collar, tuple(np.rint(origin).astype(int)), (3, 2),
                            float(phase * 180.0), 20, 330, 255, 2, cv2.LINE_AA)
                cv2.ellipse(paint, tuple(np.rint(origin).astype(int)), (3, 2),
                            float(phase * 180.0), 20, 330,
                            tuple(float(v) for v in palette[(i + 2 * j) % 12]), 2, cv2.LINE_AA)

            if (i + 3 * j) % 13 == 0:
                for q in (-1.0, 0.0, 1.0):
                    a = origin + tangent * q - normal * 2.2
                    b = origin + tangent * q + normal * 2.2
                    _line(wound, np.asarray((a, b)), 1)
                    cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                             (0.04, 0.02, 0.07), 1, cv2.LINE_AA)

    masks = [m.astype(np.float32) / 255.0 for m in (
        trellis, stem, branch, lamina_a, lamina_b, margin, midrib,
        tendril, thorn, pod, collar, wound)]
    (trellis_f, stem_f, branch_f, la, lb, margin_f, midrib_f,
     tendril_f, thorn_f, pod_f, collar_f, wound_f) = masks
    paint = _f(paint)
    neutral = _f(np.dot(paint, np.asarray((0.2126, 0.7152, 0.0722), np.float32)))
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    metal_field = _f(0.04 + 0.44 * margin_f + 0.64 * tendril_f
                     + 0.58 * pod_f + 0.48 * collar_f + 0.20 * la
                     - 0.18 * trellis_f)
    rough_field = _f(0.07 + 0.62 * trellis_f + 0.51 * stem_f
                     + 0.42 * branch_f + 0.67 * thorn_f + 0.72 * wound_f
                     - 0.24 * lb)
    coat_field = _f(0.05 + 0.53 * la + 0.69 * lb + 0.51 * midrib_f
                    + 0.36 * pod_f - 0.38 * wound_f - 0.19 * trellis_f)
    metal = _tier(metal_field, (6, 30, 59, 93, 130, 169, 213, 250))
    rough = _tier(rough_field, (14, 40, 71, 105, 141, 180, 220, 249))
    coat = _tier(coat_field, (5, 28, 57, 90, 128, 169, 214, 252))

    marks = (
        ("weathered_trellis_strands", trellis_f, "N"),
        ("primary_climbing_stems", stem_f, "N"),
        ("axillary_branch_stems", branch_f, "N"),
        ("opponent_leaf_lamina_A", la, "A"),
        ("opponent_leaf_lamina_B", lb, "B"),
        ("serrated_leaf_margins", margin_f, "A"),
        ("leaf_midribs", midrib_f, "B"),
        ("tendril_wraps", tendril_f, "A"),
        ("thorn_tips", thorn_f, "N"),
        ("seed_pods", pod_f, "B"),
        ("over_under_node_collars", collar_f, "B"),
        ("stem_wound_cuts", wound_f, "N"),
    )
    absent = [(name, float(mask.std())) for name, mask, _bank in marks
              if float(mask.std()) < 0.003]
    if absent:
        raise ValueError(f"Leafvine I1 has absent causal marks: {absent}")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="fourteen unequal off-canvas vines attached to one warped incomplete trellis",
    )


def clear_cache() -> None:
    _build.cache_clear()


def debug_grammar() -> Grammar:
    return _build()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    owners = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        owners[bank] = np.maximum(owners[bank], mask)
    return owners


def debug_angle_pair() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.50 + 0.46 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.04, 0.53, 0.45), np.float32)
    a += owners["B"][..., None] * np.asarray((0.29, 0.07, 0.34), np.float32)
    b = grammar.paint * (0.49 + 0.47 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.57, 0.08, 0.38), np.float32)
    b += owners["A"][..., None] * np.asarray((0.30, 0.27, 0.03), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


def _authored() -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)


def render_native(size: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    paint, spec = _authored()
    if size == WORK:
        return paint.copy(), spec.copy()
    paint = cv2.resize(paint, (size, size), interpolation=cv2.INTER_CUBIC)
    spec = cv2.resize(spec, (size, size), interpolation=cv2.INTER_NEAREST)
    return _f(paint), spec.astype(np.uint8)


def _write_rgb(path: Path, image: np.ndarray) -> None:
    u8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"failed to write {path}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_evidence(output_dir: str | Path) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    clear_cache()
    started = time.perf_counter()
    paint, spec = render_native(2048)
    elapsed = time.perf_counter() - started
    angle_a, angle_b, delta = debug_angle_pair()
    angle_a = cv2.resize(angle_a, (2048, 2048), interpolation=cv2.INTER_CUBIC)
    angle_b = cv2.resize(angle_b, (2048, 2048), interpolation=cv2.INTER_CUBIC)
    delta = cv2.resize(delta, (2048, 2048), interpolation=cv2.INTER_CUBIC)
    paths = {
        "paint": output / f"{ID}_paint_2048.png",
        "M": output / f"{ID}_M_2048.png",
        "R": output / f"{ID}_R_2048.png",
        "Cc": output / f"{ID}_Cc_2048.png",
        "angle_A": output / f"{ID}_angle_A_2048.png",
        "angle_B": output / f"{ID}_angle_B_2048.png",
        "angle_delta": output / f"{ID}_angle_delta_2048.png",
    }
    _write_rgb(paths["paint"], paint)
    for label, channel in zip(("M", "R", "Cc"), cv2.split(spec)):
        if not cv2.imwrite(str(paths[label]), channel):
            raise OSError(f"failed to write {paths[label]}")
    _write_rgb(paths["angle_A"], angle_a)
    _write_rgb(paths["angle_B"], angle_b)
    _write_rgb(paths["angle_delta"], np.clip(delta * 2.0, 0, 1))
    crop_path = output / f"{ID}_detail_1to1_1024.png"
    _write_rgb(crop_path, paint[512:1536, 512:1536])
    paths["detail_1to1"] = crop_path

    grammar = _build()
    owners = owner_unions(grammar)
    channels = [c.astype(np.float32).ravel() for c in cv2.split(spec)]
    corr = np.corrcoef(np.stack(channels))
    payload = {
        "schema": "spb-wilds-leafvine-drape-i1/1",
        "status": "REJECT-RAILS-LEAF-GLYPHS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": grammar.topology,
        "determinism": "analytic vines plus direct vector anatomy; no RNG/noise/grain/stamps",
        "native_builder_seconds": round(elapsed, 6),
        "within_3_second_budget": elapsed <= 3.0,
        "owner_coverage": {
            "A": round(float(np.mean(owners["A"] > 0.08)), 6),
            "B": round(float(np.mean(owners["B"] > 0.08)), 6),
            "angle_delta_mean": round(float(delta.mean()), 6),
            "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        },
        "causal_marks": [
            {"name": name, "bank": bank,
             "coverage": round(float(np.mean(mask > 0.08)), 6)}
            for name, mask, bank in grammar.marks
        ],
        "spec_stats": {
            label: {"min": int(c.min()), "max": int(c.max()),
                    "std": round(float(c.std()), 6),
                    "unique_values": int(np.unique(c).size)}
            for label, c in zip(("M", "R", "Cc"), cv2.split(spec))
        },
        "spec_correlations": {
            "M_R": round(float(corr[0, 1]), 6),
            "M_Cc": round(float(corr[0, 2]), 6),
            "R_Cc": round(float(corr[1, 2]), 6),
        },
        "files": {key: {"path": path.name, "sha256": _sha(path)}
                  for key, path in paths.items()},
    }
    (output / "manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-leafvine-drape-i1: 0 pending studies advanced"


if __name__ == "__main__":
    render_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "leafvine_drape_i1"
    )


__all__ = [
    "ID", "Grammar", "clear_cache", "debug_angle_pair", "debug_grammar",
    "install_into_engine", "owner_unions", "render_evidence", "render_native",
]
