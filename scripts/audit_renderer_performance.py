#!/usr/bin/env python3
"""Sample renderer performance for shipping patterns, spec overlays, and fusions."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


@dataclass
class PerfRow:
    kind: str
    id: str
    phase: str
    elapsed_sec: float
    budget_sec: float
    over_budget: bool
    error: str | None = None


def _safe_console(text: str) -> str:
    return str(text).encode("ascii", "replace").decode("ascii")


def _load_js_catalogs() -> dict[str, Any]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
const patternGroups = vm.runInContext('PATTERN_GROUPS', ctx);
const specGroups = vm.runInContext('SPEC_PATTERN_GROUPS', ctx);
const specialGroups = vm.runInContext('SPECIAL_GROUPS', ctx);
console.log(JSON.stringify({ patternGroups, specGroups, specialGroups }));
"""
    out = subprocess.check_output(["node", "-e", script], cwd=REPO, text=True, encoding="utf-8")
    return json.loads(out)


def _ordered_unique(groups: dict[str, list[str]]) -> list[str]:
    ids: list[str] = []
    for group_ids in groups.values():
        for item in group_ids:
            if item not in ids:
                ids.append(item)
    return ids


def _sample(ids: list[str], limit: int) -> list[str]:
    if limit <= 0 or len(ids) <= limit:
        return ids
    if limit == 1:
        return [ids[0]]
    step = (len(ids) - 1) / float(limit - 1)
    return [ids[round(i * step)] for i in range(limit)]


def _parse_ids(text: str | None) -> list[str] | None:
    if not text:
        return None
    return [part.strip() for part in text.split(",") if part.strip()]


def _quiet_engine():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import shokker_engine_v2 as eng

        eng._ensure_expansions_loaded()
    return eng


def _time_row(kind: str, item_id: str, phase: str, budget: float, fn: Callable[[], Any]) -> PerfRow:
    start = time.perf_counter()
    try:
        out = fn()
        elapsed = time.perf_counter() - start
        if isinstance(out, np.ndarray) and 0 in out.shape:
            raise ValueError(f"empty array output shape={out.shape}")
        return PerfRow(kind, item_id, phase, round(elapsed, 6), budget, elapsed > budget)
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return PerfRow(kind, item_id, phase, round(elapsed, 6), budget, True, f"{type(exc).__name__}: {exc}")


