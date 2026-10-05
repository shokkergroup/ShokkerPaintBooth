"""Extra GREEN contract tests for server_routes helpers + the sync manifest.

These are deliberately *finish-neutral*: they only read the runtime-sync
manifest and unit-test the framework-light pure helpers in server_routes/* .
No live Flask server is started, no HTTP request is made, and no engine /
paint / spec math is touched.

This file complements (does NOT duplicate) the existing tests_v2 files:
  * tests_v2/test_server_contract.py already pins:
      - _raw_path_is_traversal / _resolve_within_roots accept+reject behavior,
      - render_monitoring._clamped_limit,
      - the observability env flag + install_flask_error_handler clean-500.
    We do NOT re-assert those; we add the gaps below.

Gaps added here:
  * MANIFEST COMPLETENESS (pure JSON + filesystem; fast):
      - every file listed under 'files' actually EXISTS at the project root
        (catches a manifest still referencing a renamed/deleted file),
      - 'files' has NO duplicate entries (copy/paste dup line),
      - every 'targets' / 'directories' / 'check_only_directories' path that
        is supposed to exist does exist,
      - paths are root-relative + POSIX-slashed (sync script joins them).
  * paint_upload_routes._resolve_within_roots: an EXISTING in-root file
    resolves, and a Windows-backslash literal '..' is rejected pre-abspath
    (the separator-normalization branch), plus the realpath==root exact-match
    branch (serving the root dir entry itself) — angles not covered upstream.
  * diagnostics._registry_counts: returns the documented 4-key shape, tolerates
    a None engine (all zeros), and reads BASE/PATTERN/MONOLITHIC/FUSION
    registries off a stand-in object (no real engine import needed).
  * observability: the _FALSEY tuple is honored case-insensitively + with
    surrounding whitespace, default-ON when unset, and the install_flask_error
    _handler / _flask_handlers reset pattern (id(app) reuse landmine — same
    pattern as test_server_contract.force_observability_on).
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import pathlib
import tempfile

import pytest


# --------------------------------------------------------------------------- #
# Local fixtures (tests_v2/conftest.py exposes engine/registries only; the
# helpers here need neither, so we keep everything self-contained and cheap).
# --------------------------------------------------------------------------- #
_ROOT = pathlib.Path(__file__).resolve().parents[1]

# A logger that never emits, so the guards' warning() calls are harmless.
_NULL_LOG = logging.getLogger("tests_v2.route_and_manifest_contracts")
_NULL_LOG.addHandler(logging.NullHandler())
_NULL_LOG.propagate = False


@pytest.fixture(scope="module")
def project_root():
    return _ROOT


@pytest.fixture(scope="module")
def manifest_path(project_root):
    return project_root / "scripts" / "runtime-sync-manifest.json"


@pytest.fixture(scope="module")
def manifest(manifest_path):
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def paint_upload():
    return importlib.import_module("server_routes.paint_upload_routes")


@pytest.fixture(scope="module")
def diagnostics():
    return importlib.import_module("server_routes.diagnostics")


@pytest.fixture(scope="module")
def observability():
    return importlib.import_module("server_routes.observability")


def _make_app():
    flask = importlib.import_module("flask")
    return flask.Flask(__name__)


def _reset_observability_state(observability):
    """Clear module-level install-tracking state (id(app) reuse landmine).

    Mirrors test_server_contract.force_observability_on: install_flask_error_
    handler() records id(app) in a module-level set and returns False on repeat;
    across a suite run a GC'd app's id can be reused, so a genuinely-new app
    could spuriously return False. Clearing the set isolates each test and
    cannot affect production behavior.
    """
    if hasattr(observability, "_flask_handlers"):
        observability._flask_handlers.clear()
    if hasattr(observability, "_excepthook_installed"):
        observability._excepthook_installed = False


# =========================================================================== #
# 1. Sync-manifest COMPLETENESS  (pure JSON + filesystem; fast)
# =========================================================================== #
class TestManifestCompleteness:
    def test_files_list_present_and_nonempty(self, manifest):
        files = manifest.get("files")
        assert isinstance(files, list) and files

    def test_every_listed_file_exists_at_root(self, manifest, project_root):
        """Every 'files' entry must resolve to a real file at the project root.

        Catches a manifest that still references a renamed/deleted module, which
        would make scripts/sync-runtime-copies.js fail (or silently skip it).
        """
        files = manifest["files"]
        missing = [f for f in files if not (project_root / f).is_file()]
        assert not missing, f"manifest lists non-existent files: {missing}"

    def test_files_entries_are_unique(self, manifest):
        """No duplicate entries in 'files' (a copy/paste dup line)."""
        files = manifest["files"]
        seen = set()
        dupes = sorted({f for f in files if (f in seen) or seen.add(f)})
        assert not dupes, f"manifest has duplicate files entries: {dupes}"

    def test_files_entries_are_relative(self, manifest):
        """No absolute paths in 'files' (must be root-relative)."""
        files = manifest["files"]
        absolute = [f for f in files if os.path.isabs(f) or f.startswith("/")]
        assert not absolute, f"manifest entries must be relative: {absolute}"

    def test_files_entries_use_forward_slashes(self, manifest):
        """'files' paths are POSIX-style (the JS sync script joins them)."""
        files = manifest["files"]
        backslashed = [f for f in files if "\\" in f]
        assert not backslashed, f"manifest entries must use '/': {backslashed}"

    def test_listed_directories_exist_at_root(self, manifest, project_root):
        """Every mirrored 'directories' entry must exist as a real directory."""
        dirs = manifest.get("directories", [])
        assert isinstance(dirs, list)
        missing = [d for d in dirs if not (project_root / d).is_dir()]
        assert not missing, f"manifest lists non-existent directories: {missing}"

    def test_check_only_directories_exist_at_root(self, manifest, project_root):
        dirs = manifest.get("check_only_directories", [])
        assert isinstance(dirs, list)
        missing = [d for d in dirs if not (project_root / d).is_dir()]
        assert not missing, f"check_only_directories missing: {missing}"

    def test_targets_present_and_relative(self, manifest):
        """Sync targets are declared and root-relative (the mirror destinations)."""
        targets = manifest.get("targets")
        assert isinstance(targets, list) and targets
        absolute = [t for t in targets if os.path.isabs(t) or t.startswith("/")]
        assert not absolute, f"targets must be relative: {absolute}"


# =========================================================================== #
# 2. paint_upload_routes._resolve_within_roots — angles NOT covered upstream
# =========================================================================== #
class TestResolveWithinRootsExtra:
    def test_resolves_existing_in_root_file(self, paint_upload):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            inside = os.path.join(root, "asset.png")
            open(inside, "w").close()
            resolved = paint_upload._resolve_within_roots(inside, [root], _NULL_LOG)
            assert resolved is not None
            assert os.path.realpath(resolved) == os.path.realpath(inside)
            # Containment: the resolved path lives at/under the allowed root.
            assert resolved == root or resolved.startswith(root + os.sep)

    def test_root_itself_is_allowed_exact_match(self, paint_upload):
        """The realpath==root branch: requesting the root dir itself resolves.

        test_server_contract covers files *under* root and the sibling-prefix
        rejection; the exact-equality arm of the containment check is pinned
        here so a refactor of `real_full == root or startswith(...)` is caught.
        """
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            assert paint_upload._resolve_within_roots(root, [root], _NULL_LOG) == root

    def test_windows_backslash_dotdot_rejected(self, paint_upload):
        """A literal backslash '..' segment is caught by the separator-normalize
        branch BEFORE abspath collapses it (Windows-authored path)."""
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            assert paint_upload._resolve_within_roots(
                r"sub\..\..\etc\passwd", [root], _NULL_LOG
            ) is None

    def test_raw_traversal_helper_segment_only(self, paint_upload):
        """Spot-check _raw_path_is_traversal: only a whole '..' segment counts,
        not '..' embedded in a filename (defends the .split('/') logic)."""
        f = paint_upload._raw_path_is_traversal
        assert f("x/../y") is True
        assert f(r"x\..\y") is True
        assert f("dot..dot/file.png") is False
        assert f("") is False
        assert f(None) is False


# =========================================================================== #
# 3. diagnostics._registry_counts — shape + None-engine tolerance
# =========================================================================== #
class _StubEngine:
    """A stand-in engine exposing only the four registries _registry_counts reads.

    Avoids importing the real (slow) engine — the helper just does len(getattr()).
    """
    def __init__(self, bases, patterns, monolithics, fusions):
        self.BASE_REGISTRY = bases
        self.PATTERN_REGISTRY = patterns
        self.MONOLITHIC_REGISTRY = monolithics
        self.FUSION_REGISTRY = fusions


class TestRegistryCounts:
    EXPECTED_KEYS = {"bases", "patterns", "monolithics", "fusions"}

    def test_none_engine_is_all_zero(self, diagnostics):
        counts = diagnostics._registry_counts(None)
        assert set(counts.keys()) == self.EXPECTED_KEYS
        assert counts == {"bases": 0, "patterns": 0, "monolithics": 0, "fusions": 0}

    def test_counts_reflect_registry_sizes(self, diagnostics):
        eng = _StubEngine(
            bases={"a": 1, "b": 2},
            patterns={"p": 1},
            monolithics={},
            fusions={"f1": 1, "f2": 2, "f3": 3},
        )
        counts = diagnostics._registry_counts(eng)
        assert set(counts.keys()) == self.EXPECTED_KEYS
        assert counts == {"bases": 2, "patterns": 1, "monolithics": 0, "fusions": 3}

    def test_missing_registry_attr_defaults_to_zero(self, diagnostics):
        """An engine object missing a registry attr -> that count is 0, no crash."""
        class Partial:
            BASE_REGISTRY = {"x": 1}
            # PATTERN_REGISTRY / MONOLITHIC_REGISTRY / FUSION_REGISTRY absent
        counts = diagnostics._registry_counts(Partial())
        assert counts == {"bases": 1, "patterns": 0, "monolithics": 0, "fusions": 0}


# =========================================================================== #
# 4. observability env flag + _flask_handlers reset (id(app) reuse landmine)
# =========================================================================== #
class TestObservabilityFlag:
    def test_default_on_when_unset(self, observability, monkeypatch):
        monkeypatch.delenv("SHOKKER_OBSERVABILITY", raising=False)
        assert observability.observability_enabled() is True

    @pytest.mark.parametrize(
        "value", ["0", "false", "no", "off", "n", "f", "FALSE", "Off", " no ", "  0 "]
    )
    def test_falsey_variants_disable(self, observability, monkeypatch, value):
        monkeypatch.setenv("SHOKKER_OBSERVABILITY", value)
        assert observability.observability_enabled() is False

    @pytest.mark.parametrize(
        "value", ["1", "true", "yes", "on", "", "  ", "enabled", "maybe"]
    )
    def test_truthy_or_unrecognized_variants_enable(self, observability, monkeypatch, value):
        # Default-ON semantics: anything not in _FALSEY counts as enabled.
        monkeypatch.setenv("SHOKKER_OBSERVABILITY", value)
        assert observability.observability_enabled() is True

    def test_falsey_tuple_matches_documented_values(self, observability):
        # Guard against silent drift of the documented opt-out token set.
        assert set(observability._FALSEY) == {"0", "false", "no", "off", "n", "f"}


class TestObservabilityInstallReset:
    def test_install_idempotent_with_reset(self, observability, monkeypatch):
        monkeypatch.setenv("SHOKKER_OBSERVABILITY", "1")
        _reset_observability_state(observability)
        app = _make_app()
        # Fresh app id -> registers this call; repeat is a keyed no-op.
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is True
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is False

    def test_reset_allows_reinstall_demonstrating_landmine(self, observability, monkeypatch):
        """After clearing _flask_handlers the same app installs again (True).

        Without the reset the second install would be a no-op (False) — this is
        exactly the id(app) reuse landmine that test_server_contract.py guards
        against by clearing the module set between tests.
        """
        monkeypatch.setenv("SHOKKER_OBSERVABILITY", "1")
        _reset_observability_state(observability)
        app = _make_app()
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is True
        _reset_observability_state(observability)
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is True

    def test_install_noop_when_disabled(self, observability, monkeypatch):
        monkeypatch.setenv("SHOKKER_OBSERVABILITY", "0")
        _reset_observability_state(observability)
        app = _make_app()
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is False
