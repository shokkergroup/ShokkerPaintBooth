"""
engine/asset_packs.py - Finish Pack resolver + downloader
==========================================================
finish-pack-downloader 2026-06-07

v7.0.2 shipped only a few bundled reference_textures (cultural/{rising_sun,
union_jacked,viva_mexico}). The heavier image-plate families
(forbidden_dragon, mortal_shokk, spec_overlays, colorshoxx, grunge_fun,
grunge_&_fun, pattern_plates, guest_designers) were NOT bundled into the
installer, so for buyers those finishes show in the picker but produce no
preview / will not render on a car (works in dev because the plates are local).

This module powers an in-app Finish Pack downloader. Packs are zipped + hosted
on the GitHub release feed and extract into:
    APP_DATA_DIR/asset_packs/reference_textures/<pack-internal-paths>

LOCKED CONVENTION (do not change):
  - A pack zip's internal paths are RELATIVE TO reference_textures
    (e.g. the mortal_shokk zip contains 'mortal_shokk/...'; the
    forbidden_dragon zip contains 'cultural/forbidden_dragon/...').
  - APP_DATA_DIR = %APPDATA%/ShokkerPaintBooth (the SAME dir main.js uses for
    the license). Python: os.path.join(os.environ.get('APPDATA') or
    os.path.expanduser('~'), 'ShokkerPaintBooth'). NOT Electron userData.
  - resolve_ref_dir(rel) returns the FIRST existing of
        (1) <bundled>/assets/reference_textures/<rel>
        (2) APP_DATA_DIR/asset_packs/reference_textures/<rel>
    and if neither exists returns the bundled path -> behavior is UNCHANGED
    when bundled assets are present (rising_sun keeps working).
"""

import os
import shutil
import tempfile
import zipfile
import urllib.request
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------

# GitHub release feed that hosts the pack zips as <id>.zip assets.
_RELEASE_BASE = (
    "https://github.com/shokkergroup/ShokkerPaintBooth/"
    "releases/download/asset-packs-v1"
)


