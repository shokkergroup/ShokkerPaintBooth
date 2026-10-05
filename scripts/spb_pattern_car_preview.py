#!/usr/bin/env python3
"""Render SPB-106 pattern reworks through build_multi_zone at 2048² (same as in-app).

Writes flat UV paint + an HTML page that clips to the finish-viewer stock-car
silhouette so you can judge scale on a body, not just square thumbs.

  python scripts/spb_pattern_car_preview.py
  python scripts/spb_pattern_car_preview.py --ids decade_50s_diner_chrome,decade_70s_funk_zigzag
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_IDS = [
    "aztec",
    "corrugated",
    "decade_50s_atomic_reactor",
    "decade_50s_diner_checkerboard",
    "decade_50s_diner_chrome",
    "decade_50s_jukebox_arc",
    "decade_60s_opart_illusion",
    "decade_70s_funk_zigzag",
    "decade_70s_pong_pixel",
    "decade_70s_studio54_glitter",
]

OUT_UV = ROOT / "_pattern_car_preview" / "uv"
OUT_HTML = ROOT / "SPB_PATTERN_CAR_PREVIEW.html"
SIZE = 2048
THUMB = 640


def _zone_for_pattern(pattern_id: str, base: str, paint_rgb: tuple[float, float, float]):
    return {
        "name": f"Car-{pattern_id}",
        "color": "remaining",
        "base": base,
        "pattern": pattern_id,
        "intensity": "100",
        "paint_color": list(paint_rgb),
        "base_color_mode": "solid",
        "base_color": list(paint_rgb),
        "base_color_strength": 0.35,
    }


def render_uv(pattern_id: str, base: str, paint_rgb: tuple[float, float, float], seed: int = 42):
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY
    import shokker_engine_v2 as eng

    eng.BASE_REGISTRY = BASE_REGISTRY
    eng.PATTERN_REGISTRY = PATTERN_REGISTRY
    eng.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY
    eng._spb_apply_regular_pattern_rebuilds()

    gray = np.full((SIZE, SIZE, 3), 140, dtype=np.uint8)
    with tempfile.TemporaryDirectory(prefix="spb_car_prev_") as tmp:
        src = os.path.join(tmp, "paint_src.png")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)
        Image.fromarray(gray).save(src)
        zone = _zone_for_pattern(pattern_id, base, paint_rgb)
        paint_rgb_out, spec, _extras = eng.build_multi_zone(
            src,
            out_dir,
            [zone],
            iracing_id="23371",
            seed=seed,
            save_debug_images=False,
            preview_mode=False,
        )
    return np.clip(paint_rgb_out, 0, 255).astype(np.uint8), spec


def build_html(ids: list[str], meta: dict):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cards = []
    for pid in ids:
        uv_rel = f"_pattern_car_preview/uv/{pid}.png"
        if not (ROOT / uv_rel.replace("/", os.sep)).is_file():
            continue
        note = meta.get(pid, {}).get("note", "")
        cards.append(
            f"""
    <section class="card" data-id="{pid}">
      <h2>{pid}</h2>
      <p class="meta">{note}</p>
      <canvas class="car" width="{THUMB}" height="{int(THUMB * 0.52)}" data-uv="{uv_rel}"></canvas>
    </section>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>SPB Pattern — Car preview (2048 pipeline)</title>
  <style>
    body {{ font-family: system-ui, Segoe UI, sans-serif; background: #0d1016; color: #e8eaed; margin: 0; padding: 1.25rem; }}
    h1 {{ font-size: 1.25rem; margin: 0 0 0.5rem; }}
    .lede {{ color: #9aa0a6; max-width: 52rem; line-height: 1.5; margin-bottom: 1.25rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }}
    .card {{ background: #1a1f28; border-radius: 10px; padding: 0.75rem 1rem 1rem; }}
    .card h2 {{ font-family: ui-monospace, monospace; font-size: 0.95rem; margin: 0 0 0.35rem; }}
    .meta {{ font-size: 0.8rem; color: #8b939c; margin: 0 0 0.5rem; min-height: 1.2em; }}
    canvas.car {{ width: 100%; height: auto; background: #252a33; border-radius: 8px; display: block; }}
  </style>
</head>
<body>
  <h1>Pattern rework — stock car preview</h1>
  <p class="lede">Generated {ts}. Each panel is <strong>build_multi_zone @ 2048²</strong>
  (living_matte + pattern @ 100%, burgundy zone tint) clipped to the same stock-car silhouette as
  <code>finish-viewer.html</code>. Open from project root. <strong>Restart the SPB server/Electron</strong>
  after pulling engine changes to see these patterns live in the booth.</p>
  <div class="grid">
    {"".join(cards)}
  </div>
  <script>
    const TAU = Math.PI * 2;
    function stockCarBodyPath(w, h) {{
      const p = new Path2D();
      p.moveTo(w * 0.020, h * 0.720);
      p.lineTo(w * 0.067, h * 0.667);
      p.bezierCurveTo(w * 0.150, h * 0.642, w * 0.270, h * 0.602, w * 0.352, h * 0.520);
      p.lineTo(w * 0.405, h * 0.320);
      p.lineTo(w * 0.462, h * 0.240);
      p.lineTo(w * 0.595, h * 0.240);
      p.lineTo(w * 0.660, h * 0.318);
      p.bezierCurveTo(w * 0.692, h * 0.378, w * 0.710, h * 0.470, w * 0.770, h * 0.520);
      p.bezierCurveTo(w * 0.846, h * 0.545, w * 0.930, h * 0.584, w * 0.980, h * 0.666);
      p.lineTo(w * 0.984, h * 0.760);
      p.bezierCurveTo(w * 0.948, h * 0.810, w * 0.872, h * 0.842, w * 0.780, h * 0.846);
      p.lineTo(w * 0.130, h * 0.846);
      p.bezierCurveTo(w * 0.068, h * 0.838, w * 0.026, h * 0.798, w * 0.020, h * 0.748);
      p.closePath();
      return p;
    }}
    function drawWheel(c, x, y, r) {{
      c.fillStyle = "#1a1a1a";
      c.beginPath(); c.arc(x, y, r, 0, TAU); c.fill();
      c.strokeStyle = "rgba(255,255,255,0.15)"; c.lineWidth = Math.max(1, r * 0.08);
      c.beginPath(); c.arc(x, y, r * 0.55, 0, TAU); c.stroke();
    }}
    function paintCarCanvas(canvas, uvSrc) {{
      const w = canvas.width, h = canvas.height;
      const ctx = canvas.getContext("2d");
      const img = new Image();
      img.onload = () => {{
        ctx.fillStyle = "#0a0c10";
        ctx.fillRect(0, 0, w, h);
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.5)";
        ctx.shadowBlur = 14;
        ctx.shadowOffsetY = 6;
        ctx.fillStyle = "rgba(0,0,0,0.45)";
        ctx.beginPath();
        ctx.ellipse(w * 0.5, h * 0.92, w * 0.42, h * 0.06, 0, 0, TAU);
        ctx.fill();
        ctx.shadowColor = "transparent";
        const body = stockCarBodyPath(w, h);
        ctx.save();
        ctx.clip(body);
        ctx.drawImage(img, 0, 0, w, h);
        const g = ctx.createLinearGradient(0, h * 0.15, 0, h * 0.9);
        g.addColorStop(0, "rgba(255,255,255,0.14)");
        g.addColorStop(0.5, "rgba(255,255,255,0.03)");
        g.addColorStop(1, "rgba(0,0,0,0.22)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.restore();
        const wy = h * 0.82, fr = w * 0.22, rr = w * 0.74, tr = h * 0.16;
        ctx.fillStyle = "#05080d";
        for (const wx of [fr, rr]) {{
          ctx.beginPath();
          ctx.arc(wx, wy, tr * 1.25, Math.PI, TAU);
          ctx.lineTo(wx + tr * 1.25, h);
          ctx.lineTo(wx - tr * 1.25, h);
          ctx.closePath();
          ctx.fill();
        }}
        drawWheel(ctx, fr, wy, tr);
        drawWheel(ctx, rr, wy, tr);
        ctx.restore();
      }};
      img.src = uvSrc;
    }}
    document.querySelectorAll("canvas.car").forEach((c) => paintCarCanvas(c, c.dataset.uv));
  </script>
</body>
</html>
"""
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=",".join(DEFAULT_IDS), help="Comma-separated pattern ids")
    ap.add_argument("--base", default="living_matte", help="Undercoat base id")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    paint_rgb = (0.78, 0.10, 0.14)
    OUT_UV.mkdir(parents=True, exist_ok=True)
    meta = {}
    for pid in ids:
        print(f"Rendering {pid} @ {SIZE}² …")
        try:
            rgb, _spec = render_uv(pid, args.base, paint_rgb, seed=args.seed)
            path = OUT_UV / f"{pid}.png"
            Image.fromarray(rgb).save(path)
            meta[pid] = {"ok": True, "path": str(path)}
            print(f"  -> {path}")
        except Exception as ex:
            meta[pid] = {"ok": False, "error": str(ex)}
            print(f"  FAIL {pid}: {ex}")
    manifest = ROOT / "_pattern_car_preview" / "manifest.json"
    manifest.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    build_html(ids, meta)


if __name__ == "__main__":
    main()
