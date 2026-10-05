#!/usr/bin/env python3
"""Bootstrap living-queue rate portals from scripts/rate_portals_config.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.rate_portals_config import PORTALS
from scripts.spb_rate_portal_lib import generate_queue, render_thumbs

TEMPLATE = (ROOT / "SPB_RATE_EXOTIC_METAL.html").read_text(encoding="utf-8")


def make_html(cfg: dict) -> str:
    slug = cfg["slug"]
    upper = slug.upper()
    html = TEMPLATE
    html = html.replace("Exotic Metal Base Audit", cfg["title"] + " Audit")
    html = html.replace("Exotic Metal", cfg["title"])
    html = html.replace("SPB_RATE_EXOTIC_METAL", f"SPB_RATE_{upper}")
    html = html.replace("spb_rate_exotic_metal", f"spb_rate_{slug}")
    html = html.replace("/_exotic_metal_thumbs/", f"/{cfg['thumb_dir']}/")
    html = html.replace("/rate_exotic_metal_state", f"/rate_{slug}_state")
    html = html.replace("/save_rate_exotic_metal", f"/save_rate_{slug}")
    html = html.replace(
        "python scripts/spb_read_exotic_metal_notes.py",
        f"python scripts/spb_read_rate_portal_notes.py --portal {slug}",
    )
    reasons = json.dumps(cfg["failure_reasons"], indent=2)
    start = html.find("const FAILURE_REASONS = [")
    end = html.find("];", start)
    if start >= 0 and end >= 0:
        html = html[:start] + f"const FAILURE_REASONS = {reasons};" + html[end + 2 :]
    html = html.replace(
        "'Exotic Metal', portal: 'SPB_RATE_EXOTIC_METAL.html'",
        f"'{cfg['title']}', portal: 'SPB_RATE_{upper}.html'",
    )
    return html


def portal_cfg(slug: str) -> dict:
    p = dict(PORTALS[slug])
    p["slug"] = slug
    return p


def main() -> int:
    links: list[str] = []
    for slug, cfg_raw in PORTALS.items():
        cfg = portal_cfg(slug)
        html_path = ROOT / cfg["html"]
        json_path = ROOT / cfg["rate_json"]
        loop_path = ROOT / "_loop_state" / cfg["loop_state"]
        thumb_dir = ROOT / cfg["thumb_dir"]
        thumb_dir.mkdir(parents=True, exist_ok=True)
        if not json_path.exists():
            json_path.write_text(json.dumps({"ratings": {}, "meta": {"portal": slug}}, indent=2), encoding="utf-8")
        if not loop_path.exists():
            loop_path.write_text(json.dumps({"group": cfg["group_name"], "ticks": []}, indent=2), encoding="utf-8")
        html_path.write_text(make_html(cfg), encoding="utf-8")
        queue = generate_queue(cfg)
        (thumb_dir / "audit_queue.json").write_text(json.dumps(queue, indent=2), encoding="utf-8")
        print(f"portal {slug}: catalog={queue['totals']['catalog']} visible={queue['totals']['visible']}")
        render_thumbs(cfg, all_catalog=True, force=True)
        links.append(f"<li><a href='/{cfg['html']}'>{cfg['title']}</a> — {queue['totals']['catalog']} finishes</li>")

    index = (
        "<html><head><meta charset='utf-8'><title>SPB Overnight Rate Portals</title>"
        "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:30px}"
        "a{color:#7cf}li{margin:8px 0}</style></head><body>"
        "<h1>SPB Living Queue Portals</h1><ul>"
        + "\n".join(links)
        + "<li><a href='/SPB_RATE_CANDY_PEARL.html'>Candy &amp; Pearl</a></li>"
        + "<li><a href='/SPB_RATE_EXOTIC_METAL.html'>Exotic Metal</a></li>"
        + "<li><a href='/SPB_RATE_10.html'>Spec Patterns (SPB_RATE_10)</a></li>"
        + "</ul></body></html>"
    )
    (ROOT / "SPB_RATE_PORTALS_INDEX.html").write_text(index, encoding="utf-8")
    print("index -> SPB_RATE_PORTALS_INDEX.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
