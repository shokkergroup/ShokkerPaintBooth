#!/usr/bin/env python3
"""Backup, rebake, and build before/after HTML for SPB-106 top-10 pattern rework."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TOP10 = [
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

THUMB_DIR = os.path.join(ROOT, "thumbnails", "pattern")
BEFORE_DIR = os.path.join(ROOT, "_pattern_rework_before", "pattern")
FIELD_DIR = os.path.join(ROOT, "_pattern_rework_field", "pattern")
OUT_HTML = os.path.join(ROOT, "SPB_PATTERN_TOP10_COMPARE.html")
ROLLUP = os.path.join(ROOT, "_workbook_metrics", "m_pattern_weakness_rollup.json")
SIZE = 256


def load_rollup():
    if not os.path.isfile(ROLLUP):
        return {}
    with open(ROLLUP, encoding="utf-8") as f:
        data = json.load(f)
    by_id = {}
    for row in data.get("rework_queue") or []:
        by_id[row.get("id")] = row
    for row in data.get("patterns") or []:
        pid = row.get("id")
        if pid and pid not in by_id:
            by_id[pid] = row
    return by_id


def backup_thumbnails():
    os.makedirs(BEFORE_DIR, exist_ok=True)
    copied = []
    for pid in TOP10:
        src = os.path.join(THUMB_DIR, f"{pid}.png")
        dst = os.path.join(BEFORE_DIR, f"{pid}.png")
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            copied.append(pid)
    return copied


def export_field_previews():
    """Grayscale pattern_val — what drives spec, independent of paint wash-out."""
    import numpy as np
    from PIL import Image

    import shokker_engine_v2 as e
    from engine.registry import PATTERN_REGISTRY

    e.PATTERN_REGISTRY = PATTERN_REGISTRY
    e._spb_apply_regular_pattern_rebuilds()

    os.makedirs(FIELD_DIR, exist_ok=True)
    shape = (512, 512)
    mask = np.ones(shape, dtype=np.float32)
    for pid in TOP10:
        entry = PATTERN_REGISTRY.get(pid)
        if not entry:
            continue
        tex = entry["texture_fn"](shape, mask, 42, 1.0)
        pv = np.clip(tex["pattern_val"], 0, 1).astype(np.float32)
        img = Image.fromarray((pv * 255).astype(np.uint8), mode="L")
        img = img.resize((SIZE, SIZE), Image.Resampling.BILINEAR)
        img.save(os.path.join(FIELD_DIR, f"{pid}.png"))


def rebake():
    script = os.path.join(ROOT, "rebuild_thumbnails.py")
    for pid in TOP10:
        cmd = [sys.executable, script, "--type", "pattern", "--size", str(SIZE), "--key", pid]
        subprocess.run(cmd, cwd=ROOT, check=True)


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_html(rollup_by_id: dict, backed_up: list):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = []
    for pid in TOP10:
        meta = rollup_by_id.get(pid) or {}
        m7 = meta.get("m7_composite")
        m7s = f"{m7:.1f}" if isinstance(m7, (int, float)) else "—"
        flags = ", ".join(meta.get("flags") or []) or "—"
        before_rel = f"_pattern_rework_before/pattern/{pid}.png"
        field_rel = f"_pattern_rework_field/pattern/{pid}.png"
        after_rel = f"thumbnails/pattern/{pid}.png"
        before_src = before_rel if os.path.isfile(os.path.join(ROOT, before_rel.replace("/", os.sep))) else ""
        field_src = field_rel if os.path.isfile(os.path.join(ROOT, field_rel.replace("/", os.sep))) else ""
        after_src = after_rel if os.path.isfile(os.path.join(ROOT, after_rel.replace("/", os.sep))) else ""
        rows.append(
            f"""
    <section class="card" id="{esc(pid)}">
      <header>
        <h2>{esc(pid)}</h2>
        <p class="meta">M7 (pre-rework rollup): <strong>{esc(m7s)}</strong> · flags: {esc(flags)}</p>
      </header>
      <div class="compare">
        <figure>
          <figcaption>Before (tick 1)</figcaption>
          {"<img src=\"" + esc(before_src) + "\" alt=\"before\" loading=\"lazy\" />" if before_src else "<p class=\"missing\">No backup</p>"}
        </figure>
        <figure>
          <figcaption>Pattern field (spec)</figcaption>
          {"<img src=\"" + esc(field_src) + "\" alt=\"field\" loading=\"lazy\" />" if field_src else "<p class=\"missing\">Field export pending</p>"}
        </figure>
        <figure>
          <figcaption>After thumb (tick 2)</figcaption>
          {"<img src=\"" + esc(after_src) + "\" alt=\"after\" loading=\"lazy\" />" if after_src else "<p class=\"missing\">Rebake pending</p>"}
        </figure>
      </div>
    </section>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>SPB Pattern Top-10 — Before / After</title>
  <style>
    :root {{ font-family: system-ui, Segoe UI, sans-serif; background: #0f1115; color: #e8eaed; }}
    body {{ margin: 0 auto; max-width: 1400px; padding: 1.5rem; }}
    h1 {{ font-size: 1.35rem; font-weight: 600; }}
    .lede {{ color: #9aa0a6; margin-bottom: 1.5rem; line-height: 1.5; }}
    .card {{ background: #1a1d24; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1.25rem; }}
    .card h2 {{ margin: 0 0 0.35rem; font-size: 1.05rem; font-family: ui-monospace, monospace; }}
    .meta {{ margin: 0 0 0.75rem; font-size: 0.85rem; color: #9aa0a6; }}
    .compare {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.75rem; }}
    figure {{ margin: 0; }}
    figcaption {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #7c838a; margin-bottom: 0.35rem; }}
    img {{ width: 100%; height: auto; border-radius: 6px; background: #252830; }}
    .missing {{ color: #c45c5c; font-size: 0.85rem; padding: 1.5rem; text-align: center; background: #252830; border-radius: 6px; }}
    @media (max-width: 900px) {{ .compare {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>Pattern weakness rollup — top 10 rework</h1>
  <p class="lede">Generated {esc(ts)}. <strong>Before</strong> = pre-SP-106 thumb (often chroma-baked paint).
  <strong>Field</strong> = <code>pattern_val</code> grayscale (spec driver). <strong>After</strong> = tick-2 thumb at {SIZE}²
  (luminance paint + stronger structure). Open from project root.</p>
  {"".join(rows)}
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT_HTML}")


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--no-backup", action="store_true", help="Skip copying current thumbs to before/")
    ap.add_argument("--rebake-only", action="store_true", help="Rebake + field + HTML only")
    args = ap.parse_args()

    rollup = load_rollup()
    backed = []
    if not args.rebake_only and not args.no_backup:
        backed = backup_thumbnails()
        print(f"Backed up {len(backed)} thumbnails -> {BEFORE_DIR}")
    rebake()
    export_field_previews()
    build_html(rollup, backed or TOP10)


if __name__ == "__main__":
    main()
