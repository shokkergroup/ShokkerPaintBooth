"""Regression guardrails for the runtime-mirror three-copy rule.

## Context (2026-04-20 regression loop iter 9)

Checklist #9 asked: do runtime mirrors stay synced and do JS/Python
files stay parse-clean across copies?

The SPB architecture uses THREE runtime copies of each shipped file:
  - `<root>/<name>`                                      — dev source
  - `<root>/electron-app/server/<name>`                   — build-stage
  - `<root>/electron-app/server/pyserver/_internal/<name>`— Electron bundle

Two separate sync mechanisms operate:

1. **`scripts/sync-runtime-copies.js`** — covers ONLY front-end
   assets (HTML/CSS/JS, 17 files in the manifest × 2 targets = 34
   pairs). Runs per-iter via the `--check` / `--write` gate. Hot-
   reloadable: JS/CSS edits visible on Electron reload.

2. **`electron-app/copy-server-assets.js`** — copies Python files
   (BACKEND_ASSETS list: 12 Python files) + the `engine/` directory
   + thumbnails + assets. Runs ONLY at Electron build time, not
   per-edit. **Python mirrors drift from root between builds — this
   is expected.**

The `--check` gate I've been running per-iter does NOT cover Python.
That's by design (Python isn't hot-reloadable for Electron anyway;
it requires rebuild).

## Audit findings

- Manifest enumerates 17 front-end files × 2 targets → 34 pairs.
  No drift detected via `--check`. Safe.
- All 3 Python mirror locations parse-clean. No corruption from
  HARDMODE loop, no truncation, no trailing garbage.
- All 3 JS mirror locations parse-clean via `node --check`.
- Python mirror copies are stale vs root (expected — they're
  updated on build, not on edit). Not a regression.

## What these tests do

Pin the manifest's structure (expected file count, target paths),
pin that BACKEND_ASSETS list in copy-server-assets.js matches the
documented mirror requirement, and run a syntactic parse check
over all 3 copies of the most-important files. If a future refactor
drops a file from the manifest or corrupts a copy, this fires.
"""

import ast
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "scripts" / "runtime-sync-manifest.json"
COPY_SCRIPT = REPO / "electron-app" / "copy-server-assets.js"

MIRROR_TARGETS = [
    REPO,
    REPO / "electron-app" / "server",
    REPO / "electron-app" / "server" / "pyserver" / "_internal",
]

# Key Python files that MUST exist in all three mirror locations
# (subset of BACKEND_ASSETS; verified in build copy script).
KEY_PYTHON_FILES = [
    "shokker_engine_v2.py",
    "server.py",
    "server_v5.py",
    "shokk_manager.py",
    "config.py",
    "finish_colors_lookup.py",
    "shokker_24k_expansion.py",
    "shokker_color_monolithics.py",
    "shokker_fusions_expansion.py",
    "engine/expansions/owner_review_effects.py",
]

# Key JS files (subset of the front-end manifest).
KEY_JS_FILES = [
    "paint-booth-0-finish-data.js",
    "paint-booth-0-catalog-scorecard.js",
    "paint-booth-0-picker-owner-ratings.js",
    "paint-booth-2-state-zones.js",
    "paint-booth-3-canvas.js",
    "js/canvas/dispatch.js",
    "js/canvas/layer/healing-brush.js",
    "paint-booth-5-api-render.js",
    "paint-booth-6-ui-boot.js",
    "paint-booth-7-shokk.js",
]


