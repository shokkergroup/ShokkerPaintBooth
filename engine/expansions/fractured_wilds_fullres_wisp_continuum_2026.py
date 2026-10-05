# -*- coding: utf-8 -*-
"""Native-2048 Will-o'-Wisp continuum study, isolated and unwired.

One deterministic Clifford trajectory owns the entire finish.  Density,
velocity, curvature, return visits and escape states of that same trajectory
cause the hot core, opposed wakes, hooked turns, localized orbit satellites,
interference collars and extinguished gaps.  There is no grid, tile, stamp,
particle scatter, sampled stochastic field, or texture grain.

SPB-WILDS-WISP-C1, tick 1, 2026-08-24.  Owner verdict addressed: full native
2048 art is the acceptance target; differently named micro-glyph matrices are
still lazy.  Native review verdict: REJECT.  The single trajectory becomes one
oversized sparse gesture with too much empty ground, and the authored build
also measured 3.548379 s.  This is a frozen negative study, not a candidate;
prior M7 is not applicable and no production acceptance or wiring is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np


S = 2048
FID = "fc_will_o_wisp"
CALM_SPEC = np.asarray((12, 218, 10), np.float32)


@dataclass(frozen=True)
class WispGrammar:
    marks: tuple[tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    explicit_spec: tuple[np.ndarray, np.ndarray, np.ndarray]
    topology: str


def _trajectory(count: int = 350_000, burn: int = 1_200):
    """Return one continuous asymmetric Clifford trajectory."""
    # This parameter set produces a connected, folded attractor rather than a
    # rotational rosette.  The initial state is literal and immutable.
    a, b, c, d = -1.4, 1.6, 1.0, .7
    x, y = .071, -.113
    xs = np.empty(count, np.float32)
    ys = np.empty(count, np.float32)
    write = 0
    for index in range(count + burn):
        next_x = math.sin(a * y) + c * math.cos(a * x)
        next_y = math.sin(b * x) + d * math.cos(b * y)
        x, y = next_x, next_y
        if index >= burn:
            xs[write] = x
            ys[write] = y
            write += 1
    return xs, ys


def _map_to_canvas(xs, ys):
    """Bend the attractor into an asymmetric rising apparition."""
    xlo, xhi = np.percentile(xs, (.08, 99.92))
    ylo, yhi = np.percentile(ys, (.08, 99.92))
    u = np.clip((xs - xlo) / max(xhi - xlo, 1e-6) * 2.0 - 1.0, -1.08, 1.08)
    v = np.clip((ys - ylo) / max(yhi - ylo, 1e-6) * 2.0 - 1.0, -1.08, 1.08)

    # A continuous shear/taper makes one leaning wisp body.  It does not add
    # any extra trajectory or image-space decoration.
    taper = .72 + .23 * (v + 1.0) * .5
    px = (S * .50 + S * .355 *
          (u * taper + .115 * np.sin(2.1 * v) + .055 * u * v))
    py = (S * .51 + S * .405 *
          (v + .105 * u * u - .07 * np.sin(1.7 * u)))
    return px.astype(np.float32), py.astype(np.float32), u, v


def _deposit(px, py, weights=None):
    ix = np.rint(px).astype(np.int32)
    iy = np.rint(py).astype(np.int32)
    valid = (ix >= 0) & (ix < S) & (iy >= 0) & (iy < S)
    out = np.zeros((S, S), np.float32)
    if weights is None:
        np.add.at(out, (iy[valid], ix[valid]), 1.0)
    else:
        np.add.at(out, (iy[valid], ix[valid]), np.asarray(weights, np.float32)[valid])
    return out


def _normalize(field, percentile=99.65):
    active = field[field > 0]
    if not active.size:
        return np.zeros_like(field, np.float32)
    scale = float(np.percentile(active, percentile))
    return np.clip(field / max(scale, 1e-6), 0, 1).astype(np.float32)


def _blur(field, sigma):
    return cv2.GaussianBlur(field, (0, 0), float(sigma), borderType=cv2.BORDER_REFLECT)


def _u8(field):
    return np.clip(field * 255.0, 0, 255).astype(np.uint8)


def _colourize_collar(collar, phase):
    """Give the one interference film a continuous spectral phase."""
    hue = np.mod(141.0 + 92.0 * phase, 180.0)
    hsv = np.empty((S, S, 3), np.uint8)
    hsv[:, :, 0] = hue.astype(np.uint8)
    hsv[:, :, 1] = np.clip(178 + 72 * collar, 0, 255).astype(np.uint8)
    hsv[:, :, 2] = np.clip(255 * collar, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0


def _build_fc_will_o_wisp() -> WispGrammar:
    xs, ys = _trajectory()
    px, py, state_u, state_v = _map_to_canvas(xs, ys)

    dx = np.gradient(px).astype(np.float32)
    dy = np.gradient(py).astype(np.float32)
    speed = np.sqrt(dx * dx + dy * dy)
    safe_speed = np.maximum(speed, 1e-4)
    nx, ny = -dy / safe_speed, dx / safe_speed

    prev_dx, prev_dy = np.roll(dx, 1), np.roll(dy, 1)
    denom = np.maximum(np.sqrt(prev_dx * prev_dx + prev_dy * prev_dy) * safe_speed, 1e-4)
    turn_cos = np.clip((prev_dx * dx + prev_dy * dy) / denom, -1, 1)
    curvature = np.clip((1.0 - turn_cos) * .5, 0, 1).astype(np.float32)

    # Extinction is a physical escape state: fast, nearly straight transitions
    # do not deposit light.  It is not a cosmetic gate or stochastic dropout.
    speed_hi = float(np.percentile(speed, 81.0))
    curve_lo = float(np.percentile(curvature, 38.0))
    extinguished_state = (speed > speed_hi) & (curvature < curve_lo)
    alive = (~extinguished_state).astype(np.float32)

    dwell = 1.0 / (1.0 + speed / max(float(np.percentile(speed, 46.0)), 1e-4))
    deposition_raw = _deposit(px, py, alive * (.42 + .58 * dwell))
    deposition = _normalize(_blur(deposition_raw, 1.45), 99.35)

    hot_gate = (dwell > np.percentile(dwell, 68.0)).astype(np.float32)
    hot_raw = _deposit(px, py, alive * hot_gate * (.35 + .65 * curvature))
    hot_core = _normalize(_blur(hot_raw, 2.35), 99.2)

    # The twin wake is the same trajectory displaced by its instantaneous
    # normal.  Unequal state-derived offsets stop it becoming two cloned lines.
    offset_a = 7.5 + 4.5 * (state_u + 1.0) * .5
    offset_b = 9.0 + 5.5 * (state_v + 1.0) * .5
    wake_a_raw = _deposit(px + nx * offset_a, py + ny * offset_a,
                          alive * (.32 + .68 * dwell))
    wake_b_raw = _deposit(px - nx * offset_b, py - ny * offset_b,
                          alive * (.28 + .72 * curvature))
    wake_a = _normalize(_blur(wake_a_raw, 1.7), 99.4)
    wake_b = _normalize(_blur(wake_b_raw, 2.0), 99.4)

    hook_gate = (curvature > np.percentile(curvature, 89.0)) & (speed < np.percentile(speed, 84.0))
    hooked_raw = _deposit(px, py, hook_gate.astype(np.float32) * (.2 + .8 * curvature))
    hooked_turns = _normalize(_blur(hooked_raw, 2.05), 99.15)

    extinct_raw = _deposit(px, py, extinguished_state.astype(np.float32))
    extinguished_gaps = _normalize(_blur(extinct_raw, 2.8), 99.0)

    # Interference collars are distance bands around actual hot deposition.
    # They are incomplete wherever the trajectory escaped, so they cannot
    # become a repeated loop field.
    hot_binary = (hot_core > .34).astype(np.uint8)
    outside_distance = cv2.distanceTransform(1 - hot_binary, cv2.DIST_L2, 5)
    collar_envelope = np.exp(-outside_distance / 25.0).astype(np.float32)
    yy, xx = np.indices((S, S), dtype=np.float32)
    collar_phase = np.mod(
        outside_distance / 9.5 + .19 * np.arctan2(yy - S * .51, xx - S * .50),
        1.0,
    )
    interference = collar_envelope * (.5 + .5 * np.cos(2.0 * np.pi * collar_phase))
    interference *= (outside_distance >= 3.5) & (outside_distance <= 31.5)
    interference *= np.clip(1.0 - .72 * extinguished_gaps, 0, 1)
    interference = _normalize(_blur(interference.astype(np.float32), .65), 99.4)

    # Local orbit satellites amplify real recurrence islands of the same
    # trajectory.  Three spatially separated density maxima are windowed; no
    # circle, ellipse, stamp or secondary orbit is drawn.
    recurrence = _normalize(_blur(deposition_raw, 5.2), 99.25)
    coarse = cv2.resize(recurrence, (128, 128), interpolation=cv2.INTER_AREA)
    satellite_window = np.zeros((S, S), np.float32)
    work = coarse.copy()
    anchors = []
    for anchor_index in range(3):
        cy_small, cx_small = np.unravel_index(int(np.argmax(work)), work.shape)
        cx = (cx_small + .5) * (S / 128.0)
        cy = (cy_small + .5) * (S / 128.0)
        anchors.append((cx, cy))
        angle = .47 + anchor_index * 1.13
        ca, sa = math.cos(angle), math.sin(angle)
        local_x = (xx - cx) * ca + (yy - cy) * sa
        local_y = -(xx - cx) * sa + (yy - cy) * ca
        window = np.exp(-((local_x / (42 + 8 * anchor_index)) ** 4
                          + (local_y / (24 + 5 * anchor_index)) ** 4)).astype(np.float32)
        satellite_window = np.maximum(satellite_window, window)
        cv2.circle(work, (cx_small, cy_small), 18 + anchor_index * 3, 0.0, -1)
    orbit_satellites = _normalize(
        _blur(recurrence * satellite_window * (.35 + .65 * hooked_turns), 1.1), 99.0
    )

    # A return-visit filament is dense recurrence after removing the hot core;
    # it gives the apparition internal tendon-like structure.
    return_visits = _normalize(
        np.clip(recurrence - .52 * hot_core, 0, 1) * np.clip(deposition * 1.4, 0, 1),
        99.25,
    )

    # Native paint: hot ember core, cyan/violet opposed wakes and one spectral
    # film.  Extinguished escape states subtract light rather than add texture.
    base = np.asarray((.006, .008, .020), np.float32)
    paint = np.broadcast_to(base, (S, S, 3)).copy()
    paint += deposition[..., None] * np.asarray((.18, .055, .22), np.float32)
    paint += wake_a[..., None] * np.asarray((.02, .68, .82), np.float32)
    paint += wake_b[..., None] * np.asarray((.63, .035, .78), np.float32)
    paint += hot_core[..., None] * np.asarray((1.05, .26, .025), np.float32)
    paint += (hot_core * hot_core)[..., None] * np.asarray((.82, .83, .28), np.float32)
    paint += hooked_turns[..., None] * np.asarray((1.00, .74, .18), np.float32)
    paint += orbit_satellites[..., None] * np.asarray((.15, .94, .62), np.float32)
    paint += return_visits[..., None] * np.asarray((.18, .20, .66), np.float32)
    paint += _colourize_collar(interference, collar_phase) * interference[..., None] * .72
    paint *= np.clip(1.0 - .74 * extinguished_gaps[..., None]
                     * (1.0 - hot_core[..., None]), .12, 1.0)
    paint = np.clip(1.0 - np.exp(-1.36 * paint), 0, 1).astype(np.float32)

    # M/R/Cc are different physical measurements, not palette copies:
    # M = hot deposition/return metal; R = twin-wake abrasion and extinction;
    # Cc = interference film/orbit satellites.
    metal = np.clip(
        5.0 + 194.0 * hot_core + 104.0 * deposition + 72.0 * hooked_turns
        + 42.0 * return_visits - 28.0 * extinguished_gaps,
        0, 255,
    ).astype(np.uint8)
    rough = np.clip(
        248.0 - 172.0 * wake_a - 136.0 * wake_b - 68.0 * deposition
        + 54.0 * extinguished_gaps + 22.0 * return_visits,
        0, 255,
    ).astype(np.uint8)
    coat = np.clip(
        3.0 + 228.0 * interference + 196.0 * orbit_satellites
        + 62.0 * wake_b + 34.0 * hooked_turns,
        0, 255,
    ).astype(np.uint8)

    marks = (
        ("continuous_trajectory_deposition", _u8(deposition), "A"),
        ("hot_core_dwell_deposition", _u8(hot_core), "A"),
        ("left_normal_twin_wake", _u8(wake_a), "A"),
        ("right_normal_twin_wake", _u8(wake_b), "B"),
        ("high_curvature_hooked_turns", _u8(hooked_turns), "A"),
        ("return_visit_filaments", _u8(return_visits), "B"),
        ("trajectory_interference_collars", _u8(interference), "B"),
        ("localized_recurrence_satellites", _u8(orbit_satellites), "B"),
        ("extinguished_escape_gaps", _u8(extinguished_gaps), "B"),
    )
    grammar = WispGrammar(
        marks, paint, (metal, rough, coat),
        "one continuous Clifford trajectory with state-derived deposition, wakes, turns, returns and extinction",
    )
    _assert_grammar(grammar)
    return grammar


def _assert_grammar(grammar: WispGrammar):
    if grammar.paint.shape != (S, S, 3):
        raise ValueError("Will-o'-Wisp paint is not native 2048")
    if len(grammar.marks) < 8 or {bank for _name, _mask, bank in grammar.marks} != {"A", "B"}:
        raise ValueError("Will-o'-Wisp lacks causal marks or opposed ownership")
    for label, channel in zip(("M", "R", "Cc"), grammar.explicit_spec):
        if channel.shape != (S, S) or channel.dtype != np.uint8:
            raise ValueError(f"{label} is not native uint8")
        if float(channel.std()) < 20.0 or int(channel.max()) - int(channel.min()) < 180:
            raise ValueError(
                f"{label} lacks material range: std={float(channel.std()):.3f}, "
                f"range={int(channel.max()) - int(channel.min())}"
            )


BUILDERS = {FID: _build_fc_will_o_wisp}


@lru_cache(maxsize=1)
def _authored(fid=FID):
    grammar = BUILDERS[fid]()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2)


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid=FID):
    return BUILDERS[fid]()


def owner_unions(grammar: WispGrammar):
    result = {"A": np.zeros((S, S), np.float32), "B": np.zeros((S, S), np.float32)}
    for _name, mask, bank in grammar.marks:
        result[bank] = np.maximum(result[bank], mask.astype(np.float32) / 255.0)
    return result


def debug_angle_pair(fid=FID):
    grammar = BUILDERS[fid]()
    owners = owner_unions(grammar)
    metal, rough, coat = (channel.astype(np.float32) / 255.0 for channel in grammar.explicit_spec)
    aperture = np.clip(1.0 - .62 * rough, .16, 1.0)
    gain_a = np.clip(.24 + 1.22 * metal * aperture + .56 * owners["A"]
                     - .30 * owners["B"], .07, 1.48)
    gain_b = np.clip(.24 + 1.22 * coat * aperture + .56 * owners["B"]
                     - .30 * owners["A"], .07, 1.48)
    ember = np.asarray((.38, .075, .008), np.float32)
    spectral = np.asarray((.025, .11, .42), np.float32)
    angle_a = grammar.paint * gain_a[..., None] + ember * (owners["A"] * aperture)[..., None]
    angle_b = grammar.paint * gain_b[..., None] + spectral * (owners["B"] * aperture)[..., None]
    angle_a = np.clip(angle_a, 0, 1).astype(np.float32)
    angle_b = np.clip(angle_b, 0, 1).astype(np.float32)
    return angle_a, angle_b, np.abs(angle_a - angle_b).astype(np.float32)


def _write_rgb(path: Path, rgb):
    image = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)):
        raise OSError(f"failed to write {path}")


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_fullres_evidence(output_dir: str | Path):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    grammar = _build_fc_will_o_wisp()
    elapsed = time.perf_counter() - start
    angle_a, angle_b, delta = debug_angle_pair()

    paths = {}
    paths["paint"] = output / f"{FID}_paint_2048.png"
    _write_rgb(paths["paint"], grammar.paint)
    for label, channel in zip(("M", "R", "Cc"), grammar.explicit_spec):
        paths[label] = output / f"{FID}_{label}_2048.png"
        if not cv2.imwrite(str(paths[label]), channel):
            raise OSError(f"failed to write {paths[label]}")
    for label, image in (("angle_A", angle_a), ("angle_B", angle_b), ("angle_delta", delta)):
        paths[label] = output / f"{FID}_{label}_2048.png"
        _write_rgb(paths[label], image)

    owners = owner_unions(grammar)
    channels = grammar.explicit_spec
    channel_vectors = [channel.astype(np.float32).ravel() for channel in channels]
    correlations = np.corrcoef(np.stack(channel_vectors, axis=0))
    manifest = {
        "schema": "spb-wilds-wisp-continuum-c1/1",
        "status": "REJECT-OVERSIZED-SPARSE-GESTURE-DO-NOT-WIRE",
        "visual_verdict": "REJECT",
        "visual_reason": "one oversized sparse trajectory gesture leaves most of the native canvas empty and violates the fine dense finish doctrine",
        "finish_id": FID,
        "native_size": [S, S],
        "topology": grammar.topology,
        "acceptance_target": "full native 2048 only; picker size ignored",
        "construction": "single deterministic trajectory; no grid/tile/stamp/secondary orbit/stochastic texture",
        "native_builder_seconds": round(elapsed, 6),
        "within_3_second_budget": elapsed <= 3.0,
        "causal_marks": [
            {"name": name, "bank": bank, "coverage": round(float(np.mean(mask > 0)), 6)}
            for name, mask, bank in grammar.marks
        ],
        "owner_coverage": {
            "A": round(float(np.mean(owners["A"] > 0)), 6),
            "B": round(float(np.mean(owners["B"] > 0)), 6),
            "angle_delta_mean": round(float(delta.mean()), 6),
            "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        },
        "spec_stats": {
            label: {
                "min": int(channel.min()), "max": int(channel.max()),
                "std": round(float(channel.std()), 6),
                "unique_values": int(np.unique(channel).size),
            }
            for label, channel in zip(("M", "R", "Cc"), channels)
        },
        "spec_correlations": {
            "M_R": round(float(correlations[0, 1]), 6),
            "M_Cc": round(float(correlations[0, 2]), 6),
            "R_Cc": round(float(correlations[1, 2]), 6),
        },
        "files": {key: {"path": path.name, "sha256": _sha(path)} for key, path in paths.items()},
    }
    (output / "fullres_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    render_fullres_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "wisp_continuum"
    )


__all__ = [
    "BUILDERS", "FID", "S", "_authored", "clear_cache", "debug_angle_pair",
    "debug_grammar", "owner_unions", "render_fullres_evidence",
]
