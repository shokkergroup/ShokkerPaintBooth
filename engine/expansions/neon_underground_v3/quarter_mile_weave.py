"""Quarter-Mile Weave — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick QMW-P2 / owner screen 2026-08-27: the first v3
attempt was rejected because its uniform weave became wallpaper while broad
sinusoidal M/R/Cc bands became macro panels.  This rebuild authors only local
8-16px cells and at-most-two-cell slip packets.  Every visible and material
response comes from that fine textile history; nothing is registered live.
Owner verdict remains "Claude's rebuild has failed miserably." Audit movement:
rejected/unscored P1 -> deterministic ~1.5s P2, eleven anatomy families,
M/R/Cc std 82.790/83.301/83.261, 461 material triples, and passing 128/64
contacts. Official M7 is N/A until an isolated scorer exists, not fabricated.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np

from engine.paint_v2 import neon_material_core_v3 as core


ID = "neon2_quarter_mile_weave"
NAME = "Quarter-Mile Weave"
SEED = 21027


def _diamond(local_x: np.ndarray, local_y: np.ndarray, cx: float, cy: float, radius: float) -> np.ndarray:
    return np.clip(1.0 - (np.abs(local_x - cx) + np.abs(local_y - cy)) / float(radius), 0.0, 1.0)


def _make_cell_history(ny: int, nx: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Author manufacturing events on the fine-cell lattice.

    Event extents are one cell except local slip/pickup pairs, which span at
    most two 16px cells.  The grid is only a state ledger: no cell border is
    painted, and row/column offsets prevent a recoverable global checker.
    """
    tier = rng.integers(0, 8, size=(ny, nx), dtype=np.uint8)
    skew = rng.uniform(-0.20, 0.20, size=(ny, nx)).astype(np.float32)
    twist = rng.uniform(-0.14, 0.14, size=(ny, nx)).astype(np.float32)
    warp_center = rng.uniform(0.28, 0.43, size=(ny, nx)).astype(np.float32)
    weft_center = rng.uniform(0.57, 0.72, size=(ny, nx)).astype(np.float32)
    warp_width = rng.uniform(0.25, 0.34, size=(ny, nx)).astype(np.float32)
    weft_width = rng.uniform(0.25, 0.34, size=(ny, nx)).astype(np.float32)
    angle = np.clip(rng.normal(-0.38, 0.27, size=(ny, nx)), -0.82, 0.18).astype(np.float32)
    mode = rng.integers(0, 3, size=(ny, nx), dtype=np.uint8)
    warp_weight = np.where(mode == 2, 0.30, 1.0).astype(np.float32)
    weft_weight = np.where(mode == 1, 0.30, 1.0).astype(np.float32)
    over = rng.integers(0, 2, size=(ny, nx), dtype=np.uint8)

    slip = np.zeros((ny, nx), np.float32)
    slip_direction = np.zeros((ny, nx), np.float32)
    slip_events = int(round(ny * nx * 0.105))
    for _ in range(slip_events):
        y = int(rng.integers(1, ny - 1))
        x = int(rng.integers(1, nx - 2))
        direction = -1 if rng.random() < 0.22 else 1
        strength = float(rng.uniform(0.38, 1.0))
        steps = int(rng.integers(1, 3))
        for step in range(steps):
            py = int(np.clip(y + (step if rng.random() < 0.18 else 0) * int(rng.choice((-1, 1))), 0, ny - 1))
            px = int(np.clip(x + direction * step, 0, nx - 1))
            if strength > slip[py, px]:
                slip[py, px] = strength
                slip_direction[py, px] = float(direction)

    # Tiny 2x2 torn micro-check fragments are the only literal check cue.
    microcheck = np.zeros((ny, nx), np.int8)
    check_events = int(round(ny * nx * 0.017))
    for _ in range(check_events):
        y = int(rng.integers(0, ny - 1))
        x = int(rng.integers(0, nx - 1))
        phase = int(rng.choice((-1, 1)))
        microcheck[y, x] = phase
        microcheck[y, x + 1] = -phase
        microcheck[y + 1, x] = -phase
        microcheck[y + 1, x + 1] = phase

    broken = (rng.random((ny, nx)) < (0.026 + 0.135 * slip)).astype(np.float32)
    broken_axis = rng.integers(0, 2, size=(ny, nx), dtype=np.uint8)
    timing = (rng.random((ny, nx)) < (0.019 + 0.058 * slip)).astype(np.float32)
    bridge = ((rng.random((ny, nx)) < (0.046 + 0.128 * slip)) & (broken < 0.5)).astype(np.float32)
    knot = (rng.random((ny, nx)) < (0.026 + 0.035 * (1.0 - slip))).astype(np.float32)
    ladder = (rng.random((ny, nx)) < (0.014 + 0.026 * slip)).astype(np.float32)

    pickup = np.zeros((ny, nx), np.float32)
    pickup_events = int(round(ny * nx * 0.035))
    for _ in range(pickup_events):
        y = int(rng.integers(0, ny))
        x = int(rng.integers(0, nx - 1))
        strength = float(rng.uniform(0.45, 1.0))
        pickup[y, x] = max(pickup[y, x], strength)
        if rng.random() < 0.48:
            pickup[y, x + 1] = max(pickup[y, x + 1], strength * float(rng.uniform(0.64, 0.92)))

    return {
        "tier": tier,
        "skew": skew,
        "twist": twist,
        "warp_center": warp_center,
        "weft_center": weft_center,
        "warp_width": warp_width,
        "weft_width": weft_width,
        "angle": angle,
        "warp_weight": warp_weight,
        "weft_weight": weft_weight,
        "over": over,
        "slip": slip,
        "slip_direction": slip_direction,
        "microcheck": microcheck,
        "broken": broken,
        "broken_axis": broken_axis,
        "timing": timing,
        "bridge": bridge,
        "knot": knot,
        "ladder": ladder,
        "pickup": pickup,
    }


