#!/usr/bin/env python3
"""Bake the interactive SPB spec-overlay owner-review gallery.

SPB-105 review companion, 2026-07-13. Renders the exact 181 JS picker ids
through the current Python catalog and writes one compact five-panel WebP per
overlay: structure, combined material response, Metallic, Roughness, Clearcoat.
The hand-authored HTML reads the generated ``manifest.js`` and stores owner
feedback locally in the browser.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "_spec_overlay_review"
ASSET_DIR = OUT_DIR / "assets"
REPORT_CANDIDATES = (
    ROOT / "_spec_overlay_overhaul" / "deconfetti_release2_gate_512" / "report.json",
    ROOT / "_spec_overlay_overhaul" / "semantic_final_gate_512" / "report.json",
    ROOT / "_spec_overlay_overhaul" / "round5_final_gate_512" / "report.json",
)


def _norm(field: np.ndarray) -> np.ndarray:
    field = np.asarray(field, dtype=np.float32)
    lo, hi = float(field.min()), float(field.max())
    if hi - lo < 1e-7:
        return np.full_like(field, .5, dtype=np.float32)
    return ((field - lo) / (hi - lo)).astype(np.float32)


def _channel_tint(field: np.ndarray, lane: str) -> np.ndarray:
    value = np.clip(field, 0.0, 1.0)[:, :, None]
    if lane == "m":
        low, high = np.asarray((.025, .010, .014)), np.asarray((1.0, .24, .20))
    elif lane == "r":
        low, high = np.asarray((.012, .025, .015)), np.asarray((.24, 1.0, .30))
    else:
        low, high = np.asarray((.012, .018, .035)), np.asarray((.22, .45, 1.0))
    return (low + value * (high - low)).astype(np.float32)


def _review_strip(arr: np.ndarray, panel_size: int, authored_structure: np.ndarray | None = None) -> np.ndarray:
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"expected 3-channel M/R/CC array, got {arr.shape}")
    arr = np.clip(arr[:, :, :3], 0.0, 1.0).astype(np.float32)
    if arr.shape[:2] != (panel_size, panel_size):
        arr = cv2.resize(arr, (panel_size, panel_size), interpolation=cv2.INTER_AREA)
    m, rough, cc = (arr[:, :, lane] for lane in range(3))
    structure = (_norm(authored_structure) if authored_structure is not None
                 else _norm(m * .40 + (1.0 - rough) * .30 + cc * .30))
    if structure.shape != (panel_size, panel_size):
        structure = cv2.resize(structure, (panel_size, panel_size), interpolation=cv2.INTER_AREA)
    structure_rgb = np.repeat(structure[:, :, None], 3, axis=2)
    combined = np.clip(np.dstack([m, 1.0 - rough, cc]), 0.0, 1.0) ** .88
    panels = (structure_rgb, combined, _channel_tint(m, "m"),
              _channel_tint(rough, "r"), _channel_tint(cc, "cc"))
    return (np.clip(np.hstack(panels), 0.0, 1.0) * 255.0 + .5).astype(np.uint8)


def _load_metrics() -> dict[str, dict]:
    report = next((path for path in REPORT_CANDIDATES if path.is_file()), None)
    if report is None:
        return {}
    data = json.loads(report.read_text(encoding="utf-8"))
    return {str(row["id"]): row for row in data.get("rows", [])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render-size", type=int, default=512)
    ap.add_argument("--panel-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=7301)
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--only", default="", help="Comma-separated ids to rebake; manifest still covers all ids")
    args = ap.parse_args(argv)
    only = {value.strip() for value in args.only.split(",") if value.strip()}

    from scripts.audit_spec_pattern_quality import _load_ui_spec_patterns
    from engine.spec_pattern_families.overhaul_2026 import _coords, _grammar_for, _material_for, _stable, _work_shape
    from engine.spec_pattern_families.semantic_overlays_2026 import semantic_field
    from engine.spec_pattern_families.visible_overlays_2026 import PICKER_VISIBLE_SPEC_IDS

    specs, group_by_id = _load_ui_spec_patterns()
    picker_ids = tuple(str(meta.get("id") or "") for meta in specs)
    if picker_ids != PICKER_VISIBLE_SPEC_IDS:
        raise RuntimeError("JS picker ids drifted from PICKER_VISIBLE_SPEC_IDS; run the parity gate first")

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from engine.spec_patterns import PATTERN_CATALOG

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    metrics = _load_metrics()
    render_size = max(128, int(args.render_size))
    panel_size = max(96, int(args.panel_size))
    started = time.perf_counter()
    rendered = skipped = 0
    items: list[dict] = []

    for index, meta in enumerate(specs, start=1):
        pid = str(meta["id"])
        key = _stable(pid)
        grammar = _grammar_for(pid, key)
        material = _material_for(pid, key)
        asset_name = f"{pid}.webp"
        asset_path = ASSET_DIR / asset_name
        should_render = not only or pid in only or not asset_path.is_file()
        if should_render:
            fn = PATTERN_CATALOG.get(pid)
            if fn is None:
                raise KeyError(f"picker id missing renderer: {pid}")
            arr = np.asarray(fn((render_size, render_size), args.seed, 1.0), dtype=np.float32)
            render_key = key ^ ((int(args.seed) * 0x9E3779B185EBCA87) & 0xFFFFFFFFFFFFFFFF)
            wh, ww, _ = _work_shape((render_size, render_size))
            sx, sy = _coords(wh, ww)
            target_feature = float(np.clip(8.0 + float((render_key >> 19) % 25), 8.0, 32.0))
            feature = max(1.25, target_feature * max(wh, ww) / 2048.0)
            angle = float((render_key >> 27) % 24) * np.pi / 24.0
            authored_structure = semantic_field(pid, sx, sy, feature, angle, render_key,
                                                int((render_key >> 11) % 5))
            strip = _review_strip(arr, panel_size, authored_structure)
            ok = cv2.imwrite(str(asset_path), strip[:, :, ::-1],
                             [cv2.IMWRITE_WEBP_QUALITY, int(np.clip(args.quality, 1, 100))])
            if not ok:
                raise OSError(f"failed to write {asset_path}")
            rendered += 1
        else:
            skipped += 1

        row = metrics.get(pid, {})
        score = round(float(row.get("score", 0.0)), 2) if row else None
        items.append({
            "id": pid,
            "name": str(meta.get("name") or pid),
            "description": str(meta.get("desc") or ""),
            "category": str(group_by_id.get(pid) or meta.get("category") or "Ungrouped"),
            "material": material,
            "grammar": grammar,
            "asset": f"_spec_overlay_review/assets/{asset_name}",
            "score": score,
            "detail": round(float(row.get("detail", 0.0)), 2) if row else None,
            "wow": round(float(row.get("wow", 0.0)), 2) if row else None,
            "physics": round(float(row.get("physics", 0.0)), 2) if row else None,
            "originality": round(float(row.get("originality", 0.0)), 2) if row else None,
            "nearestId": str(row.get("nearest_id") or ""),
            "nearestSimilarity": round(float(row.get("max_abs_correlation", 0.0)), 5) if row else None,
            "channelStds": row.get("channel_stds") or [],
            "channelSpans": row.get("channel_spans") or [],
            "channelCorrelation": round(float(row.get("max_channel_correlation", 0.0)), 5) if row else None,
            "renderMs": round(float(row.get("render_ms", 0.0)), 2) if row else None,
        })
        if should_render and (rendered == 1 or rendered % 20 == 0):
            print(f"[{index:3d}/{len(specs)}] baked {rendered}: {pid}")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest = {
        "version": 1,
        "generatedAt": generated_at,
        "seed": int(args.seed),
        "renderSize": render_size,
        "panelSize": panel_size,
        "count": len(items),
        "materialCounts": dict(sorted(Counter(item["material"] for item in items).items())),
        "grammarCounts": dict(sorted(Counter(item["grammar"] for item in items).items())),
        "items": items,
    }
    manifest_text = "window.SPB_SPEC_OVERLAY_REVIEW = " + json.dumps(
        manifest, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    (OUT_DIR / "manifest.js").write_text(manifest_text, encoding="utf-8")
    seconds = time.perf_counter() - started
    total_bytes = sum(path.stat().st_size for path in ASSET_DIR.glob("*.webp"))
    print(f"Gallery manifest: {len(items)} items; rendered={rendered} skipped={skipped}")
    print(f"Assets: {total_bytes / (1024 * 1024):.1f} MiB; elapsed={seconds:.1f}s")
    print(f"Open: {ROOT / 'SPB_SPEC_OVERLAY_REVIEW.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
