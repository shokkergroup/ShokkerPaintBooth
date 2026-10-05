"""shokk_manager.py - SHOKK file system for Shokker Paint Booth V5.

A ``.shokk`` file is a ZIP archive containing:

==================  =====================================================
``manifest.json``   name, author, tags, version metadata
``session.json``    full zone config (same schema as template JSON)
``spec.png``        baked spec map (may also be ``.tga`` / ``.jpg`` legacy)
``preview.jpg``     thumbnail (auto-generated from last preview)
``paint.tga``       (optional) source paint file
==================  =====================================================

Typical usage
-------------
    >>> from shokk_manager import ShokkManager
    >>> mgr = ShokkManager(library_dir)
    >>> path = mgr.save(name="Purple ColorShift", author="Ricky", ...)
    >>> data = mgr.open(path)
    >>> entries = mgr.list_library()

Cross-module dependencies
-------------------------
* :mod:`config` -- library/factory dirs originate from ``CFG``.
* :mod:`server_v5` / :mod:`server` -- call :meth:`ShokkManager.list_library`
  via the ``/api/shokk/*`` endpoints.

Threading
---------
Each public method is effectively independent (no shared mutable state except
the library directory on disk). Multiple threads can call :meth:`list_library`
concurrently without coordination.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    "ShokkManager",
    "SHOKK_EXT",
    "SHOKK_VERSION",
    "MANAGER_MODULE_VERSION",
]

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: File extension for SHOKK archives.
SHOKK_EXT: str = ".shokk"

#: On-disk manifest schema version. Bump on breaking manifest changes.
SHOKK_VERSION: str = "1.0"

#: Version of this module itself (for diagnostics).
MANAGER_MODULE_VERSION: str = "1.1.0"

#: Manifest filename inside the archive.
_MANIFEST_NAME: str = "manifest.json"

#: Session JSON filename inside the archive.
_SESSION_NAME: str = "session.json"

#: Preview filename inside the archive (always JPEG).
_PREVIEW_NAME: str = "preview.jpg"

#: Default SPB version string stamped into manifests when not provided.
_DEFAULT_SPB_VERSION: str = "5.0.0"

#: ZIP compression level (higher = smaller but slower).
_ZIP_COMPRESSLEVEL: int = 6

#: Bytes-per-MB for human-readable size.
_BYTES_PER_MB: int = 1024 * 1024

#: Accepted image extensions for the spec map.
_SPEC_EXTS: tuple = (".png", ".tga", ".jpg", ".jpeg")

#: Exact filenames recognised as the primary spec map (case-insensitive).
_SPEC_EXACT_CANDIDATES: frozenset = frozenset({
    "spec.png", "spec.tga", "spec.jpg", "spec.jpeg",
    "render_spec.png", "render_spec.tga",
})

#: Regex of characters kept verbatim in a sanitised filename stem.
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9 _\-]")

logger = logging.getLogger("shokker.shokk_manager")


# ---------------------------------------------------------------------------
# Internal helpers (module-level so tests / callers can reuse if needed)
# ---------------------------------------------------------------------------

def _sanitize_stem(name: str) -> str:
    """Return a filesystem-safe stem derived from ``name``.

    * Strips characters outside ``[A-Za-z0-9 _-]``.
    * Collapses spaces to underscores.
    * Falls back to ``"shokk"`` if the input is empty after cleaning.

    Args:
        name: Human-readable preset name.

    Returns:
        A non-empty stem suitable for inclusion in a filename.
    """
    if not isinstance(name, str):
        name = str(name or "shokk")
    cleaned = _SAFE_FILENAME_RE.sub("_", name).strip()
    cleaned = cleaned.replace(" ", "_")
    return cleaned or "shokk"


def _timestamp() -> str:
    """Return a compact ``YYYYMMDD_HHMMSS`` stamp in local time."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _find_spec_name(names: Iterable[str]) -> Optional[str]:
    """Locate the spec map inside a zip namelist, handling legacy variants.

    Two-pass strategy: first prefer exact filenames in :data:`_SPEC_EXACT_CANDIDATES`,
    then fall back to any basename containing ``"spec"`` with a known extension.

    Args:
        names: Iterable of archive member names.

    Returns:
        The matching member name, or ``None`` if none found.
    """
    names_list = list(names)
    for n in names_list:
        if os.path.basename(n).lower() in _SPEC_EXACT_CANDIDATES:
            return n
    for n in names_list:
        base = os.path.basename(n).lower()
        if "spec" in base and base.endswith(_SPEC_EXTS):
            return n
    return None


