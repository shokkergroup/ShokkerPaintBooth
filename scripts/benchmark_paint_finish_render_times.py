#!/usr/bin/env python3
"""Benchmark SPB paint-finish render times in resumable chunks.

This covers regular bases, monolithics/special finishes, and dynamic color
finishes such as gradients. It times the actual paint/spec renderer functions
at a requested canvas size and writes a rolling before/after HTML report.
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import html
import io
import json
import os
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "reports" / "paint_finish_perf"
STATE_PATH = OUT_DIR / "state.json"
HTML_PATH = OUT_DIR / "SPB_PAINT_FINISH_RENDER_TIME_OPTIMIZATION_2026-05-31.html"


def _lower_process_priority_for_background_benchmark() -> None:
    """Keep long benchmark chunks from starving live SPB renders on Windows."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.GetCurrentProcess()
        kernel32.SetPriorityClass(handle, 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    except Exception:
        pass


@dataclass
class BenchRow:
    id: str
    kind: str
    module: str
    function: str
    seconds: float
    ms: float
    status: str
    size: int
    paint_mean: float | None = None
    paint_std: float | None = None
    paint_grad_mean: float | None = None
    spec_mean: float | None = None
    spec_std: float | None = None
    spec_grad_mean: float | None = None
    error: str | None = None


def _quiet_imports() -> tuple[dict[str, Any], dict[str, Any]]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY

    return dict(BASE_REGISTRY), dict(MONOLITHIC_REGISTRY)


def _load_finish_colors() -> dict[str, Any]:
    path = REPO / "finish_colors.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _humanize_id(fid: str) -> str:
    return " ".join(part for part in str(fid).replace("-", "_").split("_") if part).title()


def _target_key(kind: str, fid: str) -> str:
    return f"{kind}/{fid}"


def _row_key(row: dict[str, Any]) -> str:
    return _target_key(str(row.get("kind") or ""), str(row.get("id") or ""))


def _load_finish_names() -> dict[str, str]:
    names: dict[str, str] = {}

    finish_data = REPO / "paint-booth-0-finish-data.js"
    if finish_data.is_file():
        text = finish_data.read_text(encoding="utf-8", errors="ignore")
        object_re = re.compile(r"\{[^{}]*?\bid\s*:\s*['\"]([^'\"]+)['\"][^{}]*?\}", re.DOTALL)
        name_re = re.compile(r"\bname\s*:\s*['\"]([^'\"]+)['\"]", re.DOTALL)
        for match in object_re.finditer(text):
            name_match = name_re.search(match.group(0))
            if name_match:
                names.setdefault(match.group(1), name_match.group(1))

    for fid, entry in _load_finish_colors().items():
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("displayName") or entry.get("display_name") or entry.get("title")
            if name:
                names.setdefault(str(fid), str(name))

    return names


def _load_targets(category: str) -> list[tuple[str, str]]:
    base_reg, mono_reg = _quiet_imports()
    dynamic = _load_finish_colors()
    dynamic_prefixes = ("grad_", "gradm_", "grad3_", "ghostg_", "clr_", "cs_duo_", "mc_")

    targets: list[tuple[str, str]] = []
    if category in ("all", "base"):
        targets.extend(("base", fid) for fid in sorted(base_reg))
    if category in ("all", "monolithic", "special"):
        targets.extend(("monolithic", fid) for fid in sorted(mono_reg))
    if category in ("all", "dynamic", "gradient"):
        for fid in sorted(dynamic):
            if fid in mono_reg or fid in base_reg:
                continue
            if fid.startswith(dynamic_prefixes):
                targets.append(("dynamic", fid))
    # Registry merge layers can expose the same kind/id pair more than once.
    # Phase files are keyed by kind/id, so de-dupe here or coverage can never reach 100%.
    return list(dict.fromkeys(targets))


def _read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return dict(default or {})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default or {})
    except json.JSONDecodeError:
        return dict(default or {})


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _empty_paint(shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    paint = np.zeros((h, w, 4), dtype=np.float32)
    paint[:, :, :3] = 0.533
    paint[:, :, 3] = 1.0
    return paint


def _constant_spec(shape: tuple[int, int], m: float, r: float, cc: float) -> np.ndarray:
    h, w = shape
    spec = np.empty((h, w, 3), dtype=np.float32)
    spec[:, :, 0] = float(m)
    spec[:, :, 1] = float(r)
    spec[:, :, 2] = float(cc)
    return spec


def _normalize_spec(result: Any, shape: tuple[int, int], fallback: tuple[float, float, float]) -> np.ndarray:
    if result is None:
        return _constant_spec(shape, *fallback)
    if isinstance(result, (tuple, list)) and len(result) >= 3:
        channels = [np.asarray(result[idx], dtype=np.float32) for idx in range(3)]
        return np.stack(channels, axis=2)
    arr = np.asarray(result)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=2)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        arr = arr[:, :, :3].astype(np.float32, copy=False)
        if float(np.nanmax(arr)) <= 1.5:
            arr = arr * 255.0
        return arr
    return _constant_spec(shape, *fallback)