def build(size: int = core.WORK, seed: int = SEED) -> core.PilotResult:
    if int(size) < 256:
        raise ValueError("Quarter-Mile Weave work size must be at least 256")
    rng = core.seeded(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)

    # One cell is exactly 16 native pixels at standard resolution.  Independent
    # row/column offsets and per-cell skew break global grid recovery while
    # preserving a genuinely woven local crossing in every cell.
    pitch = max(4, core.native_px(16.0, size))
    ny = int(np.ceil(size / pitch)) + 6
    nx = int(np.ceil(size / pitch)) + 6
    history = _make_cell_history(ny, nx, rng)
    row_shift = rng.uniform(-0.34, 0.34, size=ny).astype(np.float32)
    col_shift = rng.uniform(-0.28, 0.28, size=nx).astype(np.float32)

    row0 = np.floor(yy / pitch).astype(np.int32) % ny
    warped_x = xx + row_shift[row0] * pitch
    col = np.floor(warped_x / pitch).astype(np.int32) % nx
    warped_y = yy + col_shift[col] * pitch
    row = np.floor(warped_y / pitch).astype(np.int32) % ny
    warped_x = xx + row_shift[row] * pitch
    col = np.floor(warped_x / pitch).astype(np.int32) % nx

    local_x = np.mod(warped_x, pitch) / float(pitch)
    local_y = np.mod(warped_y, pitch) / float(pitch)
    state = {name: values[row, col] for name, values in history.items()}

    slip = state["slip"]
    local_x = np.mod(
        local_x
        + state["skew"] * (local_y - 0.5)
        + state["slip_direction"] * slip * 0.42 * (local_y - 0.5),
        1.0,
    )
    local_y = np.mod(local_y + state["twist"] * (local_x - 0.5) - slip * 0.12 * (local_x - 0.5), 1.0)

    local_angle = state["angle"] + state["slip_direction"] * slip * 0.24
    cos_a = np.cos(local_angle)
    sin_a = np.sin(local_angle)
    dx = local_x - 0.5
    dy = local_y - 0.5
    local_x = 0.5 + cos_a * dx - sin_a * dy
    local_y = 0.5 + sin_a * dx + cos_a * dy

    warp = np.exp(-((np.abs(local_x - state["warp_center"]) / state["warp_width"]) ** 4)).astype(np.float32)
    weft = np.exp(-((np.abs(local_y - state["weft_center"]) / state["weft_width"]) ** 4)).astype(np.float32)
    over = state["over"].astype(np.float32)
    warp_face = warp * state["warp_weight"] * (0.52 + 0.48 * over)
    weft_face = weft * state["weft_weight"] * (0.52 + 0.48 * (1.0 - over))
    crossing = np.sqrt(np.clip(warp_face * weft_face, 0.0, 1.0))
    woven = np.clip(np.maximum(warp_face, weft_face), 0.0, 1.0)

    broken_axis = state["broken_axis"].astype(np.float32)
    warp_gap_profile = np.exp(-((local_y - 0.50) / 0.25) ** 4).astype(np.float32)
    weft_gap_profile = np.exp(-((local_x - 0.50) / 0.25) ** 4).astype(np.float32)
    broken_gap = state["broken"] * (
        (1.0 - broken_axis) * warp_face * warp_gap_profile
        + broken_axis * weft_face * weft_gap_profile
    )
    end_y = np.maximum(
        np.exp(-((local_y - 0.20) / 0.20) ** 4),
        np.exp(-((local_y - 0.80) / 0.20) ** 4),
    ).astype(np.float32)
    end_x = np.maximum(
        np.exp(-((local_x - 0.20) / 0.20) ** 4),
        np.exp(-((local_x - 0.80) / 0.20) ** 4),
    ).astype(np.float32)
    broken_ends = state["broken"] * (
        (1.0 - broken_axis) * warp_face * end_y
        + broken_axis * weft_face * end_x
    )

    timing_shape = np.clip(1.0 - np.abs(local_y - (0.25 + 0.50 * local_x)) / 0.24, 0.0, 1.0)
    timing = state["timing"] * timing_shape
    ladder_shape = np.maximum(
        _diamond(local_x, local_y, 0.31, 0.36, 0.31),
        _diamond(local_x, local_y, 0.69, 0.64, 0.31),
    )
    ladder = state["ladder"] * ladder_shape
    pickup_shape = np.clip(1.0 - np.abs(local_y - (0.56 + 0.22 * (local_x - 0.5))) / 0.29, 0.0, 1.0)
    pickup_shape *= core.smoothstep(0.05, 0.20, local_x) * (1.0 - core.smoothstep(0.80, 0.95, local_x))
    pickup = state["pickup"] * pickup_shape
    bridge_shape = np.clip(1.0 - np.abs((local_x - 0.5) + (local_y - 0.5)) / 0.30, 0.0, 1.0)
    bridge = state["bridge"] * bridge_shape * (0.35 + 0.65 * woven)
    knot = state["knot"] * _diamond(local_x, local_y, 0.50, 0.50, 0.34)
    microcheck = np.abs(state["microcheck"].astype(np.float32)) * woven
    slip_packet = slip * (0.45 * woven + 0.55 * crossing)
    lead_center = np.where(state["slip_direction"] >= 0.0, 0.22, 0.78).astype(np.float32)
    slip_lip = slip * np.exp(-((local_x - lead_center) / 0.20) ** 4).astype(np.float32) * (0.34 + 0.66 * woven)

    tier_values = np.asarray((0.22, 0.31, 0.41, 0.52, 0.63, 0.74, 0.86, 1.00), np.float32)
    tier = tier_values[state["tier"].astype(np.int32)]
    check_warm = (state["microcheck"] > 0).astype(np.float32)
    check_cool = (state["microcheck"] < 0).astype(np.float32)

    # Deep technical cloth first, then its segmented red/violet warp and weft.
    # Local check fragments, damage and encapsulation remain visibly distinct.
    paint = np.zeros((size, size, 3), np.float32)
    paint[:] = (0.020, 0.012, 0.028)
    warp_energy = warp_face * (0.10 + 0.40 * tier) * (0.86 + 0.25 * slip)
    weft_energy = weft_face * (0.09 + 0.34 * (1.0 - 0.42 * tier)) * (0.88 + 0.22 * slip)
    paint += warp_energy[..., None] * np.asarray((0.79, 0.008, 0.105), np.float32)
    paint += weft_energy[..., None] * np.asarray((0.42, 0.014, 0.58), np.float32)
    paint += crossing[..., None] * (0.04 + 0.31 * tier)[..., None] * np.asarray((1.00, 0.36, 0.12), np.float32)
    paint += (check_warm * woven)[..., None] * np.asarray((0.48, 0.15, 0.01), np.float32)
    paint += (check_cool * woven)[..., None] * np.asarray((0.02, 0.20, 0.55), np.float32)
    paint += slip_packet[..., None] * np.asarray((0.17, 0.015, 0.22), np.float32)
    warm_slip = (state["slip_direction"] >= 0.0).astype(np.float32) * slip_lip
    cool_slip = (state["slip_direction"] < 0.0).astype(np.float32) * slip_lip
    paint += warm_slip[..., None] * np.asarray((0.72, 0.03, 0.24), np.float32)
    paint += cool_slip[..., None] * np.asarray((0.10, 0.30, 0.88), np.float32)

    paint *= 1.0 - 0.88 * broken_gap[..., None]
    paint *= 1.0 - 0.76 * pickup[..., None]
    paint += broken_ends[..., None] * np.asarray((0.92, 0.03, 0.22), np.float32) * 0.75
    paint += timing[..., None] * np.asarray((0.76, 0.90, 1.00), np.float32) * 0.82
    paint += ladder[..., None] * np.asarray((1.00, 0.46, 0.04), np.float32) * 0.86
    paint += bridge[..., None] * np.asarray((0.08, 0.46, 1.00), np.float32) * 0.84
    paint += knot[..., None] * np.asarray((1.00, 0.90, 0.58), np.float32)
    core.add_glow(paint, bridge, (0.05, 0.22, 1.0), 9.0, 0.21, size)
    core.add_glow(paint, timing + knot, (0.62, 0.76, 1.0), 8.0, 0.18, size)
    core.add_glow(paint, slip_lip, (0.55, 0.02, 0.28), 8.0, 0.16, size)
    paint = np.clip(paint, 0.0, 1.0)

    damage = np.clip(np.maximum.reduce((broken_gap, timing, pickup)), 0.0, 1.0)
    intact_laminate = np.clip(0.58 * woven + 0.48 * crossing + 0.42 * bridge - 0.72 * damage, 0.0, 1.0)

    # Independent questions about the same local cells—no macro carrier and no
    # unrelated texture field.  Cell tier and continuous thread profiles give
    # each feature many responses before the shared eight-tier quantizer.
    metal_score = (
        0.18 * woven
        + 0.48 * warp_face * tier
        + 0.34 * crossing
        + 0.88 * knot
        + 0.69 * timing
        + 0.54 * broken_ends
        + 0.37 * ladder
        + 0.71 * slip_lip
        - 0.44 * pickup
    )
    rough_score = (
        0.19 * woven
        + 0.58 * slip_packet
        + 0.92 * broken_gap
        + 1.05 * pickup
        + 0.46 * timing
        + 0.28 * ladder
        - 0.31 * slip_lip
        - 0.63 * bridge
        - 0.42 * knot
    )
    coat_score = (
        0.16
        + 0.87 * intact_laminate
        + 0.93 * bridge
        + 0.39 * crossing
        - 0.94 * pickup
        - 0.83 * broken_gap
        - 0.46 * timing
        - 0.31 * slip_packet
        - 0.47 * slip_lip
    )
    spec = core.pack_material(metal_score, rough_score, coat_score)

    masks = {
        "segmented weave cells": woven,
        "local slip packets": slip_packet,
        "burnished slip lips": slip_lip,
        "broken thread gaps": broken_gap,
        "exposed thread ends": broken_ends,
        "timing hairlines": timing,
        "micro-ladders": ladder,
        "rubber pickup": pickup,
        "resin bridges": bridge,
        "reflective knots": knot,
        "micro-check cues": microcheck,
    }
    geometry = (
        core.GeometryMark("warp/weft cell", 16.0, int(ny * nx)),
        core.GeometryMark("two-cell local slip packet", 32.0, int(np.count_nonzero(history["slip"]))),
        core.GeometryMark("burnished slip lip", 8.0, int(np.count_nonzero(history["slip"]))),
        core.GeometryMark("broken thread gap", 12.0, int(np.count_nonzero(history["broken"]))),
        core.GeometryMark("exposed thread end", 8.0, int(np.count_nonzero(history["broken"])) * 2),
        core.GeometryMark("timing hairline", 8.0, int(np.count_nonzero(history["timing"]))),
        core.GeometryMark("two-stage micro-ladder", 10.0, int(np.count_nonzero(history["ladder"]))),
        core.GeometryMark("rubber pickup packet", 32.0, int(np.count_nonzero(history["pickup"]))),
        core.GeometryMark("resin bridge", 10.0, int(np.count_nonzero(history["bridge"]))),
        core.GeometryMark("reflective stitch knot", 9.0, int(np.count_nonzero(history["knot"]))),
        core.GeometryMark("torn 2x2 micro-check cell", 16.0, int(np.count_nonzero(history["microcheck"]))),
    )
    return core.PilotResult(
        finish_id=ID,
        display_name=NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "metalized warp faces, reflective knots, timing hairs, micro-ladders, and exposed thread ends",
            "R": "local slip, broken fibers, timing cuts, and attached rubber pickup; bridges and knots stay smooth",
            "Cc": "intact woven laminate and resin bridges rise while slip damage, pickup, and thread rupture fall",
        },
        carrier="locally speed-sheared fluorescent 16px micro-check textile laminated under clear",
        vetoes=(
            "flags",
            "checker banners",
            "full-width ribbons",
            "Christmas trees",
            "lanes",
            "uniform checker wallpaper",
            "macro panels",
            "authored primitives over 32px",
        ),
    )


