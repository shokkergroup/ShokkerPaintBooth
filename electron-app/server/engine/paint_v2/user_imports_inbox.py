"""Inbox batch import for USER IMPORTS."""

from __future__ import annotations

from pathlib import Path
from typing import List

from engine.paint_v2.user_imports_ingest import import_paint_files
from engine.paint_v2.user_imports_paths import user_imports_root

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def inbox_dir() -> Path:
    d = user_imports_root() / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def process_inbox(*, also_pattern: bool = False) -> List[dict]:
    """Import every image in inbox/ then move to inbox/done/."""
    root = inbox_dir()
    done = root / "done"
    done.mkdir(exist_ok=True)
    imported: List[dict] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in _IMAGE_EXTS:
            continue
        entry = import_paint_files([(path.name, path)], display_name=path.stem, also_pattern=also_pattern)
        imported.append(entry)
        path.rename(done / path.name)
    return imported
