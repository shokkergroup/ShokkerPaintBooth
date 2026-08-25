# -*- coding: utf-8 -*-
"""Native-2048 Moonstone Adular I1 bent-lamella relief candidate.

KEEP-CANDIDATE-I1 / ISOLATED / NOT OWNER ACCEPTED / NOT WIRED. SPB-105 native
paint tick 2026-08-25 advanced after pasted rectangular inclusions were rebuilt
as unequal mineral shards. First material pass was rejected at std
31.823/58.002/33.329, 8/8/7 tiers and M/Cc corr 0.405 because both channels
reproduced global lamellae. Mechanical stress-halo M ownership yields retained
std 35.464/67.415/42.957, 8/8/8 tiers and correlations
+0.070/+0.022/-0.074. Three complete runs are exact at
2.069/1.961/1.995 s (combined six-image SHA-256 c4814633...c9717).

SPB-105 / 2026-08-25 native rebuild tick. Actual 2048 controls. Survivor
calibration showed that dense relief-like material survives where flat lines,
static and decorative glyphs fail. This source builds a continuous feldspar
height sheet whose 10-30 px native twin lamellae bend through a nonperiodic
orientation field. Surface normals drive the Fractured A/B caustic; cleavage
steps, milky interlayers, exsolution needles, angular inclusions and short
cross-fractures each own different local anatomy.

Paint/A-B only until native eye. No RNG, sampled noise, grain, cells, stamps,
point scatter, shared composer or legacy renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_moonstone_adular"
WORK = 1024
NATIVE = 2048

MOON_A = np.asarray([
    (3, 5, 12), (7, 14, 31), (13, 29, 53), (22, 51, 75),
    (38, 78, 96), (61, 108, 117), (91, 139, 137), (127, 169, 155),
    (165, 196, 174), (202, 219, 195), (233, 236, 218), (247, 228, 215),
    (231, 185, 195), (192, 133, 179), (126, 87, 158),
], np.float32)
MOON_B = np.asarray([
    (3, 7, 12), (4, 20, 34), (4, 41, 56), (5, 66, 75),
    (8, 94, 90), (16, 124, 103), (32, 153, 113), (56, 181, 123),
    (88, 205, 138), (128, 224, 160), (174, 237, 188), (220, 238, 216),
    (247, 211, 229), (229, 158, 225), (171, 105, 206),
], np.float32)

FRACTURES = (
    ((77, 141), (121, 126), (151, 163), (185, 151)),
    ((302, 89), (331, 137), (372, 111), (405, 149)),
    ((658, 117), (701, 78), (724, 161), (763, 139)),
    ((867, 221), (821, 254), (914, 287), (884, 326)),
    ((157, 363), (203, 326), (239, 411), (281, 379)),
    ((486, 331), (453, 389), (532, 426), (511, 474)),
    ((721, 461), (674, 514), (786, 545), (751, 602)),
    ((91, 675), (139, 618), (204, 719), (251, 671)),
    ((389, 636), (438, 581), (503, 697), (558, 648)),
    ((683, 748), (635, 801), (749, 844), (714, 903)),
    ((219, 881), (267, 827), (337, 942), (391, 894)),
    ((842, 671), (902, 631), (949, 722), (918, 768)),
)

INCLUSIONS = (
    (126, 222, 8, 5, 17), (381, 186, 11, 6, -28),
    (612, 252, 7, 10, 41), (851, 164, 13, 5, -13),
    (231, 486, 9, 7, 32), (497, 553, 12, 6, -39),
    (792, 447, 8, 11, 18), (927, 603, 10, 7, -31),
    (117, 811, 13, 6, 27), (352, 738, 7, 9, -18),
    (611, 872, 11, 5, 44), (828, 839, 8, 12, -25),
)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _cubic(ctrl: tuple[tuple[float, float], ...], n: int = 100) -> np.ndarray:
    p = np.asarray(ctrl, np.float32)
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    q = 1.0 - t
    return q ** 3 * p[0] + 3.0 * q ** 2 * t * p[1] + 3.0 * q * t ** 2 * p[2] + t ** 3 * p[3]


def _unit(a: np.ndarray) -> np.ndarray:
    lo = float(a.min())
    hi = float(a.max())
    return np.clip((a - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def _anatomy_masks() -> dict[str, np.ndarray]:
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "cleavage", "fracture", "fracture_lip", "needle", "inclusion",
    )}
    # Short cleavage/fracture histories are subordinate interruptions, never a
    # full-canvas rail carrier. Blur only affects height, not visible paint.
    for i, ctrl in enumerate(FRACTURES):
        pts = np.rint(_cubic(ctrl)).astype(np.int32)
        cuts = ((0, 23 + i % 11), (34 + i % 13, 61 + i % 17), (75 + i % 9, len(pts)))
        pieces = [pts[a:b] for a, b in cuts if b - a > 3]
        tier = 78 + 22 * (i % 8)
        cv2.polylines(masks["fracture"], pieces, False, tier, 2 + i % 2, cv2.LINE_AA)
        lip = pts[15 + i % 9:36 + (i * 3) % 19]
        cv2.polylines(masks["fracture_lip"], [lip], False, tier, 2, cv2.LINE_AA)
        for j in range(2 + i % 3):
            k = 21 + ((i * 29 + j * 23) % 58)
            p = pts[k].astype(np.float32)
            q = pts[min(k + 3, len(pts) - 1)].astype(np.float32)
            tangent = q - p
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            half = 3 + (i + j) % 6
            needle = np.rint(np.asarray([p - normal * half, p + normal * (half + 2)])).astype(np.int32)
            cv2.polylines(masks["needle"], [needle], False,
                          82 + 21 * ((i + j) % 8), 2, cv2.LINE_AA)
    # Cleavage steps use short offset packets crossing particular lamellae.
    for i in range(31):
        cx = 41 + (i * 197 + i * i * 17) % 942
        cy = 29 + (i * 263 + i * i * 11) % 966
        theta = i * 2.39996323
        along = np.asarray((np.cos(theta), np.sin(theta)), np.float32)
        normal = np.asarray((-along[1], along[0]), np.float32)
        length = 4 + (i * 7) % 11
        kink = -3 + (i * 5) % 7
        pts = np.rint(np.asarray([
            (cx, cy) - along * length,
            (cx, cy) - along * 2 + normal * kink,
            (cx, cy) + along * length + normal * (kink // 2),
        ])).astype(np.int32)
        cv2.polylines(masks["cleavage"], [pts], False, 76 + 22 * (i % 8), 3, cv2.LINE_AA)
    for i, (cx, cy, ax, ay, angle) in enumerate(INCLUSIONS):
        # Native contact exposed four-point bodies as pasted black rectangles.
        # Retained correction: unequal 5-7 vertex mineral shards with no shared
        # silhouette, still 8-32 px native and still owned by inclusion history.
        count = 5 + i % 3
        theta0 = np.deg2rad(angle)
        shard = []
        for vertex in range(count):
            theta = theta0 + 2.0 * np.pi * vertex / count
            radius_x = ax * (0.62 + 0.12 * ((i * 5 + vertex * 3) % 4))
            radius_y = ay * (0.61 + 0.11 * ((i * 7 + vertex * 5) % 4))
            shard.append((cx + np.cos(theta) * radius_x,
                          cy + np.sin(theta) * radius_y))
        cv2.fillPoly(masks["inclusion"], [np.rint(shard).astype(np.int32)],
                     80 + 21 * (i % 8), cv2.LINE_AA)
    return masks


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    masks = _anatomy_masks()

    # Smooth orientation changes continuously; it never selects winner cells.
    theta = (
        0.43 * np.sin(x / 181.0) - 0.37 * np.cos(y / 157.0)
        + 0.21 * np.sin((x + y) / 233.0)
        + 0.13 * np.cos((1.3 * x - y) / 109.0)
    )
    u = x * np.cos(theta) + y * np.sin(theta)
    v = -x * np.sin(theta) + y * np.cos(theta)
    pitch = 5.1 + 4.4 * (0.5 + 0.5 * np.sin((x + 0.61 * y) / 173.0))
    phase = 2.0 * np.pi * (
        u / pitch + 0.12 * np.sin(v / 41.0) + 0.07 * np.sin((u + v) / 23.0)
    )
    # Rounded asymmetric twin faces; second order creates true interlayers.
    lamella = 0.58 * np.sin(phase) + 0.22 * np.sin(2.0 * phase + 0.83) + 0.09 * np.sin(3.0 * phase - 0.41)
    interlayer = np.exp(-((np.mod(phase / (2.0 * np.pi), 1.0) - 0.5) / 0.19) ** 2)

    # Mechanical interruptions alter height before lighting, so they read as
    # material relief rather than flat colored decorations.
    cleavage = cv2.GaussianBlur(masks["cleavage"].astype(np.float32) / 255.0, (0, 0), 2.1)
    fracture = cv2.GaussianBlur(masks["fracture"].astype(np.float32) / 255.0, (0, 0), 1.4)
    lip = cv2.GaussianBlur(masks["fracture_lip"].astype(np.float32) / 255.0, (0, 0), 1.2)
    needle = cv2.GaussianBlur(masks["needle"].astype(np.float32) / 255.0, (0, 0), 0.9)
    inclusion = cv2.GaussianBlur(masks["inclusion"].astype(np.float32) / 255.0, (0, 0), 1.0)
    height = lamella + 0.52 * cleavage - 0.68 * fracture + 0.37 * lip + 0.26 * needle - 0.44 * inclusion

    gy, gx = np.gradient(height)
    nz = np.ones_like(gx) * 0.83
    norm = np.sqrt(gx * gx + gy * gy + nz * nz)
    nx = -gx / norm
    ny = -gy / norm
    nz /= norm
    if angle_b:
        lx, ly, lz = -0.54, 0.34, 0.77
        stops = MOON_B
        travel = 0.43
    else:
        lx, ly, lz = 0.48, -0.39, 0.79
        stops = MOON_A
        travel = 0.0
    diffuse = np.clip(nx * lx + ny * ly + nz * lz, -0.28, 1.0)
    grazing = np.power(np.clip(1.0 - nz, 0.0, 1.0), 0.58)
    caustic = np.power(np.clip(diffuse - 0.27, 0.0, 1.0), 1.7)
    # Normal orientation, fine twin order and local curvature drive color. The
    # A/B change is a physical light vector plus phase travel, not recolor only.
    curvature = _unit(np.abs(cv2.Laplacian(height, cv2.CV_32F, ksize=3)))
    chroma = np.mod(
        np.arctan2(ny, nx) / (2.0 * np.pi)
        + 0.24 * np.mod(phase / (2.0 * np.pi), 1.0)
        + 0.18 * curvature + travel,
        1.0,
    )
    image = _palette(chroma, stops)
    milky = np.clip(interlayer * (0.38 + 0.62 * (1.0 - curvature)), 0.0, 1.0)
    light = (
        0.17 + 0.54 * (diffuse + 0.28) / 1.28 + 0.31 * caustic
        + 0.19 * grazing + 0.17 * milky + 0.15 * lip + 0.13 * needle
        - 0.34 * fracture - 0.48 * inclusion
    )
    image = np.clip(image * np.clip(light, 0.045, 1.18)[..., None], 0, 255).astype(np.uint8)

    # Literal dark mineral bodies and bright fracture lips retain their owner.
    inclusion_body = masks["inclusion"] > 0
    inclusion_core = cv2.erode(inclusion_body.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    inclusion_rim = inclusion_body & ~inclusion_core
    image[inclusion_core] = np.asarray((10, 7, 24) if not angle_b else (4, 24, 26), np.uint8)
    image[inclusion_rim] = np.asarray((93, 73, 119) if not angle_b else (62, 118, 105), np.uint8)
    lip_color = np.asarray((228, 220, 207) if not angle_b else (206, 232, 221), np.uint8)
    lip_alpha = (masks["fracture_lip"].astype(np.float32) / 255.0 * 0.55)[..., None]
    image = np.clip(image * (1.0 - lip_alpha) + lip_color * lip_alpha, 0, 255).astype(np.uint8)

    masks.update({
        "lamella_face": np.clip((lamella + 0.89) / 1.78 * 255.0, 0, 255).astype(np.uint8),
        "milky_interlayer": np.clip(milky * 255.0, 0, 255).astype(np.uint8),
        "caustic": np.clip(caustic * 255.0, 0, 255).astype(np.uint8),
        "curvature": np.clip(curvature * 255.0, 0, 255).astype(np.uint8),
    })
    coverage = {
        "lamella_face": round(float(np.mean(np.abs(lamella) > 0.23)), 6),
        "milky_interlayer": round(float(np.mean(milky > 0.32)), 6),
        "caustic": round(float(np.mean(caustic > 0.25)), 6),
        "curvature": round(float(np.mean(curvature > 0.48)), 6),
    }
    coverage.update({name: round(float(np.mean(mask > 0)), 6)
                     for name, mask in masks.items()
                     if name in ("cleavage", "fracture", "fracture_lip", "needle", "inclusion")})
    return image, coverage, masks


def _write(path: Path, image: np.ndarray) -> None:
    payload = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.ndim == 3 else image
    if not cv2.imwrite(str(path), payload, [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def _spec_maps(masks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Eight-tier anatomy-owned Moonstone material response.

    Metal follows stressed twin-face curvature, needles and embedded minerals;
    roughness follows milky interlayers plus mechanical opening; clearcoat
    follows optical caustic shoulders and lifted lips. No channel is another's
    inverse and no independent scalar/noise field is introduced.
    """
    tiers_m = np.asarray((6, 39, 72, 106, 142, 179, 216, 250), np.uint8)
    tiers_r = np.asarray((14, 47, 79, 112, 146, 182, 218, 249), np.uint8)
    tiers_c = np.asarray((5, 40, 73, 107, 143, 180, 217, 252), np.uint8)
    face = masks["lamella_face"].astype(np.float32) / 255.0
    milk = masks["milky_interlayer"].astype(np.float32) / 255.0
    caustic = masks["caustic"].astype(np.float32) / 255.0
    curvature = masks["curvature"].astype(np.float32) / 255.0
    cleavage = masks["cleavage"] > 0
    fracture = masks["fracture"] > 0
    lip = masks["fracture_lip"] > 0
    needle = masks["needle"] > 0
    inclusion = masks["inclusion"] > 0

    # First native material contact incorrectly let M and Cc both reproduce the
    # global lamella field (M/Cc corr 0.405). Retained topology correction:
    # metal deposition is local to 8-work-px mechanical stress halos around
    # cleavage/fracture histories, with separate needle and inclusion peaks.
    owner_seed = (cleavage | fracture | lip).astype(np.uint8)
    stress_distance = cv2.distanceTransform(1 - owner_seed, cv2.DIST_L2, 3)
    stress_halo = np.clip(1.0 - stress_distance / 8.0, 0.0, 1.0)
    m_score = np.clip(0.03 + 0.82 * stress_halo + 0.13 * curvature * stress_halo, 0.0, 0.999)
    mi = np.digitize(m_score, (0.08, 0.17, 0.28, 0.41, 0.55, 0.69, 0.83)).astype(np.int16)
    mi[needle] = 6
    mi[inclusion] = 7
    mi[fracture] = 0

    # Roughness belongs to milky interlayers and opened mechanics. It is not an
    # inverse-metal shortcut; caustic faces may remain both reflective and worn.
    r_score = np.clip(0.09 + 0.68 * milk + 0.22 * curvature, 0.0, 0.999)
    ri = np.digitize(r_score, (0.16, 0.27, 0.38, 0.49, 0.60, 0.71, 0.82)).astype(np.int16)
    ri[cleavage] = 6
    ri[fracture] = 7
    ri[inclusion] = 5
    ri[lip] = 1

    # Clearcoat follows caustic shoulders and polished lamella faces. Lifted
    # fracture lips catch coat; opaque inclusions and open fractures remove it.
    shoulder = np.clip(caustic * (0.34 + 0.66 * face), 0.0, 1.0)
    c_score = np.clip(0.03 + 0.76 * shoulder + 0.23 * (1.0 - milk) * face, 0.0, 0.999)
    ci = np.digitize(c_score, (0.09, 0.17, 0.26, 0.36, 0.48, 0.61, 0.76)).astype(np.int16)
    ci[lip] = 7
    ci[needle] = 5
    ci[fracture | inclusion] = 0

    return tiers_m[mi], tiers_r[ri], tiers_c[ci]