def _bundled_root():
    """Engine's existing assets root - the same <root>/assets that the other
    loaders compute. engine/ lives one folder below the project root, so the
    bundled assets root is dirname(dirname(__file__)). Prefer CFG.ROOT_DIR when
    available (matches render.py::_get_pattern_root and registry root_dir) so
    dev + frozen Electron resolve identically."""
    try:
        from config import CFG
        if getattr(CFG, "ROOT_DIR", None) and os.path.isdir(CFG.ROOT_DIR):
            return CFG.ROOT_DIR
    except Exception:
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_data_dir():
    """APP_DATA_DIR = %APPDATA%/ShokkerPaintBooth (matches main.js LICENSE_DIR)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ShokkerPaintBooth")


def _packs_ref_root():
    """Where downloaded packs extract to:
    APP_DATA_DIR/asset_packs/reference_textures/"""
    return os.path.join(app_data_dir(), "asset_packs", "reference_textures")


def _bundled_ref_path(rel):
    """<bundled>/assets/reference_textures/<rel>."""
    rel = (rel or "").replace("/", os.sep)
    return os.path.normpath(
        os.path.join(_bundled_root(), "assets", "reference_textures", rel)
    )


def _downloaded_ref_path(rel):
    """APP_DATA_DIR/asset_packs/reference_textures/<rel>."""
    rel = (rel or "").replace("/", os.sep)
    return os.path.normpath(os.path.join(_packs_ref_root(), rel))


# ----------------------------------------------------------------------------
# RESOLVER
# ----------------------------------------------------------------------------

def resolve_ref_dir(rel):
    """Return a path under reference_textures for the given relative subpath.

    First existing of:
      (1) <bundled>/assets/reference_textures/<rel>   (shipped with installer)
      (2) APP_DATA_DIR/asset_packs/reference_textures/<rel>  (downloaded pack)
    If neither exists, return the bundled path (so behavior is UNCHANGED when
    bundled assets are present, and callers keep their existing fallback logic
    for missing assets).

    rel uses forward slashes (e.g. 'cultural/forbidden_dragon' or
    'mortal_shokk'); both separators are tolerated.
    """
    bundled = _bundled_ref_path(rel)
    if os.path.exists(bundled):
        return bundled
    downloaded = _downloaded_ref_path(rel)
    if os.path.exists(downloaded):
        return downloaded
    return bundled


# ----------------------------------------------------------------------------
# MANIFEST
# ----------------------------------------------------------------------------
# One entry per MISSING pack. "rel" is the pack's subpath under
# reference_textures (matches the zip's internal top-level path). "url" follows
# the locked GitHub release pattern .../asset-packs-v1/<id>.zip.

PACKS = [
    {
        "id": "forbidden_dragon",
        "label": "Forbidden Dragon",
        "rel": "cultural/forbidden_dragon",
        "sizeMB": 44,
        "enables": "cultural_forbidden_dragon",
    },
    {
        "id": "mortal_shokk",
        "label": "Mortal Shokk",
        "rel": "mortal_shokk",
        "sizeMB": 185,
        "enables": "mortal_shokk",
    },
    {
        "id": "spec_overlays",
        "label": "Money Shokk (Spec Overlays)",
        "rel": "spec_overlays",
        "sizeMB": 665,
        "enables": "money_shokk",
    },
    {
        "id": "colorshoxx",
        "label": "ColorShoxx",
        "rel": "colorshoxx",
        "sizeMB": 268,
        "enables": "colorshoxx",
    },
    {
        "id": "grunge_fun",
        "label": "Grunge Fun",
        "rel": "grunge_fun",
        "sizeMB": 302,
        "enables": "grunge_fun",
    },
    # 2026-06-08 audit: orphaned 'grunge_and_fun' pack (rel='grunge_&_fun', 170MB)
    # REMOVED — no runtime loader resolves grunge_&_fun. The real Grunge & Fun
    # finishes load from the 'grunge_fun' pack above via cultural_grunge_fun.py,
    # so this entry enabled nothing the app renders (wasted bandwidth + buyer
    # confusion in the downloader modal).
    {
        "id": "pattern_plates",
        "label": "Pattern Plates",
        "rel": "pattern_plates",
        "sizeMB": 195,
        "enables": "pattern_plates",
    },
    {
        "id": "guest_designers",
        "label": "Guest Designers",
        "rel": "guest_designers",
        "sizeMB": 18,
        "enables": "guest_designers",
    },
]


def _pack_url(pack_id):
    return "{base}/{pid}.zip".format(base=_RELEASE_BASE, pid=pack_id)


def get_pack(pack_id):
    """Return the manifest entry for pack_id, or None."""
    for p in PACKS:
        if p["id"] == pack_id:
            return p
    return None


def get_packs_manifest():
    """Return the manifest as a list of dicts enriched with url + installed.
    Safe to JSON-serialize for the /api/finish-packs endpoint."""
    out = []
    for p in PACKS:
        entry = dict(p)
        entry["url"] = _pack_url(p["id"])
        entry["installed"] = pack_installed(p["id"])
        out.append(entry)
    return out


# ----------------------------------------------------------------------------
# INSTALL STATE
# ----------------------------------------------------------------------------

def pack_installed(pack_id):
    """True if the pack's reference_textures assets are AVAILABLE — either BUNDLED in
    the installer (the all-in-one build) OR downloaded into APP_DATA. 2026-06-08:
    made bundled-aware so the full bundle reports every pack 'installed' (no download
    prompt, no pack_missing error) while a slim build still flags un-downloaded packs.
    Non-empty-dir check so a half-deleted shell does not read as installed."""
    pack = get_pack(pack_id)
    if not pack:
        return False
    for target in (_bundled_ref_path(pack["rel"]), _downloaded_ref_path(pack["rel"])):
        if os.path.isdir(target):
            try:
                for _root, _dirs, files in os.walk(target):
                    if files:
                        return True
            except Exception:
                pass
    return False


# ----------------------------------------------------------------------------
# SAFE EXTRACTION
# ----------------------------------------------------------------------------

def _is_within(directory, target):
    """True if `target` is inside `directory` (after normalization). Blocks
    zip path-traversal (../, absolute, drive-relative entries)."""
    directory = os.path.abspath(directory)
    target = os.path.abspath(target)
    try:
        common = os.path.commonpath([directory, target])
    except ValueError:
        # Different drives on Windows -> definitely outside.
        return False
    return common == directory


def _safe_extract(zip_path, dest_root):
    """Extract zip_path into dest_root, refusing any entry that would escape
    dest_root. Returns the number of files written."""
    os.makedirs(dest_root, exist_ok=True)
    written = 0
    with zipfile.ZipFile(zip_path) as zf:
        # Pre-validate every member before writing anything.
        for name in zf.namelist():
            # Normalize separators; reject absolute / drive / traversal entries.
            norm = name.replace("\\", "/")
            if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
                raise ValueError("Unsafe zip entry (absolute path): %r" % name)
            target = os.path.join(dest_root, *[p for p in norm.split("/") if p not in ("", ".")])
            if not _is_within(dest_root, target):
                raise ValueError("Unsafe zip entry (path traversal): %r" % name)
        # Validated -> extract.
        for member in zf.infolist():
            norm = member.filename.replace("\\", "/")
            parts = [p for p in norm.split("/") if p not in ("", ".")]
            if not parts:
                continue
            target = os.path.join(dest_root, *parts)
            if member.is_dir() or norm.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            written += 1
    return written


# ----------------------------------------------------------------------------
# INSTALL
# ----------------------------------------------------------------------------

def install_pack(pack_id, zip_path=None, url=None, expected_size=None):
    """Install a finish pack into
    APP_DATA_DIR/asset_packs/reference_textures/.

    - If `zip_path` is given, extract that local zip (used by tests / offline /
      side-loading).
    - Otherwise download `<url or manifest url>` to a temp file, then extract.

    `expected_size` (bytes), when provided, is enforced as a size sanity check
    on the downloaded zip. Extraction is path-traversal safe.

    Returns a dict: {"status": "ok"/"error", "id": ..., "files": N, "reason": ...}.
    """
    pack = get_pack(pack_id)
    if not pack:
        return {"status": "error", "id": pack_id, "reason": "unknown pack id"}

    dest_root = _packs_ref_root()
    tmp_zip = None
    try:
        os.makedirs(dest_root, exist_ok=True)

        if zip_path:
            if not os.path.isfile(zip_path):
                return {"status": "error", "id": pack_id,
                        "reason": "zip not found: %s" % zip_path}
            src_zip = zip_path
        else:
            dl_url = url or _pack_url(pack_id)
            fd, tmp_zip = tempfile.mkstemp(suffix=".zip", prefix="spb_pack_")
            os.close(fd)
            urllib.request.urlretrieve(dl_url, tmp_zip)
            size = os.path.getsize(tmp_zip)
            if size <= 0:
                return {"status": "error", "id": pack_id,
                        "reason": "downloaded zip is empty"}
            if expected_size is not None and abs(size - int(expected_size)) > max(
                    4096, int(expected_size) // 100):
                return {"status": "error", "id": pack_id,
                        "reason": "size mismatch (got %d, expected ~%d)" % (
                            size, int(expected_size))}
            src_zip = tmp_zip

        # Validate it is a real zip before touching the live asset dir.
        if not zipfile.is_zipfile(src_zip):
            return {"status": "error", "id": pack_id,
                    "reason": "not a valid zip archive"}

        n = _safe_extract(src_zip, dest_root)
        if n <= 0:
            return {"status": "error", "id": pack_id,
                    "reason": "zip contained no files"}
        return {"status": "ok", "id": pack_id, "files": n}
    except Exception as ex:  # noqa: BLE001 - surfaced to caller as error string
        return {"status": "error", "id": pack_id, "reason": str(ex)}
    finally:
        if tmp_zip and os.path.isfile(tmp_zip):
            try:
                os.remove(tmp_zip)
            except OSError:
                pass