def _path_is_within(target: str, base: str) -> bool:
    """Return True if ``target`` normalises to a path under ``base``.

    Used to defeat ZIP path-traversal (``../``) when extracting files.
    """
    base_abs = os.path.realpath(base)
    target_abs = os.path.realpath(os.path.join(base, target))
    try:
        return os.path.commonpath([base_abs, target_abs]) == base_abs
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# ShokkManager
# ---------------------------------------------------------------------------

class ShokkManager:
    """File system helper for saving/loading/listing ``.shokk`` archives.

    Args:
        library_dir: Directory for user-saved SHOKK files (created if missing).
        factory_dir: Optional read-only directory of bundled factory presets.

    Raises:
        TypeError: If ``library_dir`` is not a string.
        OSError: If ``library_dir`` cannot be created.
    """

    def __init__(self, library_dir: str, factory_dir: Optional[str] = None) -> None:
        if not isinstance(library_dir, str) or not library_dir:
            raise TypeError("library_dir must be a non-empty string")
        self.library_dir: str = os.path.abspath(library_dir)
        self.factory_dir: Optional[str] = (
            os.path.abspath(factory_dir) if factory_dir else None
        )
        try:
            os.makedirs(self.library_dir, exist_ok=True)
        except OSError as e:
            logger.error(
                "[shokk] Could not create library dir %s (%s)", self.library_dir, e
            )
            raise

    # ─── CREATE ──────────────────────────────────────────────────────────

    def save(
        self,
        name: str,
        author: str,
        description: str,
        tags: Optional[List[str]],
        session_json: Dict[str, Any],
        spec_path: Optional[str] = None,
        paint_path: Optional[str] = None,
        preview_path: Optional[str] = None,
        include_paint: bool = True,
        spb_version: str = _DEFAULT_SPB_VERSION,
    ) -> str:
        """Package a paint preset into a ``.shokk`` archive and save it.

        Args:
            name: Human-readable preset name (used in the filename).
            author: Author attribution; ``"Unknown"`` if falsy.
            description: Free-form description.
            tags: List of tag strings, or ``None``.
            session_json: Full zone configuration (serialisable dict).
            spec_path: Path to baked spec image, or ``None``.
            paint_path: Path to source paint file (TGA/PNG), or ``None``.
            preview_path: Path to JPEG thumbnail, or ``None``.
            include_paint: When True, bundle the paint file into the archive.
            spb_version: SPB semver string (defaults to
                :data:`_DEFAULT_SPB_VERSION`).

        Returns:
            Absolute path of the written ``.shokk`` file.

        Raises:
            TypeError: If ``session_json`` is not a dict.
            OSError: If the archive cannot be written.
        """
        if not isinstance(session_json, dict):
            raise TypeError(
                f"session_json must be dict, got {type(session_json).__name__}"
            )

        safe_name = _sanitize_stem(name)
        filename = f"{safe_name}_{_timestamp()}{SHOKK_EXT}"
        out_path = os.path.join(self.library_dir, filename)

        paint_exists = bool(include_paint and paint_path and os.path.exists(paint_path))
        spec_exists = bool(spec_path and os.path.exists(spec_path))

        manifest = {
            "shokk_version": SHOKK_VERSION,
            "name": name,
            "author": author or "Unknown",
            "description": description or "",
            "tags": list(tags) if tags else [],
            "created": datetime.datetime.now().isoformat(),
            "spb_version": spb_version,
            "includes_paint": paint_exists,
            "has_spec": spec_exists,
        }

        try:
            with zipfile.ZipFile(
                out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=_ZIP_COMPRESSLEVEL
            ) as zf:
                zf.writestr(_MANIFEST_NAME, json.dumps(manifest, indent=2))
                zf.writestr(_SESSION_NAME, json.dumps(session_json, indent=2))
                if spec_exists:
                    zf.write(spec_path, "spec.png")  # type: ignore[arg-type]
                if preview_path and os.path.exists(preview_path):
                    zf.write(preview_path, _PREVIEW_NAME)
                if paint_exists:
                    ext = os.path.splitext(paint_path)[1] or ".tga"  # type: ignore[arg-type]
                    zf.write(paint_path, f"paint{ext}")  # type: ignore[arg-type]
        except OSError as e:
            logger.error("[shokk] Save failed for %s: %s", out_path, e)
            # Leave a partial file if it exists -- helpful for debugging.
            raise

        logger.info("[shokk] Saved %s (%d bytes)", out_path, os.path.getsize(out_path))
        return out_path

    # ─── READ ────────────────────────────────────────────────────────────

    def open(
        self, shokk_path: str, extract_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Open a ``.shokk`` archive and extract its contents.

        Args:
            shokk_path: Absolute path to the archive.
            extract_dir: Directory to extract into; a tempdir is created when
                ``None``. The caller is responsible for cleaning it up.

        Returns:
            Dict with keys:

            * ``manifest``      -- parsed manifest (may be ``{}``)
            * ``session_json``  -- parsed session (may be ``{}``)
            * ``spec_path``     -- absolute path to extracted spec file (or ``None``)
            * ``paint_path``    -- absolute path to extracted paint file (or ``None``)
            * ``preview_bytes`` -- raw JPEG bytes (or ``None``)
            * ``extract_dir``   -- directory files were extracted to

        Raises:
            FileNotFoundError: If ``shokk_path`` does not exist.
            zipfile.BadZipFile: If the archive is corrupt.
        """
        if not os.path.exists(shokk_path):
            raise FileNotFoundError(f"SHOKK file not found: {shokk_path}")

        if extract_dir is None:
            extract_dir = tempfile.mkdtemp(prefix="shokk_")
        else:
            os.makedirs(extract_dir, exist_ok=True)

        result: Dict[str, Any] = {
            "manifest": {},
            "session_json": {},
            "spec_path": None,
            "paint_path": None,
            "preview_bytes": None,
            "extract_dir": extract_dir,
        }

        with zipfile.ZipFile(shokk_path, "r") as zf:
            names = zf.namelist()

            if _MANIFEST_NAME in names:
                try:
                    result["manifest"] = json.loads(zf.read(_MANIFEST_NAME))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning("[shokk] bad manifest in %s: %s", shokk_path, e)

            if _SESSION_NAME in names:
                try:
                    result["session_json"] = json.loads(zf.read(_SESSION_NAME))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning("[shokk] bad session in %s: %s", shokk_path, e)

            # Spec map (handles legacy formats).
            spec_name = _find_spec_name(names)
            if spec_name:
                ext = os.path.splitext(spec_name)[1] or ".png"
                dest_rel = f"spec{ext}"
                if _path_is_within(dest_rel, extract_dir):
                    spec_path = os.path.join(extract_dir, dest_rel)
                    with open(spec_path, "wb") as fh:
                        fh.write(zf.read(spec_name))
                    result["spec_path"] = spec_path
                else:
                    logger.warning(
                        "[shokk] spec path traversal blocked for %s", shokk_path
                    )

            if _PREVIEW_NAME in names:
                result["preview_bytes"] = zf.read(_PREVIEW_NAME)

            # Paint file (paint.tga, paint.png, ...).
            paint_name = next(
                (n for n in names if os.path.basename(n).lower().startswith("paint.")),
                None,
            )
            if paint_name:
                dest_rel = os.path.basename(paint_name)
                if _path_is_within(dest_rel, extract_dir):
                    paint_path = os.path.join(extract_dir, dest_rel)
                    with open(paint_path, "wb") as fh:
                        fh.write(zf.read(paint_name))
                    result["paint_path"] = paint_path
                else:
                    logger.warning(
                        "[shokk] paint path traversal blocked for %s", shokk_path
                    )

        return result

    def get_preview_bytes(self, shokk_path: str) -> Optional[bytes]:
        """Return just the ``preview.jpg`` bytes without full extraction.

        Args:
            shokk_path: Absolute path to the archive.

        Returns:
            The JPEG bytes, or ``None`` if absent or the file is unreadable.
        """
        try:
            with zipfile.ZipFile(shokk_path, "r") as zf:
                if _PREVIEW_NAME in zf.namelist():
                    return zf.read(_PREVIEW_NAME)
        except (zipfile.BadZipFile, OSError, KeyError) as e:
            logger.debug("[shokk] preview read failed for %s: %s", shokk_path, e)
        return None

    def get_manifest(self, shokk_path: str) -> Dict[str, Any]:
        """Return just the manifest from a ``.shokk`` file (fast path).

        Args:
            shokk_path: Absolute path to the archive.

        Returns:
            Parsed manifest dict; ``{}`` if the file is unreadable or the
            manifest is absent / corrupt.
        """
        try:
            with zipfile.ZipFile(shokk_path, "r") as zf:
                if _MANIFEST_NAME in zf.namelist():
                    return json.loads(zf.read(_MANIFEST_NAME))
        except (zipfile.BadZipFile, OSError, json.JSONDecodeError,
                UnicodeDecodeError, KeyError) as e:
            logger.debug("[shokk] manifest read failed for %s: %s", shokk_path, e)
        return {}

    # ─── LIBRARY ─────────────────────────────────────────────────────────

    def list_library(self) -> List[Dict[str, Any]]:
        """Scan library (and factory) directories for ``.shokk`` files.

        Returns:
            A list of dicts, one per archive, sorted by filename within each
            source. Each dict is suitable for direct JSON serialisation to
            the UI browser (see :meth:`_entry_for` for the schema).

        Notes:
            Performance: scans with :func:`os.listdir` + ``getsize`` per file.
            For libraries with thousands of files, call this off the request
            thread or add caching at the caller level.
        """
        dirs_to_scan: List[tuple] = [(self.library_dir, "user")]
        if self.factory_dir and os.path.isdir(self.factory_dir):
            dirs_to_scan.append((self.factory_dir, "factory"))

        entries: List[Dict[str, Any]] = []
        for scan_dir, source in dirs_to_scan:
            try:
                filenames = sorted(os.listdir(scan_dir))
            except OSError as e:
                logger.warning("[shokk] Could not scan %s: %s", scan_dir, e)
                continue
            for fname in filenames:
                if not fname.lower().endswith(SHOKK_EXT):
                    continue
                entries.append(self._entry_for(scan_dir, fname, source))
        return entries

    def _entry_for(self, scan_dir: str, fname: str, source: str) -> Dict[str, Any]:
        """Build a library-listing dict for a single ``.shokk`` file."""
        fpath = os.path.join(scan_dir, fname)
        try:
            manifest = self.get_manifest(fpath)
            size = os.path.getsize(fpath)
            return {
                "filename": fname,
                "path": fpath,
                "source": source,
                "name": manifest.get("name", fname.replace(SHOKK_EXT, "")),
                "author": manifest.get("author", ""),
                "description": manifest.get("description", ""),
                "tags": manifest.get("tags", []),
                "created": manifest.get("created", ""),
                "includes_paint": manifest.get("includes_paint", False),
                "has_spec": manifest.get("has_spec", False),
                "spb_version": manifest.get("spb_version", ""),
                "size_bytes": size,
                "size_mb": round(size / _BYTES_PER_MB, 2),
                "preview_url": f"/api/shokk/preview/{fname}",
            }
        except Exception as e:  # noqa: BLE001 - UI-facing, must never 500
            logger.warning("[shokk] Failed to read entry %s: %s", fpath, e)
            return {
                "filename": fname,
                "path": fpath,
                "source": source,
                "name": fname,
                "author": "",
                "description": f"Error reading file: {e}",
                "tags": [],
                "created": "",
                "includes_paint": False,
                "has_spec": False,
                "spb_version": "",
                "size_bytes": 0,
                "size_mb": 0,
                "preview_url": None,
            }

    def delete(self, filename: str) -> bool:
        """Delete a ``.shokk`` file from the *user* library (not factory).

        Args:
            filename: Basename of the file to delete. Path separators are
                rejected to prevent traversal.

        Returns:
            True if the file existed and was removed; False otherwise.
        """
        if not isinstance(filename, str) or not filename.endswith(SHOKK_EXT):
            return False
        # Reject any path segments -- we only accept bare filenames.
        if os.sep in filename or "/" in filename or ".." in filename:
            logger.warning("[shokk] Rejected delete with path chars: %r", filename)
            return False
        path = os.path.join(self.library_dir, filename)
        if not _path_is_within(filename, self.library_dir):
            logger.warning("[shokk] Rejected delete outside library: %r", filename)
            return False
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.info("[shokk] Deleted %s", path)
                return True
            except OSError as e:
                logger.error("[shokk] Delete failed for %s: %s", path, e)
        return False

    # ─── MISC ────────────────────────────────────────────────────────────

    @staticmethod
    def get_default_library_path() -> str:
        """Return the default SHOKK Library path for the current OS user.

        Returns:
            ``~/Documents/Shokker Paint Booth/SHOKK Library`` (expanded).
        """
        return os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "Shokker Paint Booth",
            "SHOKK Library",
        )

    def __repr__(self) -> str:
        return (
            f"<ShokkManager library={self.library_dir!r} "
            f"factory={self.factory_dir!r}>"
        )