def test_runtime_manifest_structure_is_stable():
    """The runtime-sync manifest must contain exactly 25 files and 2
    targets. Original count was 17 front-end-only (iter 9 of the
    2026-04-20 regression loop); extended on 2026-04-21 post-Codex-
    audit to also include 4 hot-path Python modules (shokker_engine_v2.py
    + engine/compose.py + engine/core.py + engine/spec_patterns.py)
    and engine/paint_v2/foundation_enhanced.py so per-edit sync
    catches Python changes that previously only reached the Electron
    runtime at build time.

    2026-04-22 HEENAN FAMILY overnight iter 4 (Foundation trust):
    added engine/base_registry_data.py (count: 22 → 23). This file
    carries the BASE_REGISTRY data dict (Foundation Bases + every
    other base finish); previously it was only copied at Electron
    build time via copy-server-assets.js, which caused recurring
    drift when root was edited between builds. Now it auto-syncs
    per edit alongside the rest of the hot-path Python.

    2026-04-23 special-finish repair: added
    engine/paint_v2/paradigm_scifi.py (count: 23 -> 24) because p_volcanic
    is wired from base_registry_data.py into that module. Per-edit runtime
    sync must include both ends of that registry/function dependency.

    2026-04-23 HyperFlip color-shift research: added
    engine/perceptual_color_shift.py (count: 24 -> 25). This module is a
    shipping monolithic source file, not a test artifact.

    2026-04-24 audit/visual-health pass: added hot-path generator modules that
    are edited directly during finish-quality work and must reach Electron per
    edit, not only during packaging. Later the same morning, Metals & Forged
    work added arsenal_24k.py + spec_paint.py to the same per-edit mirror path.
    COLORSHOXX rebuild then added dual_color_shift.py for the same reason.

    2026-05-29 DUP-01 close (A2 sync covers engine/): whole-tree engine
    coverage is now added via the manifest's new `check_only_directories`
    key (`["engine"]`), NOT by enumerating every engine module under `files`.
    That keeps the explicit-`files` count stable while `--check`/`--list`
    walk the whole engine tree and REPORT drift. So the `files` count is
    unchanged by DUP-01 — it remains whatever the explicit allow-list holds.
    To stop this assertion drifting against the real manifest, the expected
    count is DERIVED from the manifest's own `files` length and then sanity-
    bounded, with the reviewed exact value pinned in EXPECTED_FILE_COUNT
    below (bump it deliberately when files are intentionally added/removed).
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert "files" in manifest and isinstance(manifest["files"], list), (
        "runtime-sync-manifest.json lost its `files` array. Schema changed."
    )
    assert "targets" in manifest and isinstance(manifest["targets"], list), (
        "runtime-sync-manifest.json lost its `targets` array. Schema changed."
    )
    assert "directories" in manifest and isinstance(manifest["directories"], list), (
        "runtime-sync-manifest.json lost its `directories` array for shipped asset folders."
    )

    file_count = len(manifest["files"])
    target_count = len(manifest["targets"])
    directory_count = len(manifest["directories"])

    # Reviewed exact count of explicitly-listed `files` entries. DUP-01 added
    # whole-engine coverage via `check_only_directories`, NOT new `files`, so
    # this stays at the post-2026-04-24 reviewed value of 220. Bump
    # deliberately (with a dated note above) when files are intentionally
    # added or removed from the explicit allow-list.
    # 2026-07-15 SPB-93 tick 12: dedicated Layer Healing Brush module.
    EXPECTED_FILE_COUNT = 221
    assert file_count == EXPECTED_FILE_COUNT, (
        f"runtime-sync manifest now lists {file_count} files "
        f"(expected {EXPECTED_FILE_COUNT} reviewed runtime files). "
        f"NOTE: DUP-01 engine coverage is added via "
        f"`check_only_directories`, not by enumerating engine modules "
        f"under `files` — so this count should NOT change when engine "
        f"drift coverage is extended. Confirm each added/removed `files` "
        f"entry is either a front-end asset or an explicitly-synced "
        f"Python module; tests and build artifacts must never be added. "
        f"Update EXPECTED_FILE_COUNT after review."
    )
    assert target_count == 2, (
        f"runtime-sync manifest now lists {target_count} targets "
        f"(was 2). The three-copy rule mandates exactly two "
        f"mirror targets: `electron-app/server` and "
        f"`electron-app/server/pyserver/_internal`. Confirm any "
        f"addition is intentional."
    )
    assert directory_count == 6, (
        f"runtime-sync manifest now lists {directory_count} directories "
        f"(expected 6 shipped texture folders). Confirm shipped image "
        f"asset folders are intentional and do not include raw source dumps. "
        f"NOTE: the engine tree is covered via `check_only_directories`, "
        f"NOT `directories`, so this count is unaffected by DUP-01."
    )

    # 2026-05-29 DUP-01: the whole engine/ tree must be a *report-only*
    # synced directory so `--check`/`--list` SEE engine drift (previously
    # engine/ was only mirrored at Electron build time and `--check` was
    # blind to it). It must live under `check_only_directories` (report-only)
    # and NOT under `directories` (writable) — converging drifted
    # finish-output engine modules is the owner's call, not an auto-write.
    check_only_dirs = manifest.get("check_only_directories", [])
    assert isinstance(check_only_dirs, list), (
        "runtime-sync-manifest.json: `check_only_directories` must be an array."
    )
    assert "engine" in check_only_dirs, (
        "runtime-sync-manifest.json must list `engine` under "
        "`check_only_directories` so `--check` reports engine drift "
        "(DUP-01). It was found neither there. Without it, the drift-check "
        "is blind to the ~106 unmanaged engine modules."
    )
    assert "engine" not in manifest["directories"], (
        "`engine` must NOT be under `directories` (which is writable / "
        "auto-synced by --write). Engine drift coverage is REPORT-ONLY: "
        "converging drifted finish-output modules is the owner's call. "
        "Move `engine` to `check_only_directories`."
    )

    expected_targets = {
        "electron-app/server",
        "electron-app/server/pyserver/_internal",
    }
    got_targets = set(manifest["targets"])
    assert got_targets == expected_targets, (
        f"runtime-sync manifest targets changed.\n"
        f"  expected: {expected_targets}\n"
        f"  got:      {got_targets}"
    )


def test_runtime_manifest_contains_no_test_or_artifact_files():
    """The runtime-sync manifest must NOT contain test files or
    build artifacts. It MAY contain a small explicit allow-list of
    hot-path Python modules (added 2026-04-21 post-Codex-audit so
    per-edit sync catches Python changes that used to only reach
    the Electron runtime at build time). Everything else that's
    not a front-end asset is forbidden.

    Allowed Python entries (in addition to all front-end assets):
      - shokker_engine_v2.py
      - engine/compose.py
      - engine/core.py
      - engine/spec_patterns.py
      - active finish generator modules listed in ALLOWED_PYTHON below
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = manifest["files"]

    ALLOWED_PYTHON = {
        "shokker_engine_v2.py",
        "config.py",
        "server.py",
        "server_routes/__init__.py",
        "server_routes/asset_routes.py",
        "server_routes/diagnostics.py",
        "server_routes/finish_catalog_routes.py",
        "server_routes/finish_lookup_routes.py",
        "server_routes/static_pages.py",
        "server_routes/config_routes.py",
        "server_routes/render_monitoring.py",
        "server_routes/system_status.py",
        "server_routes/license_routes.py",
        "server_routes/default_asset_routes.py",
        "server_routes/photoshop_export_routes.py",
        "server_routes/photoshop_import_routes.py",
        "server_routes/spec_channel_export_routes.py",
        "server_routes/psd_layer_export_routes.py",
        "server_routes/psd_import_routes.py",
        "server_routes/dual_shift_routes.py",
        "server_routes/legacy_apply_finish_routes.py",
        "server_routes/paint_recolor_support.py",
        "server_routes/render_file_routes.py",
        "server_routes/file_picker_routes.py",
        "server_routes/paint_upload_routes.py",
        "server_routes/iracing_utility_routes.py",
        "server_routes/validation_routes.py",
        "server_routes/pattern_layer_routes.py",
        "server_routes/thumbnail_status.py",
        "server_routes/cache_admin_routes.py",
        "server_routes/swatch_review_routes.py",
        "server_routes/job_cleanup.py",
        "server_routes/server_bootstrap.py",
        "server_routes/spec_result_support.py",
        "server_routes/swatch_routes.py",
        "server_routes/shokk_routes.py",
        "server_routes/custom_finish_routes.py",
        "server_routes/user_import_routes.py",
        "server_routes/preview_source_cache.py",
        "server_routes/guest_designer_routes.py",
        "server_routes/custom_finish_mixer_routes.py",
        "server_routes/finish_viewer_render_routes.py",
        "server_routes/finish_viewer_recent_routes.py",
        "server_v5.py",
        "server_health.py",
        "engine/compose.py",
        "engine/overlay.py",
        "engine/core.py",
        "engine/dual_color_shift.py",
        "engine/color_shift.py",
        "engine/spec_paint.py",
        "engine/spec_patterns.py",
        "engine/spec_pattern_families/__init__.py",
        "engine/spec_pattern_families/mechanical.py",
        "engine/spec_pattern_families/weather_track.py",
        "engine/spec_pattern_families/artistic.py",
        "engine/spec_pattern_families/abstract_art.py",
        "engine/micro_flake_shift.py",
        "engine/prizm.py",
        "engine/pattern_expansion.py",
        "engine/expansions/arsenal_24k.py",
        "engine/expansions/color_clash.py",
        "engine/expansions/color_monolithics.py",
        "engine/expansions/fusions.py",
        "engine/expansions/living_finishes.py",
        "engine/expansions/atelier.py",
        "engine/expansions/paradigm.py",
        "engine/expansions/owner_review_chameleon.py",
        "engine/expansions/owner_review_effects.py",
        "engine/expansions/owner_review_standalone.py",
        "engine/paint_v2/brushed_directional.py",
        "engine/paint_v2/candy_special.py",
        "engine/paint_v2/cultural_rising_sun.py",
        "engine/paint_v2/cultural_union_jacked.py",
        "engine/paint_v2/cultural_viva_mexico.py",
        "engine/paint_v2/cultural_grunge_fun.py",
        "engine/paint_v2/cultural_placement.py",
        "engine/paint_v2/placement_context.py",
        "engine/paint_v2/cultural_mortal_shokk.py",
        "engine/paint_v2/exotic_metal.py",
        "engine/paint_v2/foundation_enhanced.py",
        "engine/paint_v2/guest_designers.py",
        "engine/paint_v2/user_imports.py",
        "engine/paint_v2/user_imports_ingest.py",
        "engine/paint_v2/user_imports_paths.py",
        "engine/paint_v2/user_imports_spec_dna.py",
        "engine/paint_v2/user_imports_engine_preview.py",
        "engine/paint_v2/metallic_flake.py",
        "engine/paint_v2/metallic_standard.py",
        "engine/paint_v2/paint_technique.py",
        # 2026-04-22 HEENAN FAMILY overnight iter 4 (Foundation trust):
        # added so Foundation-Base metadata edits at root auto-sync to
        # Electron mirrors instead of drifting between builds.
        "engine/base_registry_data.py",
        "engine/chameleon.py",
        # p_volcanic's registry entry points here; syncing only
        # base_registry_data.py would leave Electron running stale math.
        "engine/paint_v2/paradigm_scifi.py",
        "engine/paint_v2/structural_color.py",
        "engine/registry_patches/candy_special_reg.py",
        "engine/registry_patches/exotic_metal_reg.py",
        "engine/registry_patches/metallic_flake_reg.py",
        "engine/registry_patches/paint_technique_reg.py",
        "engine/perceptual_color_shift.py",
        "engine/registry.py",
        "engine/spec_sculpt/__init__.py",
        "engine/spec_sculpt/core.py",
        "engine/spec_sculpt/export.py",
        "engine/spec_sculpt/generate.py",
        "engine/spec_sculpt/preview.py",
        "engine/spec_sculpt/catalog_blend.py",
        "engine/spec_sculpt/presets.py",
    }

    leaks = []
    for f in files:
        lower = f.lower()
        if "test" in lower:
            leaks.append(f"test-file leak: {f}")
        if lower.endswith(".py") and f not in ALLOWED_PYTHON:
            leaks.append(f"unapproved python leak: {f}")
        if lower.endswith((".pyc", ".pyo", ".exe", ".dll")):
            leaks.append(f"build-artifact leak: {f}")

    assert not leaks, (
        "runtime-sync manifest contains files that don't belong:\n  "
        + "\n  ".join(leaks)
    )


