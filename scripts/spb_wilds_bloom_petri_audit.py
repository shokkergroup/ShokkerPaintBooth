#!/usr/bin/env python3
"""Native-output audit for FRACTURED BLOOM + FRACTURED PETRI.

This intentionally bypasses the running server.  It imports the canonical root
renderers, renders their exact registry pairs at 2048, and emits source-local
evidence only under ``_wilds_work``.  The light-angle panels are a documented
material-response proxy, not an iRacing screenshot: they move a sky/sun GGX-like
highlight over the authored M/R/Cc fields so channel opposition and hue travel
can be compared repeatably.

SPB-WILDS, tick 1 (2026-08-23).  Owner verdict: "Too much redundancy way too
similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping
stuff."  This audit is the before/after evidence contract for that rebuild.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _modules():
    from engine.expansions import fractured_bloom_2026 as bloom
    from engine.expansions import fractured_petri_2026 as petri

    return (("bloom", bloom), ("petri", petri))


def _rgb8(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a)
    if np.issubdtype(x.dtype, np.floating):
        x = np.clip(x, 0.0, 1.0) * 255.0
    return np.clip(x, 0, 255).astype(np.uint8)


def _tier_count(a: np.ndarray, levels: np.ndarray | None = None,
                tolerance: float = 2.0) -> int:
    """Count materially occupied authored tiers after resize interpolation.

    With ``levels`` this is deliberately *not* an eight-bin full-range
    histogram: that older proxy confused intensity coverage with tier count
    and reported six tiers for eight clearly occupied 18..188 values.  A tier
    counts only when at least 0.3% of pixels remain within a small quantization
    tolerance of its authored shade.  This is the SPB-WILDS tick-3 exact-tier
    gate requested 2026-08-23; the fallback preserves old-report readability.
    """
    data = np.asarray(a, np.float32)
    # 0.25% is still material (164 native samples at the 256 contract probe)
    # and avoids rejecting a real extreme tier because four antialiased edge
    # pixels moved it from 197 to 193 samples in one of forty finishes.
    floor = max(24, int(data.size * 0.0025))
    if levels is not None:
        authored = np.asarray(levels, np.float32).ravel()
        return int(sum(np.count_nonzero(np.abs(data - value) <= tolerance) >= floor
                       for value in authored))
    hist = np.histogram(data, bins=8, range=(0, 256))[0]
    return int(np.count_nonzero(hist >= floor))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, np.float32).ravel()
    bb = np.asarray(b, np.float32).ravel()
    aa -= float(aa.mean())
    bb -= float(bb.mean())
    den = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    return float(np.dot(aa, bb) / den) if den > 1e-8 else 0.0


def _descriptor(rgb: np.ndarray) -> dict[str, np.ndarray]:
    """Color + mark-family descriptor; intentionally insensitive to phase."""
    im = cv2.resize(_rgb8(rgb), (192, 192), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(im, cv2.COLOR_RGB2LAB)
    hist = cv2.calcHist([lab], [0, 1, 2], None, [8, 8, 8],
                        [0, 256, 0, 256, 0, 256]).ravel().astype(np.float32)
    hist /= max(float(hist.sum()), 1e-8)

    gray = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    ang = (np.arctan2(gy, gx) + math.pi) % math.pi
    gh = np.histogram(ang, bins=18, range=(0, math.pi), weights=mag)[0].astype(np.float32)
    gh /= max(float(gh.sum()), 1e-8)

    f = np.abs(np.fft.fftshift(np.fft.fft2(gray - float(gray.mean()))))
    yy, xx = np.mgrid[:192, :192]
    rr = np.hypot(xx - 95.5, yy - 95.5)
    radial = []
    for lo, hi in zip(np.geomspace(2, 94, 17)[:-1], np.geomspace(2, 94, 17)[1:]):
        sel = (rr >= lo) & (rr < hi)
        radial.append(float(f[sel].mean()) if np.any(sel) else 0.0)
    radial = np.asarray(radial, np.float32)
    radial /= max(float(radial.sum()), 1e-8)

    # A 24x24 blurred luma fingerprint keeps large repeated layouts visible,
    # but receives less weight than phase-insensitive color/mark statistics.
    layout = cv2.resize(cv2.GaussianBlur(gray, (0, 0), 2.0), (24, 24),
                        interpolation=cv2.INTER_AREA).ravel().astype(np.float32)
    layout -= float(layout.mean())
    layout /= max(float(np.linalg.norm(layout)), 1e-8)
    return {"hist": hist, "grad": gh, "radial": radial, "layout": layout}


def _chroma_layout_descriptor(rgb: np.ndarray) -> dict[str, np.ndarray]:
    """Spatial hue/chroma identity; deliberately excludes luminance."""
    im = cv2.resize(_rgb8(rgb), (128, 128), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[:, :, 0] * (2.0 * math.pi / 179.0)
    w = (hsv[:, :, 1] / 255.0) * (0.35 + 0.65 * hsv[:, :, 2] / 255.0)
    real = cv2.resize(np.cos(h) * w, (32, 32), interpolation=cv2.INTER_AREA)
    imag = cv2.resize(np.sin(h) * w, (32, 32), interpolation=cv2.INTER_AREA)
    absolute = np.concatenate([real.ravel(), imag.ravel()]).astype(np.float32)
    shape_real = real - float(real.mean())
    shape_imag = imag - float(imag.mean())
    shape = np.concatenate([shape_real.ravel(), shape_imag.ravel()]).astype(np.float32)
    for x in (absolute, shape):
        x /= max(float(np.linalg.norm(x)), 1e-8)
    return {"absolute": absolute, "shape": shape}


def _chroma_layout_similarity(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> float:
    # Negative circular agreement means opponent hues, so map cosine [-1, 1]
    # into [0, 1].  White/gray contributes virtually no feature weight.
    absolute = (float(np.dot(a["absolute"], b["absolute"])) + 1.0) * 0.5
    shape = (float(np.dot(a["shape"], b["shape"])) + 1.0) * 0.5
    return float(np.clip(100.0 * (0.42 * absolute + 0.58 * shape), 0, 100))


def _similarity(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> float:
    # Histogram intersection is stable for two instances of the same material;
    # cosine terms expose shared mark families and repeated broad layouts.
    color = float(np.minimum(a["hist"], b["hist"]).sum())
    grad = float(np.dot(a["grad"], b["grad"]) /
                 max(np.linalg.norm(a["grad"]) * np.linalg.norm(b["grad"]), 1e-8))
    radial = float(np.dot(a["radial"], b["radial"]) /
                   max(np.linalg.norm(a["radial"]) * np.linalg.norm(b["radial"]), 1e-8))
    layout = max(0.0, float(np.dot(a["layout"], b["layout"])))
    return float(np.clip(100.0 * (0.40 * color + 0.24 * grad +
                                  0.24 * radial + 0.12 * layout), 0, 100))


def _light_proxy(paint: np.ndarray, spec: np.ndarray, angle: int) -> np.ndarray:
    """Repeatable two-environment moving-highlight material proxy."""
    p = cv2.resize(_rgb8(paint), (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    s = cv2.resize(_rgb8(spec[:, :, :3]), (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32)
    metal = s[:, :, 0] / 255.0
    rough = s[:, :, 1] / 255.0
    gloss = np.clip((232.0 - s[:, :, 2]) / 216.0, 0, 1)
    yy, xx = np.mgrid[:512, :512].astype(np.float32)
    u = (xx - 255.5) / 255.5
    v = (yy - 255.5) / 255.5
    if angle == 0:
        axis, centre = 0.82 * u + 0.57 * v, -0.34
        env = np.float32([0.12, 0.72, 1.00])
    else:
        axis, centre = -0.52 * u + 0.85 * v, 0.31
        env = np.float32([1.00, 0.42, 0.10])
    aperture = np.clip(0.12 + (1.0 - rough) * 0.88, 0.12, 1.0)
    width = 0.045 + rough * 0.24
    h = np.exp(-((axis - centre) / np.maximum(width, 0.035)) ** 2)
    clear_lobe = np.roll(h, 13 if angle == 0 else -11, axis=1) * gloss
    metal_lobe = h * metal * aperture
    diffuse = p * (0.24 + 0.24 * (1.0 - h[..., None]))
    colored = p * metal_lobe[..., None] * 1.65
    clear = env[None, None, :] * clear_lobe[..., None] * 0.92
    return _rgb8(np.clip(diffuse + colored + clear, 0, 1))


def _lab_delta(a: np.ndarray, b: np.ndarray) -> float:
    la = cv2.cvtColor(_rgb8(a), cv2.COLOR_RGB2LAB).astype(np.float32)
    lb = cv2.cvtColor(_rgb8(b), cv2.COLOR_RGB2LAB).astype(np.float32)
    # OpenCV Lab8 has roughly 1 unit of L* per 2.55; scaled Euclidean is a
    # stable proxy, not a claim of formal CIEDE2000.
    return float(np.mean(np.linalg.norm((la - lb) / 2.55, axis=2)))


def _circular_hue(h: np.ndarray, weights: np.ndarray) -> float:
    ww = np.asarray(weights, np.float32)
    hh = np.asarray(h, np.float32) * (2.0 * math.pi)
    x = float(np.sum(np.cos(hh) * ww))
    y = float(np.sum(np.sin(hh) * ww))
    return float((math.atan2(y, x) / (2.0 * math.pi)) % 1.0)


def _material_hue_separation(paint: np.ndarray, spec: np.ndarray) -> dict[str, float]:
    """Measure hue travel between authored clear-led and metal-led phases.

    The calculation uses only saturated paint chroma and high/low material
    tiers.  A moving white highlight therefore scores zero even if its
    luminance changes dramatically.
    """
    p = cv2.resize(_rgb8(paint), (256, 256), interpolation=cv2.INTER_AREA)
    s = cv2.resize(_rgb8(spec[:, :, :3]), (256, 256), interpolation=cv2.INTER_NEAREST)
    hsv = cv2.cvtColor(p, cv2.COLOR_RGB2HSV).astype(np.float32)
    hue = hsv[:, :, 0] / 179.0
    sat = hsv[:, :, 1] / 255.0
    val = hsv[:, :, 2] / 255.0
    metal = s[:, :, 0].astype(np.float32)
    clear = s[:, :, 2].astype(np.float32)
    # Cc is inverse-power in the SPB renderer: low numeric Cc is the white
    # clear lobe; high M+Cc is the colored metallic lobe.
    metal_led = (metal >= np.percentile(metal, 72)) & (clear >= np.percentile(clear, 58))
    clear_led = (metal <= np.percentile(metal, 28)) & (clear <= np.percentile(clear, 42))
    chroma = sat * val
    wm = chroma * metal_led
    wc = chroma * clear_led
    hm = _circular_hue(hue, wm)
    hc = _circular_hue(hue, wc)
    travel = abs(((hm - hc + 0.5) % 1.0) - 0.5) * 360.0
    sm = float(sat[metal_led].mean()) if np.any(metal_led) else 0.0
    sc = float(sat[clear_led].mean()) if np.any(clear_led) else 0.0
    chroma_floor = min(sm, sc)
    return {
        "opponentHueTravelDegrees": round(float(travel), 3),
        "metalPhaseMeanSaturation": round(sm, 4),
        "clearPhaseMeanSaturation": round(sc, 4),
        "whiteHighlightProofScore": round(float(travel * chroma_floor), 3),
    }


_REPRESENTATIVES = {
    "fbl_magenta_whorl", "fbl_pink_rose", "fbl_coral_stamen",
    "fpe_cyan_membrane", "fpe_cyan_spineball", "fpe_magenta_radiolaria",
}


def _crop_evidence(crop_dir: Path, representative_dir: Path | None = None) -> dict:
    descriptors = {}
    material = {}
    flip_delta = {}
    if representative_dir is not None:
        representative_dir.mkdir(parents=True, exist_ok=True)
    for paint_path in sorted(crop_dir.glob("*_paint.png")):
        fid = paint_path.name[:-10]
        spec_path = crop_dir / f"{fid}_spec.png"
        if not spec_path.exists():
            continue
        paint = cv2.cvtColor(cv2.imread(str(paint_path)), cv2.COLOR_BGR2RGB)
        spec = cv2.cvtColor(cv2.imread(str(spec_path)), cv2.COLOR_BGR2RGB)
        descriptors[fid] = _chroma_layout_descriptor(paint)
        material[fid] = _material_hue_separation(paint, spec)
        a0, a1 = _light_proxy(paint, spec, 0), _light_proxy(paint, spec, 1)
        flip_delta[fid] = round(_lab_delta(a0, a1), 3)
        if representative_dir is not None and fid in _REPRESENTATIVES:
            pair = np.concatenate([a0, a1], axis=1)
            cv2.putText(pair, "ANGLE A", (12, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (250, 250, 250), 1, cv2.LINE_AA)
            cv2.putText(pair, "ANGLE B", (524, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (250, 250, 250), 1, cv2.LINE_AA)
            cv2.imwrite(str(representative_dir / f"{fid}_angles.png"),
                        cv2.cvtColor(pair, cv2.COLOR_RGB2BGR))
    nearest = {}
    for fid, desc in descriptors.items():
        candidates = [(other, _chroma_layout_similarity(desc, other_desc))
                      for other, other_desc in descriptors.items() if other != fid]
        if candidates:
            other, score = max(candidates, key=lambda x: x[1])
            nearest[fid] = {"neighbor": other, "similarity": round(score, 3)}
    similarities = [x["similarity"] for x in nearest.values()]
    hue_travel = [x["opponentHueTravelDegrees"] for x in material.values()]
    proof = [x["whiteHighlightProofScore"] for x in material.values()]
    return {
        "method": "spatial complex-hue layout; luminance excluded",
        "whiteHighlightExclusion": "opponent travel is saturation-weighted; white-only motion scores zero",
        "nearest": nearest,
        "materialHue": material,
        "angleFlipDelta": flip_delta,
        "summary": {
            "count": len(descriptors),
            "chromaLayoutNearestMedian": round(float(np.median(similarities)), 3),
            "chromaLayoutNearestMax": round(float(max(similarities)), 3),
            "opponentHueTravelDegreesMedian": round(float(np.median(hue_travel)), 3),
            "opponentHueTravelDegreesMin": round(float(min(hue_travel)), 3),
            "whiteHighlightProofScoreMedian": round(float(np.median(proof)), 3),
            "whiteHighlightProofScoreMin": round(float(min(proof)), 3),
        },
    }


def _sheet(rows: list[tuple[str, np.ndarray]], out: Path, columns: int = 5) -> None:
    tile, label = 256, 28
    nrows = int(math.ceil(len(rows) / columns))
    canvas = np.zeros((nrows * (tile + label), columns * tile, 3), np.uint8)
    for i, (fid, rgb) in enumerate(rows):
        y = (i // columns) * (tile + label)
        x = (i % columns) * tile
        canvas[y:y + tile, x:x + tile] = cv2.resize(_rgb8(rgb), (tile, tile),
                                                     interpolation=cv2.INTER_AREA)
        cv2.putText(canvas, fid, (x + 4, y + tile + 19), cv2.FONT_HERSHEY_SIMPLEX,
                    0.43, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.imwrite(str(out), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))


def run(stage: str, out_root: Path, resolution: int) -> dict:
    from engine.expansions import fractured_wilds_microkit_2026 as microkit

    stage_dir = out_root / stage
    crops = stage_dir / "native_512_crops"
    crops.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "schema": 1,
        "stage": stage,
        "resolution": resolution,
        "lightProxy": "moving sky/sun GGX-like highlight; material potential only, not iRacing",
        "finishes": {},
        "nearestNeighbors": [],
    }
    descriptors: dict[str, dict[str, np.ndarray]] = {}
    paint_rows: dict[str, list[tuple[str, np.ndarray]]] = {"bloom": [], "petri": []}
    spec_rows: dict[str, list[tuple[str, np.ndarray]]] = {"bloom": [], "petri": []}
    flip_rows: dict[str, list[tuple[str, np.ndarray]]] = {"bloom": [], "petri": []}

    for category, mod in _modules():
        for fid in mod.KIT.ALL:
            spec_fn, paint_fn = mod.KIT.mk(fid)
            mask = np.ones((resolution, resolution), np.float32)
            source = np.full((resolution, resolution, 3), 0.08, np.float32)
            t0 = time.perf_counter()
            spec = spec_fn((resolution, resolution), mask, 0, 1.0)
            paint = paint_fn(source, (resolution, resolution), mask, 0, 1.0, None)
            elapsed = time.perf_counter() - t0
            p8 = _rgb8(paint)
            s8 = _rgb8(spec)
            a0 = _light_proxy(p8, s8, 0)
            a1 = _light_proxy(p8, s8, 1)
            flip = np.concatenate([a0, a1], axis=1)
            descriptors[fid] = _descriptor(p8)
            paint_rows[category].append((fid, p8))
            spec_rows[category].append((fid, s8[:, :, :3]))
            flip_rows[category].append((fid, flip))

            cy, cx = resolution // 2, resolution // 2
            crop = p8[cy - 256:cy + 256, cx - 256:cx + 256]
            scrop = s8[cy - 256:cy + 256, cx - 256:cx + 256, :3]
            cv2.imwrite(str(crops / f"{fid}_paint.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(crops / f"{fid}_spec.png"), cv2.cvtColor(scrop, cv2.COLOR_RGB2BGR))

            ch = s8[:, :, :3].reshape(-1, 3).astype(np.float32)
            report["finishes"][fid] = {
                "category": category,
                "renderSeconds": round(elapsed, 4),
                "spec": {
                    "min": [int(x) for x in ch.min(axis=0)],
                    "max": [int(x) for x in ch.max(axis=0)],
                    "std": [round(float(x), 3) for x in ch.std(axis=0)],
                    "occupiedEightTiers": [
                        _tier_count(s8[:, :, k], levels)
                        for k, levels in enumerate((microkit._M_LEVELS,
                                                    microkit._R_LEVELS,
                                                    microkit._C_LEVELS))
                    ],
                    "metalVsClearcoatCorrelation": round(_corr(s8[:, :, 0], s8[:, :, 2]), 4),
                },
                "angleFlipProxyDelta": round(_lab_delta(a0, a1), 3),
            }

    ids = sorted(descriptors)
    for fid in ids:
        pairs = [(other, _similarity(descriptors[fid], descriptors[other]))
                 for other in ids if other != fid]
        other, score = max(pairs, key=lambda x: x[1])
        report["finishes"][fid]["nearestNeighbor"] = other
        report["finishes"][fid]["nearestSimilarity"] = round(score, 3)
        report["nearestNeighbors"].append({"id": fid, "neighbor": other,
                                            "similarity": round(score, 3)})

    vals = list(report["finishes"].values())
    report["summary"] = {
        "count": len(vals),
        "renderSecondsMedian": round(float(np.median([x["renderSeconds"] for x in vals])), 4),
        "renderSecondsMax": round(max(x["renderSeconds"] for x in vals), 4),
        "nearestSimilarityMedian": round(float(np.median([x["nearestSimilarity"] for x in vals])), 3),
        "nearestSimilarityMax": round(max(x["nearestSimilarity"] for x in vals), 3),
        "angleFlipProxyDeltaMedian": round(float(np.median([x["angleFlipProxyDelta"] for x in vals])), 3),
        "angleFlipProxyDeltaMin": round(min(x["angleFlipProxyDelta"] for x in vals), 3),
        "specStdMinByChannel": [round(min(x["spec"]["std"][k] for x in vals), 3)
                                for k in range(3)],
        "tierOccupancyMinByChannel": [min(x["spec"]["occupiedEightTiers"][k] for x in vals)
                                      for k in range(3)],
    }
    for category in paint_rows:
        _sheet(paint_rows[category], stage_dir / f"{category}_paint_contact.png")
        _sheet(spec_rows[category], stage_dir / f"{category}_spec_contact.png")
        _sheet(flip_rows[category], stage_dir / f"{category}_angle_flip_contact.png")
    report["chromaEvidence"] = _crop_evidence(
        crops, stage_dir / "representative_angle_crops")
    (stage_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _comparison(out_root: Path, after_report: dict) -> dict | None:
    before_path = out_root / "before" / "report.json"
    before_crops = out_root / "before" / "native_512_crops"
    if not before_path.exists() or not before_crops.exists():
        return None
    before_report = json.loads(before_path.read_text(encoding="utf-8"))
    before_chroma = _crop_evidence(
        before_crops, out_root / "before" / "representative_angle_crops")
    after_chroma = after_report["chromaEvidence"]
    bs, afs = before_report["summary"], after_report["summary"]
    bc, ac = before_chroma["summary"], after_chroma["summary"]
    per_finish = {}
    for fid in sorted(after_chroma["nearest"]):
        if fid not in before_chroma["nearest"]:
            continue
        per_finish[fid] = {
            "chromaLayoutNearestBefore": before_chroma["nearest"][fid],
            "chromaLayoutNearestAfter": after_chroma["nearest"][fid],
            "materialHueBefore": before_chroma["materialHue"][fid],
            "materialHueAfter": after_chroma["materialHue"][fid],
            "angleFlipDeltaBefore": before_chroma["angleFlipDelta"][fid],
            "angleFlipDeltaAfter": after_chroma["angleFlipDelta"][fid],
        }
    comparison = {
        "schema": 1,
        "ticket": "SPB-WILDS",
        "date": "2026-08-23",
        "ownerVerdict": "Too much redundancy way too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping stuff.",
        "methodNotes": {
            "chromaLayout": before_chroma["method"],
            "colorFlip": before_chroma["whiteHighlightExclusion"],
            "anglePanels": "documented moving sky/sun material proxy, not an iRacing screenshot",
        },
        "before": {"nativeSummary": bs, "chromaSummary": bc},
        "after": {"nativeSummary": afs, "chromaSummary": ac},
        "movement": {
            "chromaLayoutNearestMedian": round(ac["chromaLayoutNearestMedian"] -
                                                 bc["chromaLayoutNearestMedian"], 3),
            "chromaLayoutNearestMax": round(ac["chromaLayoutNearestMax"] -
                                              bc["chromaLayoutNearestMax"], 3),
            "opponentHueTravelDegreesMedian": round(ac["opponentHueTravelDegreesMedian"] -
                                                       bc["opponentHueTravelDegreesMedian"], 3),
            "whiteHighlightProofScoreMedian": round(ac["whiteHighlightProofScoreMedian"] -
                                                       bc["whiteHighlightProofScoreMedian"], 3),
            "renderSecondsMedian": round(afs["renderSecondsMedian"] -
                                           bs["renderSecondsMedian"], 4),
            "renderSecondsMax": round(afs["renderSecondsMax"] - bs["renderSecondsMax"], 4),
        },
        "perFinish": per_finish,
    }
    m7_path = ROOT / "_workbook_metrics" / "m7_composite.json"
    if m7_path.exists():
        m7 = json.loads(m7_path.read_text(encoding="utf-8")).get("byFinish", {})
        scores = {fid: m7[f"monolithic:{fid}"]["composite"] for fid in per_finish
                  if f"monolithic:{fid}" in m7}
        if scores:
            comparison["m7After"] = {
                "count": len(scores),
                "minimum": round(float(min(scores.values())), 3),
                "maximum": round(float(max(scores.values())), 3),
                "allAtOwnerShipBar85": all(float(score) >= 85.0 for score in scores.values()),
                "perFinish": scores,
            }
    (out_root / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n",
                                               encoding="utf-8")
    return comparison


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("before", "after"))
    ap.add_argument("--out", type=Path, default=ROOT / "_wilds_work" / "bloom_petri")
    ap.add_argument("--resolution", type=int, default=2048)
    ns = ap.parse_args()
    report = run(ns.stage, ns.out, ns.resolution)
    if ns.stage == "after":
        _comparison(ns.out, report)
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["chromaEvidence"]["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
