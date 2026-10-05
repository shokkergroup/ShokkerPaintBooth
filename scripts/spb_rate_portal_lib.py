"""Shared living-queue + thumbnail render for rate portals."""
from __future__ import annotations

import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
FINISH_DATA = ROOT / "paint-booth-0-finish-data.js"
SEED = 7777

TINT_M = (1.00, 0.30, 0.30)
TINT_R = (0.30, 1.00, 0.30)
TINT_CC = (0.30, 0.50, 1.00)


def parse_iso(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def load_group_ids(group_name: str) -> list[str]:
    src = FINISH_DATA.read_text(encoding="utf-8", errors="replace")
    m = re.search(rf'"{re.escape(group_name)}"\s*:\s*\[(.*?)\]', src, re.DOTALL)
    if not m:
        return []
    return re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]*)"', m.group(1))


def load_finish_meta() -> dict[str, dict]:
    src = FINISH_DATA.read_text(encoding="utf-8", errors="replace")
    out: dict[str, dict] = {}
    for m in re.finditer(
        r'\{\s*id:\s*"([a-zA-Z_][a-zA-Z0-9_]*)"\s*,\s*name:\s*"([^"]*)"\s*,\s*desc:\s*"([^"]*)"\s*,\s*swatch:\s*"([^"]*)"',
        src,
    ):
        out[m.group(1)] = {"name": m.group(2), "desc": m.group(3), "swatch": m.group(4)}
    return out


