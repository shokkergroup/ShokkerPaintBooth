#!/usr/bin/env python3
"""Overnight autonomous finish improvement — one tick per invocation.

Processes batches across Light & Optics, Prizm, Chameleon, COLORSHOXX portals.
Called every 15 minutes by scripts/overnight_loop.sh.

Progress: _loop_state/overnight_progress.json
Log:       _loop_state/overnight_log.txt
Status:    OVERNIGHT_STATUS.md
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.rate_portals_config import OVERNIGHT_PORTAL_ORDER, PORTALS
from scripts.spb_rate_portal_lib import load_group_ids, render_thumbs

sys.path.insert(0, str(ROOT / "engine"))
from overnight_boost import bump_wave, current_wave  # noqa: E402

PROGRESS = ROOT / "_loop_state" / "overnight_progress.json"
LOG = ROOT / "_loop_state" / "overnight_log.txt"
STATUS = ROOT / "OVERNIGHT_STATUS.md"

BATCH_SIZE = 5


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    line = f"[{_utc()}] {msg}\n"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line.rstrip())


def _load_progress() -> dict:
    default = {"portal_idx": 0, "finish_idx": 0, "ticks": 0, "last_portal": "", "last_batch": []}
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text(encoding="utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            return default
    return default


def _save_progress(data: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _append_loop_tick(portal_slug: str, ids: list[str], note: str) -> None:
    cfg = PORTALS[portal_slug]
    path = ROOT / "_loop_state" / cfg["loop_state"]
    try:
        data = json.loads(path.read_text(encoding="utf-8") if path.exists() else '{"ticks":[]}')
    except (ValueError, json.JSONDecodeError):
        data = {"ticks": []}
    ticks = data.get("ticks") or []
    tick_n = len(ticks) + 1
    ticks.append({
        "tick": tick_n,
        "started_at": _utc(),
        "ended_at": _utc(),
        "bases": ids,
        "note": note,
    })
    data["ticks"] = ticks
    data["group"] = cfg["group_name"]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _run_improvements(portal_slug: str, batch: list[str]) -> str:
    """Bump overnight wave counter — renderers read wave_mult() for escalating strength."""
    wave = bump_wave(portal_slug, batch)
    notes = {
        "light_optics": "Light & Optics _lw_fields glint/sparkle wave",
        "prizm": "Prizm pin/dot spec wave",
        "chameleon": "Chameleon hue-walk sparkle wave",
        "colorshoxx": "COLORSHOXX dual/micro-flake shift wave",
    }
    base = notes.get(portal_slug, portal_slug)
    return f"wave={wave} — {base} — batch {batch}"


def _write_status(prog: dict) -> None:
    lines = [
        "# Overnight Finish Run — Live Status",
        "",
        f"Updated: {_utc()}",
        f"Ticks completed: {prog.get('ticks', 0)}",
        f"Overnight wave: {current_wave()} (each tick escalates renderer strength)",
        f"Current portal: {prog.get('last_portal', '—')}",
        f"Last batch: {', '.join(prog.get('last_batch') or [])}",
        "",
        "## Review portals (http://127.0.0.1:7777/)",
        "",
        "| Portal | URL | Catalog |",
        "|--------|-----|---------|",
    ]
    for slug, cfg in PORTALS.items():
        ids = load_group_ids(cfg["group_name"])
        lines.append(f"| {cfg['title']} | [{cfg['html']}](http://127.0.0.1:7777/{cfg['html']}) | {len(ids)} |")
    lines += [
        "",
        "**Index:** [SPB_RATE_PORTALS_INDEX.html](http://127.0.0.1:7777/SPB_RATE_PORTALS_INDEX.html)",
        "",
        "Also: [Candy & Pearl](http://127.0.0.1:7777/SPB_RATE_CANDY_PEARL.html) · "
        "[Exotic Metal](http://127.0.0.1:7777/SPB_RATE_EXOTIC_METAL.html)",
        "",
    ]
    STATUS.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    prog = _load_progress()
    portal_idx = int(prog.get("portal_idx", 0)) % len(OVERNIGHT_PORTAL_ORDER)
    finish_idx = int(prog.get("finish_idx", 0))
    slug = OVERNIGHT_PORTAL_ORDER[portal_idx]
    cfg = dict(PORTALS[slug])
    cfg["slug"] = slug
    all_ids = load_group_ids(cfg["group_name"])
    if not all_ids:
        _log(f"ERROR no ids for portal {slug}")
        # Advance past this empty portal so the next tick doesn't re-enter it forever.
        prog["portal_idx"] = (portal_idx + 1) % len(OVERNIGHT_PORTAL_ORDER)
        prog["finish_idx"] = 0
        _save_progress(prog)
        return 1

    if finish_idx >= len(all_ids):
        portal_idx = (portal_idx + 1) % len(OVERNIGHT_PORTAL_ORDER)
        finish_idx = 0
        slug = OVERNIGHT_PORTAL_ORDER[portal_idx]
        cfg = dict(PORTALS[slug])
        cfg["slug"] = slug
        all_ids = load_group_ids(cfg["group_name"])

    batch = all_ids[finish_idx : finish_idx + BATCH_SIZE]
    if not batch:
        portal_idx = (portal_idx + 1) % len(OVERNIGHT_PORTAL_ORDER)
        finish_idx = 0
        slug = OVERNIGHT_PORTAL_ORDER[portal_idx]
        cfg = dict(PORTALS[slug])
        cfg["slug"] = slug
        all_ids = load_group_ids(cfg["group_name"])
        batch = all_ids[:BATCH_SIZE]

    _log(f"TICK start portal={slug} batch={batch}")
    note = _run_improvements(slug, batch)
    t0 = time.perf_counter()

    try:
        render_thumbs(cfg, only=set(batch), force=True)
    except Exception as exc:
        _log(f"render failed: {exc!r}")

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_rate_portal_queue.py"), slug],
        cwd=str(ROOT),
        check=False,
    )
    if slug == "colorshoxx":
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "colorshoxx_desc_audit.py")],
            cwd=str(ROOT),
            check=False,
        )
    _append_loop_tick(slug, batch, note)
    dt = time.perf_counter() - t0
    _log(f"TICK done portal={slug} in {dt:.1f}s — {note}")

    prog["portal_idx"] = portal_idx
    prog["finish_idx"] = finish_idx + len(batch)
    prog["ticks"] = int(prog.get("ticks", 0)) + 1
    prog["last_portal"] = slug
    prog["last_batch"] = batch
    prog["last_tick_at"] = _utc()
    _save_progress(prog)
    _write_status(prog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
