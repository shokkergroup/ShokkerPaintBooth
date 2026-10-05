#!/usr/bin/env python
"""Build a catalog-wide SPB finish scorecard.

This is intentionally a heuristic scoreboard, not a replacement for owner
review. It renders every registered surface at a fixed audit size, measures
speed/detail/spec behavior, and writes a spreadsheet that makes weak or slow
items easy to sort by category.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "electron-app" / "server"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from scripts.spb_visual_workbench import (  # noqa: E402
    _block_energy,
    _color_population,
    _fine_energy,
    _macro_energy,
    _micro_macro_ratio,
    _norm01,
    _render_item,
    _residual_energy,
)


@dataclass
class CatalogItem:
    surface: str
    item_id: str
    name: str
    category: str
    description: str
    kind: str
    meta: dict[str, Any]
    active_in_ui: bool
    active_sources: str


@dataclass
class ScoreRow:
    surface: str
    category: str
    item_id: str
    name: str
    description: str
    active_in_ui: bool
    active_sources: str
    status: str
    priority: str
    render_ms: float
    ms_per_megapixel: float
    estimated_2048_ms: float
    paint_quality_100: int
    spec_quality_100: int
    speed_score_100: int
    overall_quality_100: int
    quality_profile: str
    reason_flags: str
    render_kind: str
    error: str
    paint_luma_std: float
    paint_luma_span: float
    paint_fine_energy: float
    paint_residual_energy: float
    paint_block_energy: float
    paint_macro_energy: float
    paint_micro_macro_ratio: float
    paint_color_population: int
    paint_saturation_mean: float
    spec_m_range: float
    spec_r_range: float
    spec_cc_range: float
    spec_m_std: float
    spec_r_std: float
    spec_cc_std: float
    spec_channel_independence: float


def _load_finish_data() -> dict[str, Any]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
function safe(name, fallback) {
  try { return vm.runInContext(name, ctx) || fallback; } catch (e) { return fallback; }
}
function meta(arrName) {
  const arr = safe(arrName, []);
  return Object.fromEntries(arr.filter(x => x && x.id).map(x => [x.id, x]));
}
console.log(JSON.stringify({
  groups: {
    base: safe('BASE_GROUPS', {}),
    pattern: safe('PATTERN_GROUPS', {}),
    special: safe('SPECIAL_GROUPS', {}),
    monolithic: safe('MONOLITHIC_GROUPS', {}),
    spec: safe('SPEC_PATTERN_GROUPS', {})
  },
  meta: {
    base: meta('BASES'),
    pattern: meta('PATTERNS'),
    monolithic: meta('MONOLITHICS'),
    spec: meta('SPEC_PATTERNS')
  }
}));
"""
    out = subprocess.check_output(["node", "-e", script], cwd=SERVER, text=True, encoding="utf-8")
    return json.loads(out)


