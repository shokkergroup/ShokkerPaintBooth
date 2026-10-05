"""Audit and assemble the five isolated Neon Underground v3 pilot proofs.

This is deliberately separate from the live catalog.  It exercises each
candidate through its public ``authored`` path, verifies the owner-facing fine
geometry and causal material contracts, and builds review sheets from the
evidence folders.  It does not register, mirror, or ship a finish.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paint_v2 import neon_material_core_v3 as core  # noqa: E402


CANDIDATES = (
    ("blue_breakdown", "engine.expansions.neon_underground_v3.blue_breakdown", "build_blue_breakdown"),
    ("sodium_scuff", "engine.expansions.neon_underground_v3.sodium_scuff", "build_sodium_scuff"),
    ("redline_shear", "engine.expansions.neon_underground_v3.redline_shear", "build_redline_shear"),
    ("quarter_mile_weave", "engine.expansions.neon_underground_v3.quarter_mile_weave", "build"),
    ("torque_scar", "engine.expansions.neon_underground_v3.torque_scar", "build_torque_scar"),
)
EVIDENCE = ROOT / "_neon_oil_slick_reset_work"


def _rgb(path: Path) -> np.ndarray:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _write_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(np.clip(image, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    if not cv2.imwrite(str(path), bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise OSError(path)


def _label(image: np.ndarray, text: str, bar: int = 48) -> np.ndarray:
    out = np.asarray(image, np.uint8).copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], bar), (5, 7, 13), -1)
    cv2.putText(out, text, (14, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.82,
                (255, 235, 130), 2, cv2.LINE_AA)
    return out


def _paint_signature(paint: np.ndarray) -> np.ndarray:
    small = cv2.resize(np.asarray(paint, np.float32), (192, 192), interpolation=cv2.INTER_AREA)
    lum = small[..., 0] * 0.2126 + small[..., 1] * 0.7152 + small[..., 2] * 0.0722
    # Compare structure rather than palette: local high-pass plus edge energy.
    local = lum - cv2.GaussianBlur(lum, (0, 0), 5.0)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    return np.concatenate((local.ravel(), np.hypot(gx, gy).ravel()))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, np.float64).ravel()
    bb = np.asarray(b, np.float64).ravel()
    if aa.std() < 1e-9 or bb.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(aa, bb)[0, 1])


def _largest_dark_void_native(paint: np.ndarray) -> float:
    lum = np.max(np.asarray(paint, np.float32), axis=2)
    visible = (lum > max(0.055, float(np.quantile(lum, 0.54)))).astype(np.uint8)
    distance = cv2.distanceTransform(1 - visible, cv2.DIST_L2, 5)
    return float(distance.max() * core.NATIVE / paint.shape[0])


def _audit_one(slug: str, module_name: str, builder_name: str) -> tuple[dict[str, Any], np.ndarray]:
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name)

    start = time.perf_counter()
    first = builder()
    paint_native, spec_native = core.resize_result(first)
    elapsed = time.perf_counter() - start

    second = builder()
    deterministic = bool(
        np.array_equal(first.paint, second.paint)
        and np.array_equal(first.spec, second.spec)
    )
    material = core.material_stats(first.spec)
    geometry = core.geometry_stats(first.geometry)
    levels = (core.M_LEVELS, core.R_LEVELS, core.C_LEVELS)
    tier_exact = all(np.array_equal(np.unique(first.spec[..., i]), levels[i]) for i in range(3))
    max_channel_corr = max(abs(float(v)) for v in material["correlation"].values())
    picker = cv2.resize(
        np.clip(first.paint * 255.0, 0, 255).astype(np.uint8),
        (64, 64), interpolation=cv2.INTER_AREA,
    )
    picker_luma = cv2.cvtColor(picker, cv2.COLOR_RGB2GRAY)

    checks = {
        "deterministic": deterministic,
        "native_render_le_3s": elapsed <= 3.0,
        "shape_2048": list(paint_native.shape) == [2048, 2048, 3]
        and list(spec_native.shape) == [2048, 2048, 3],
        "five_plus_families": int(geometry["family_count"]) >= 5,
        "all_geometry_8_32px": float(geometry["fine_8_32_fraction"]) == 1.0,
        "eight_exact_tiers_each": tier_exact,
        "material_std_ge_20": min(float(v) for v in material["std"].values()) >= 20.0,
        "channels_not_copies": max_channel_corr < 0.80,
        "picker_has_structure": float(picker_luma.std()) >= 2.0,
    }
    record: dict[str, Any] = {
        "slug": slug,
        "finish_id": first.finish_id,
        "display_name": first.display_name,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "native_authored_elapsed_seconds": round(elapsed, 6),
        "material": material,
        "geometry": geometry,
        "mask_coverage": core.mask_coverage(first.masks),
        "picker_luma_std": round(float(picker_luma.std()), 6),
        "largest_dark_void_native_px": round(_largest_dark_void_native(first.paint), 3),
        "m7": None,
        "m7_note": "Pending owner keep and live-contract integration; isolated audit does not invent an M7 score.",
    }
    return record, _paint_signature(first.paint)


def _assemble_contacts(records: list[dict[str, Any]]) -> dict[str, str]:
    slugs = [str(r["slug"]) for r in records]
    names = [str(r["display_name"]) for r in records]

    paints = []
    pickers = []
    material_rows = []
    light_rows = []
    for slug, name in zip(slugs, names):
        folder = EVIDENCE / slug
        paint = cv2.resize(_rgb(folder / "paint_2048.png"), (448, 448), interpolation=cv2.INTER_AREA)
        paints.append(_label(paint, name))
        picker = cv2.resize(_rgb(folder / "paint_64.png"), (320, 320), interpolation=cv2.INTER_NEAREST)
        pickers.append(_label(picker, f"{name} - 64px", 42))

        material = cv2.resize(_rgb(folder / "material_contact.png"), (1536, 384), interpolation=cv2.INTER_AREA)
        material_rows.append(_label(material, name))
        sweep = cv2.resize(_rgb(folder / "light_sweep_contact.png"), (1536, 512), interpolation=cv2.INTER_AREA)
        light_rows.append(_label(sweep, name))

    paint_sheet = np.concatenate(paints, axis=1)
    picker_sheet = np.concatenate(pickers, axis=1)
    material_sheet = np.concatenate(material_rows, axis=0)
    light_sheet = np.concatenate(light_rows, axis=0)

    outputs = {
        "paint_contact": "pilot_paint_contact.png",
        "picker_64_contact": "pilot_picker_64_contact.png",
        "material_contact": "pilot_material_contact.png",
        "light_sweep_contact": "pilot_light_sweep_contact.png",
    }
    _write_rgb(EVIDENCE / outputs["paint_contact"], paint_sheet)
    _write_rgb(EVIDENCE / outputs["picker_64_contact"], picker_sheet)
    _write_rgb(EVIDENCE / outputs["material_contact"], material_sheet)
    _write_rgb(EVIDENCE / outputs["light_sweep_contact"], light_sheet)
    return outputs


def run() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    signatures: dict[str, np.ndarray] = {}
    for slug, module_name, builder_name in CANDIDATES:
        record, signature = _audit_one(slug, module_name, builder_name)
        records.append(record)
        signatures[slug] = signature

    m7_path = EVIDENCE / "official_isolated_m7.json"
    m7_payload: dict[str, Any] | None = None
    if m7_path.is_file():
        m7_payload = json.loads(m7_path.read_text(encoding="utf-8"))
        m7_by_slug = {
            str(row.get("slug")): row
            for row in m7_payload.get("byFinish", {}).values()
            if isinstance(row, dict) and row.get("slug")
        }
        for record in records:
            row = m7_by_slug.get(str(record["slug"]))
            if row is None:
                continue
            record["m7"] = row.get("composite")
            record["m7_pass_85"] = bool(row.get("pass_85"))
            record["m7_note"] = "Official workbook modules run against isolated refreshed pilot evidence."
            record["checks"]["official_isolated_m7_ge_85"] = bool(row.get("pass_85"))
            record["status"] = "PASS" if all(record["checks"].values()) else "FAIL"

    distinctness: dict[str, float] = {}
    for index, (left, _, _) in enumerate(CANDIDATES):
        for right, _, _ in CANDIDATES[index + 1:]:
            distinctness[f"{left}__{right}"] = round(_corr(signatures[left], signatures[right]), 6)

    outputs = _assemble_contacts(records)
    ids = [str(r["finish_id"]) for r in records]
    summary = {
        "schema": "spb-neon-oil-slick-five-pilot-audit/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "all_mechanical_checks_pass": all(r["status"] == "PASS" for r in records),
        "unique_finish_ids": len(ids) == len(set(ids)) == 5,
        "pilots": records,
        "pairwise_structural_correlation": distinctness,
        "max_pairwise_structural_correlation": max(abs(v) for v in distinctness.values()),
        "contacts": outputs,
        "official_isolated_m7": m7_payload,
        "official_m7_note": (
            "Official workbook stack ran against isolated refreshed evidence; candidates remain absent from live registry/catalog."
            if m7_payload else
            "Run scripts/spb_neon_oil_slick_pilot_m7.py after final visual iteration."
        ),
    }
    (EVIDENCE / "five_pilot_audit.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    summary = run()
    print(json.dumps({
        "all_mechanical_checks_pass": summary["all_mechanical_checks_pass"],
        "unique_finish_ids": summary["unique_finish_ids"],
        "max_pairwise_structural_correlation": summary["max_pairwise_structural_correlation"],
        "contacts": summary["contacts"],
    }, indent=2))
    return 0 if summary["all_mechanical_checks_pass"] and summary["unique_finish_ids"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