def test_runtime_manifest_mirrors_cultural_texture_directories():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    directories = set(manifest.get("directories", []))

    expected = {
        "assets/reference_textures/cultural/rising_sun",
        "assets/reference_textures/cultural/union_jacked",
        "assets/reference_textures/cultural/viva_mexico",
        "assets/reference_textures/mortal_shokk",
        "assets/reference_textures/guest_designers/lyons_designs",
    }
    assert expected <= directories

    for rel_dir in expected:
        root_dir = REPO / rel_dir
        assert (root_dir / "manifest.json").is_file(), f"{rel_dir} is missing manifest.json"
        textures = [
            p for p in root_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
        ]
        assert textures, f"{rel_dir} has no shipped texture images"


def test_backend_assets_list_includes_core_python_mirrors():
    """The `BACKEND_ASSETS` list in electron-app/copy-server-assets.js
    is the build-time mirror source for Python files. It must include
    the core backend files so they get shipped in the Electron bundle.
    """
    src = COPY_SCRIPT.read_text(encoding="utf-8")

    # Extract the BACKEND_ASSETS array literal.
    start = src.find("const BACKEND_ASSETS = [")
    assert start >= 0, (
        "electron-app/copy-server-assets.js no longer contains "
        "`const BACKEND_ASSETS = [`. The Python-mirror source may "
        "have been restructured — rerun this audit."
    )
    end = src.find("]", start)
    block = src[start:end]

    required = [
        "config.py",
        "server.py",
        "shokker_engine_v2.py",
        "shokk_manager.py",
        "finish_colors_lookup.py",
    ]
    missing = [f for f in required if f"'{f}'" not in block]
    assert not missing, (
        f"BACKEND_ASSETS list is missing required Python mirrors: "
        f"{missing}. The Electron bundle may not include these — "
        f"end users would run a bundle without the core backend."
    )