def authored() -> tuple[np.ndarray, np.ndarray]:
    result = core.timed_result(build)
    return core.resize_result(result)


def _edge_audit(paint: np.ndarray) -> dict[str, object]:
    luma = np.asarray(paint, np.float32) @ np.asarray((0.2126, 0.7152, 0.0722), np.float32)
    gx = np.pad(np.abs(np.diff(luma, axis=1)), ((0, 0), (0, 1)))
    gy = np.pad(np.abs(np.diff(luma, axis=0)), ((0, 1), (0, 0)))
    gradient = np.hypot(gx, gy)
    band = max(4, luma.shape[0] // 64)
    edge = np.concatenate((gradient[:band].ravel(), gradient[-band:].ravel(), gradient[:, :band].ravel(), gradient[:, -band:].ravel()))
    ratio = float(edge.mean() / max(float(gradient.mean()), 1e-7))
    return {"edge_to_global_gradient_ratio": round(ratio, 6), "pass": bool(0.50 <= ratio <= 1.50)}


def _picker_audit(paint: np.ndarray) -> dict[str, object]:
    rgb = np.clip(np.asarray(paint, np.float32), 0.0, 1.0)
    contacts: dict[str, object] = {}
    passed = True
    for size in (128, 64):
        reduced = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)
        luma = reduced @ np.asarray((0.2126, 0.7152, 0.0722), np.float32)
        chroma = reduced[..., 0] - reduced[..., 1]
        luma_std = float(luma.std())
        chroma_std = float(chroma.std())
        contact_pass = bool(luma_std >= 0.015 and chroma_std >= 0.025)
        contacts[str(size)] = {
            "luma_std": round(luma_std, 6),
            "red_green_chroma_std": round(chroma_std, 6),
            "pass": contact_pass,
        }
        passed = passed and contact_pass
    return {"contacts": contacts, "pass": bool(passed)}