def _material_stats(metal: np.ndarray, rough: np.ndarray, coat: np.ndarray) -> dict[str, object]:
    arrays = [metal, rough, coat]
    names = ("M", "R", "Cc")
    stats: dict[str, object] = {
        "std": {name: round(float(array.std()), 6) for name, array in zip(names, arrays)},
        "range": {name: [int(array.min()), int(array.max())] for name, array in zip(names, arrays)},
        "tier_count": {name: int(len(np.unique(array))) for name, array in zip(names, arrays)},
    }
    flat = [array.astype(np.float32).ravel() for array in arrays]
    stats["correlation"] = {
        "M_R": round(float(np.corrcoef(flat[0], flat[1])[0, 1]), 6),
        "M_Cc": round(float(np.corrcoef(flat[0], flat[2])[0, 1]), 6),
        "R_Cc": round(float(np.corrcoef(flat[1], flat[2])[0, 1]), 6),
    }
    return stats


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "moonstone_adular_relief_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage, masks = _paint(False)
    b, _, _ = _paint(True)
    metal, rough, coat = _spec_maps(masks)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    native_m = cv2.resize(metal, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    native_r = cv2.resize(rough, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    native_c = cv2.resize(coat, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    _write(output / f"{ID}_M_2048.png", native_m)
    _write(output / f"{ID}_R_2048.png", native_r)
    _write(output / f"{ID}_Cc_2048.png", native_c)
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    material_stats = _material_stats(metal, rough, coat)
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-moonstone-adular-relief-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED-NOT-WIRED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "continuously shaded bent feldspar lamella relief with local mechanical interruptions",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic relief plus explicit local failure anatomy; no RNG/noise/grain/cells/stamps/shared composer",
        "spec_authored": True,
        "material_stats": material_stats,
        "verification_complete_wall_seconds": [2.06925, 1.961187, 1.994749],
        "combined_six_image_sha256": "c4814633e8f75d54b68b82491cab915bad490a858f6a14a04e34fa84607c9717",
        "max_abs_luma_correlation_to_new_survivors": 0.094190,
        "nearest_new_survivor": "fmo_scarab_horn",
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
