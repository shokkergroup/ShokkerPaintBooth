"""Thumbnail status route for Shokker Paint Booth."""

from __future__ import annotations

import json
import os

from flask import jsonify
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _safe_thumb_key(key):
    if not key:
        return "none"
    return str(key).replace("/", "_").replace("\\", "_").replace(":", "_").strip() or "none"


def _load_canonical_finish_ids(server_dir):
    """Load finish_ids_canonical.json if present."""
    path = os.path.join(server_dir, "finish_ids_canonical.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as _spb_ex:
            _spb_swallow('_load_canonical_finish_ids@L24', _spb_ex)
    return None


def build_thumbnail_inventory(thumbnail_dir, engine):
    """Compare each live registry with its own thumbnail directory.

    Raw folder totals are not coverage: an obsolete pattern PNG must never hide
    a missing base or monolithic PNG. This helper deliberately works per
    category and treats the loaded runtime registries as the source of truth.
    """
    categories = (
        ("bases", "base", getattr(engine, "BASE_REGISTRY", {})),
        ("patterns", "pattern", getattr(engine, "PATTERN_REGISTRY", {})),
        ("monolithics", "monolithic", getattr(engine, "MONOLITHIC_REGISTRY", {})),
    )
    report = {
        "thumbnail_dir": os.path.abspath(thumbnail_dir),
        "exists": os.path.isdir(thumbnail_dir),
        "inventory_source": "live_runtime_registries",
        "categories": {},
        "png_count": 0,
        "expected_total": 0,
        "present_total": 0,
        "missing_count": 0,
        "stale_count": 0,
        "missing_sample": [],
        "stale_sample": [],
    }

    for label, subdir_name, registry in categories:
        registry = registry or {}
        expected_by_filename = {}
        for key in registry:
            if label == "patterns" and (not key or key == "none"):
                continue
            expected_by_filename[_safe_thumb_key(key) + ".png"] = str(key)

        subdir = os.path.join(thumbnail_dir, subdir_name)
        files = set()
        if os.path.isdir(subdir):
            try:
                files = {
                    name for name in os.listdir(subdir)
                    if name.lower().endswith(".png") and os.path.isfile(os.path.join(subdir, name))
                }
            except OSError:
                files = set()

        expected_files = set(expected_by_filename)
        missing_files = sorted(expected_files - files)
        stale_files = sorted(files - expected_files)
        present = len(expected_files & files)
        category_report = {
            "directory": subdir_name,
            "expected": len(expected_files),
            "present": present,
            "missing_count": len(missing_files),
            "missing_sample": [expected_by_filename[name] for name in missing_files[:20]],
            "png_count": len(files),
            "stale_count": len(stale_files),
            "stale_sample": stale_files[:20],
        }
        report["categories"][label] = category_report
        report["png_count"] += len(files)
        report["expected_total"] += len(expected_files)
        report["present_total"] += present
        report["missing_count"] += len(missing_files)
        report["stale_count"] += len(stale_files)
        report["missing_sample"].extend(
            f"{subdir_name}/{expected_by_filename[name]}" for name in missing_files
        )
        report["stale_sample"].extend(
            f"{subdir_name}/{name}" for name in stale_files
        )

    report["missing_sample"] = report["missing_sample"][:50]
    report["stale_sample"] = report["stale_sample"][:50]
    return report


def register_thumbnail_status_routes(
    app,
    *,
    engine_getter,
    thumbnail_dir_getter,
    server_dir_getter,
    logger=None,
) -> None:
    """Register /api/thumbnail-status."""

    @app.route('/api/thumbnail-status', methods=['GET'])
    def api_thumbnail_status():
        """Return thumbnail directory status and a bounded sample of missing keys."""
        if logger is not None:
            logger.info("[thumbnail-status] Status check requested")

        thumbnail_dir = thumbnail_dir_getter()
        engine = engine_getter()
        inventory = build_thumbnail_inventory(thumbnail_dir, engine)
        canon = _load_canonical_finish_ids(server_dir_getter())
        catalog_snapshot = None
        if canon:
            catalog_snapshot = {
                "bases": len(canon.get("bases", [])),
                "patterns": len(canon.get("patterns", [])),
                "specials": len(canon.get("specials", [])),
            }
            catalog_snapshot["total"] = sum(catalog_snapshot.values())

        bases = inventory["categories"]["bases"]
        patterns = inventory["categories"]["patterns"]
        monolithics = inventory["categories"]["monolithics"]
        payload = {
            **inventory,
            "expected": {
                "bases": bases["expected"],
                "patterns": patterns["expected"],
                "specials": monolithics["expected"],
                "total": inventory["expected_total"],
            },
            "canonical_used": False,
            "catalog_snapshot": catalog_snapshot,
            "catalog_snapshot_used_for_runtime_coverage": False,
            "hint": (
                "Run from V5 folder: python rebuild_thumbnails.py. "
                "Regenerate canonical list: python scripts/export_finish_ids.py"
            ) if (not inventory["exists"] or inventory["png_count"] == 0) else None,
        }
        return jsonify(payload)
