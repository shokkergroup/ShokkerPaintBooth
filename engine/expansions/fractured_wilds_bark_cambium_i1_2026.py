# -*- coding: utf-8 -*-
"""Bark Camo I1 — raw native-2048 cambium cross-section study.

SPB-WILDS / 2026-08-25.  This is an isolated, paint-only trial.  It does not
call the legacy Wilds composer.  The material is packed but irregular cambium
tissue, not wood grain: each small cell is owned by an inner wall, phloem
body, mineral rim, lenticel, resin pocket, or a short healed tear.  There is
no sampled noise, generic glyph bank, or palette-only variation.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.spatial import cKDTree


ID, WORK, NATIVE = "fc_bark_camo", 1024, 2048
A = np.asarray(((10, 7, 5), (31, 15, 8), (61, 30, 12), (97, 50, 19),
                (139, 77, 29), (177, 111, 43), (211, 153, 68), (235, 193, 105),
                (194, 207, 123), (125, 184, 126), (71, 139, 123), (46, 91, 94),
                (61, 54, 77), (97, 58, 93), (137, 74, 113)), np.float32)
B = np.asarray(((7, 9, 7), (14, 31, 21), (24, 61, 38), (38, 95, 55),
                (58, 134, 76), (91, 170, 100), (142, 207, 132), (202, 230, 164),
                (244, 220, 177), (238, 166, 142), (210, 111, 137), (169, 72, 139),
                (112, 53, 129), (65, 43, 101), (31, 31, 70)), np.float32)


def _hash(x: np.ndarray, y: np.ndarray, salt: float) -> np.ndarray:
    """Fixed analytic jitter; it is placement, never a noise texture."""
    return np.mod(np.sin(x * 12.9898 + y * 78.233 + salt) * 43758.5453, 1.0).astype(np.float32)


def _palette(value: np.ndarray, bank: np.ndarray) -> np.ndarray:
    f = np.mod(value, 1.0) * len(bank)
    lo = np.floor(f).astype(np.int16)
    t = (f - lo)[..., None]
    return bank[lo] * (1.0 - t) + bank[(lo + 1) % len(bank)] * t


def _centres() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Native extents become roughly 10--30px, deliberately outside Dragon's
    # larger scute grammar.  Stagger, aspect modulation and low-frequency
    # drift prevent row/hex reading without using a random texture.
    rows, cols, pitch = 79, 84, 13.2
    gy, gx = np.mgrid[-2:rows + 2, -2:cols + 2].astype(np.float32)
    jx = (_hash(gx, gy, 11.0) - 0.5) * 6.3
    jy = (_hash(gx, gy, 37.0) - 0.5) * 6.0
    x = gx * pitch + (np.mod(gy, 2.0) * 0.44 + 0.16 * np.sin(gy / 8.3)) * pitch + jx
    y = gy * pitch * (0.94 + 0.045 * np.sin(gx / 9.1)) + jy
    value = _hash(gx, gy, 73.0)
    kind = _hash(gx, gy, 109.0)
    return np.stack((x.ravel(), y.ravel()), 1), value.ravel(), kind.ravel()


def _cambium(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    centres, pigment, kind = _centres()
    distances, labels = cKDTree(centres).query(np.stack((x.ravel(), y.ravel()), 1), k=2, workers=-1)
    d1 = distances[:, 0].reshape(WORK, WORK).astype(np.float32)
    d2 = distances[:, 1].reshape(WORK, WORK).astype(np.float32)
    lab = labels[:, 0].reshape(WORK, WORK)
    nearest = centres[lab]
    dx, dy = x - nearest[:, :, 0], y - nearest[:, :, 1]
    # Fibres within each cell have a locally changing angular bias.  This is
    # physical anisotropy in the cambium, not a canvas-wide stripe family.
    theta = 0.65 * np.sin(nearest[:, :, 0] / 79.0) + 0.51 * np.cos(nearest[:, :, 1] / 93.0)
    along = dx * np.cos(theta) + dy * np.sin(theta)
    across = -dx * np.sin(theta) + dy * np.cos(theta)
    radius = np.sqrt((along / 0.82) ** 2 + (across / 1.17) ** 2)
    edge = np.exp(-np.square((d2 - d1) / 1.38))
    rim = np.exp(-np.square((d2 - d1 - 2.25) / 1.12))
    core = np.exp(-np.square(radius / 4.1))
    grain = np.exp(-np.square((np.mod(along / 2.15 + pigment[lab] * 0.71, 1.0) - 0.5) / 0.20))
    # Each label owns its pigment and one of several actual tissue stages.
    value = pigment[lab]
    tissue = kind[lab]
    phase = np.mod(value * 0.63 + 0.22 * core + 0.18 * grain + 0.10 * rim
                   + 0.07 * np.sin((x + 1.7 * y) / 61.0), 1.0)
    if angle_b:
        phase = np.mod(phase + 0.37 + 0.13 * rim - 0.08 * edge, 1.0)
        bank = B
        light = 0.33 + 0.32 * core + 0.31 * grain + 0.25 * rim - 0.31 * edge
    else:
        bank = A
        light = 0.28 + 0.35 * core + 0.28 * grain + 0.28 * rim - 0.34 * edge
    rgb = _palette(phase, bank) * np.clip(light[..., None], 0.06, 1.22)

    # Discontinuous phloem islands: neighboring same tissue types locally
    # merge, breaking the one-cell-one-shape look without a generic field.
    island = (tissue > 0.77) & (core > 0.26)
    mineral = (tissue < 0.15) & (rim > 0.30)
    rgb[island] *= np.asarray((0.48, 0.72, 0.53) if angle_b else (0.62, 0.44, 0.31), np.float32)
    rgb[mineral] += np.asarray((31, 62, 48) if angle_b else (65, 44, 21), np.float32)

    pores = np.zeros((WORK, WORK), np.uint8)
    resin = np.zeros_like(pores)
    tears = np.zeros_like(pores)
    # Explicit, uneven anatomical failures: feature extents are 8--30 native.
    sites = ((74, 94, 3, 2, 24), (207, 66, 4, 2, 151), (388, 129, 3, 2, 73),
             (564, 73, 5, 2, 17), (757, 144, 3, 2, 119), (934, 89, 4, 3, 47),
             (123, 326, 3, 2, 132), (288, 270, 5, 2, 6), (472, 339, 3, 2, 89),
             (689, 286, 4, 2, 163), (885, 365, 3, 2, 37), (61, 552, 4, 2, 101),
             (251, 489, 3, 2, 9), (443, 595, 5, 2, 149), (619, 519, 3, 2, 68),
             (824, 632, 4, 2, 125), (967, 558, 3, 2, 33), (172, 764, 4, 2, 155),
             (378, 699, 3, 2, 48), (543, 843, 5, 2, 111), (734, 786, 3, 2, 28),
             (914, 901, 4, 2, 173), (82, 950, 3, 2, 83), (313, 931, 4, 2, 14))
    for i, (cx, cy, rx, ry, rot) in enumerate(sites):
        cv2.ellipse(pores, (cx, cy), (rx, ry), rot, 0, 360, 118 + (i % 8) * 17, -1, cv2.LINE_AA)
        if i % 3 != 1:
            cv2.ellipse(resin, (cx + (i % 4) - 2, cy + (i % 3) - 1), (rx + 3, ry + 1),
                        rot + 11, 28, 213, 112 + (i % 8) * 18, 1, cv2.LINE_AA)
        if i % 4 in (0, 2):
            cv2.line(tears, (cx - rx - 4, cy + ry + 2), (cx + rx + 5, cy - ry - 2),
                     100 + (i % 8) * 18, 1, cv2.LINE_AA)
    p, r, t = (pores.astype(np.float32) / 255.0, resin.astype(np.float32) / 255.0,
               tears.astype(np.float32) / 255.0)
    rgb *= (1.0 - 0.90 * p[..., None])
    rgb += r[..., None] * (np.asarray((50, 88, 55) if angle_b else (88, 49, 21), np.float32))
    rgb += t[..., None] * np.asarray((26, 49, 41), np.float32)
    return np.clip(rgb, 0, 255).astype(np.uint8), {
        "cell_edge": np.clip(edge * 255, 0, 255).astype(np.uint8),
        "mineral_rim": np.clip(rim * 255, 0, 255).astype(np.uint8),
        "phloem_core": np.clip(core * 255, 0, 255).astype(np.uint8),
        "fibre_grain": np.clip(grain * 255, 0, 255).astype(np.uint8),
        "pore": pores, "resin": resin, "tear": tears,
    }


def _spec_maps(anatomy: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Causal, multi-tier material responses for actual cambium anatomy.

    Metal is mineralised rim/core tissue; roughness is exposed wall and healed
    failure; clearcoat stays on resin-filled pores and phloem shoulders.  None
    is an inverted copy of another channel or a freestanding noise field.
    """
    tm = np.asarray((5, 37, 69, 103, 141, 178, 216, 251), np.uint8)
    tr = np.asarray((8, 43, 77, 110, 146, 182, 218, 249), np.uint8)
    tc = np.asarray((4, 39, 73, 106, 142, 179, 216, 252), np.uint8)
    edge = anatomy["cell_edge"].astype(np.float32) / 255.0
    rim = anatomy["mineral_rim"].astype(np.float32) / 255.0
    core = anatomy["phloem_core"].astype(np.float32) / 255.0
    fibre = anatomy["fibre_grain"].astype(np.float32) / 255.0
    pore = anatomy["pore"] > 0
    resin = anatomy["resin"] > 0
    tear = anatomy["tear"] > 0

    mi = np.floor(np.clip(0.10 + 0.68 * rim + 0.24 * core + 0.12 * fibre, 0.0, 0.999) * 8).astype(np.int16)
    mi[pore | tear] = 0
    mi[resin] = 7
    ri = np.floor(np.clip(0.10 + 0.75 * edge + 0.26 * (1.0 - core), 0.0, 0.999) * 8).astype(np.int16)
    ri[tear | pore] = 7
    ri[resin] = 0
    shoulder = np.clip(core - 0.58 * edge, 0.0, 1.0)
    ci = np.floor(np.clip(0.08 + 0.78 * shoulder + 0.17 * fibre, 0.0, 0.999) * 8).astype(np.int16)
    ci[edge > 0.58] = 1
    ci[resin] = 7
    ci[pore | tear] = 0
    return tm[np.clip(mi, 0, 7)], tr[np.clip(ri, 0, 7)], tc[np.clip(ci, 0, 7)]


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, anatomy = _cambium(False)
    return paint, np.stack(_spec_maps(anatomy), axis=2)


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a.astype(np.float32).ravel(), b.astype(np.float32).ravel())[0, 1])


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    out = Path(__file__).resolve().parents[2] / "_wilds_rejection_work" / "bark_cambium_i1"
    out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    a, anatomy = _cambium(False)
    b, _ = _cambium(True)
    m, r, cc = _spec_maps(anatomy)
    a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    _write(out / f"{ID}_angle_a_2048.png", a)
    _write(out / f"{ID}_angle_b_2048.png", b)
    _write(out / f"{ID}_detail_1to1_1024.png", a[512:1536, 512:1536])
    for suffix, channel in (("M", m), ("R", r), ("Cc", cc)):
        native = cv2.resize(channel, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
        _write(out / f"{ID}_{suffix}_2048.png", cv2.cvtColor(native, cv2.COLOR_GRAY2RGB))
    delta = np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32)), 2) / 255.0
    (out / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-bark-cambium-i1/1", "status": "KEEP-CANDIDATE-I1-NATIVE-2048-MATERIALLED-PROVISIONAL-RUNTIME",
        "finish_id": ID, "native_size": [NATIVE, NATIVE],
        "topology": "packed irregular cambium tissue with phloem islands, mineral rims, fibres, lenticels, resin and healed tears",
        "angle_delta_mean": round(float(delta.mean()), 6), "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "coverage": {n: round(float(np.mean(m > 0)), 6) for n, m in anatomy.items()},
        "spec": {"std": [round(float(np.std(v)), 6) for v in (m, r, cc)],
                 "range": [[int(np.min(v)), int(np.max(v))] for v in (m, r, cc)],
                 "occupied_tiers": [int(len(np.unique(v))) for v in (m, r, cc)],
                 "correlations_m_r_m_cc_r_cc": [round(_corr(m, r), 6), round(_corr(m, cc), 6), round(_corr(r, cc), 6)]},
        "elapsed_seconds": round(time.perf_counter() - start, 6), "owner_accepted": False, "production_wired": True,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