@pytest.mark.parametrize("filename", KEY_PYTHON_FILES)
def test_python_mirrors_parse_clean_in_all_three_locations(filename):
    """For each key Python file, every location where it exists
    must parse as valid Python. Stale mirrors are acceptable (they
    get refreshed on build) but CORRUPT mirrors are not — partial
    writes, truncations, encoding issues would fail py_compile.
    """
    errs = []
    checked = 0
    for target in MIRROR_TARGETS:
        path = target / filename
        if not path.exists():
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8")
            ast.parse(text, filename=str(path))
        except SyntaxError as e:
            errs.append(f"{path}: {e}")
        except UnicodeDecodeError as e:
            errs.append(f"{path}: non-utf8 content: {e}")

    assert checked > 0, (
        f"{filename} not found in any of the 3 expected mirror "
        f"locations. The file may have been renamed or removed — "
        f"update KEY_PYTHON_FILES."
    )
    assert not errs, (
        f"{filename} fails to parse in one or more mirror copies:\n  "
        + "\n  ".join(errs)
    )


@pytest.mark.parametrize("filename", KEY_JS_FILES)
def test_js_mirrors_parse_clean_in_all_three_locations(filename):
    """For each key JS file, every location where it exists must
    parse cleanly via `node --check`. Catches corrupt/truncated
    mirror copies.

    Requires `node` on PATH. Skipped if node is unavailable.
    """
    # Node is required; if missing, skip (matches the behavior of
    # sync-runtime-copies.js which requires node to run at all).
    try:
        subprocess.run(
            ["node", "--version"], capture_output=True, check=True, timeout=10
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("node not available; skipping JS parse check")

    errs = []
    checked = 0
    for target in MIRROR_TARGETS:
        path = target / filename
        if not path.exists():
            continue
        checked += 1
        result = subprocess.run(
            ["node", "--check", str(path)],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            errs.append(
                f"{path}: node --check exit={result.returncode}\n"
                f"  stderr: {result.stderr.decode('utf-8', errors='replace')[:500]}"
            )

    assert checked > 0, (
        f"{filename} not found in any of the 3 expected mirror "
        f"locations. The file may have been renamed or removed — "
        f"update KEY_JS_FILES."
    )
    assert not errs, (
        f"{filename} fails `node --check` in one or more mirror "
        f"copies:\n  " + "\n  ".join(errs)
    )


def test_sync_runtime_copies_script_check_mode_runs_clean():
    """A dedicated run of `node scripts/sync-runtime-copies.js --check`
    must exit 0 (no drift). If it fails, a front-end edit was made
    at root without a corresponding `--write` to refresh the mirrors.

    This is the equivalent of running the per-iteration gate as a
    pytest case so CI catches it.
    """
    try:
        subprocess.run(
            ["node", "--version"], capture_output=True, check=True, timeout=10
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("node not available; skipping sync check")

    result = subprocess.run(
        ["node", str(REPO / "scripts" / "sync-runtime-copies.js"), "--check"],
        capture_output=True,
        timeout=60,
        cwd=str(REPO),
    )
    assert result.returncode == 0, (
        f"sync-runtime-copies.js --check failed (exit "
        f"{result.returncode}). Front-end mirrors have drifted. Run "
        f"`node scripts/sync-runtime-copies.js --write` to fix.\n"
        f"  stdout: {result.stdout.decode('utf-8', errors='replace')[:800]}\n"
        f"  stderr: {result.stderr.decode('utf-8', errors='replace')[:800]}"
    )


def test_orphan_mirror_count_does_not_grow_beyond_known_baseline():
    """Iter 9 of the 2026-04-21 follow-up sweep discovered that
    `node scripts/sync-runtime-copies.js --check --check-orphans`
    reports 2 orphan files — both copies of `paint-booth-app.js` under
    `electron-app/server/` and `electron-app/server/pyserver/_internal/`.

    Root cause: `paint-booth-app.js` was retired and moved to
    `_archive/legacy/paint-booth-app.js`, but the two mirror copies
    were never deleted. They're stale dangling mirrors — the file is
    no longer at canonical root and no longer in the manifest, yet
    the mirrors survive.

    Painter-visible impact: LOW — the Electron runtime loads whatever
    the HTML `<script src>` tags actually reference. If nothing
    references `paint-booth-app.js` anymore, the orphan is dead
    weight, not a footgun. However, if a NEW orphan appears (e.g.
    a fresh JS file is dropped into a mirror dir without a manifest
    entry), that IS a footgun — the file gets shipped without being
    tracked.

    RATCHET form: pins the current known orphan count (2). If the
    count GROWS, something has drifted. If it SHRINKS (the legacy
    `paint-booth-app.js` mirrors get cleaned up), the test skips
    with a note asking for the baseline to be updated.
    """
    try:
        subprocess.run(
            ["node", "--version"], capture_output=True, check=True, timeout=10
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("node not available; skipping orphan scan")

    result = subprocess.run(
        ["node", str(REPO / "scripts" / "sync-runtime-copies.js"),
         "--check", "--check-orphans"],
        capture_output=True,
        timeout=60,
        cwd=str(REPO),
    )
    # Orphan scan exits 2 when orphans are found. A real drift would
    # exit 1 first (drift takes precedence). Exit 0 = no drift, no
    # orphans.
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    combined = stdout + stderr

    # Parse the reported orphan count from the log line:
    #   "[runtime-sync] warn  N orphan file(s) found in target directories"
    import re
    m = re.search(r"(\d+)\s+orphan file\(s\) found", combined)
    if m is None:
        # Zero orphans reported — baseline has SHRUNK
        orphan_count = 0
    else:
        orphan_count = int(m.group(1))

    KNOWN_ORPHAN_BASELINE = 0  # 2026-04-26: mirror orphan floor is clean.

    if orphan_count < KNOWN_ORPHAN_BASELINE:
        pytest.skip(
            f"Orphan count ({orphan_count}) is BELOW the baseline of "
            f"{KNOWN_ORPHAN_BASELINE} — someone cleaned up one or both "
            f"legacy paint-booth-app.js mirrors. Please update "
            f"KNOWN_ORPHAN_BASELINE in this test to {orphan_count} so "
            f"the ratchet reflects the new floor."
        )

    assert orphan_count == KNOWN_ORPHAN_BASELINE, (
        f"Orphan file count has GROWN from baseline of "
        f"{KNOWN_ORPHAN_BASELINE} to {orphan_count}. A new file was "
        f"dropped into a mirror directory without a corresponding "
        f"manifest entry, OR a retired file left behind additional "
        f"mirror copies. Investigate with:\n"
        f"  node scripts/sync-runtime-copies.js --check --check-orphans\n"
        f"If the new orphan is intentional and should be a managed "
        f"mirror, add it to scripts/runtime-sync-manifest.json. "
        f"Otherwise delete the orphan copies.\n"
        f"  stdout: {stdout[:800]}\n"
        f"  stderr: {stderr[:800]}"
    )
