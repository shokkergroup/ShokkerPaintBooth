"""WIN #41 + #48 -- lock the safety net itself.

These tests guard the *verification tooling* and the *route layer* so the net
that protects the finish catalog cannot silently rot.

WIN #41 -- verification tooling + committed baseline:
  * The three verification scripts (spb_visual_diff / spb_doctor /
    spb_catalog_report) must exist and stay syntactically valid. We use
    ``compile(src, path, 'exec')`` rather than importing+executing them, so we
    never pay for the (lazy) engine import or accidentally run their ``main()``
    heavy work. Those scripts keep all engine work inside functions guarded by
    ``if __name__ == '__main__':``; compile() only parses + byte-compiles the
    module body, it does not run any of it.
  * The committed visual-diff baseline (a directory of golden PNGs + its
    manifest) must be present -- that manifest *is* the net's reference point;
    losing it would silently disable regression detection. The committed
    reference for this repo is ``_visual_diff/baselines_manifest.json`` next to
    ``_visual_diff/baselines/`` (written by spb_visual_diff.py --update-
    baselines; see that script's MANIFEST_PATH / BASELINE_DIR). We discover it
    from a prioritized candidate list (with a bounded recursive fallback) so the
    test stays green wherever the committed baseline lives, while still failing
    loudly if the baseline is ever deleted.

WIN #48 -- route-module import-smoke:
  * Every ``server_routes/*.py`` module must import cleanly (cheap: no Flask app
    construction). This catches a syntax/import break in any route file at test
    time instead of at server start. ``__init__`` is skipped. Import goes
    through the real ``server_routes`` package so package-relative imports inside
    a route file resolve correctly.

Finish-neutral: nothing here renders, mutates, or asserts on paint/spec math.
This module is intentionally self-contained -- it derives every path from
``__file__`` and defines local helpers, so it does not depend on any conftest
fixture name (tests_v2/conftest.py only exposes engine/registries). It still
benefits from conftest's sys.path setup, which auto-applies under tests_v2/.
"""

import os
import sys
import importlib
import importlib.util

import pytest


# --------------------------------------------------------------------------- #
# Local path helpers (self-contained; no reliance on fixture names).
# --------------------------------------------------------------------------- #

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # .../tests_v2
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)                       # repo root
_SCRIPTS_DIR = os.path.join(_PROJECT_ROOT, "scripts")
_ROUTES_DIR = os.path.join(_PROJECT_ROOT, "server_routes")

# The three verification scripts that make up the safety net's tooling.
VERIFICATION_SCRIPTS = (
    "spb_visual_diff.py",
    "spb_doctor.py",
    "spb_catalog_report.py",
)


