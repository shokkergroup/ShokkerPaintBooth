"""WIN #51 + #58 -- route-registration + manifest<->mirror existence contracts.

These are *finish-neutral* structural contract tests. They do NOT touch engine
paint/spec math or finish output; they only assert that the codebase keeps two
invariants intact:

  WIN #51 -- Registration convention:
    Every ``server_routes/*.py`` module (except ``__init__``) that is meant to
    register HTTP routes exposes at least one top-level callable named
    ``register_*`` (the project convention, documented in
    ``server_routes/__init__.py`` -- "Each module exposes
    register_*_routes(app, ...)" -- e.g. ``register_diagnostics_routes``).
    Modules that legitimately register nothing (pure helpers such as
    ``spec_result_support`` / ``paint_recolor_support`` / ``job_cleanup`` /
    ``server_bootstrap`` / ``observability``) are tolerated via
    skip-with-reason rather than failing the build.

  WIN #58 -- Manifest <-> mirror *existence*:
    Every file listed under ``files`` in ``scripts/runtime-sync-manifest.json``
    exists at the repo ROOT *and* at BOTH mirror roots
    (``electron-app/server/<f>`` and
    ``electron-app/server/pyserver/_internal/<f>``).  This catches a manifest
    entry whose mirror directory/file was never created.  It deliberately does
    NOT assert byte-identical content -- ``test_sync_integrity.py`` already owns
    the drift/identity check; this test only complements it with existence.

The tests are intentionally *self-discovering*: they enumerate modules and
manifest entries at runtime so they stay correct as the route set evolves.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import sys

import pytest


# --------------------------------------------------------------------------- #
# Path discovery (robust to where pytest is invoked from)
# --------------------------------------------------------------------------- #

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_THIS_DIR)

SERVER_ROUTES_DIR = os.path.join(ROOT, "server_routes")
MANIFEST_PATH = os.path.join(ROOT, "scripts", "runtime-sync-manifest.json")

# Mirror roots, relative to ROOT, per scripts/runtime-sync-manifest.json "targets".
# 2026-06-09: 3-copy -> 2-copy. The vestigial electron-app/server/pyserver/_internal mirror was
# removed (excluded from the installer, shipped to nobody). Only one mirror root remains.
MIRROR_RELATIVE_ROOTS = (
    os.path.join("electron-app", "server"),
)


# --------------------------------------------------------------------------- #
# WIN #51 -- registration convention
# --------------------------------------------------------------------------- #

def _server_route_module_files():
    """Return sorted list of server_routes/*.py basenames (excluding __init__)."""
    if not os.path.isdir(SERVER_ROUTES_DIR):
        return []
    names = []
    for fn in sorted(os.listdir(SERVER_ROUTES_DIR)):
        if not fn.endswith(".py"):
            continue
        if fn == "__init__.py":
            continue
        names.append(fn)
    return names


_ROUTE_MODULE_FILES = _server_route_module_files()


def _register_callables_via_ast(py_path):
    """Discover top-level ``register_*`` callables without importing the module.

    Importing every route module can drag in heavy optional deps (PIL, flask,
    engine state, ...).  AST inspection of the *source* is sufficient to verify
    the convention -- and it is what makes this test cheap and import-safe.
    A name counts as a register-callable if it is a top-level ``def`` /
    ``async def`` whose name starts with ``register_``.
    """
    with open(py_path, "r", encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src, filename=py_path)
    found = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("register_"):
                found.append(node.name)
    return found


def _import_module_register_callables(module_basename):
    """Import the module and return top-level ``register_*`` *callables*.

    Used as the authoritative (executes-the-real-object) check when import is
    feasible.  Returns ``(callables_or_None, import_error_or_None)``.
    """
    mod_name = "server_routes." + module_basename[:-3]
    try:
        # Ensure ROOT on sys.path so ``import server_routes.xxx`` resolves.
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        module = importlib.import_module(mod_name)
    except Exception as exc:  # pragma: no cover - depends on optional deps
        return None, exc
    callables = []
    for name, obj in vars(module).items():
        if name.startswith("register_") and callable(obj):
            # Only count callables actually defined in this module (not imports
            # re-exported from elsewhere), to keep the convention honest.
            try:
                defined_here = getattr(obj, "__module__", None) == mod_name
            except Exception:
                defined_here = True
            if defined_here:
                callables.append(name)
    return callables, None


@pytest.mark.parametrize("module_basename", _ROUTE_MODULE_FILES)
def test_route_module_exposes_register_callable(module_basename):
    """Each route module exposes >=1 top-level ``register_*`` callable.

    Genuine non-registering helper modules (no ``register_*`` of any kind) are
    skipped-with-reason rather than failed, per the WIN #51 contract.
    """
    py_path = os.path.join(SERVER_ROUTES_DIR, module_basename)
    assert os.path.isfile(py_path), "route module vanished: %s" % py_path

    # Primary, import-safe discovery via AST.
    ast_regs = _register_callables_via_ast(py_path)

    if ast_regs:
        # Strengthen: when import is feasible, confirm the name(s) are truly
        # callable at runtime, not just a `def` shadowed/redefined oddly.
        rt_regs, import_err = _import_module_register_callables(module_basename)
        if import_err is None and rt_regs is not None:
            assert rt_regs, (
                "%s: source declares register_* via AST %r but no callable "
                "register_* survived import" % (module_basename, ast_regs)
            )
        # If import failed (optional dep missing in test env) the AST evidence
        # alone satisfies the structural convention -- do not fail on env deps.
        return

    # No register_* callable found at all -> treat as a legitimate pure helper
    # module and skip with a clear note (tolerated by the contract).
    pytest.skip(
        "no top-level register_* callable in %s -- treated as a pure-helper "
        "module (e.g. spec_result_support / paint_recolor_support / job_cleanup "
        "/ server_bootstrap / observability style)" % module_basename
    )


def test_at_least_one_route_module_registers():
    """Sanity: the convention is actually in use somewhere.

    Guards against the above per-module test silently degenerating into
    all-skips (which would hide a real regression in the discovery logic).
    """
    assert _ROUTE_MODULE_FILES, "no server_routes/*.py modules discovered"
    any_registrar = False
    for fn in _ROUTE_MODULE_FILES:
        if _register_callables_via_ast(os.path.join(SERVER_ROUTES_DIR, fn)):
            any_registrar = True
            break
    assert any_registrar, (
        "no server_routes module exposes a register_* callable -- the "
        "registration convention appears to have been lost entirely"
    )


def test_known_registrar_module_is_discovered():
    """Pin the discovered convention against a known-good registrar.

    ``diagnostics.py`` is documented to expose ``register_diagnostics_routes``;
    if the AST discovery ever stops finding it, the per-module parametrization
    above would silently degrade -- this catches that directly.
    """
    diag = os.path.join(SERVER_ROUTES_DIR, "diagnostics.py")
    if not os.path.isfile(diag):
        pytest.skip("diagnostics.py not present in this checkout")
    regs = _register_callables_via_ast(diag)
    assert "register_diagnostics_routes" in regs, (
        "expected register_diagnostics_routes in diagnostics.py; found %r" % regs
    )


# --------------------------------------------------------------------------- #
# WIN #58 -- manifest <-> mirror *existence* (NOT byte-identity)
# --------------------------------------------------------------------------- #

def _load_manifest_files():
    """Return the list of manifest ``files`` entries (relative POSIX paths)."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data.get("files", []))


_MANIFEST_FILES = _load_manifest_files()


def _mirror_path(mirror_relative_root, root_rel_file):
    return os.path.join(ROOT, mirror_relative_root, *root_rel_file.split("/"))


def test_manifest_has_files():
    """The manifest must list files (otherwise the parametrize is hollow)."""
    assert _MANIFEST_FILES, (
        "runtime-sync-manifest.json declares no 'files' -- nothing to mirror"
    )


@pytest.mark.parametrize("rel_file", _MANIFEST_FILES)
def test_manifest_entry_exists_at_root(rel_file):
    """Every manifest 'files' entry exists at the repo ROOT (source of truth)."""
    root_path = os.path.join(ROOT, *rel_file.split("/"))
    assert os.path.exists(root_path), (
        "manifest lists %r but it is missing at ROOT: %s" % (rel_file, root_path)
    )


@pytest.mark.parametrize("rel_file", _MANIFEST_FILES)
def test_manifest_entry_exists_at_both_mirrors(rel_file):
    """Every manifest 'files' entry exists at BOTH mirror roots.

    Existence only -- byte-identity is owned by test_sync_integrity.py.  This
    catches a manifest entry whose mirror file/dir was never created.
    """
    missing = []
    for mirror in MIRROR_RELATIVE_ROOTS:
        mpath = _mirror_path(mirror, rel_file)
        if not os.path.exists(mpath):
            missing.append(mpath)
    assert not missing, (
        "manifest entry %r is missing at mirror(s):\n  %s"
        % (rel_file, "\n  ".join(missing))
    )
