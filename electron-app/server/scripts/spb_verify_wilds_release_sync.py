"""Exact two-copy SHA-256 verifier for the 110-finish Wilds release set.

This command is read-only.  It checks the canonical root against the sole
packaged runtime tree (``electron-app/server``); it never creates or accepts
the retired PyInstaller ``pyserver/_internal`` third copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_wilds_release_gate import canonical_wilds_110  # noqa: E402
from scripts.spb_wilds_quality_release_lock import (  # noqa: E402
    DEFAULT_MANIFEST as DEFAULT_QUALITY_RELEASE_MANIFEST,
    QualityReleaseBlocked,
    validate_quality_release_manifest,
)


ELECTRON_REL = Path("electron-app") / "server"
CRITICAL_RUNTIME_FILES = (
    "engine/expansions/fractured_themes_2026.py",
    "engine/expansions/fractured_themes_fix_2026.py",
    "engine/expansions/fractured_morpho_2026.py",
    "engine/expansions/fractured_bloom_2026.py",
    "engine/expansions/fractured_petri_2026.py",
    "engine/expansions/fractured_wilds_microkit_2026.py",
    "engine/expansions/fractured_wilds_signatures_2026.py",
    "engine/paint_v2/surface_intent.py",
    "paint-booth-0-finish-data.js",
    "paint-booth-0-catalog-scorecard.js",
    "server.py",
    "shokker_engine_v2.py",
    "rebuild_thumbnails.py",
    "rebuild_picker_swatches.py",
    "server_routes/swatch_routes.py",
    "scripts/runtime-sync-manifest.json",
    "scripts/spb_wilds_quality_release_lock.py",
    "scripts/spb_wilds_release_gate.py",
    "thumbnails/picker_split/_manifest.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_quality_source_paths(source_paths) -> tuple[str, ...]:
    """Return canonical project-relative quality sources or fail closed.

    ``source_paths`` crosses a report-to-filesystem trust boundary.  Even
    though the quality lock validates the report, the delivery verifier must
    not accept absolute paths, traversal, platform-ambiguous spellings, or two
    names that address the same Windows path.
    """
    if not isinstance(source_paths, (list, tuple)):
        raise RuntimeError("quality source_paths must be a list or tuple")

    validated: list[str] = []
    seen: dict[str, str] = {}
    for index, value in enumerate(source_paths):
        label = f"quality source_paths[{index}]"
        if not isinstance(value, str) or not value:
            raise RuntimeError(f"{label} must be a non-empty string")
        if value != value.strip():
            raise RuntimeError(f"unsafe {label}: surrounding whitespace")
        if "\\" in value:
            raise RuntimeError(f"unsafe {label}: backslashes are not canonical")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise RuntimeError(f"unsafe {label}: control character")
        if ":" in value:
            raise RuntimeError(f"unsafe {label}: drive or stream syntax")

        posix = PurePosixPath(value)
        windows = PureWindowsPath(value)
        raw_parts = value.split("/")
        if posix.is_absolute() or windows.is_absolute() or windows.drive:
            raise RuntimeError(f"unsafe absolute {label}: {value!r}")
        if any(part in ("", ".", "..") for part in raw_parts):
            raise RuntimeError(f"unsafe traversal or non-canonical {label}: {value!r}")
        if any(part != part.rstrip(" .") for part in raw_parts):
            raise RuntimeError(f"unsafe Windows-ambiguous {label}: {value!r}")
        if any(any(char in '<>"|?*' for char in part) for part in raw_parts):
            raise RuntimeError(f"unsafe Windows filename syntax in {label}: {value!r}")
        reserved = {"CON", "PRN", "AUX", "NUL"}
        reserved.update(f"COM{number}" for number in range(1, 10))
        reserved.update(f"LPT{number}" for number in range(1, 10))
        if any(part.split(".", 1)[0].upper() in reserved for part in raw_parts):
            raise RuntimeError(f"unsafe Windows reserved name in {label}: {value!r}")
        if posix.as_posix() != value:
            raise RuntimeError(f"unsafe non-canonical {label}: {value!r}")

        collision_key = value.casefold()
        if collision_key in seen:
            raise RuntimeError(
                "duplicate dynamic quality source path: "
                f"{seen[collision_key]!r} and {value!r}"
            )
        seen[collision_key] = value
        validated.append(value)

    return tuple(sorted(validated, key=lambda item: (item.casefold(), item)))


def _release_relative_paths(
    ids: list[str],
    critical_files=CRITICAL_RUNTIME_FILES,
    *,
    source_paths=(),
):
    paths = []
    for fid in ids:
        if not re.fullmatch(r"[a-z0-9_]+", fid):
            raise RuntimeError(f"Unsafe Wilds finish ID in release census: {fid!r}")
        paths.append(f"thumbnails/monolithic/{fid}.png")
        paths.append(f"thumbnails/picker_split/monolithic/{fid}.png")
    paths.extend(critical_files)
    static_by_key: dict[str, str] = {}
    for relative in paths:
        key = str(relative).casefold()
        if key in static_by_key:
            raise RuntimeError("Release verification path list contains duplicates")
        static_by_key[key] = str(relative)

    for relative in _validated_quality_source_paths(source_paths):
        key = relative.casefold()
        existing = static_by_key.get(key)
        if existing is not None:
            if existing != relative:
                raise RuntimeError(
                    "quality source path has ambiguous case collision: "
                    f"{existing!r} and {relative!r}"
                )
            # A quality source can legitimately already be an unconditional
            # critical runtime file.  One exact SHA pair is sufficient.
            continue
        static_by_key[key] = relative
        paths.append(relative)
    if len(paths) != len({str(path).casefold() for path in paths}):
        raise RuntimeError("Release verification path list contains duplicates")
    return paths


def _resolves_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def verify_exact_two_copy(
    root: Path,
    ids: list[str],
    *,
    critical_files=CRITICAL_RUNTIME_FILES,
    source_paths=(),
    enforce_manifest_contract: bool = True,
):
    root = Path(root).resolve()
    electron = root / ELECTRON_REL
    errors: list[str] = []
    quality_sources = _validated_quality_source_paths(source_paths)
    release_paths = _release_relative_paths(
        ids, critical_files, source_paths=quality_sources,
    )

    if enforce_manifest_contract:
        manifest_path = root / "scripts" / "runtime-sync-manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"runtime sync manifest unreadable: {exc}")
            manifest = {}
        if manifest.get("targets") != ["electron-app/server"]:
            errors.append(
                f"runtime sync targets must be exactly ['electron-app/server']; "
                f"got {manifest.get('targets')!r}"
            )
        managed = list(manifest.get("files", ())) + list(manifest.get("directories", ()))
        if any("pyserver/_internal" in str(value).replace("\\", "/") for value in managed):
            errors.append("runtime sync manifest still manages the retired third copy")
        retired = electron / "pyserver" / "_internal"
        if retired.exists():
            errors.append(f"retired third runtime copy exists: {retired}")

    checked = []
    quality_source_set = set(quality_sources)
    for relative in release_paths:
        source = root / Path(relative)
        target = electron / Path(relative)
        if relative in quality_source_set:
            if not _resolves_within(source, root):
                errors.append(f"unsafe resolved quality source path: {relative}")
                continue
            if not _resolves_within(target, electron):
                errors.append(f"unsafe resolved electron quality source path: {relative}")
                continue
        if not source.is_file():
            errors.append(f"root missing: {relative}")
            continue
        if not target.is_file():
            errors.append(f"electron missing: {relative}")
            continue
        source_hash = _sha256(source)
        target_hash = _sha256(target)
        if source_hash != target_hash:
            errors.append(
                f"SHA-256 drift: {relative} root={source_hash} electron={target_hash}"
            )
            continue
        checked.append({"path": relative, "sha256": source_hash})

    expected = len(release_paths)
    if len(checked) != expected and not errors:
        errors.append(f"verified {len(checked)} paths, expected {expected}")
    return {
        "schema": 1,
        "copyRule": "root -> electron-app/server (two copies only)",
        "wildsCount": len(ids),
        "expectedPairs": expected,
        "verifiedPairs": len(checked),
        "qualitySourcePaths": list(quality_sources),
        "qualitySourcePathCount": len(quality_sources),
        "ok": not errors and len(checked) == expected,
        "errors": errors,
        "files": checked,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Wilds delivery integrity and require the explicit 110-ID "
            "owner-quality release manifest"
        )
    )
    parser.add_argument("--json", action="store_true", help="Emit the full machine-readable report")
    parser.add_argument(
        "--quality-manifest", type=Path, default=DEFAULT_QUALITY_RELEASE_MANIFEST,
    )
    args = parser.parse_args(argv)

    from engine.registry import MONOLITHIC_REGISTRY

    _lanes, ids = canonical_wilds_110(MONOLITHIC_REGISTRY)
    try:
        quality = validate_quality_release_manifest(
            args.quality_manifest, ids, registry=MONOLITHIC_REGISTRY,
        )
    except (OSError, TypeError, QualityReleaseBlocked) as exc:
        quality = {
            "status": "quality_release_blocked",
            "owner_accepted": 0,
            "production_wired": 0,
            "error": str(exc),
        }
    try:
        if quality["status"] == "quality_release_lock_open":
            delivery = verify_exact_two_copy(
                ROOT, ids, source_paths=quality.get("source_paths"),
            )
        else:
            delivery = verify_exact_two_copy(ROOT, ids)
    except (RuntimeError, TypeError, ValueError) as exc:
        delivery = {
            "schema": 1,
            "copyRule": "root -> electron-app/server (two copies only)",
            "wildsCount": len(ids),
            "expectedPairs": len(ids) * 2 + len(CRITICAL_RUNTIME_FILES),
            "verifiedPairs": 0,
            "qualitySourcePaths": [],
            "qualitySourcePathCount": 0,
            "ok": False,
            "errors": [f"release path contract rejected: {exc}"],
            "files": [],
        }
    report = {
        "schema": 2,
        "ok": bool(delivery["ok"] and quality["status"] == "quality_release_lock_open"),
        "delivery": delivery,
        "qualityRelease": quality,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    elif report["ok"]:
        print(
            f"PASS: {delivery['wildsCount']}/110 Wilds finishes; "
            f"{delivery['verifiedPairs']}/{delivery['expectedPairs']} exact two-copy pairs; "
            f"{quality['owner_accepted']}/110 explicitly owner accepted"
        )
    else:
        print(
            f"FAIL: delivery {delivery['verifiedPairs']}/{delivery['expectedPairs']} exact pairs; "
            f"quality={quality['status']}"
        )
        for error in delivery["errors"][:40]:
            print(f"  {error}")
        if len(delivery["errors"]) > 40:
            print(f"  ... and {len(delivery['errors']) - 40} more delivery errors")
        if quality["status"] != "quality_release_lock_open":
            print(f"  quality lock: {quality['error']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