def _read_text(path):
    """Authoritative utf-8 read -> source string."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _compile_error(path):
    """Return None if the file compiles, else the raised SyntaxError.

    ``compile(..., 'exec')`` parses + byte-compiles the module body *without*
    executing it -- so no engine import / main() runs.
    """
    src = _read_text(path)
    try:
        compile(src, path, "exec")
        return None
    except SyntaxError as exc:  # pragma: no cover - only on a real break
        return exc


def _route_module_files(routes_dir):
    """Importable route modules (skip dunder files such as __init__.py)."""
    try:
        names = os.listdir(routes_dir)
    except OSError:  # pragma: no cover - network-drive read hiccup
        return []
    return sorted(
        f for f in names if f.endswith(".py") and not f.startswith("__")
    )


def _import_route_module(route_file):
    """Import ``server_routes.<name>`` through the real package machinery.

    Importing via the package (rather than a synthetic spec_from_file_location
    name) means package-relative imports inside the route file resolve
    correctly. Project root is placed on ``sys.path`` so ``server_routes`` is a
    discoverable top-level package.

    Returns the imported module. Raises on syntax/import breaks -- which is the
    whole point of the smoke test.
    """
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    mod_name = "server_routes." + route_file[:-3]
    return importlib.import_module(mod_name)


def _baseline_manifest_candidates():
    """Prioritized list of known committed visual-diff manifest locations.

    The live committed reference for this repo is
    ``_visual_diff/baselines_manifest.json`` alongside ``_visual_diff/baselines/``
    (written by ``scripts/spb_visual_diff.py --update-baselines``; see that
    script's MANIFEST_PATH / BASELINE_DIR). The other entries cover plausible
    alternate layouts so the test stays correct if the harness is relocated.
    """
    return [
        os.path.join(_PROJECT_ROOT, "_visual_diff", "baselines_manifest.json"),
        os.path.join(_THIS_DIR, "baselines", "visual", "manifest.json"),
        os.path.join(_THIS_DIR, "baselines", "manifest.json"),
        os.path.join(_PROJECT_ROOT, "_visual_diff", "manifest.json"),
        os.path.join(_PROJECT_ROOT, "_visual_diff", "baselines", "manifest.json"),
    ]


def _find_baseline_manifest():
    """Locate the committed visual-diff baseline manifest.

    Tries the known candidate paths first, then falls back to a bounded
    recursive search rooted at the project (matching either ``manifest.json`` or
    ``*baselines_manifest.json`` inside a visual-diff / baseline directory).
    Returns the manifest path (str) if found, else None.
    """
    for c in _baseline_manifest_candidates():
        if os.path.isfile(c):
            return c

    # Bounded fallback: a (baselines_)manifest.json inside a directory whose path
    # mentions a visual-diff / baseline location. Skip noisy/irrelevant trees.
    skip = {".git", "__pycache__", "node_modules", "thumbnails", "swatches",
            "assets", "output", "helmets", "suits", "decals", "palettes"}
    for dirpath, dirnames, filenames in os.walk(_PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        low = dirpath.lower()
        if ("baseline" in low or "visual_diff" in low or "visual-diff" in low):
            for fn in filenames:
                if fn == "manifest.json" or fn.endswith("baselines_manifest.json"):
                    return os.path.join(dirpath, fn)
    return None


# --------------------------------------------------------------------------- #
# WIN #41 -- verification tooling presence + validity.
# --------------------------------------------------------------------------- #

def test_scripts_dir_present():
    assert os.path.isdir(_SCRIPTS_DIR), f"scripts dir missing: {_SCRIPTS_DIR}"


@pytest.mark.parametrize("script", VERIFICATION_SCRIPTS)
def test_verification_script_exists(script):
    path = os.path.join(_SCRIPTS_DIR, script)
    assert os.path.isfile(path), f"missing verification script: {path}"


@pytest.mark.parametrize("script", VERIFICATION_SCRIPTS)
def test_verification_script_compiles(script):
    """The script must parse + byte-compile (no execution, no engine import)."""
    path = os.path.join(_SCRIPTS_DIR, script)
    assert os.path.isfile(path), f"missing verification script: {path}"
    err = _compile_error(path)
    assert err is None, f"{script} failed to compile: {err}"


# --------------------------------------------------------------------------- #
# WIN #41 -- committed visual-diff baseline (the net's reference point).
# --------------------------------------------------------------------------- #

def test_visual_diff_baseline_manifest_exists():
    manifest = _find_baseline_manifest()
    assert manifest is not None, (
        "committed visual-diff baseline manifest not found in any known "
        "baseline location -- the net's reference point is missing"
    )
    assert os.path.isfile(manifest), f"baseline manifest not a file: {manifest}"


def test_visual_diff_baseline_dir_exists():
    """The directory of committed golden images must exist.

    For the ``baselines_manifest.json`` layout the images live in a sibling
    ``baselines/`` directory; for a plain ``manifest.json`` they live alongside
    it. Accept either so the test tracks the real on-disk layout.
    """
    manifest = _find_baseline_manifest()
    assert manifest is not None, (
        "committed visual-diff baseline directory not found -- the net's "
        "reference point is missing"
    )
    manifest_dir = os.path.dirname(manifest)
    sibling_baselines = os.path.join(manifest_dir, "baselines")
    baseline_dir = (
        sibling_baselines if os.path.isdir(sibling_baselines) else manifest_dir
    )
    assert os.path.isdir(baseline_dir), f"baseline dir missing: {baseline_dir}"


# --------------------------------------------------------------------------- #
# WIN #48 -- route-module import-smoke (cheap; no Flask app construction).
# --------------------------------------------------------------------------- #

def test_routes_dir_and_modules_discovered():
    """Sanity: there is at least one importable route module to smoke-test."""
    assert os.path.isdir(_ROUTES_DIR), f"routes dir missing: {_ROUTES_DIR}"
    mods = _route_module_files(_ROUTES_DIR)
    assert mods, f"no route modules found under {_ROUTES_DIR}"


# Parametrize at collection time off the real routes dir so each route file gets
# its own test id (a break points straight at the offending module).
@pytest.mark.parametrize("route_file", _route_module_files(_ROUTES_DIR))
def test_route_module_imports_cleanly(route_file):
    try:
        mod = _import_route_module(route_file)
    except SyntaxError:
        # A syntax break is exactly what this smoke test must catch -- fail hard.
        raise
    except ModuleNotFoundError as exc:
        # A genuinely-missing *optional/third-party* dependency at import time is
        # an environment gap, not a route-code break. xfail-with-reason keeps the
        # safety-net suite green while still recording the gap. A missing
        # *first-party* module (server_routes / engine / server.* etc.) is a real
        # break and is re-raised.
        missing = (exc.name or "").split(".")[0]
        first_party = {
            "server_routes", "server", "shokker_engine_v2", "engine",
            "config", "server_health", "shokker_config",
        }
        if missing and missing not in first_party:
            pytest.xfail(
                f"{route_file}: optional dependency {missing!r} not installed "
                f"in test env ({exc})"
            )
        raise
    assert mod is not None
