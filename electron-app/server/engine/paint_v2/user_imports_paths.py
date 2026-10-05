"""Resolve the persistent SHOKK DROP library directory (internal: user_imports)."""

from __future__ import annotations

import os
from pathlib import Path

CATEGORY_NAME = "SHOKK DROP"
ID_PREFIX = "ui_"
SCHEMA_VERSION = 1
CANVAS_SIZE = 2048
DROP_PACK_EXT = ".spbdrop"
LEGACY_DROP_PACK_EXT = ".spbshokk"


def is_drop_pack_filename(name: str) -> bool:
    lower = (name or "").lower()
    return lower.endswith(DROP_PACK_EXT) or lower.endswith(LEGACY_DROP_PACK_EXT)

def user_imports_root() -> Path:
    env = os.environ.get("SPB_USER_IMPORTS_DIR", "").strip()
    if env:
        return Path(env)
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(appdata) / "ShokkerPaintBooth" / "user_imports"