def main() -> int:
    output = Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "quarter_mile_weave"
    result = core.timed_result(build)
    manifest = core.render_evidence(result, output)
    rerun_start = time.perf_counter()
    rerun = build()
    rerun_seconds = time.perf_counter() - rerun_start
    stats = core.material_stats(result.spec)
    geometry = manifest["geometry_stats"]
    edge = _edge_audit(result.paint)
    picker = _picker_audit(result.paint)
    unique_triples = int(np.unique(result.spec.reshape(-1, 3), axis=0).shape[0])
    correlations = stats["correlation"]
    gates = {
        "builder_under_3s": bool(result.elapsed_seconds <= 3.0),
        "deterministic_paint": bool(np.array_equal(result.paint, rerun.paint)),
        "deterministic_spec": bool(np.array_equal(result.spec, rerun.spec)),
        "rerun_under_3s": bool(rerun_seconds <= 3.0),
        "five_plus_anatomy_families": bool(geometry["family_count"] >= 5),
        "all_geometry_8_to_32_native": bool(geometry["fine_8_32_fraction"] == 1.0),
        "eight_tiers_each": bool(all(value == 8 for value in stats["tier_count"].values())),
        "material_std_at_least_30": bool(all(value >= 30.0 for value in stats["std"].values())),
        "channels_not_copied_or_inverse": bool(all(abs(value) < 0.90 for value in correlations.values())),
        "many_material_triples": bool(unique_triples >= 128),
        "edge_continuity": bool(edge["pass"]),
        "picker_128_64_survival": bool(picker["pass"]),
    }
    audit = {
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": ID,
        "builder_seconds": round(float(result.elapsed_seconds), 6),
        "rerun_seconds": round(float(rerun_seconds), 6),
        "material_stats": stats,
        "unique_mrc_triples": unique_triples,
        "geometry": geometry,
        "causal_mask_coverage": manifest["causal_mask_coverage"],
        "edge_continuity": edge,
        "picker_survival": picker,
        "mechanical_gates": gates,
        "mechanical_gates_pass": bool(all(gates.values())),
        "official_m7": None,
        "official_m7_note": "Unwired isolated pilot; no registry/workbook record exists, so no composite is fabricated.",
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0 if audit["mechanical_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