def load_rating_signals(rate_json: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not rate_json.exists():
        return out
    data = json.loads(rate_json.read_text(encoding="utf-8") or "{}")
    for name, entry in (data.get("ratings") or {}).items():
        if not isinstance(entry, dict):
            continue
        if entry.get("verdict") or entry.get("rating"):
            out[name] = {
                "last_verdict": entry.get("verdict"),
                "last_rating": entry.get("rating"),
                "last_rated_at": entry.get("submitted_at"),
            }
    return out


def load_rebuild_signals(loop_state: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not loop_state.exists():
        return out
    data = json.loads(loop_state.read_text(encoding="utf-8") or "{}")
    for t in data.get("ticks") or []:
        if not isinstance(t, dict):
            continue
        ts = t.get("ended_at") or t.get("started_at") or t.get("at") or ""
        for nm in t.get("bases") or t.get("rebuilt") or t.get("patterns") or []:
            if nm and ts and (nm not in out or ts > out[nm]):
                out[nm] = ts
    return out


def generate_queue(portal: dict[str, Any]) -> dict[str, Any]:
    group = portal["group_name"]
    rate_json = ROOT / portal["rate_json"]
    loop_state = ROOT / "_loop_state" / portal["loop_state"]
    bakeoff = bool(portal.get("bakeoff_mode"))
    ids = load_group_ids(group)
    meta = load_finish_meta()
    ratings = load_rating_signals(rate_json)
    rebuilds = load_rebuild_signals(loop_state)
    visible: list[dict] = []
    hidden_keep = hidden_pending = 0
    for fid in ids:
        m = meta.get(fid, {})
        title = m.get("name") or fid.replace("_", " ").title()
        identity = m.get("desc") or title
        if m.get("swatch"):
            identity = f"Swatch {m['swatch']}. {identity}"
        rating = ratings.get(fid) or {}
        last_v = rating.get("last_verdict")
        last_r = rating.get("last_rating")
        rated_at = rating.get("last_rated_at")
        rebuilt_at = rebuilds.get(fid)
        if last_v == "KEEP" and not bakeoff:
            hidden_keep += 1
            continue
        rated_dt = parse_iso(rated_at)
        rebuilt_dt = parse_iso(rebuilt_at)
        is_rebuilt = rated_dt and rebuilt_dt and rebuilt_dt > rated_dt
        if last_v is None:
            cat, reason = "NEW", "never_rated"
        elif is_rebuilt or (last_v in ("REBUILD", "MIXED", "REPLACE") and rebuilt_at and not rated_dt):
            cat, reason = "RE-REVIEW", "rebuilt_since_rating"
        elif bakeoff:
            cat = "RATED" if last_v else "NEW"
            reason = "bakeoff_always_visible"
        else:
            hidden_pending += 1
            continue
        visible.append({
            "id": fid,
            "title": title,
            "category": cat,
            "identity": identity[:400],
            "swatch": m.get("swatch", "#888899"),
            "last_verdict": last_v,
            "last_rating": last_r,
            "last_rated_at": rated_at,
            "last_rebuilt_at": rebuilt_at,
            "reason_visible": reason,
        })
    order = {"RE-REVIEW": 0, "REDO": 1, "MIXED": 2, "NEW": 3}
    visible.sort(key=lambda e: (order.get(e["category"], 9), e["id"]))
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "group": group,
        "portal": portal.get("slug", ""),
        "totals": {
            "catalog": len(ids),
            "visible": len(visible),
            "hidden_keep": hidden_keep,
            "hidden_pending_rebuild": hidden_pending,
        },
        "bases": visible,
    }


def _tint_channel(field2d: np.ndarray, color: tuple[float, float, float]) -> np.ndarray:
    arr = np.clip(field2d, 0, 1)
    rgb = np.stack([arr * color[0], arr * color[1], arr * color[2]], axis=-1)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def _spec_array(spec_raw, shape: tuple[int, int]) -> np.ndarray:
    if isinstance(spec_raw, np.ndarray) and spec_raw.ndim == 3 and spec_raw.shape[2] >= 3:
        M, R, CC = spec_raw[:, :, 0], spec_raw[:, :, 1], spec_raw[:, :, 2]
    elif isinstance(spec_raw, (tuple, list)) and len(spec_raw) >= 3:
        M, R, CC = spec_raw[0], spec_raw[1], spec_raw[2]
    else:
        return np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
    M = np.clip(M.astype(np.float32) / 255.0, 0, 1)
    R = np.clip(R.astype(np.float32) / 255.0, 0, 1)
    CC = np.clip(CC.astype(np.float32) / 255.0, 0, 1)
    return np.stack([M, R, CC], axis=-1)


def import_engine():
    sys.path.insert(0, str(ROOT))
    import shokker_engine_v2 as eng  # noqa: WPS433

    return eng


def _validate_paint_rgb(paint_raw, fid: str, registry: str) -> np.ndarray:
    """Coerce a paint_fn return to an HxWx3+ float array or raise KeyError.

    A paint_fn that returns None/scalar/tuple/wrong-rank would otherwise raise
    AttributeError/TypeError on `.ndim`/`.shape` access, which render_finish's
    `except KeyError` does NOT catch — short-circuiting the base<->monolithic
    fallback. Raising KeyError keeps that fallback engaged.
    """
    try:
        arr = np.asarray(paint_raw, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise KeyError(f"{registry} paint_fn returned non-array for {fid}: {exc}")
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise KeyError(
            f"{registry} paint_fn returned bad shape {getattr(arr, 'shape', None)} for {fid}"
        )
    return arr


def _render_finish_registry(eng, fid: str, size: int, registry: str, swatch: str):
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    seed = SEED

    def hex_rgb01(h: str):
        s = (h or "#888899").lstrip("#")
        if len(s) != 6:
            return 0.5, 0.5, 0.55
        return int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0

    if registry == "monolithic":
        entry = eng.MONOLITHIC_REGISTRY.get(fid)
        if not entry:
            raise KeyError(f"not in MONOLITHIC_REGISTRY: {fid}")
        spec_fn, paint_fn = entry[0], entry[1]
        neutral = np.array([hex_rgb01(swatch)], dtype=np.float32)
        neutral = np.broadcast_to(neutral, (size, size, 3)).copy()
        spec_raw = spec_fn(shape, mask, seed, 1.0)
        paint_rgb = _validate_paint_rgb(
            paint_fn(neutral, shape, mask, seed, 1.0, np.ones(shape, dtype=np.float32)),
            fid,
            registry,
        )
        spec_u8 = _spec_array(spec_raw, shape)
        rgb = np.clip(paint_rgb[:, :, :3], 0, 1)
        return rgb.astype(np.float32), spec_u8

    entry = eng.BASE_REGISTRY.get(fid)
    if not entry:
        raise KeyError(f"not in BASE_REGISTRY: {fid}")
    neutral = np.array([hex_rgb01(swatch)], dtype=np.float32)
    neutral = np.broadcast_to(neutral, (size, size, 3)).copy()
    paint_fn = entry.get("paint_fn")
    spec_fn = entry.get("base_spec_fn")
    if paint_fn:
        rgb = _validate_paint_rgb(
            paint_fn(neutral, shape, mask, seed, 1.0, np.ones(shape, dtype=np.float32)),
            fid,
            registry,
        )
    else:
        rgb = neutral
    spec_u8 = None
    if spec_fn:
        spec_raw = spec_fn(shape, seed, 1.0, float(entry.get("M", 120)), float(entry.get("R", 80)))
        spec_u8 = _spec_array(spec_raw, shape)
    if spec_u8 is None:
        spec_u8 = np.zeros((size, size, 3), dtype=np.uint8)
    return np.clip(rgb[:, :, :3], 0, 1).astype(np.float32), spec_u8


def render_finish(eng, fid: str, size: int, registry: str, swatch: str = "#888899"):
    """Render finish — dedicated BASE cx_* wins over generic micro-flake monolithics."""
    order: list[str] = []
    in_base = fid in eng.BASE_REGISTRY
    in_mono = fid in eng.MONOLITHIC_REGISTRY
    if registry == "base":
        if in_base:
            order.append("base")
        if in_mono and not in_base:
            order.append("monolithic")
    else:
        if in_mono:
            order.append("monolithic")
        if in_base and "base" not in order:
            order.append("base")
    if not order:
        order = [registry, "monolithic" if registry == "base" else "base"]
    last_err: KeyError | None = None
    for reg in order:
        try:
            return _render_finish_registry(eng, fid, size, reg, swatch)
        except KeyError as exc:
            last_err = exc
    raise last_err or KeyError(fid)


def render_thumbs(
    portal: dict[str, Any],
    *,
    force: bool = False,
    only: set[str] | None = None,
    all_catalog: bool = False,
    size: int = 512,
    max_items: int = 0,
) -> int:
    thumb_dir = ROOT / portal["thumb_dir"]
    thumb_dir.mkdir(parents=True, exist_ok=True)
    queue_path = thumb_dir / "audit_queue.json"
    meta = load_finish_meta()

    if all_catalog or not queue_path.exists():
        payload = generate_queue(portal)
        queue_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        queue_bases = [{"id": i, "swatch": meta.get(i, {}).get("swatch", "#888899")} for i in load_group_ids(portal["group_name"])]
    else:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
        if portal.get("bakeoff_mode"):
            queue_bases = [{"id": i, "swatch": meta.get(i, {}).get("swatch", "#888899")} for i in load_group_ids(portal["group_name"])]
        else:
            queue_bases = payload.get("bases", [])

    if only:
        queue_bases = [b for b in queue_bases if b["id"] in only]
    if max_items > 0:
        queue_bases = queue_bases[:max_items]

    try:
        import cv2

        has_cv2 = True
    except Exception:
        has_cv2 = False

    def write_png(rgb_uint8: np.ndarray, path: Path) -> None:
        if has_cv2:
            import cv2

            cv2.imwrite(str(path), rgb_uint8[:, :, [2, 1, 0]])
        else:
            from PIL import Image

            Image.fromarray(rgb_uint8, mode="RGB").save(path)

    eng = import_engine()
    registry = portal["registry"]
    manifest_path = thumb_dir / "manifest.json"
    existing: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            for p in json.loads(manifest_path.read_text(encoding="utf-8")).get("bases", []):
                existing[p.get("id")] = p
        except Exception:
            pass

    source_mtime = max(
        (ROOT / "engine" / "expansions" / "fusions.py").stat().st_mtime,
        (ROOT / "engine" / "prizm.py").stat().st_mtime,
        (ROOT / "engine" / "chameleon.py").stat().st_mtime,
        (ROOT / "engine" / "base_registry_data.py").stat().st_mtime,
        (ROOT / "engine" / "overnight_boost.py").stat().st_mtime,
        (ROOT / "_loop_state" / "overnight_wave.json").stat().st_mtime if (ROOT / "_loop_state" / "overnight_wave.json").exists() else 0.0,
        FINISH_DATA.stat().st_mtime if FINISH_DATA.exists() else 0.0,
    )

    results: list[dict] = []
    rendered = skipped = missing = 0
    t0_all = time.perf_counter()
    rel = portal["thumb_dir"]

    for entry in queue_bases:
        fid = entry["id"]
        swatch = entry.get("swatch") or meta.get(fid, {}).get("swatch", "#888899")
        paths_ok = all((thumb_dir / f"{fid}{s}.png").exists() for s in ("_paint", "", "_M", "_R", "_CC"))
        if not force and paths_ok and fid in existing:
            newest = min((thumb_dir / f"{fid}{s}.png").stat().st_mtime for s in ("_paint", "", "_M", "_R", "_CC"))
            if newest >= source_mtime:
                results.append(existing[fid])
                skipped += 1
                continue
        try:
            paint_rgb, spec_u8 = render_finish(eng, fid, size, registry, swatch)
        except KeyError:
            print(f"  MISSING registry: {fid}")
            missing += 1
            continue
        except Exception as exc:
            print(f"  FAIL {fid}: {exc!r}")
            continue

        paint_u8 = (np.clip(paint_rgb, 0, 1) * 255).astype(np.uint8)
        write_png(paint_u8, thumb_dir / f"{fid}_paint.png")
        spec_f = spec_u8.astype(np.float32)
        if float(spec_f.max()) > 1.5:
            spec_f = spec_f / 255.0
        spec_f = np.clip(spec_f, 0, 1)
        M_arr, R_arr, CC_arr = spec_f[:, :, 0], spec_f[:, :, 1], spec_f[:, :, 2]
        spec_rgb = (spec_f * 255).astype(np.uint8)
        write_png(spec_rgb, thumb_dir / f"{fid}.png")
        write_png(_tint_channel(M_arr, TINT_M), thumb_dir / f"{fid}_M.png")
        write_png(_tint_channel(R_arr, TINT_R), thumb_dir / f"{fid}_R.png")
        write_png(_tint_channel(CC_arr, TINT_CC), thumb_dir / f"{fid}_CC.png")
        rendered += 1
        results.append({
            "id": fid,
            "thumb_paint": f"{rel}/{fid}_paint.png",
            "thumb_spec": f"{rel}/{fid}.png",
            "thumb_M": f"{rel}/{fid}_M.png",
            "thumb_R": f"{rel}/{fid}_R.png",
            "thumb_CC": f"{rel}/{fid}_CC.png",
            "M_mean": round(float(M_arr.mean()) * 255, 1),
            "M_std": round(float(M_arr.std()) * 255, 1),
            "R_mean": round(float(R_arr.mean()) * 255, 1),
            "R_std": round(float(R_arr.std()) * 255, 1),
            "CC_mean": round(float(CC_arr.mean()) * 255, 1),
            "CC_std": round(float(CC_arr.std()) * 255, 1),
        })

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "group": portal["group_name"],
        "portal": portal.get("slug", ""),
        "size": size,
        "bases": results,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    dt = time.perf_counter() - t0_all
    print(f"render {portal.get('slug')}: rendered={rendered} skipped={skipped} missing={missing} in {dt:.1f}s")
    return 0 if missing == 0 else 1
