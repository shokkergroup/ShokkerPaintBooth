"""Fail-closed *delivery* helpers for the 110 Fractured Wilds finishes.

The release census is intentionally derived from the four renderer families,
not from catalog/scorecard categories.  Category membership is presentation
metadata and has previously described only 90 of the 110 runtime finishes.

These helpers cannot declare visual quality or owner acceptance. Production
release paths must also pass ``spb_wilds_quality_release_lock.py``; a green
census, renderer hash, PNG, or two-copy check is delivery evidence only.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence


EXPECTED_WILDS_LANE_COUNTS = {
    "cryptid": 20,
    "morpho": 50,
    "bloom": 20,
    "petri": 20,
}
EXPECTED_WILDS_TOTAL = sum(EXPECTED_WILDS_LANE_COUNTS.values())


def _entry_callables(entry):
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        return entry[0], entry[1]
    if isinstance(entry, dict):
        return entry.get("spec_fn"), entry.get("paint_fn")
    return None, None


def validate_wilds_110_census(
    lanes: Mapping[str, Sequence[str]],
    registry: Mapping[str, object],
) -> list[str]:
    """Return the canonical ordered IDs or fail on any census/registry drift."""
    actual_counts = {name: len(lanes.get(name, ())) for name in EXPECTED_WILDS_LANE_COUNTS}
    if actual_counts != EXPECTED_WILDS_LANE_COUNTS:
        raise RuntimeError(
            f"Wilds renderer census mismatch: {actual_counts} != {EXPECTED_WILDS_LANE_COUNTS}"
        )
    unexpected_lanes = sorted(set(lanes) - set(EXPECTED_WILDS_LANE_COUNTS))
    if unexpected_lanes:
        raise RuntimeError(f"Wilds renderer census has unexpected lane(s): {unexpected_lanes}")

    ids = [
        fid
        for lane in ("cryptid", "morpho", "bloom", "petri")
        for fid in lanes[lane]
    ]
    if len(ids) != EXPECTED_WILDS_TOTAL:
        raise RuntimeError(f"Wilds renderer census is {len(ids)}, expected {EXPECTED_WILDS_TOTAL}")
    duplicates = sorted({fid for fid in ids if ids.count(fid) > 1})
    if duplicates:
        raise RuntimeError(f"Wilds renderer census contains duplicate ID(s): {duplicates}")

    missing = [fid for fid in ids if fid not in registry]
    invalid = []
    for fid in ids:
        if fid not in registry:
            continue
        spec_fn, paint_fn = _entry_callables(registry[fid])
        if not callable(spec_fn) or not callable(paint_fn):
            invalid.append(fid)
    if missing or invalid:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if invalid:
            details.append(f"non-callable={invalid}")
        raise RuntimeError("Wilds MONOLITHIC_REGISTRY gate failed: " + "; ".join(details))
    return ids


def canonical_wilds_110(registry: MutableMapping[str, object] | None = None):
    """Validate the final runtime registry's canonical 20/50/20/20 census.

    This function is deliberately read-only. Reinstalling legacy modules here
    could overwrite later owner-approved authority immediately before a bake.
    The supplied registry must therefore be the final registry the caller will
    actually render through.
    """
    if registry is None:
        from engine.registry import MONOLITHIC_REGISTRY

        registry = MONOLITHIC_REGISTRY

    lanes, _declared_ids = declared_wilds_110()
    ids = validate_wilds_110_census(lanes, registry)
    return lanes, ids


def declared_wilds_110():
    """Return the exact Wilds ID census without installing renderer overrides."""
    from engine.expansions import fractured_bloom_2026 as bloom
    from engine.expansions import fractured_morpho_2026 as morpho
    from engine.expansions import fractured_petri_2026 as petri
    from engine.expansions import fractured_themes_2026 as themes

    lanes = {
        "cryptid": sorted(fid for fid in themes.ALL if fid.startswith("fc_")),
        "morpho": sorted(morpho.ALL),
        "bloom": sorted(bloom.ALL),
        "petri": sorted(petri.ALL),
    }
    counts = {name: len(lanes[name]) for name in EXPECTED_WILDS_LANE_COUNTS}
    if counts != EXPECTED_WILDS_LANE_COUNTS:
        raise RuntimeError(
            f"Wilds declared census mismatch: {counts} != {EXPECTED_WILDS_LANE_COUNTS}"
        )
    ids = [
        fid
        for lane in ("cryptid", "morpho", "bloom", "petri")
        for fid in lanes[lane]
    ]
    if len(ids) != EXPECTED_WILDS_TOTAL or len(set(ids)) != EXPECTED_WILDS_TOTAL:
        raise RuntimeError("Wilds declared census must contain exactly 110 unique IDs")
    return lanes, ids


def require_wilds_quality_release_for_items(
    items, *, manifest_path=None, root=None, registry=None,
):
    """Fail closed before any selected Wilds thumbnail can be written.

    The full 110-ID owner manifest is required even when a caller selects only
    one Wilds ID. This prevents single-ID, category, worker, or API paths from
    bypassing the release command's all-or-nothing quality contract.
    """
    _lanes, ids = declared_wilds_110()
    wilds = set(ids)
    targeted = sorted({
        finish_key
        for finish_type, finish_key in items
        if finish_type == "monolithic" and finish_key in wilds
    })
    if not targeted:
        return None

    from scripts.spb_wilds_quality_release_lock import (
        DEFAULT_MANIFEST,
        validate_quality_release_manifest,
    )

    validate_kwargs = {} if root is None else {"root": root}
    report = validate_quality_release_manifest(
        DEFAULT_MANIFEST if manifest_path is None else manifest_path,
        ids,
        registry=registry,
        **validate_kwargs,
    )
    return {**report, "targeted_wilds": targeted}


def verify_picker_snapshot_postconditions(server_module, items: Iterable[tuple[str, str]]):
    """Verify snapshot delivery against its current renderer hash/path.

    A zero-error baker result is insufficient: an under-selected 90-item list,
    stale manifest entry, or missing PNG must fail the release gate.
    This function never confers owner acceptance; the separate quality-state
    release lock remains mandatory.
    """
    requested = list(items)
    duplicates = sorted({item for item in requested if requested.count(item) > 1})
    errors: list[str] = []
    if duplicates:
        errors.append(f"duplicate requested item(s): {duplicates}")

    manifest = server_module._load_picker_split_manifest()
    finishes = manifest.get("finishes", {}) if isinstance(manifest, dict) else {}
    for finish_type, finish_key in requested:
        manifest_key = f"{finish_type}:{finish_key}"
        entry = finishes.get(manifest_key)
        path = server_module._picker_split_static_path(finish_type, finish_key)
        current_hash = server_module._picker_finish_renderer_hash(finish_type, finish_key)
        if not current_hash:
            errors.append(f"{manifest_key}: current renderer hash is empty")
        if not os.path.isfile(path):
            errors.append(f"{manifest_key}: snapshot path missing: {path}")
        if not isinstance(entry, dict):
            errors.append(f"{manifest_key}: manifest entry missing")
            continue
        if entry.get("hash") != current_hash:
            errors.append(
                f"{manifest_key}: manifest hash {entry.get('hash')!r} != current {current_hash!r}"
            )
        expected_color = server_module._catalog_color_for_picker_swatch(
            finish_type, finish_key
        )
        if entry.get("color_hex") != expected_color:
            errors.append(
                f"{manifest_key}: manifest color {entry.get('color_hex')!r} "
                f"!= current {expected_color!r}"
            )
        if entry.get("render_scale") != server_module.PICKER_SNAPSHOT_RENDER_SCALE:
            errors.append(f"{manifest_key}: render scale is stale")
    return errors


def acquire_exclusive_lock(
    lock_path: str | Path,
    *,
    stale_secs: float = 3600,
    wait_secs: float = 0,
    poll_secs: float = 0.25,
):
    """Acquire an atomic lock, optionally waiting a bounded nonzero interval."""
    lock = os.fspath(lock_path)
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    wait_secs = max(0.0, float(wait_secs))
    poll_secs = max(0.005, float(poll_secs))
    deadline = time.monotonic() + wait_secs
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("ascii"))
            finally:
                os.close(fd)
            return lock
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(lock)
            except OSError:
                age = stale_secs + 1
            if age >= stale_secs:
                try:
                    os.remove(lock)
                    continue
                except OSError:
                    pass
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            time.sleep(min(poll_secs, remaining))