def _reverse_groups(groups: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for category, ids in groups.items():
        if not isinstance(ids, list):
            continue
        for item_id in ids:
            result.setdefault(str(item_id), str(category))
    return result


def _active_source_map(meta: dict[str, dict[str, Any]], groups: dict[str, list[str]], source_name: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item_id in meta:
        result.setdefault(str(item_id), []).append(f"{source_name} metadata")
    for category, ids in groups.items():
        if not isinstance(ids, list):
            continue
        for item_id in ids:
            result.setdefault(str(item_id), []).append(f"{source_name} group: {category}")
    return result


def _friendly_name(item_id: str, meta: dict[str, Any], fallback: dict[str, Any] | tuple[Any, ...] | None = None) -> str:
    for key in ("name", "label", "title"):
        value = meta.get(key)
        if value:
            return str(value)
    if isinstance(fallback, dict):
        for key in ("name", "label", "title"):
            value = fallback.get(key)
            if value:
                return str(value)
    return item_id.replace("_", " ").replace("-", " ").title()


def _description(meta: dict[str, Any], fallback: dict[str, Any] | tuple[Any, ...] | None = None) -> str:
    for key in ("desc", "description", "details"):
        value = meta.get(key)
        if value:
            return str(value)
    if isinstance(fallback, dict):
        for key in ("desc", "description", "details"):
            value = fallback.get(key)
            if value:
                return str(value)
    return ""


def _quality_profile(surface: str, category: str, item_id: str) -> str:
    text = f"{surface} {category} {item_id}".lower()
    quiet = ("foundation", "oem", "solid", "primer", "clearcoat", "gloss", "matte", "satin")
    if any(token in text for token in quiet):
        return "controlled_material"
    if surface.lower() == "spec overlay pattern" or "spec overlay" in surface.lower():
        return "spec_overlay"
    if "gradient" in text or item_id.startswith(("grad_", "gradm_", "grad3_", "ghostg_")):
        return "gradient"
    if "pattern" in surface.lower():
        return "pattern"
    return "expressive_finish"


def _build_catalog(eng: Any, finish_data: dict[str, Any]) -> list[CatalogItem]:
    groups = finish_data["groups"]
    meta = finish_data["meta"]
    base_group = _reverse_groups(groups.get("base", {}))
    pattern_group = _reverse_groups(groups.get("pattern", {}))
    special_group = _reverse_groups(groups.get("special", {}))
    mono_group = _reverse_groups(groups.get("monolithic", {}))
    spec_group = _reverse_groups(groups.get("spec", {}))
    active_sources = {
        "Base": _active_source_map(meta.get("base", {}), groups.get("base", {}), "BASES"),
        "Pattern": _active_source_map(meta.get("pattern", {}), groups.get("pattern", {}), "PATTERNS"),
        "Special / Monolithic": {},
        "Spec Overlay Pattern": _active_source_map(meta.get("spec", {}), groups.get("spec", {}), "SPEC_PATTERNS"),
    }
    active_sources["Special / Monolithic"].update(_active_source_map(meta.get("monolithic", {}), groups.get("special", {}), "MONOLITHICS/SPECIAL_GROUPS"))
    for item_id, sources in _active_source_map({}, groups.get("monolithic", {}), "MONOLITHIC_GROUPS").items():
        active_sources["Special / Monolithic"].setdefault(item_id, []).extend(sources)

    items: list[CatalogItem] = []

    for item_id, entry in sorted(eng.BASE_REGISTRY.items()):
        ui = meta.get("base", {}).get(item_id, {})
        sources = active_sources["Base"].get(item_id, [])
        items.append(
            CatalogItem(
                surface="Base",
                item_id=item_id,
                name=_friendly_name(item_id, ui, entry),
                category=base_group.get(item_id, "Ungrouped Base"),
                description=_description(ui, entry),
                kind="base",
                meta=dict(ui),
                active_in_ui=bool(sources),
                active_sources="; ".join(sources),
            )
        )

    for item_id, entry in sorted(eng.MONOLITHIC_REGISTRY.items()):
        ui = meta.get("monolithic", {}).get(item_id, {})
        category = special_group.get(item_id) or mono_group.get(item_id) or "Ungrouped Monolithic"
        sources = active_sources["Special / Monolithic"].get(item_id, [])
        items.append(
            CatalogItem(
                surface="Special / Monolithic",
                item_id=item_id,
                name=_friendly_name(item_id, ui, entry),
                category=category,
                description=_description(ui, entry),
                kind="monolithic",
                meta=dict(ui),
                active_in_ui=bool(sources),
                active_sources="; ".join(sources),
            )
        )

    for item_id, entry in sorted(eng.PATTERN_REGISTRY.items()):
        ui = dict(meta.get("pattern", {}).get(item_id, {}))
        if isinstance(entry, dict) and entry.get("image_path") and not ui.get("swatch_image"):
            ui["swatch_image"] = entry["image_path"]
        sources = active_sources["Pattern"].get(item_id, [])
        items.append(
            CatalogItem(
                surface="Pattern",
                item_id=item_id,
                name=_friendly_name(item_id, ui, entry),
                category=pattern_group.get(item_id, "Ungrouped Pattern"),
                description=_description(ui, entry),
                kind="pattern",
                meta=ui,
                active_in_ui=bool(sources),
                active_sources="; ".join(sources),
            )
        )

    from engine.spec_patterns import PATTERN_CATALOG

    for item_id in sorted(PATTERN_CATALOG):
        ui = meta.get("spec", {}).get(item_id, {})
        sources = active_sources["Spec Overlay Pattern"].get(item_id, [])
        items.append(
            CatalogItem(
                surface="Spec Overlay Pattern",
                item_id=item_id,
                name=_friendly_name(item_id, ui),
                category=spec_group.get(item_id, "Ungrouped Spec Overlay"),
                description=_description(ui),
                kind="spec-pattern",
                meta=dict(ui),
                active_in_ui=bool(sources),
                active_sources="; ".join(sources),
            )
        )

    return items


def _clip_score(value: float) -> int:
    if math.isnan(value) or math.isinf(value):
        return 0
    return int(round(max(0.0, min(100.0, value))))


def _smooth_score(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return (3 * t * t - 2 * t * t * t) * 100.0


def _speed_score(estimated_2048_ms: float) -> int:
    if estimated_2048_ms <= 3000:
        return 100
    if estimated_2048_ms <= 5000:
        return _clip_score(100 - (estimated_2048_ms - 3000) / 2000 * 25)
    if estimated_2048_ms <= 12000:
        return _clip_score(75 - (estimated_2048_ms - 5000) / 7000 * 55)
    return _clip_score(20 - min(20, (estimated_2048_ms - 12000) / 3000 * 20))


def _rgb_metrics(rgb: np.ndarray) -> dict[str, float | int]:
    rgb = np.clip(rgb[:, :, :3].astype(np.float32), 0.0, 1.0)
    luma = rgb.mean(axis=2)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    residual = _residual_energy(luma)
    macro = _macro_energy(luma)
    return {
        "luma_std": float(luma.std()),
        "luma_span": float(luma.max() - luma.min()),
        "fine": _fine_energy(luma),
        "residual": residual,
        "block": _block_energy(luma),
        "macro": macro,
        "micro_macro_ratio": _micro_macro_ratio(residual, macro),
        "color_population": _color_population(rgb),
        "saturation_mean": float(sat.mean()),
    }


def _spec_metrics(spec: np.ndarray | None) -> dict[str, float]:
    if spec is None:
        return {
            "m_range": 0.0,
            "r_range": 0.0,
            "cc_range": 0.0,
            "m_std": 0.0,
            "r_std": 0.0,
            "cc_std": 0.0,
            "independence": 0.0,
        }
    arr = np.asarray(spec)
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    arr = arr[:, :, :3].astype(np.float32)
    chans = [arr[:, :, idx] for idx in range(3)]
    ranges = [float(ch.max() - ch.min()) for ch in chans]
    stds = [float(ch.std()) for ch in chans]
    corr_scores = []
    for a_idx in range(3):
        for b_idx in range(a_idx + 1, 3):
            a = chans[a_idx].ravel()
            b = chans[b_idx].ravel()
            if float(a.std()) < 1e-5 or float(b.std()) < 1e-5:
                corr_scores.append(0.0)
            else:
                corr_scores.append(1.0 - abs(float(np.corrcoef(a, b)[0, 1])))
    return {
        "m_range": ranges[0],
        "r_range": ranges[1],
        "cc_range": ranges[2],
        "m_std": stds[0],
        "r_std": stds[1],
        "cc_std": stds[2],
        "independence": float(np.mean(corr_scores)) if corr_scores else 0.0,
    }


def _paint_quality(metrics: dict[str, float | int], profile: str) -> int:
    detail = _smooth_score(float(metrics["fine"]), 0.004, 0.045)
    residual = _smooth_score(float(metrics["residual"]), 0.002, 0.035)
    range_score = _smooth_score(float(metrics["luma_span"]), 0.05, 0.65)
    color_score = _smooth_score(float(metrics["color_population"]), 1, 24)
    sat_score = _smooth_score(float(metrics["saturation_mean"]), 0.02, 0.28)
    block_penalty = max(0.0, min(22.0, _smooth_score(float(metrics["block"]), 0.18, 0.42) * 0.22))
    macro_penalty = 0.0
    if profile not in {"controlled_material", "gradient"}:
        macro_penalty = max(0.0, min(28.0, _smooth_score(float(metrics["macro"]), 0.040, 0.115) * 0.28))
        if float(metrics["micro_macro_ratio"]) >= 0.48:
            macro_penalty *= 0.35

    if profile == "controlled_material":
        score = 26 + detail * 0.22 + residual * 0.18 + range_score * 0.18 + color_score * 0.08 + sat_score * 0.04
    elif profile == "spec_overlay":
        score = 20 + detail * 0.34 + residual * 0.30 + range_score * 0.18 + color_score * 0.03
    elif profile == "gradient":
        score = 14 + detail * 0.18 + residual * 0.16 + range_score * 0.27 + color_score * 0.18 + sat_score * 0.08
    else:
        score = 10 + detail * 0.26 + residual * 0.24 + range_score * 0.18 + color_score * 0.18 + sat_score * 0.07
    return _clip_score(score - block_penalty - macro_penalty)


def _spec_quality(metrics: dict[str, float], profile: str) -> int:
    m = _smooth_score(metrics["m_range"], 12, 180)
    r = _smooth_score(metrics["r_range"], 12, 150)
    cc = _smooth_score(metrics["cc_range"], 10, 120)
    std = _smooth_score(metrics["m_std"] + metrics["r_std"] + metrics["cc_std"], 8, 130)
    independence = _smooth_score(metrics["independence"], 0.05, 0.45)
    if profile == "controlled_material":
        score = 36 + m * 0.18 + r * 0.18 + cc * 0.12 + std * 0.18 + independence * 0.08
    elif profile == "spec_overlay":
        score = 10 + m * 0.22 + r * 0.18 + cc * 0.20 + std * 0.26 + independence * 0.10
    else:
        score = 16 + m * 0.20 + r * 0.17 + cc * 0.18 + std * 0.24 + independence * 0.10
    return _clip_score(score)


def _flags(
    status: str,
    render_ms: float,
    estimated_2048_ms: float,
    paint_quality: int,
    spec_quality: int,
    paint_metrics: dict[str, float | int],
    spec_metrics: dict[str, float],
    profile: str,
) -> list[str]:
    flags: list[str] = []
    if status != "OK":
        flags.append("broken_render")
    if estimated_2048_ms > 5000:
        flags.append("slow_estimated_2048")
    elif estimated_2048_ms > 3000:
        flags.append("watch_estimated_2048")
    if render_ms > 5000:
        flags.append("slow_actual_audit_render")
    if paint_quality < 55:
        flags.append("low_paint_quality")
    if spec_quality < 55:
        flags.append("low_spec_quality")
    if profile != "controlled_material" and float(paint_metrics["fine"]) < 0.010:
        flags.append("low_fine_detail")
    if profile != "controlled_material" and float(paint_metrics["residual"]) < 0.007:
        flags.append("low_micro_detail")
    if profile != "controlled_material" and float(paint_metrics["residual"]) < 0.012:
        flags.append("needs_2048_micro_detail")
    if profile not in {"controlled_material", "gradient"} and float(paint_metrics["macro"]) > 0.045 and float(paint_metrics["micro_macro_ratio"]) < 0.42:
        flags.append("macro_dominated_too_large")
    if profile != "controlled_material" and int(paint_metrics["color_population"]) < 3:
        flags.append("low_color_population")
    if float(paint_metrics["block"]) > 0.24:
        flags.append("large_blocky_forms")
    if spec_metrics["m_range"] < 24 and spec_metrics["r_range"] < 24 and spec_metrics["cc_range"] < 24:
        flags.append("flat_spec_finish")
    return flags


def _priority(status: str, overall: int, flags: list[str]) -> str:
    if status != "OK" or "broken_render" in flags:
        return "BROKEN"
    if "slow_estimated_2048" in flags or overall < 55:
        return "FIX"
    if overall < 70 or flags:
        return "REVIEW"
    return "PASS"


def _score_item(eng: Any, item: CatalogItem, size: int, seed: int) -> ScoreRow:
    start = time.perf_counter()
    status = "OK"
    error = ""
    render_kind = item.kind
    rgb = None
    spec = None
    try:
        rgb, spec, render_kind = _render_item(eng, item.item_id, item.kind, size, seed, item.meta)
    except Exception as exc:
        status = "BROKEN"
        error = f"{type(exc).__name__}: {exc}"
        rgb = np.zeros((size, size, 3), dtype=np.float32)
        spec = None
    render_ms = (time.perf_counter() - start) * 1000.0
    mp = (size * size) / 1_000_000.0
    ms_per_mp = render_ms / max(mp, 1e-9)
    estimated_2048 = ms_per_mp * ((2048 * 2048) / 1_000_000.0)

    profile = _quality_profile(item.surface, item.category, item.item_id)
    paint = _rgb_metrics(rgb)
    specm = _spec_metrics(spec)
    paint_quality = _paint_quality(paint, profile) if status == "OK" else 0
    spec_quality = _spec_quality(specm, profile) if status == "OK" else 0
    speed = _speed_score(estimated_2048) if status == "OK" else 0
    overall = _clip_score(paint_quality * 0.43 + spec_quality * 0.43 + speed * 0.14)
    flags = _flags(status, render_ms, estimated_2048, paint_quality, spec_quality, paint, specm, profile)
    priority = _priority(status, overall, flags)

    return ScoreRow(
        surface=item.surface,
        category=item.category,
        item_id=item.item_id,
        name=item.name,
        description=item.description,
        active_in_ui=item.active_in_ui,
        active_sources=item.active_sources,
        status=status,
        priority=priority,
        render_ms=round(render_ms, 2),
        ms_per_megapixel=round(ms_per_mp, 2),
        estimated_2048_ms=round(estimated_2048, 2),
        paint_quality_100=paint_quality,
        spec_quality_100=spec_quality,
        speed_score_100=speed,
        overall_quality_100=overall,
        quality_profile=profile,
        reason_flags=", ".join(flags),
        render_kind=render_kind,
        error=error,
        paint_luma_std=round(float(paint["luma_std"]), 6),
        paint_luma_span=round(float(paint["luma_span"]), 6),
        paint_fine_energy=round(float(paint["fine"]), 6),
        paint_residual_energy=round(float(paint["residual"]), 6),
        paint_block_energy=round(float(paint["block"]), 6),
        paint_macro_energy=round(float(paint["macro"]), 6),
        paint_micro_macro_ratio=round(float(paint["micro_macro_ratio"]), 6),
        paint_color_population=int(paint["color_population"]),
        paint_saturation_mean=round(float(paint["saturation_mean"]), 6),
        spec_m_range=round(specm["m_range"], 3),
        spec_r_range=round(specm["r_range"], 3),
        spec_cc_range=round(specm["cc_range"], 3),
        spec_m_std=round(specm["m_std"], 3),
        spec_r_std=round(specm["r_std"], 3),
        spec_cc_std=round(specm["cc_std"], 3),
        spec_channel_independence=round(specm["independence"], 4),
    )


def _import_engine() -> Any:
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import shokker_engine_v2 as eng

        if hasattr(eng, "_ensure_expansions_loaded"):
            eng._ensure_expansions_loaded()
    return eng


def _write_excel(out_path: Path, rows: list[ScoreRow], size: int, elapsed: float) -> None:
    df = pd.DataFrame([asdict(row) for row in rows])
    needs = df[df["priority"].isin(["BROKEN", "FIX", "REVIEW"])].sort_values(
        ["priority", "overall_quality_100", "estimated_2048_ms"], ascending=[True, True, False]
    )
    summary = (
        df.groupby(["surface", "category"], dropna=False)
        .agg(
            count=("item_id", "count"),
            avg_overall=("overall_quality_100", "mean"),
            avg_paint=("paint_quality_100", "mean"),
            avg_spec=("spec_quality_100", "mean"),
            avg_est_2048_ms=("estimated_2048_ms", "mean"),
            broken=("priority", lambda s: int((s == "BROKEN").sum())),
            fix=("priority", lambda s: int((s == "FIX").sum())),
            review=("priority", lambda s: int((s == "REVIEW").sum())),
            pass_count=("priority", lambda s: int((s == "PASS").sum())),
        )
        .reset_index()
        .sort_values(["fix", "review", "avg_overall"], ascending=[False, False, True])
    )
    for col in ("avg_overall", "avg_paint", "avg_spec", "avg_est_2048_ms"):
        summary[col] = summary[col].round(2)

    method_rows = [
        {"Field": "Audit size", "Value": f"{size}x{size}"},
        {"Field": "Elapsed seconds", "Value": round(elapsed, 2)},
        {"Field": "Render time", "Value": "Measured at audit size; estimated_2048_ms is linear per-megapixel projection for triage."},
        {"Field": "Paint quality", "Value": "Luma range, fine detail, residual micro-detail, color population, saturation, with blocky-form penalty."},
        {"Field": "Spec quality", "Value": "M/R/CC channel range, standard deviation, and channel independence."},
        {"Field": "Overall", "Value": "43% paint + 43% spec + 14% speed."},
        {"Field": "Priority", "Value": "BROKEN/FIX/REVIEW/PASS based on render errors, low scores, and >5s estimated 2048 render risk."},
        {"Field": "Caution", "Value": "This is a sorting tool. Owner visual review still decides whether a finish is actually awesome."},
        {"Field": "Active UI filter", "Value": "active_in_ui means the item appears in BASES/PATTERNS/MONOLITHICS/SPEC_PATTERNS metadata or a picker group in paint-booth-0-finish-data.js."},
    ]
    method = pd.DataFrame(method_rows)

    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="All Items", index=False)
        needs.to_excel(writer, sheet_name="Needs Work", index=False)
        summary.to_excel(writer, sheet_name="Category Summary", index=False)
        method.to_excel(writer, sheet_name="Methodology", index=False)

        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#1F2937", "font_color": "#FFFFFF"})
        pass_fmt = workbook.add_format({"bg_color": "#D1FAE5"})
        review_fmt = workbook.add_format({"bg_color": "#FEF3C7"})
        fix_fmt = workbook.add_format({"bg_color": "#FECACA"})
        broken_fmt = workbook.add_format({"bg_color": "#7F1D1D", "font_color": "#FFFFFF"})
        score_fmt = workbook.add_format({"num_format": "0"})
        time_fmt = workbook.add_format({"num_format": "0.00"})

        for sheet_name, frame in (("All Items", df), ("Needs Work", needs), ("Category Summary", summary), ("Methodology", method)):
            ws = writer.sheets[sheet_name]
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, max(len(frame), 1), max(len(frame.columns) - 1, 0))
            for idx, col in enumerate(frame.columns):
                width = min(max(len(str(col)) + 2, 12), 42)
                if col in {"description", "reason_flags", "error"}:
                    width = 48
                if col in {"item_id", "name", "category"}:
                    width = 28
                ws.set_column(idx, idx, width, time_fmt if "ms" in col else None)
                ws.write(0, idx, col, header_fmt)
            for col in ("paint_quality_100", "spec_quality_100", "speed_score_100", "overall_quality_100"):
                if col in frame.columns:
                    idx = list(frame.columns).index(col)
                    ws.set_column(idx, idx, 16, score_fmt)
                    ws.conditional_format(1, idx, max(len(frame), 1), idx, {"type": "3_color_scale"})
            if "priority" in frame.columns:
                pidx = list(frame.columns).index("priority")
                ws.conditional_format(1, pidx, max(len(frame), 1), pidx, {"type": "text", "criteria": "containing", "value": "PASS", "format": pass_fmt})
                ws.conditional_format(1, pidx, max(len(frame), 1), pidx, {"type": "text", "criteria": "containing", "value": "REVIEW", "format": review_fmt})
                ws.conditional_format(1, pidx, max(len(frame), 1), pidx, {"type": "text", "criteria": "containing", "value": "FIX", "format": fix_fmt})
                ws.conditional_format(1, pidx, max(len(frame), 1), pidx, {"type": "text", "criteria": "containing", "value": "BROKEN", "format": broken_fmt})


def _write_html(out_path: Path, rows: list[ScoreRow], size: int, elapsed: float) -> None:
    worst = sorted(rows, key=lambda r: (r.overall_quality_100, -r.estimated_2048_ms))[:80]
    slow = sorted([r for r in rows if r.estimated_2048_ms > 3000], key=lambda r: -r.estimated_2048_ms)[:80]
    by_cat: dict[tuple[str, str], list[ScoreRow]] = {}
    for row in rows:
        by_cat.setdefault((row.surface, row.category), []).append(row)
    cat_rows = []
    for (surface, category), vals in by_cat.items():
        cat_rows.append(
            {
                "surface": surface,
                "category": category,
                "count": len(vals),
                "avg": round(sum(v.overall_quality_100 for v in vals) / len(vals), 1),
                "fix": sum(1 for v in vals if v.priority == "FIX"),
                "review": sum(1 for v in vals if v.priority == "REVIEW"),
                "broken": sum(1 for v in vals if v.priority == "BROKEN"),
            }
        )
    cat_rows.sort(key=lambda x: (-(x["fix"] + x["review"] + x["broken"]), x["avg"]))

    def table(title: str, data: list[Any], cols: list[str]) -> str:
        body = []
        for row in data:
            getter = row.get if isinstance(row, dict) else lambda key: getattr(row, key)
            body.append("<tr>" + "".join(f"<td>{str(getter(col))}</td>" for col in cols) + "</tr>")
        head = "".join(f"<th>{col}</th>" for col in cols)
        return f"<section><h2>{title}</h2><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></section>"

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>SPB Catalog Scorecard</title>
<style>
body {{ background:#0d1117; color:#e6edf3; font:14px Segoe UI, Arial, sans-serif; margin:24px; }}
h1,h2 {{ color:#ff7a18; }} .meta {{ color:#9fb3c8; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0 28px; }}
th,td {{ border:1px solid #273142; padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ background:#182233; position:sticky; top:0; }}
tr:nth-child(even) {{ background:#111827; }}
.pill {{ display:inline-block; border:1px solid #ff7a18; padding:2px 8px; border-radius:999px; color:#ffb86b; }}
</style></head><body>
<h1>SPB Catalog Scorecard</h1>
<p class="meta"><span class="pill">{len(rows)} items</span> <span class="pill">{size}x{size}</span> <span class="pill">{elapsed:.1f}s elapsed</span></p>
<p>Scores are heuristic triage: 43% paint, 43% spec, 14% speed. Owner review still decides what ships.</p>
{table('Weakest Overall', worst, ['surface','category','item_id','name','priority','overall_quality_100','paint_quality_100','spec_quality_100','estimated_2048_ms','reason_flags'])}
{table('Slow / Watch List', slow, ['surface','category','item_id','name','priority','estimated_2048_ms','overall_quality_100','reason_flags'])}
{table('Category Summary', cat_rows[:120], ['surface','category','count','avg','fix','review','broken'])}
</body></html>"""
    out_path.write_text(html, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=512, help="Render size for full catalog scoring")
    parser.add_argument("--seed", type=int, default=7301)
    parser.add_argument("--limit", type=int, default=0, help="Limit item count for smoke testing")
    parser.add_argument("--surface", choices=["all", "base", "monolithic", "pattern", "spec"], default="all")
    parser.add_argument("--active-only", action="store_true", help="Score only picker-visible active UI catalog entries")
    parser.add_argument("--orphans-only", action="store_true", help="Score only registry entries not visible in the UI catalog")
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args(argv)
    if args.active_only and args.orphans_only:
        raise SystemExit("--active-only and --orphans-only cannot be used together")

    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / time.strftime("%Y-%m-%d-spb-catalog-scorecard-v1")
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    print("[scorecard] Loading engine/catalog...", flush=True)
    eng = _import_engine()
    finish_data = _load_finish_data()
    all_items = _build_catalog(eng, finish_data)

    inventory_path = out_dir / "catalog_inventory.csv"
    with inventory_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["surface", "category", "item_id", "name", "active_in_ui", "active_sources", "kind", "description"],
        )
        writer.writeheader()
        for item in all_items:
            writer.writerow(
                {
                    "surface": item.surface,
                    "category": item.category,
                    "item_id": item.item_id,
                    "name": item.name,
                    "active_in_ui": item.active_in_ui,
                    "active_sources": item.active_sources,
                    "kind": item.kind,
                    "description": item.description,
                }
            )
    orphan_path = out_dir / "orphan_inventory.csv"
    with orphan_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["surface", "category", "item_id", "name", "kind", "description"],
        )
        writer.writeheader()
        for item in all_items:
            if not item.active_in_ui:
                writer.writerow(
                    {
                        "surface": item.surface,
                        "category": item.category,
                        "item_id": item.item_id,
                        "name": item.name,
                        "kind": item.kind,
                        "description": item.description,
                    }
                )

    items = all_items
    if args.surface != "all":
        surface_map = {
            "base": "Base",
            "monolithic": "Special / Monolithic",
            "pattern": "Pattern",
            "spec": "Spec Overlay Pattern",
        }
        items = [item for item in items if item.surface == surface_map[args.surface]]
    if args.active_only:
        items = [item for item in items if item.active_in_ui]
    if args.orphans_only:
        items = [item for item in items if not item.active_in_ui]
    if args.limit > 0:
        items = items[: args.limit]

    active_count = sum(1 for item in all_items if item.active_in_ui)
    orphan_count = len(all_items) - active_count
    scope = "active UI catalog" if args.active_only else "orphan registry entries" if args.orphans_only else "all registry entries"
    print(
        f"[scorecard] Inventory: {len(all_items)} total, {active_count} active UI, {orphan_count} orphan/legacy.",
        flush=True,
    )
    print(f"[scorecard] Scoring {len(items)} {scope} item(s) at {args.size}x{args.size}...", flush=True)
    if items:
        try:
            _score_item(eng, items[0], min(args.size, 128), args.seed)
            print("[scorecard] Warmup render complete.", flush=True)
        except Exception as exc:
            print(f"[scorecard] Warmup render failed but scoring will continue: {type(exc).__name__}: {exc}", flush=True)
    rows: list[ScoreRow] = []
    for idx, item in enumerate(items, start=1):
        rows.append(_score_item(eng, item, args.size, args.seed))
        if idx == 1 or idx == len(items) or idx % max(1, args.progress_every) == 0:
            elapsed = time.perf_counter() - started
            print(f"[scorecard] {idx}/{len(items)} {item.surface}: {item.item_id} ({elapsed:.1f}s)", flush=True)

    elapsed = time.perf_counter() - started
    rows.sort(key=lambda row: (row.surface, row.category, row.item_id))

    csv_path = out_dir / "catalog_scorecard.csv"
    json_path = out_dir / "catalog_scorecard.json"
    xlsx_path = out_dir / "catalog_scorecard.xlsx"
    html_path = out_dir / "index.html"

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    json_path.write_text(json.dumps([asdict(row) for row in rows], indent=2), encoding="utf-8")
    _write_excel(xlsx_path, rows, args.size, elapsed)
    _write_html(html_path, rows, args.size, elapsed)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.priority] = counts.get(row.priority, 0) + 1
    print(f"[scorecard] Done in {elapsed:.1f}s", flush=True)
    print(f"[scorecard] Priority counts: {counts}", flush=True)
    print(f"[scorecard] XLSX: {xlsx_path}", flush=True)
    print(f"[scorecard] CSV:  {csv_path}", flush=True)
    print(f"[scorecard] HTML: {html_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