def _audit_patterns(eng, ids: list[str], size: int, seed: int, budget: float) -> list[PerfRow]:
    from engine.registry import PATTERN_REGISTRY

    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((size, size, 3), 0.42, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    rows: list[PerfRow] = []
    for pid in ids:
        entry = PATTERN_REGISTRY.get(pid)
        if not isinstance(entry, dict):
            rows.append(PerfRow("pattern", pid, "missing_renderer", 0.0, budget, False, "missing PATTERN_REGISTRY entry"))
            continue
        tex_fn = entry.get("texture_fn")
        paint_fn = entry.get("paint_fn")
        if callable(tex_fn):
            rows.append(_time_row("pattern", pid, "texture", budget, lambda tex_fn=tex_fn: tex_fn(shape, mask, seed, 1.0)))
        if callable(paint_fn):
            rows.append(
                _time_row(
                    "pattern",
                    pid,
                    "paint",
                    budget,
                    lambda paint_fn=paint_fn: paint_fn(paint.copy(), shape, mask, seed, 1.0, bb),
                )
            )
        if not callable(tex_fn) and not callable(paint_fn):
            rows.append(PerfRow("pattern", pid, "skipped_static_or_image", 0.0, budget, False, "no callable renderer"))
    return rows


def _audit_spec_patterns(ids: list[str], size: int, seed: int, budget: float) -> list[PerfRow]:
    from engine.spec_patterns import PATTERN_CATALOG

    shape = (size, size)
    rows: list[PerfRow] = []
    for pid in ids:
        fn = PATTERN_CATALOG.get(pid)
        if fn is None:
            rows.append(PerfRow("spec_pattern", pid, "lookup", 0.0, budget, True, "missing PATTERN_CATALOG entry"))
            continue
        rows.append(_time_row("spec_pattern", pid, "render", budget, lambda fn=fn: fn(shape, seed=seed, sm=1.0)))
    return rows


def _audit_fusions(ids: list[str], size: int, seed: int, budget: float) -> list[PerfRow]:
    from engine.expansions import fusions

    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((size, size, 3), 0.18, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    rows: list[PerfRow] = []
    for finish_id in ids:
        entry = fusions.FUSION_REGISTRY.get(finish_id)
        if entry is None:
            rows.append(PerfRow("fusion", finish_id, "lookup", 0.0, budget, True, "missing FUSION_REGISTRY entry"))
            continue
        spec_fn, paint_fn = entry
        rows.append(_time_row("fusion", finish_id, "spec", budget, lambda spec_fn=spec_fn: spec_fn(shape, mask, seed=seed, sm=1.0)))
        rows.append(
            _time_row(
                "fusion",
                finish_id,
                "paint",
                budget,
                lambda paint_fn=paint_fn: paint_fn(paint.copy(), shape, mask, seed=seed, pm=1.0, bb=bb),
            )
        )
    return rows


def _write_reports(out_dir: Path, rows: list[PerfRow], size: int, seed: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    worst = sorted(rows, key=lambda row: (row.over_budget, row.elapsed_sec), reverse=True)
    payload = {
        "size": size,
        "seed": seed,
        "count": len(rows),
        "over_budget_count": sum(1 for row in rows if row.over_budget),
        "max_elapsed_sec": max((row.elapsed_sec for row in rows), default=0.0),
        "rows": [asdict(row) for row in worst],
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Renderer Performance Audit",
        "",
        f"- Size: {size}",
        f"- Timed rows: {len(rows)}",
        f"- Over budget: {payload['over_budget_count']}",
        f"- Max elapsed: {payload['max_elapsed_sec']:.4f}s",
        "",
        "| Kind | ID | Phase | Seconds | Budget | Status |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in worst[:80]:
        status = row.error or ("OVER" if row.over_budget else "OK")
        lines.append(f"| {row.kind} | `{row.id}` | {row.phase} | {row.elapsed_sec:.4f} | {row.budget_sec:.2f} | {status} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--seed", type=int, default=9201)
    ap.add_argument("--sample-limit", type=int, default=40)
    ap.add_argument("--pattern-ids")
    ap.add_argument("--spec-ids")
    ap.add_argument("--fusion-ids")
    ap.add_argument("--pattern-budget", type=float, default=1.25)
    ap.add_argument("--spec-budget", type=float, default=0.90)
    ap.add_argument("--fusion-budget", type=float, default=1.25)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--fail-on-budget", action="store_true")
    args = ap.parse_args(argv)

    catalogs = _load_js_catalogs()
    pattern_ids = _parse_ids(args.pattern_ids) or _sample(_ordered_unique(catalogs["patternGroups"]), args.sample_limit)
    spec_ids = _parse_ids(args.spec_ids) or _sample(_ordered_unique(catalogs["specGroups"]), args.sample_limit)
    eng = _quiet_engine()
    from engine.expansions import fusions

    if args.fusion_ids:
        fusion_ids = _parse_ids(args.fusion_ids) or []
    else:
        shipping_specials = _ordered_unique(catalogs["specialGroups"])
        shipping_fusions = [item_id for item_id in shipping_specials if item_id in fusions.FUSION_REGISTRY]
        fusion_ids = _sample(shipping_fusions or list(fusions.FUSION_REGISTRY), args.sample_limit)

    rows: list[PerfRow] = []
    rows.extend(_audit_patterns(eng, pattern_ids, args.size, args.seed, args.pattern_budget))
    rows.extend(_audit_spec_patterns(spec_ids, args.size, args.seed, args.spec_budget))
    rows.extend(_audit_fusions(fusion_ids, args.size, args.seed, args.fusion_budget))

    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "renderer_performance" / time.strftime("%Y%m%d-%H%M%S")
    _write_reports(out_dir, rows, args.size, args.seed)

    over = [row for row in rows if row.over_budget]
    print(f"Timed rows: {len(rows)}")
    print(f"Over budget: {len(over)}")
    print(f"Output: {out_dir}")
    for row in sorted(over, key=lambda r: r.elapsed_sec, reverse=True)[:20]:
        print(_safe_console(f"  {row.kind}:{row.id}.{row.phase} {row.elapsed_sec:.3f}s > {row.budget_sec:.3f}s {row.error or ''}"))
    return 1 if args.fail_on_budget and over else 0


if __name__ == "__main__":
    raise SystemExit(main())