def _paint_stats(arr_like: Any) -> dict[str, float]:
    arr = np.asarray(arr_like, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        arr = arr[:, :, :3]
    if float(np.nanmax(arr)) > 1.5:
        arr = arr / 255.0
    src = arr.mean(axis=2) if arr.ndim == 3 else arr
    gy = float(np.abs(np.diff(src, axis=0)).mean()) if src.shape[0] > 1 else 0.0
    gx = float(np.abs(np.diff(src, axis=1)).mean()) if src.shape[1] > 1 else 0.0
    return {
        "paint_mean": float(np.nanmean(arr)),
        "paint_std": float(np.nanstd(arr)),
        "paint_grad_mean": (gx + gy) * 0.5,
    }


def _spec_stats(arr_like: Any) -> dict[str, float]:
    arr = np.asarray(arr_like, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        arr = arr[:, :, :3]
        src = arr.mean(axis=2)
    else:
        src = arr
    gy = float(np.abs(np.diff(src, axis=0)).mean()) if src.shape[0] > 1 else 0.0
    gx = float(np.abs(np.diff(src, axis=1)).mean()) if src.shape[1] > 1 else 0.0
    return {
        "spec_mean": float(np.nanmean(arr)),
        "spec_std": float(np.nanstd(arr)),
        "spec_grad_mean": (gx + gy) * 0.5,
    }


def _call_base_spec(fn: Any, entry: dict[str, Any], shape: tuple[int, int], mask: np.ndarray, seed: int, sm: float) -> Any:
    m = entry.get("M", 128)
    r = entry.get("R", 80)
    calls = (
        lambda: fn(shape, seed, sm, m, r),
        lambda: fn(shape, mask, seed, sm),
        lambda: fn((shape[0], shape[1], 3), mask, seed, sm),
    )
    last_exc: Exception | None = None
    for call in calls:
        try:
            return call()
        except (TypeError, ValueError) as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    return None


def _call_mono_spec(fn: Any, shape: tuple[int, int], mask: np.ndarray, seed: int, sm: float) -> Any:
    calls = (
        lambda: fn(shape, mask, seed, sm),
        lambda: fn((shape[0], shape[1], 3), mask, seed, sm),
        lambda: fn(shape, seed, sm, 128, 80),
        lambda: fn(shape, seed, sm),
    )
    last_exc: Exception | None = None
    for call in calls:
        try:
            return call()
        except (TypeError, ValueError) as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    return None


def _entry_functions(kind: str, fid: str) -> tuple[Any, Any, str, str]:
    base_reg, mono_reg = _quiet_imports()
    if kind == "base":
        entry = base_reg[fid]
        spec_fn = entry.get("base_spec_fn") if isinstance(entry, dict) else None
        paint_fn = entry.get("paint_fn") if isinstance(entry, dict) else None
        module = getattr(paint_fn or spec_fn, "__module__", "?")
        function = getattr(paint_fn or spec_fn, "__name__", "?")
        return spec_fn, paint_fn, module, function
    if kind == "monolithic":
        entry = mono_reg[fid]
        if isinstance(entry, (tuple, list)):
            spec_fn = entry[0] if len(entry) > 0 else None
            paint_fn = entry[1] if len(entry) > 1 else None
        elif isinstance(entry, dict):
            spec_fn = entry.get("spec_fn")
            paint_fn = entry.get("paint_fn")
        else:
            spec_fn = None
            paint_fn = entry if callable(entry) else None
        module = getattr(paint_fn or spec_fn, "__module__", "?")
        function = getattr(paint_fn or spec_fn, "__name__", "?")
        return spec_fn, paint_fn, module, function
    return None, None, "engine.render", "render_generic_finish"


def _time_one(kind: str, fid: str, size: int, seed: int, repeat: int) -> BenchRow:
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    spec_fn, paint_fn, module, function = _entry_functions(kind, fid)
    samples: list[float] = []
    last_paint: Any = None
    last_spec: Any = None
    try:
        for idx in range(max(1, repeat)):
            gc.collect()
            paint = _empty_paint(shape)
            start = time.perf_counter()
            if kind == "base":
                base_reg, _mono_reg = _quiet_imports()
                entry = base_reg[fid]
                fallback = (entry.get("M", 128), entry.get("R", 80), entry.get("CC", 16))
                last_spec = _normalize_spec(
                    _call_base_spec(spec_fn, entry, shape, mask, seed + idx, 1.0) if callable(spec_fn) else None,
                    shape,
                    fallback,
                )
                last_paint = paint_fn(paint, shape, mask, seed + idx, 1.0, 0.0) if callable(paint_fn) else paint
            elif kind == "monolithic":
                last_spec = _normalize_spec(
                    _call_mono_spec(spec_fn, shape, mask, seed + idx, 1.0) if callable(spec_fn) else None,
                    shape,
                    (128, 80, 16),
                )
                last_paint = paint_fn(paint, shape, mask, seed + idx, 1.0, 0.0) if callable(paint_fn) else paint
            else:
                from engine.render import render_generic_finish
                from finish_colors_lookup import get_finish_colors

                fc = get_finish_colors(fid)
                if not fc:
                    raise ValueError(f"finish_colors missing for {fid}")
                zone = {"finish": fid, "finish_colors": fc}
                last_spec, last_paint = render_generic_finish(
                    fid, zone, paint, shape, mask, seed + idx, 1.0, 1.0, 0.0
                )
                last_spec = _normalize_spec(last_spec, shape, (128, 80, 16))
            samples.append(time.perf_counter() - start)
        elapsed = statistics.median(samples)
        row_data = {}
        row_data.update(_paint_stats(last_paint))
        row_data.update(_spec_stats(last_spec))
        return BenchRow(
            id=fid,
            kind=kind,
            module=module,
            function=function,
            seconds=round(elapsed, 6),
            ms=round(elapsed * 1000.0, 3),
            status="ok",
            size=size,
            **row_data,
        )
    except Exception as exc:
        elapsed = samples[-1] if samples else 0.0
        return BenchRow(
            id=fid,
            kind=kind,
            module=module,
            function=function,
            seconds=round(elapsed, 6),
            ms=round(elapsed * 1000.0, 3),
            status="error",
            size=size,
            error=f"{type(exc).__name__}: {exc}",
        )


def _select_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
    all_targets = _load_targets(args.category)
    wanted = [part.strip() for part in (args.ids or "").split(",") if part.strip()]
    if wanted:
        by_id: dict[str, list[tuple[str, str]]] = {}
        by_key: dict[str, tuple[str, str]] = {}
        for kind, fid in all_targets:
            by_id.setdefault(fid, []).append((kind, fid))
            by_key[_target_key(kind, fid)] = (kind, fid)
            by_key[f"{kind}:{fid}"] = (kind, fid)
        before_kind: dict[str, str] = {}
        if args.phase == "after":
            before_data = _read_json(OUT_DIR / "before.json", {"rows": []})
            before_kind = {
                row["id"]: row.get("kind", "")
                for row in before_data.get("rows", [])
                if isinstance(row, dict) and row.get("id")
            }
        selected: list[tuple[str, str]] = []
        for fid in wanted:
            keyed = by_key.get(fid)
            if keyed is not None:
                selected.append(keyed)
                continue
            matches = by_id.get(fid, [])
            preferred_kind = before_kind.get(fid)
            preferred = next((target for target in matches if target[0] == preferred_kind), None)
            if preferred is not None:
                selected.append(preferred)
            elif matches:
                selected.extend(matches)
        return list(dict.fromkeys(selected))
    if args.slowest:
        phase_data = _read_json(OUT_DIR / f"{args.slowest_from}.json")
        rows = [row for row in phase_data.get("rows", []) if row.get("status") == "ok"]
        rows.sort(key=lambda row: float(row.get("seconds") or 0.0), reverse=True)
        target_set = set(all_targets)
        selected = []
        for row in rows[: args.slowest]:
            target = (str(row.get("kind") or ""), str(row.get("id") or ""))
            if target in target_set:
                selected.append(target)
        return selected
    if args.next:
        state = _read_json(STATE_PATH)
        key = f"{args.phase}:{args.category}:{args.size}"
        offset = int(state.get(key, 0))
        chunk = all_targets[offset : offset + args.chunk_size]
        state[key] = offset + len(chunk)
        state[f"{key}:total"] = len(all_targets)
        state["last_key"] = key
        state["last_updated"] = datetime.now().isoformat(timespec="seconds")
        _write_json(STATE_PATH, state)
        return chunk
    return all_targets[: args.limit] if args.limit else all_targets


def _merge_phase(phase: str, rows: Iterable[BenchRow], args: argparse.Namespace, total_targets: int) -> dict[str, Any]:
    path = OUT_DIR / f"{phase}.json"
    data = _read_json(path, {"rows": []})
    existing = {_row_key(row): row for row in data.get("rows", []) if isinstance(row, dict) and row.get("id")}
    for row in rows:
        existing[_target_key(row.kind, row.id)] = asdict(row)
    merged_rows = sorted(existing.values(), key=lambda row: (row.get("kind", ""), row.get("id", "")))
    ok_rows = [row for row in merged_rows if row.get("status") == "ok"]
    times = [float(row.get("seconds") or 0.0) for row in ok_rows]
    data = {
        "phase": phase,
        "created_or_updated_at": datetime.now().isoformat(timespec="seconds"),
        "size": args.size,
        "seed": args.seed,
        "repeat": args.repeat,
        "category": args.category,
        "target_count": total_targets,
        "count": len(merged_rows),
        "ok_count": len(ok_rows),
        "error_count": len(merged_rows) - len(ok_rows),
        "complete": len(merged_rows) >= total_targets if total_targets else False,
        "total_seconds": round(sum(times), 6),
        "max_seconds": round(max(times), 6) if times else 0.0,
        "p95_seconds": round(statistics.quantiles(times, n=20)[-1], 6) if len(times) >= 20 else (round(max(times), 6) if times else 0.0),
        "rows": merged_rows,
    }
    _write_json(path, data)
    return data


def _fmt_ms(sec: float | None) -> str:
    return "" if sec is None else f"{sec * 1000.0:.1f}"


def _fmt_sec(sec: float | None) -> str:
    return "" if sec is None else f"{sec:.3f}"


def _fmt_dual(sec: float | None) -> str:
    return "" if sec is None else f"{sec:.3f}s ({sec * 1000.0:.1f} ms)"


def _pct(before: float, after: float) -> str:
    if before <= 0:
        return ""
    return f"{((before - after) / before) * 100.0:.1f}%"


def _summary_card(title: str, data: dict[str, Any]) -> str:
    return f"""
    <div class="card">
      <h2>{html.escape(title)}</h2>
      <p>Coverage: <strong>{data.get('count', 0)} / {data.get('target_count', 0)}</strong></p>
      <p>Total measured time: <strong>{float(data.get('total_seconds') or 0.0):.3f}s</strong></p>
      <p>Max finish: <strong>{_fmt_dual(float(data.get('max_seconds') or 0.0))}</strong></p>
      <p>P95: <strong>{_fmt_dual(float(data.get('p95_seconds') or 0.0))}</strong></p>
      <p>OK/Error: {data.get('ok_count', 0)} / {data.get('error_count', 0)}</p>
    </div>"""


def _top_list(rows: list[dict[str, Any]], names: dict[str, str]) -> str:
    slow = sorted(
        [row for row in rows if row.get("status") == "ok"],
        key=lambda row: float(row.get("seconds") or 0.0),
        reverse=True,
    )[:20]
    return "\n".join(
        f"<li><strong>{html.escape(names.get(row['id'], _humanize_id(row['id'])))}</strong> "
        f"<code>{html.escape(row['id'])}</code> <span>{html.escape(row.get('kind', ''))}</span>: "
        f"{_fmt_dual(float(row.get('seconds') or 0.0))}</li>"
        for row in slow
    )


def _base_budget_list(rows: list[dict[str, Any]], names: dict[str, str]) -> str:
    offenders = sorted(
        [
            row
            for row in rows
            if row.get("kind") == "base" and row.get("status") == "ok" and float(row.get("seconds") or 0.0) > 4.0
        ],
        key=lambda row: float(row.get("seconds") or 0.0),
        reverse=True,
    )
    if not offenders:
        return "<p>No measured base finishes are currently above the 4.000s hard ceiling.</p>"
    items = "\n".join(
        f"<li><strong>{html.escape(names.get(row['id'], _humanize_id(row['id'])))}</strong> "
        f"<code>{html.escape(row['id'])}</code>: {_fmt_dual(float(row.get('seconds') or 0.0))} "
        f"<span class=\"small\">{html.escape(str(row.get('module') or ''))}</span></li>"
        for row in offenders[:80]
    )
    tail = ""
    if len(offenders) > 80:
        tail = f"<p class=\"small\">Showing the slowest 80 of {len(offenders)} measured base offenders.</p>"
    return f"<p><strong>{len(offenders)}</strong> measured base finish(es) are above the 4.000s hard ceiling.</p><ol>{items}</ol>{tail}"


def _write_html() -> None:
    before = _read_json(OUT_DIR / "before.json", {"rows": []})
    after = _read_json(OUT_DIR / "after.json", {"rows": []})
    names = _load_finish_names()
    before_rows = {_row_key(row): row for row in before.get("rows", []) if row.get("id")}
    after_rows = {_row_key(row): row for row in after.get("rows", []) if row.get("id")}
    keys = sorted(set(before_rows) | set(after_rows))

    comparisons: list[tuple[float, str, dict[str, Any], dict[str, Any]]] = []
    for key in keys:
        b = before_rows.get(key, {})
        a = after_rows.get(key, {})
        b_sec = float(b.get("seconds") or 0.0)
        a_sec = float(a.get("seconds") or 0.0)
        comparisons.append((b_sec - a_sec, key, b, a))
    comparisons.sort(reverse=True)

    body_rows = []
    for delta, key, b, a in comparisons:
        row = b or a
        fid = str(row.get("id") or "")
        b_sec = float(b.get("seconds") or 0.0)
        a_sec = float(a.get("seconds") or 0.0)
        has_pair = bool(b and a)
        cls = "win" if has_pair and delta > 0.03 else "loss" if has_pair and delta < -0.03 else ""
        delta_sec = f"{delta:+.3f}" if has_pair else ""
        delta_ms = f"{(delta * 1000.0):+.1f}" if has_pair else ""
        speedup = html.escape(_pct(b_sec, a_sec)) if has_pair else ""
        drift = []
        for key in ("paint_std", "paint_grad_mean", "spec_std", "spec_grad_mean"):
            if b.get(key) is not None and a.get(key) is not None:
                drift.append(f"{key}: {float(a[key]) - float(b[key]):+.4f}")
        body_rows.append(
            f"<tr class=\"{cls}\"><td><code>{html.escape(fid)}</code></td>"
            f"<td>{html.escape(names.get(fid, _humanize_id(fid)))}</td>"
            f"<td>{html.escape(str(a.get('kind') or b.get('kind') or ''))}</td>"
            f"<td>{_fmt_sec(b_sec) if b else ''}</td><td>{_fmt_ms(b_sec) if b else ''}</td>"
            f"<td>{_fmt_sec(a_sec) if a else ''}</td><td>{_fmt_ms(a_sec) if a else ''}</td>"
            f"<td>{delta_sec}</td><td>{delta_ms}</td><td>{speedup}</td>"
            f"<td>{html.escape(str(a.get('module') or b.get('module') or ''))}</td>"
            f"<td>{html.escape('; '.join(drift))}</td>"
            f"<td>{html.escape(str(a.get('error') or b.get('error') or ''))}</td></tr>"
        )

    overlap_keys = [key for key in keys if before_rows.get(key) and after_rows.get(key)]
    before_overlap_total = sum(float(before_rows[key].get("seconds") or 0.0) for key in overlap_keys)
    after_overlap_total = sum(float(after_rows[key].get("seconds") or 0.0) for key in overlap_keys)
    total_saved = before_overlap_total - after_overlap_total
    speedup = (total_saved / before_overlap_total * 100.0) if before_overlap_total > 0 else 0.0
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SPB Paint Finish Render Time Optimization</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 28px; color: #1d2329; background: #f8fafc; }}
    h1, h2 {{ margin: 0.2rem 0 0.7rem; }}
    .meta, .card {{ background: #fff; border: 1px solid #d8e0e8; border-radius: 8px; padding: 16px; margin: 14px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #e4e9ef; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ position: sticky; top: 0; background: #edf2f7; z-index: 1; }}
    tr.win {{ background: #edfdf4; }}
    tr.loss {{ background: #fff1f0; }}
    .budget {{ border-left: 4px solid #d97706; }}
    code {{ background: #eef2f6; padding: 1px 4px; border-radius: 4px; }}
    .small {{ color: #586575; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>SPB Paint Finish Render Time Optimization</h1>
  <div class="meta">
    <p><strong>Generated:</strong> {html.escape(datetime.now().isoformat(timespec='seconds'))}</p>
    <p><strong>Scope:</strong> regular bases, monolithics/special finishes, and dynamic color finishes such as gradients.</p>
    <p><strong>Method:</strong> resumable chunks; combined paint/spec function timing at requested canvas size. Quality guard columns track paint/spec detail drift.</p>
    <p><strong>Base render budget:</strong> 4.000 seconds is the hard ceiling; anything above that goes into the base offender list.</p>
    <p class="small">Green rows improved by more than 30 ms. Red rows slowed by more than 30 ms.</p>
  </div>
  <div class="grid">
    {_summary_card('Before Baseline', before)}
    {_summary_card('After Optimization', after)}
    <div class="card">
      <h2>Delta</h2>
      <p>Total saved on measured overlap: <strong>{total_saved:+.3f}s</strong></p>
      <p>Measured speedup: <strong>{speedup:.1f}%</strong></p>
      <p>Overlap measured: <strong>{len(overlap_keys)}</strong> finish(es)</p>
      <p class="small">This report fills in overnight as chunks complete.</p>
    </div>
  </div>
  <div class="grid">
    <div class="card"><h2>Slowest Before</h2><ol>{_top_list(before.get('rows', []), names)}</ol></div>
    <div class="card"><h2>Slowest After</h2><ol>{_top_list(after.get('rows', []), names)}</ol></div>
  </div>
  <div class="card budget">
    <h2>Current Base Over 4.000s</h2>
    {_base_budget_list(after.get('rows', []), names)}
    <h2>Baseline Base Over 4.000s</h2>
    {_base_budget_list(before.get('rows', []), names)}
  </div>
  <h2>Before / After By Paint Finish</h2>
  <table>
    <thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Before sec</th><th>Before ms</th><th>After sec</th><th>After ms</th><th>Delta sec</th><th>Delta ms</th><th>Speedup</th><th>Renderer Module</th><th>Quality Stat Drift</th><th>Error</th></tr></thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
</body>
</html>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(doc, encoding="utf-8")


def main() -> int:
    _lower_process_priority_for_background_benchmark()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "after"), default="before")
    parser.add_argument("--category", choices=("all", "base", "monolithic", "special", "dynamic", "gradient"), default="all")
    parser.add_argument("--size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=5312026)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ids", default="")
    parser.add_argument("--next", action="store_true", help="Benchmark the next resumable chunk for this phase/category/size.")
    parser.add_argument("--slowest", type=int, default=0, help="Benchmark the N slowest IDs from another phase file.")
    parser.add_argument("--slowest-from", default="before")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    targets = _select_targets(args)
    total_targets = len(_load_targets(args.category))
    rows: list[BenchRow] = []
    for idx, (kind, fid) in enumerate(targets, start=1):
        if args.progress:
            print(f"[{idx}/{len(targets)}] {kind}/{fid}", flush=True)
        row = _time_one(kind, fid, args.size, args.seed, args.repeat)
        rows.append(row)
        if args.progress:
            print(f"  -> {row.ms:.1f} ms {row.status}", flush=True)
    phase_data = _merge_phase(args.phase, rows, args, total_targets)
    _write_html()
    print(
        f"{args.phase}: measured {len(rows)} row(s); "
        f"coverage {phase_data.get('count', 0)}/{phase_data.get('target_count', 0)}; "
        f"report {HTML_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
