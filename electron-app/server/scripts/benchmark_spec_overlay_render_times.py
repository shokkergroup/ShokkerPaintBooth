#!/usr/bin/env python3
"""Benchmark SPB spec overlay render times and optionally write an HTML diff.

This is intentionally narrow: it times `engine.spec_patterns.PATTERN_CATALOG`
directly so spec overlay optimization work has a clean before/after artifact.

SPB-105 / owner overnight overhaul Round 1 (2026-07-13): added live-picker
scope so all five rounds compare the exact customer-visible 181-item catalog.
Owner verdict: "WIDE diversity... optimal render speeds." Baseline movement is
recorded in `_spec_overlay_overhaul/round1_baseline/perf_2048.json`.
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import html
import io
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


@dataclass
class BenchRow:
    id: str
    module: str
    function: str
    seconds: float
    ms: float
    status: str
    ndim: int | None = None
    shape: list[int] | None = None
    dtype: str | None = None
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    grad_mean: float | None = None
    error: str | None = None


def _load_catalog() -> dict[str, Any]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.spec_patterns import PATTERN_CATALOG

    return dict(PATTERN_CATALOG)


def _stats(arr_like: Any) -> dict[str, Any]:
    arr = np.asarray(arr_like)
    arr_f = arr.astype(np.float32, copy=False)
    if arr_f.ndim >= 2:
        if arr_f.ndim == 3:
            grad_src = arr_f[:, :, 0]
        else:
            grad_src = arr_f
        gy = np.abs(np.diff(grad_src, axis=0)).mean() if grad_src.shape[0] > 1 else 0.0
        gx = np.abs(np.diff(grad_src, axis=1)).mean() if grad_src.shape[1] > 1 else 0.0
        grad_mean = float((gx + gy) * 0.5)
    else:
        grad_mean = 0.0
    return {
        "ndim": int(arr.ndim),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "min": float(np.nanmin(arr_f)),
        "max": float(np.nanmax(arr_f)),
        "mean": float(np.nanmean(arr_f)),
        "std": float(np.nanstd(arr_f)),
        "grad_mean": grad_mean,
    }


def _call_pattern(fn: Any, shape: tuple[int, int], seed: int, sm: float) -> Any:
    try:
        return fn(shape, seed=seed, sm=sm)
    except TypeError:
        return fn(shape, seed, sm)


def _time_one(pid: str, fn: Any, shape: tuple[int, int], seed: int, sm: float, repeat: int) -> BenchRow:
    module = getattr(fn, "__module__", "?")
    function = getattr(fn, "__name__", repr(fn))
    samples: list[float] = []
    last_out: Any = None
    try:
        for idx in range(max(1, repeat)):
            gc.collect()
            start = time.perf_counter()
            last_out = _call_pattern(fn, shape, seed + idx, sm)
            samples.append(time.perf_counter() - start)
        elapsed = statistics.median(samples)
        data = _stats(last_out)
        return BenchRow(
            id=pid,
            module=module,
            function=function,
            seconds=round(elapsed, 6),
            ms=round(elapsed * 1000.0, 3),
            status="ok",
            **data,
        )
    except Exception as exc:
        elapsed = samples[-1] if samples else 0.0
        return BenchRow(
            id=pid,
            module=module,
            function=function,
            seconds=round(elapsed, 6),
            ms=round(elapsed * 1000.0, 3),
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def _bench(args: argparse.Namespace) -> dict[str, Any]:
    catalog = _load_catalog()
    ids = [part.strip() for part in (args.ids or "").split(",") if part.strip()]
    if ids:
        items = [(pid, catalog[pid]) for pid in ids if pid in catalog]
    elif args.visible_only:
        from scripts.audit_spec_pattern_quality import _load_ui_spec_patterns
        specs, _ = _load_ui_spec_patterns()
        visible_ids = [str(meta.get("id") or "") for meta in specs]
        items = [(pid, catalog[pid]) for pid in visible_ids if pid in catalog]
    else:
        items = sorted(catalog.items(), key=lambda item: item[0])
    shape = (args.size, args.size)
    rows = []
    for idx, (pid, fn) in enumerate(items, start=1):
        if args.progress:
            print(f"[{idx}/{len(items)}] {pid}", flush=True)
        row = _time_one(pid, fn, shape, args.seed, args.sm, args.repeat)
        rows.append(row)
        if args.progress:
            print(f"  -> {row.ms:.1f} ms {row.status}", flush=True)
    ok_rows = [row for row in rows if row.status == "ok"]
    slow_rows = sorted(ok_rows, key=lambda row: row.seconds, reverse=True)
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "size": args.size,
        "seed": args.seed,
        "sm": args.sm,
        "repeat": args.repeat,
        "count": len(rows),
        "ok_count": len(ok_rows),
        "error_count": len(rows) - len(ok_rows),
        "total_seconds": round(sum(row.seconds for row in ok_rows), 6),
        "max_seconds": round(max((row.seconds for row in ok_rows), default=0.0), 6),
        "p95_seconds": round(
            statistics.quantiles([row.seconds for row in ok_rows], n=20)[-1]
            if len(ok_rows) >= 20
            else max((row.seconds for row in ok_rows), default=0.0),
            6,
        ),
        "rows": [asdict(row) for row in slow_rows] + [asdict(row) for row in rows if row.status != "ok"],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(before: float, after: float) -> str:
    if before <= 0:
        return ""
    return f"{((before - after) / before) * 100.0:.1f}%"


def _fmt_ms(sec: float | None) -> str:
    if sec is None:
        return ""
    return f"{sec * 1000.0:.1f}"


def _html_report(before: dict[str, Any], after: dict[str, Any], out_path: Path, notes: str) -> None:
    before_rows = {row["id"]: row for row in before.get("rows", [])}
    after_rows = {row["id"]: row for row in after.get("rows", [])}
    ids = sorted(set(before_rows) | set(after_rows))

    comparisons = []
    for pid in ids:
        b = before_rows.get(pid, {})
        a = after_rows.get(pid, {})
        b_sec = float(b.get("seconds") or 0.0)
        a_sec = float(a.get("seconds") or 0.0)
        comparisons.append((b_sec - a_sec, pid, b, a))
    comparisons.sort(reverse=True)

    def row_html(pid: str, b: dict[str, Any], a: dict[str, Any]) -> str:
        b_sec = float(b.get("seconds") or 0.0)
        a_sec = float(a.get("seconds") or 0.0)
        delta = b_sec - a_sec
        cls = "win" if delta > 0.03 else "loss" if delta < -0.03 else ""
        drift_bits = []
        for key in ("mean", "std", "grad_mean"):
            if b.get(key) is not None and a.get(key) is not None:
                drift_bits.append(f"{key}: {float(a[key]) - float(b[key]):+.4f}")
        return (
            f"<tr class=\"{cls}\"><td><code>{html.escape(pid)}</code></td>"
            f"<td>{_fmt_ms(b.get('seconds'))}</td><td>{_fmt_ms(a.get('seconds'))}</td>"
            f"<td>{(delta * 1000.0):+.1f}</td><td>{html.escape(_pct(b_sec, a_sec))}</td>"
            f"<td>{html.escape(str(a.get('module') or b.get('module') or ''))}</td>"
            f"<td>{html.escape('; '.join(drift_bits))}</td></tr>"
        )

    rows_html = "\n".join(row_html(pid, b, a) for _, pid, b, a in comparisons)
    top_before = sorted(before.get("rows", []), key=lambda row: float(row.get("seconds") or 0), reverse=True)[:15]
    top_after = sorted(after.get("rows", []), key=lambda row: float(row.get("seconds") or 0), reverse=True)[:15]

    def top_list(rows: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"<li><code>{html.escape(row['id'])}</code>: {float(row.get('seconds') or 0) * 1000.0:.1f} ms</li>"
            for row in rows
        )

    doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>SPB Spec Overlay Render Time Optimization</title>
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
    code {{ background: #eef2f6; padding: 1px 4px; border-radius: 4px; }}
    .small {{ color: #586575; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>SPB Spec Overlay Render Time Optimization</h1>
  <div class=\"meta\">
    <p><strong>Generated:</strong> {html.escape(datetime.now().isoformat(timespec='seconds'))}</p>
    <p><strong>Canvas:</strong> {before.get('size')}x{before.get('size')} before, {after.get('size')}x{after.get('size')} after. Seed {after.get('seed')}, sm {after.get('sm')}.</p>
    <p><strong>Notes:</strong> {html.escape(notes or 'No notes supplied.')}</p>
  </div>
  <div class=\"grid\">
    <div class=\"card\">
      <h2>Before</h2>
      <p>Total catalog time: <strong>{before.get('total_seconds', 0):.3f}s</strong></p>
      <p>Max pattern: <strong>{before.get('max_seconds', 0) * 1000.0:.1f} ms</strong></p>
      <p>P95: <strong>{before.get('p95_seconds', 0) * 1000.0:.1f} ms</strong></p>
      <p>OK/Error: {before.get('ok_count')} / {before.get('error_count')}</p>
    </div>
    <div class=\"card\">
      <h2>After</h2>
      <p>Total catalog time: <strong>{after.get('total_seconds', 0):.3f}s</strong></p>
      <p>Max pattern: <strong>{after.get('max_seconds', 0) * 1000.0:.1f} ms</strong></p>
      <p>P95: <strong>{after.get('p95_seconds', 0) * 1000.0:.1f} ms</strong></p>
      <p>OK/Error: {after.get('ok_count')} / {after.get('error_count')}</p>
    </div>
    <div class=\"card\">
      <h2>Delta</h2>
      <p>Total saved: <strong>{before.get('total_seconds', 0) - after.get('total_seconds', 0):+.3f}s</strong></p>
      <p>Catalog speedup: <strong>{html.escape(_pct(float(before.get('total_seconds') or 0), float(after.get('total_seconds') or 0)))}</strong></p>
      <p class=\"small\">Green rows improved by more than 30 ms; red rows slowed by more than 30 ms.</p>
    </div>
  </div>
  <div class=\"grid\">
    <div class=\"card\"><h2>Slowest Before</h2><ol>{top_list(top_before)}</ol></div>
    <div class=\"card\"><h2>Slowest After</h2><ol>{top_list(top_after)}</ol></div>
  </div>
  <h2>Before / After By Spec Overlay</h2>
  <table>
    <thead><tr><th>ID</th><th>Before ms</th><th>After ms</th><th>Delta ms</th><th>Speedup</th><th>Renderer Module</th><th>Output Stat Drift</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=5302026)
    parser.add_argument("--sm", type=float, default=1.0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--ids", help="Comma-separated catalog ids. Default: all.")
    parser.add_argument("--visible-only", action="store_true", help="Benchmark only ids exposed by SPEC_PATTERNS in the live picker.")
    parser.add_argument("--progress", action="store_true", help="Print each id before and after timing.")
    parser.add_argument("--out-json", type=Path, help="Write benchmark JSON.")
    parser.add_argument("--compare-before", type=Path, help="Existing before JSON.")
    parser.add_argument("--compare-after", type=Path, help="Existing after JSON.")
    parser.add_argument("--out-html", type=Path, help="Write before/after HTML report.")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)

    if args.compare_before and args.compare_after:
        if not args.out_html:
            parser.error("--out-html is required with --compare-before/--compare-after")
        _html_report(_read_json(args.compare_before), _read_json(args.compare_after), args.out_html, args.notes)
        print(f"HTML report: {args.out_html}")
        return 0

    payload = _bench(args)
    text = json.dumps(payload, indent=2)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text + "\n", encoding="utf-8")
        print(f"JSON report: {args.out_json}")
    else:
        print(text)
    print(
        f"Timed {payload['ok_count']}/{payload['count']} spec overlays at {args.size}x{args.size}: "
        f"total={payload['total_seconds']:.3f}s p95={payload['p95_seconds']*1000.0:.1f}ms "
        f"max={payload['max_seconds']*1000.0:.1f}ms"
    )
    for row in payload["rows"][:15]:
        print(f"  {row['id']}: {row.get('ms', 0):.1f} ms {row.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
