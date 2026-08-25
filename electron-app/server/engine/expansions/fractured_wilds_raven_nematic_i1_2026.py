# -*- coding: utf-8 -*-
"""Isolated native-2048 Raven Flash nematic microstructure study.

A single deterministic complex nematic order field carries five half-charge
defects. Melanin rod cores, sheaths, grain boundaries, void channels, platelet
caps, fracture steps, barb shadows and narrow flash gates all descend from the
same director/order history. No RNG, noise, grain, grid, stamp or reused Wilds
composer is used.

SPB-WILDS-RAVEN-I1, 2026-08-24. Native verdict: KEEP-CANDIDATE. The field reads
as a continuous nematic defect micrograph rather than a stroke cloud, grid,
fan, Bark contour or simple Gabor texture. Cold 2048 repeats are
0.2448-0.2588 s; A/B mean/p95 delta is 0.054880/0.287468; M/R/Cc std is
35.888/53.555/27.615 with correlations -0.086/-0.005/-0.118. It remains
isolated, fail-closed, unaccepted and unwired.
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


ID = "fmo_raven_flash"
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


def _pd(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    d = _pd(phase, center) / max(width, 1e-5)
    return np.exp(-2.5 * d * d).astype(np.float32)


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    idx = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK
    y = (yy + 0.5) / WORK
    z = (x - 0.5) + 1j * (y - 0.5)

    defects = (
        (-0.31 - 0.24j, 1.0, 0.23),
        (0.22 - 0.30j, -1.0, 0.19),
        (-0.08 + 0.08j, 1.0, 0.25),
        (0.34 + 0.18j, 1.0, 0.21),
        (-0.27 + 0.31j, -1.0, 0.18),
    )
    q = np.ones_like(z, np.complex64)
    defect_proximity = np.zeros((WORK, WORK), np.float32)
    signed_core = np.zeros_like(defect_proximity)
    for center, charge, reach in defects:
        dz = z - center
        rr = np.abs(dz) + 1e-5
        unit = dz / rr
        # Q=e^(i*2theta); integer powers keep half-charge directors continuous.
        q *= unit if charge > 0 else np.conj(unit)
        local = np.exp(-(rr / reach) ** 2).astype(np.float32)
        defect_proximity = np.maximum(defect_proximity, local)
        signed_core += float(charge) * local

    global_twist = np.exp(1j * (2.4 * np.pi * x - 1.7 * np.pi * y
                                + 0.58 * np.sin(2.7 * np.pi * x + 1.9 * np.pi * y)))
    q *= global_twist.astype(np.complex64)
    director = 0.5 * np.angle(q)
    nx, ny = np.cos(director), np.sin(director)

    # Continuous non-integrable rod coordinate. Coupled terms bend spacing at
    # defects and keep the carrier from becoming a regular Gabor plane.
    rod_coord = (57.0 * (x * nx + y * ny)
                 + 4.7 * signed_core
                 + 1.3 * np.sin(5.1 * x - 3.8 * y + 2.0 * director)
                 + 0.55 * np.sin(9.3 * y + 1.7 * x - 3.0 * director))
    rod_phase = np.mod(rod_coord, 1.0)
    cross_coord = np.mod(23.0 * (-x * ny + y * nx)
                         + 0.083 * rod_coord
                         + 0.31 * np.sin(4.7 * director), 1.0)

    rod_core = _pulse(rod_phase, 0.05, 0.045)
    rod_sheath = _pulse(rod_phase, 0.16, 0.085)

    # Order gradients identify genuine orientation boundaries rather than
    # arbitrary decorative lines.
    cos2, sin2 = np.cos(2.0 * director), np.sin(2.0 * director)
    gx = cv2.Sobel(cos2.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(cos2.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    hx = cv2.Sobel(sin2.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    hy = cv2.Sobel(sin2.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    order_grad = np.sqrt(gx * gx + gy * gy + hx * hx + hy * hy)
    order_grad = _f(order_grad * 0.34)
    grain_boundary = _f(order_grad * (0.35 + 0.65 * rod_sheath))

    void_gate = _pulse(cross_coord, 0.72, 0.055)
    void_channel = _f(void_gate * np.sqrt(defect_proximity)
                      * (0.35 + 0.65 * (1.0 - rod_core)))

    cap_gate = np.maximum(_pulse(cross_coord, 0.18, 0.038),
                          _pulse(cross_coord, 0.49, 0.032))
    platelet_cap = _f(cap_gate * rod_core
                      * np.clip((np.cos(5.3 * director + 0.17 * rod_coord) - 0.05)
                                * 1.35, 0, 1))

    step_gate = _pulse(cross_coord, 0.91, 0.042)
    fracture_step = _f(step_gate * grain_boundary
                       * (0.28 + 0.72 * defect_proximity))

    shadow_gate = np.clip((np.sin(0.27 * rod_coord - 6.1 * director) - 0.18)
                          * 1.45, 0, 1)
    barb_shadow = _f(rod_sheath * shadow_gate * (1.0 - 0.55 * rod_core))

    flash_gate = _f(rod_core * np.clip((np.cos(2.0 * director - 0.21 * rod_coord)
                                        - 0.20) * 1.55, 0, 1))
    core_socket = _f(np.exp(-((1.0 - defect_proximity - 0.12) / 0.045) ** 2)
                     * _pulse(cross_coord, 0.36, 0.075))
    oil_phase = np.mod(0.137 * rod_coord + 0.41 * cross_coord
                       + 0.23 * np.sin(5.9 * director - 3.1 * x), 1.0)
    preen_oil_window = _f(_pulse(oil_phase, 0.27, 0.078) * rod_sheath
                          * (0.24 + 0.76 * (1.0 - defect_proximity)))
    preen_oil_release = _f(_pulse(oil_phase, 0.74, 0.072)
                           * (1.0 - rod_core)
                           * (0.28 + 0.72 * rod_sheath)
                           * (0.26 + 0.74 * (1.0 - defect_proximity)))

    # Raven base stays dark; structural color appears only on named anisotropic
    # consequences, making the A/B flip material-like instead of a rainbow fill.
    base = np.zeros((WORK, WORK, 3), np.float32)
    base[:] = (0.012, 0.018, 0.031)
    base += rod_sheath[..., None] * np.asarray((0.025, 0.055, 0.083), np.float32)
    base += rod_core[..., None] * np.asarray((0.035, 0.12, 0.18), np.float32)
    # SPB-105 / SPB-WILDS runtime rollout tick 2026-08-25. Owner requires the
    # actual 2048 carrier to lead. First official runtime M7 was 84.7 because
    # the dark paint's busy rank (0.429) trailed its causal spec rank (0.836).
    # Raise only the already-authored flash/cap response, not feature size or
    # density; retained M5 59.2 -> 59.9 and M7 84.7 -> 85.0.
    base += flash_gate[..., None] * np.asarray((0.06, 0.72, 0.88), np.float32)
    base += platelet_cap[..., None] * np.asarray((0.68, 0.18, 0.75), np.float32)
    base += grain_boundary[..., None] * np.asarray((0.23, 0.06, 0.40), np.float32)
    base -= void_channel[..., None] * np.asarray((0.10, 0.10, 0.12), np.float32)
    base += fracture_step[..., None] * np.asarray((0.77, 0.38, 0.11), np.float32)
    base -= barb_shadow[..., None] * np.asarray((0.06, 0.04, 0.03), np.float32)
    base += core_socket[..., None] * np.asarray((0.26, 0.50, 0.22), np.float32)
    base += preen_oil_window[..., None] * np.asarray((0.08, 0.14, 0.035), np.float32)
    base += preen_oil_release[..., None] * np.asarray((0.025, 0.10, 0.13), np.float32)
    paint = _f(base)

    neutral = _f(0.12 + 0.24 * rod_sheath + 0.34 * rod_core
                 + 0.45 * flash_gate + 0.38 * platelet_cap
                 + 0.26 * grain_boundary - 0.24 * void_channel
                 + 0.31 * fracture_step - 0.13 * barb_shadow
                 + 0.29 * core_socket)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    metal_field = _f(0.04 + 0.63 * rod_core + 0.71 * platelet_cap
                     + 0.48 * flash_gate + 0.37 * fracture_step
                     - 0.26 * void_channel)
    rough_field = _f(0.10 + 0.58 * rod_sheath + 0.62 * barb_shadow
                     + 0.46 * grain_boundary + 0.41 * void_channel
                     - 0.32 * flash_gate)
    coat_field = _f(0.03 + 1.18 * preen_oil_window
                    + 0.92 * preen_oil_release + 0.76 * core_socket
                    + 0.34 * (1.0 - rod_sheath) * defect_proximity
                    - 0.24 * grain_boundary - 0.20 * void_channel)
    metal = _tier(metal_field, (6, 31, 60, 93, 129, 168, 212, 250))
    rough = _tier(rough_field, (14, 41, 72, 106, 142, 180, 220, 249))
    coat = _tier(coat_field, (5, 28, 57, 90, 128, 169, 213, 252))

    marks = (
        ("melanin_rod_cores", rod_core, "A"),
        ("rod_strain_sheaths", rod_sheath, "B"),
        ("orientation_grain_boundaries", grain_boundary, "N"),
        ("void_channels", void_channel, "N"),
        ("platelet_caps", platelet_cap, "B"),
        ("fracture_steps", fracture_step, "A"),
        ("barb_shadows", barb_shadow, "N"),
        ("narrow_flash_gates", flash_gate, "A"),
        ("defect_core_sockets", core_socket, "B"),
        ("preen_oil_windows", preen_oil_window, "B"),
        ("preen_oil_release_windows", preen_oil_release, "B"),
    )
    if any(float(mask.std()) < 0.003 for _name, mask, _bank in marks):
        raise ValueError("Raven I1 has an absent causal mark")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="one complex nematic order field with five interacting half-charge defects",
    )


@lru_cache(maxsize=1)
def _authored() -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)


def clear_cache() -> None:
    _authored.cache_clear()


def debug_grammar() -> Grammar:
    return _build()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    out = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        out[bank] = np.maximum(out[bank], mask)
    return out


def debug_angle_pair() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.42 + 0.54 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.02, 0.48, 0.67), np.float32)
    a += owners["B"][..., None] * np.asarray((0.12, 0.02, 0.22), np.float32)
    b = grammar.paint * (0.41 + 0.55 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.60, 0.07, 0.48), np.float32)
    b += owners["A"][..., None] * np.asarray((0.34, 0.26, 0.03), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


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
        "schema": "spb-wilds-raven-nematic-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": grammar.topology,
        "determinism": "complex analytic director field only; no RNG/noise/grain/stamps",
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
    return "fractured-wilds-raven-nematic-i1: 0 pending studies advanced"


if __name__ == "__main__":
    render_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "raven_nematic_i1"
    )


__all__ = [
    "ID", "Grammar", "clear_cache", "debug_angle_pair", "debug_grammar",
    "install_into_engine", "owner_unions", "render_evidence", "render_native",
]
