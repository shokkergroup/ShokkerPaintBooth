"""Probe learned car-template priors against Smart TGA number crops.

This is offline Smart TGA tooling. It measures whether the learned
``_car_intel/<slug>/template_mask.png`` prior can explain reviewed hard
negatives such as grilles, headlights, and front clips before any Auto-build
Layers integration. The script is diagnostic: it writes JSON summaries and
contact sheets, but it does not affect app behavior.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - diagnostic fallback on machines without cv2
    cv2 = None


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle74_veto085_strict_corpus_v1/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/cycle75_template_prior_probe_v1")
DEFAULT_INTEL = Path("_car_intel")
WORK = 1024

ALIASES = {
    "audir8gt3": "audir8lmsevo2gt3",
    "dirtlatemodel_438": "dirtlatemodel_358",
    "ferrari488gte": "ferrari488gt3",
    "mercedesamggt3": "mercedesamgevogt3",
    "stockcars_chevycamarozl12022": "stockcars_camarozl12018",
    "stockcars_toyotacamry": "stockcars2_camry2015",
    "stockcars2_chevy_cot": "stockcars2_chevy_gen4cup",
    "streetstock_streetstock3": "streetstock_streetstock2",
    "trucks_silverado": "trucks_silverado2019",
}


def _norm_slug(value: str | None) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value or "").lower())).strip("_")


def _source_path(rec: dict[str, Any]) -> Path | None:
    for key in ("paint", "car", "car_num", "source_path"):
        value = rec.get(key)
        if value:
            return Path(value)
    return None


def _source_slug(rec: dict[str, Any]) -> str | None:
    folder = rec.get("folder")
    if folder:
        return _norm_slug(str(folder))
    source = _source_path(rec)
    if source:
        return _norm_slug(source.parent.name)
    return None


def _resolved_slug(slug: str | None, intel_root: Path) -> str | None:
    if not slug:
        return None
    direct = intel_root / slug
    if direct.is_dir():
        return slug
    alias = ALIASES.get(slug)
    if alias and (intel_root / alias).is_dir():
        return alias
    return None


def _as_xyxy(rec: dict[str, Any], prefer_raw: bool) -> list[int]:
    if prefer_raw and isinstance(rec.get("raw_box"), list) and len(rec["raw_box"]) == 4:
        x, y, w, h = [int(round(float(v))) for v in rec["raw_box"]]
        return [x, y, x + max(0, w), y + max(0, h)]
    box = rec.get("box")
    if isinstance(box, list) and len(box) == 4:
        x0, y0, x1, y1 = [int(round(float(v))) for v in box]
        return [x0, y0, x1, y1]
    if isinstance(rec.get("raw_box"), list) and len(rec["raw_box"]) == 4:
        x, y, w, h = [int(round(float(v))) for v in rec["raw_box"]]
        return [x, y, x + max(0, w), y + max(0, h)]
    return [0, 0, 0, 0]


def _clip_box(box: list[int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    x0 = max(0, min(WORK, x0))
    y0 = max(0, min(WORK, y0))
    x1 = max(0, min(WORK, x1))
    y1 = max(0, min(WORK, y1))
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return x0, y0, x1, y1


def _effective_template_prior(slug: str, intel_root: Path) -> np.ndarray | None:
    mask_path = intel_root / slug / "template_mask.png"
    median_path = intel_root / slug / "median.png"
    if not mask_path.is_file():
        return None
    raw = np.asarray(Image.open(mask_path).convert("L").resize((WORK, WORK), Image.Resampling.NEAREST))
    lowvar = raw > 127
    if cv2 is None or not median_path.is_file():
        return lowvar.astype(np.float32)

    try:
        median = np.asarray(Image.open(median_path).convert("RGB").resize((WORK, WORK), Image.Resampling.BILINEAR))
        hsv = cv2.cvtColor(median, cv2.COLOR_RGB2HSV)
        med_dark = (hsv[:, :, 2] < 72) & (hsv[:, :, 1] < 85)
        med_light = (hsv[:, :, 2] > 168) & (hsv[:, :, 1] < 95)
        template_tone = med_dark | med_light
        gray = cv2.cvtColor(median, cv2.COLOR_RGB2GRAY)
        lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
        flat = cv2.blur((lap < 8).astype(np.float32), (7, 7)) > 0.6
        return (lowvar & template_tone & flat).astype(np.float32)
    except Exception:
        return lowvar.astype(np.float32)


def _raw_template_prior(slug: str, intel_root: Path) -> np.ndarray | None:
    mask_path = intel_root / slug / "template_mask.png"
    if not mask_path.is_file():
        return None
    raw = np.asarray(Image.open(mask_path).convert("L").resize((WORK, WORK), Image.Resampling.BILINEAR))
    return (raw.astype(np.float32) / 255.0).clip(0.0, 1.0)


def _region_stats(prior: np.ndarray | None, box: list[int]) -> dict[str, float]:
    if prior is None:
        return {"mean": 0.0, "max": 0.0, "frac_025": 0.0, "frac_050": 0.0, "area_frac": 0.0}
    x0, y0, x1, y1 = _clip_box(box)
    area = max(0, x1 - x0) * max(0, y1 - y0)
    if area <= 0:
        return {"mean": 0.0, "max": 0.0, "frac_025": 0.0, "frac_050": 0.0, "area_frac": 0.0}
    region = prior[y0:y1, x0:x1]
    return {
        "mean": round(float(region.mean()), 6),
        "max": round(float(region.max()), 6),
        "frac_025": round(float((region >= 0.25).mean()), 6),
        "frac_050": round(float((region >= 0.50).mean()), 6),
        "area_frac": round(float(area / float(WORK * WORK)), 6),
    }


def _center_value(prior: np.ndarray | None, box: list[int]) -> float:
    if prior is None:
        return 0.0
    x0, y0, x1, y1 = _clip_box(box)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    cx = max(0, min(WORK - 1, int(round((x0 + x1) * 0.5))))
    cy = max(0, min(WORK - 1, int(round((y0 + y1) * 0.5))))
    return round(float(prior[cy, cx]), 6)


def _summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "p75": 0.0, "p90": 0.0, "max": 0.0}
    arr = np.asarray(values, dtype=np.float32)
    return {
        "count": int(arr.size),
        "mean": round(float(arr.mean()), 6),
        "median": round(float(np.median(arr)), 6),
        "p75": round(float(np.percentile(arr, 75)), 6),
        "p90": round(float(np.percentile(arr, 90)), 6),
        "max": round(float(arr.max()), 6),
    }


def _threshold_sweep(rows: list[dict[str, Any]], feature: str) -> list[dict[str, Any]]:
    positives = [r for r in rows if r["label"] == "number"]
    negatives = [r for r in rows if r["label"] != "number"]
    out: list[dict[str, Any]] = []
    for threshold in (0.01, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.65, 0.80):
        pos_hit = sum(1 for r in positives if float(r.get(feature, 0.0)) >= threshold)
        neg_hit = sum(1 for r in negatives if float(r.get(feature, 0.0)) >= threshold)
        out.append(
            {
                "feature": feature,
                "threshold": threshold,
                "hard_negative_rejected": neg_hit,
                "hard_negative_total": len(negatives),
                "hard_negative_reject_rate": round(neg_hit / max(1, len(negatives)), 6),
                "number_collateral": pos_hit,
                "number_total": len(positives),
                "number_collateral_rate": round(pos_hit / max(1, len(positives)), 6),
            }
        )
    return out


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, feature: str, limit: int) -> None:
    selected = rows[:limit]
    if not selected:
        return
    cols = 8
    cell = 190
    sheet = Image.new("RGB", (cols * cell, int(np.ceil(len(selected) / cols)) * cell), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(selected):
        x = (index % cols) * cell
        y = (index // cols) * cell
        try:
            img = Image.open(row["file"]).convert("RGB").resize((160, 160), Image.Resampling.LANCZOS)
        except Exception:
            img = Image.new("RGB", (160, 160), (0, 0, 0))
        sheet.paste(img, (x + 15, y + 20))
        draw.text((x + 6, y + 4), f"{index:02d} {row['label'][:12]}", fill=(255, 255, 180))
        draw.text((x + 6, y + 178), f"{feature}={float(row.get(feature, 0.0)):.3f}", fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected manifest list in {path}")
    return data


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_manifest(args.manifest)
    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    effective_cache: dict[str, np.ndarray | None] = {}
    raw_cache: dict[str, np.ndarray | None] = {}
    rows: list[dict[str, Any]] = []
    missing_template = 0
    for index, rec in enumerate(records):
        source_slug = _source_slug(rec)
        resolved_slug = _resolved_slug(source_slug, args.intel_root)
        if resolved_slug not in effective_cache:
            effective_cache[resolved_slug or ""] = (
                _effective_template_prior(resolved_slug, args.intel_root) if resolved_slug else None
            )
            raw_cache[resolved_slug or ""] = _raw_template_prior(resolved_slug, args.intel_root) if resolved_slug else None
        effective = effective_cache[resolved_slug or ""]
        raw = raw_cache[resolved_slug or ""]
        if effective is None:
            missing_template += 1
        box = _as_xyxy(rec, prefer_raw=False)
        raw_box = _as_xyxy(rec, prefer_raw=True)
        effective_box = _region_stats(effective, box)
        effective_raw = _region_stats(effective, raw_box)
        raw_box_stats = _region_stats(raw, box)
        label = "number" if rec.get("truth") == 1 or rec.get("label") == "number" else "hard_negative"
        row = {
            "index": index,
            "label": label,
            "source_slug": source_slug,
            "resolved_slug": resolved_slug,
            "template_available": effective is not None,
            "file": rec.get("file"),
            "box": box,
            "raw_box": raw_box,
            "effective_box_mean": effective_box["mean"],
            "effective_box_max": effective_box["max"],
            "effective_box_frac_025": effective_box["frac_025"],
            "effective_box_frac_050": effective_box["frac_050"],
            "effective_raw_mean": effective_raw["mean"],
            "effective_raw_max": effective_raw["max"],
            "effective_raw_frac_025": effective_raw["frac_025"],
            "effective_raw_frac_050": effective_raw["frac_050"],
            "raw_template_box_mean": raw_box_stats["mean"],
            "raw_template_box_frac_050": raw_box_stats["frac_050"],
            "center_effective": _center_value(effective, raw_box),
            "area_frac": effective_raw["area_frac"],
        }
        rows.append(row)

    features = (
        "effective_box_mean",
        "effective_box_frac_025",
        "effective_raw_mean",
        "effective_raw_frac_025",
        "raw_template_box_mean",
    )
    by_label = {}
    for label in ("number", "hard_negative"):
        label_rows = [r for r in rows if r["label"] == label and r["template_available"]]
        by_label[label] = {feature: _summarize([float(r[feature]) for r in label_rows]) for feature in features}

    source_summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("resolved_slug") or row.get("source_slug") or "unknown")
        summary = source_summary.setdefault(key, {"samples": 0, "numbers": 0, "hard_negatives": 0})
        summary["samples"] += 1
        if row["label"] == "number":
            summary["numbers"] += 1
        else:
            summary["hard_negatives"] += 1

    sweeps = []
    for feature in features:
        sweeps.extend(_threshold_sweep([r for r in rows if r["template_available"]], feature))

    (out_dir / "template_prior_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    for name, label_filter in (
        ("top_template_hard_negatives.png", "hard_negative"),
        ("top_template_numbers.png", "number"),
    ):
        selected = [r for r in rows if r["label"] == label_filter]
        selected.sort(key=lambda r: float(r["effective_raw_frac_025"]), reverse=True)
        _contact_sheet(selected, out_dir / name, f"{label_filter} by effective template overlap", "effective_raw_frac_025", args.sheet_limit)

    summary = {
        "manifest": str(args.manifest),
        "output": str(out_dir.resolve()),
        "records": len(records),
        "template_available_records": sum(1 for r in rows if r["template_available"]),
        "missing_template_records": missing_template,
        "source_summary": source_summary,
        "by_label": by_label,
        "threshold_sweep": sweeps,
        "best_veto_candidates": [
            row
            for row in sweeps
            if row["number_collateral"] <= args.max_number_collateral
        ],
    }
    (out_dir / "template_prior_probe.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--intel-root", type=Path, default=DEFAULT_INTEL)
    parser.add_argument("--sheet-limit", type=int, default=96)
    parser.add_argument("--max-number-collateral", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run_probe(parse_args()), indent=2))


if __name__ == "__main__":
    main()
