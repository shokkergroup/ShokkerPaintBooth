"""Refresh only H1's picker manifest entry from the server-compatible hash.

The official Flask writer historically stalled before touching the manifest.
This helper is intentionally narrow: it uses the same renderer-hash contract
as ``server._picker_finish_renderer_hash`` for this one monolithic route, after
the exact engine path has already baked its static images. It preserves all
other JSON keys/entries and writes each manifest atomically.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import shokker_engine_v2 as engine  # noqa: E402

FINISH_TYPE = "monolithic"
FINISH_ID = "houdini_veiled_skull"
KEY = f"{FINISH_TYPE}:{FINISH_ID}"
SALT = ("0.5", "2048", "48", "bakezone-authoredpaint-1", "spechalf-truth-1")


def _fn_hash(fn) -> str:
    parts = [getattr(fn, "__qualname__", getattr(fn, "__name__", "?"))]
    try:
        parts.append(inspect.getsource(fn))
    except Exception:
        parts.append("nosrc")
    for cell in (getattr(fn, "__closure__", None) or ()):
        try:
            value = cell.cell_contents
        except Exception:
            continue
        if callable(value):
            try:
                parts.append(inspect.getsource(value))
            except Exception:
                parts.append(getattr(value, "__qualname__", repr(value)))
        elif isinstance(value, (str, int, float, bool, type(None))):
            parts.append(repr(value))
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]


def _module_hash(name: str) -> str | None:
    try:
        module = sys.modules.get(name) or __import__(name, fromlist=["*"])
        path = Path(module.__file__)
        return hashlib.md5(path.read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def _server_compatible_hash() -> str:
    entry = engine.MONOLITHIC_REGISTRY[FINISH_ID]
    funcs = entry[:2] if isinstance(entry, (tuple, list)) else (entry["spec_fn"], entry["paint_fn"])
    parts = list(SALT)
    for fn in funcs:
        parts.append(_fn_hash(fn))
        for dep in getattr(fn, "_spb_picker_dependency_modules", ()):
            digest = _module_hash(dep)
            if digest:
                parts.append(f"module:{dep}:{digest}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]


def _refresh(path: Path, digest: str, stamp: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    finishes = data.setdefault("finishes", {})
    old = finishes.get(KEY, {})
    finishes[KEY] = {
        "hash": digest,
        "color_hex": old.get("color_hex", "2288cc"),
        "generated": stamp,
        "render_scale": .5,
    }
    data["render_scale"] = .5
    data["output_size"] = 48
    data["updated"] = stamp
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    digest = _server_compatible_hash()
    stamp = datetime.now(timezone.utc).isoformat()
    paths = (ROOT / "thumbnails" / "picker_split" / "_manifest.json",
             ROOT / "electron-app" / "server" / "thumbnails" / "picker_split" / "_manifest.json")
    for path in paths:
        _refresh(path, digest, stamp)
        print(f"updated={path} hash={digest}")


if __name__ == "__main__":
    main()
