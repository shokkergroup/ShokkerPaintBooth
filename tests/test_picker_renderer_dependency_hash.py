"""Focused buyer-facing picker cache invalidation regressions."""

from __future__ import annotations

import contextlib
import hashlib
import io
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def test_wilds_registry_is_order_independent_when_recipe_modules_import_first():
    code = r'''
import contextlib
import io
import tests.test_fractured_wilds_20260823
import tests.test_fractured_wilds_bloom_petri_20260823

sink = io.StringIO()
with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
    import server
    server.engine._ensure_expansions_loaded()

required = ("fc_batwing", "fmo_atlas_wing", "fbl_magenta_whorl", "fpe_magenta_bloom")
missing = [finish_id for finish_id in required
           if finish_id not in server.engine.MONOLITHIC_REGISTRY]
raise SystemExit(1 if missing else 0)
'''
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fractured_wilds_hash_tracks_shared_microkit_source(monkeypatch, tmp_path):
    """Bloom/Petri wrappers must invalidate when their shared microkit changes."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import server

        if hasattr(server.engine, "_ensure_expansions_loaded"):
            server.engine._ensure_expansions_loaded()

    from engine.expansions import fractured_bloom_2026 as bloom
    from engine.expansions import fractured_wilds_microkit_2026 as microkit

    finish_ids = ("fbl_magenta_whorl", "fpe_magenta_bloom")
    for finish_id in finish_ids:
        assert server.engine.MONOLITHIC_REGISTRY[finish_id][0].__module__ == microkit.__name__
    _, paint_fn = server.engine.MONOLITHIC_REGISTRY[finish_ids[0]][:2]

    shape = (96, 96)
    mask = np.ones(shape, np.float32)
    source = np.full((96, 96, 3), 0.18, np.float32)
    before_pixels = paint_fn(source, shape, mask, 42, 1.0, None)
    original_art = bloom.KIT.art_work_cached

    dependency_source = tmp_path / "fractured_wilds_microkit_2026.py"
    dependency_source.write_bytes(b"shared-dependency-version-one")
    monkeypatch.setattr(microkit, "__file__", str(dependency_source))

    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    before_hashes = {
        finish_id: server._picker_finish_renderer_hash("monolithic", finish_id)
        for finish_id in finish_ids
    }
    unaffected_before = server._picker_finish_renderer_hash("base", "ceramic")
    assert server._picker_renderer_module_hash(microkit.__name__) == hashlib.md5(
        b"shared-dependency-version-one"
    ).hexdigest()[:12]

    monkeypatch.setattr(
        bloom.KIT,
        "art_work_cached",
        lambda key: np.flip(original_art(key), axis=1).copy(),
    )
    dependency_source.write_bytes(b"shared-dependency-version-two")
    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    after_hashes = {
        finish_id: server._picker_finish_renderer_hash("monolithic", finish_id)
        for finish_id in finish_ids
    }
    unaffected_after = server._picker_finish_renderer_hash("base", "ceramic")
    after_pixels = paint_fn(source, shape, mask, 42, 1.0, None)

    snapshot = tmp_path / "picker-snapshot.png"
    snapshot.write_bytes(b"existing-picker-snapshot")
    monkeypatch.setattr(server, "_picker_split_static_path", lambda *_: str(snapshot))
    monkeypatch.setattr(server, "_catalog_color_for_picker_swatch", lambda *_: "123456")
    monkeypatch.setattr(
        server,
        "_load_picker_split_manifest",
        lambda: {
            "finishes": {
                f"monolithic:{finish_id}": {
                    "color_hex": "123456",
                    "hash": before_hashes[finish_id],
                    "render_scale": server.PICKER_SNAPSHOT_RENDER_SCALE,
                }
                for finish_id in finish_ids
            }
        },
    )

    try:
        assert not np.array_equal(before_pixels, after_pixels)
        assert all(before_hashes[finish_id] != after_hashes[finish_id]
                   for finish_id in finish_ids)
        assert all(server.picker_split_needs_rebuild("monolithic", finish_id)
                   for finish_id in finish_ids)
        assert unaffected_before == unaffected_after
    finally:
        # These process-global caches must not retain the test's temporary
        # module path if this test runs inside a broader in-process suite.
        server._PICKER_RENDERER_HASH_MEMO.clear()
        server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()


def test_cryptid_morpho_hash_tracks_shared_signature_source(monkeypatch, tmp_path):
    """Cryptid/Morpho snapshots must follow their shared signature renderer."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import server

        if hasattr(server.engine, "_ensure_expansions_loaded"):
            server.engine._ensure_expansions_loaded()

    from engine.expansions import fractured_wilds_signatures_2026 as signatures

    finish_ids = ("fc_batwing", "fmo_atlas_wing")
    for finish_id in finish_ids:
        functions = server.engine.MONOLITHIC_REGISTRY[finish_id][:2]
        assert all(fn.__module__ == signatures.__name__ for fn in functions)

    dependency_source = tmp_path / "fractured_wilds_signatures_2026.py"
    dependency_source.write_bytes(b"shared-signature-version-one")
    monkeypatch.setattr(signatures, "__file__", str(dependency_source))

    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    before_hashes = {
        finish_id: server._picker_finish_renderer_hash("monolithic", finish_id)
        for finish_id in finish_ids
    }
    unaffected_before = server._picker_finish_renderer_hash("base", "ceramic")

    dependency_source.write_bytes(b"shared-signature-version-two")
    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    after_hashes = {
        finish_id: server._picker_finish_renderer_hash("monolithic", finish_id)
        for finish_id in finish_ids
    }
    unaffected_after = server._picker_finish_renderer_hash("base", "ceramic")

    snapshot = tmp_path / "picker-snapshot.png"
    snapshot.write_bytes(b"existing-picker-snapshot")
    monkeypatch.setattr(server, "_picker_split_static_path", lambda *_: str(snapshot))
    monkeypatch.setattr(server, "_catalog_color_for_picker_swatch", lambda *_: "123456")
    monkeypatch.setattr(
        server,
        "_load_picker_split_manifest",
        lambda: {
            "finishes": {
                f"monolithic:{finish_id}": {
                    "color_hex": "123456",
                    "hash": before_hashes[finish_id],
                    "render_scale": server.PICKER_SNAPSHOT_RENDER_SCALE,
                }
                for finish_id in finish_ids
            }
        },
    )

    try:
        assert all(before_hashes[finish_id] != after_hashes[finish_id]
                   for finish_id in finish_ids)
        assert all(server.picker_split_needs_rebuild("monolithic", finish_id)
                   for finish_id in finish_ids)
        assert unaffected_before == unaffected_after
    finally:
        server._PICKER_RENDERER_HASH_MEMO.clear()
        server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()


def test_gradient_hash_tracks_shared_overhaul_source_without_broad_invalidation(
    monkeypatch, tmp_path
):
    """All gradient families follow the shared v3 module; other finishes do not."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import server

        if hasattr(server.engine, "_ensure_expansions_loaded"):
            server.engine._ensure_expansions_loaded()

    from engine.expansions import gradient_overhaul_2026 as gradient_overhaul

    # Cover the legacy, showcase/extreme, and material prefixes. Generated
    # wrappers can retain identical function source while helpers and palettes
    # in their shared module change the buyer-visible pixels.
    finish_ids = (
        "grad_fire_fade",
        "grd_hyperprism_supernova",
        "gradient_ember_ice",
    )
    for finish_id in finish_ids:
        functions = server.engine.MONOLITHIC_REGISTRY[finish_id][:2]
        assert all(fn.__module__ == gradient_overhaul.__name__ for fn in functions)

    dependency_source = tmp_path / "gradient_overhaul_2026.py"
    dependency_source.write_bytes(b"gradient-overhaul-version-one")
    monkeypatch.setattr(gradient_overhaul, "__file__", str(dependency_source))

    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    before_hashes = {
        finish_id: server._picker_finish_renderer_hash("monolithic", finish_id)
        for finish_id in finish_ids
    }
    unrelated_before = server._picker_finish_renderer_hash("base", "ceramic")
    assert server._picker_renderer_module_hash(
        gradient_overhaul.__name__
    ) == hashlib.md5(b"gradient-overhaul-version-one").hexdigest()[:12]

    dependency_source.write_bytes(b"gradient-overhaul-version-two")
    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    after_hashes = {
        finish_id: server._picker_finish_renderer_hash("monolithic", finish_id)
        for finish_id in finish_ids
    }
    unrelated_after = server._picker_finish_renderer_hash("base", "ceramic")

    snapshot = tmp_path / "picker-snapshot.png"
    snapshot.write_bytes(b"existing-picker-snapshot")
    monkeypatch.setattr(server, "_picker_split_static_path", lambda *_: str(snapshot))
    monkeypatch.setattr(server, "_catalog_color_for_picker_swatch", lambda *_: "123456")
    monkeypatch.setattr(
        server,
        "_load_picker_split_manifest",
        lambda: {
            "finishes": {
                f"monolithic:{finish_id}": {
                    "color_hex": "123456",
                    "hash": before_hashes[finish_id],
                    "render_scale": server.PICKER_SNAPSHOT_RENDER_SCALE,
                }
                for finish_id in finish_ids
            }
        },
    )

    try:
        assert all(
            before_hashes[finish_id] != after_hashes[finish_id]
            for finish_id in finish_ids
        )
        assert all(
            server.picker_split_needs_rebuild("monolithic", finish_id)
            for finish_id in finish_ids
        )
        assert unrelated_before == unrelated_after
    finally:
        server._PICKER_RENDERER_HASH_MEMO.clear()
        server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()


def test_math_gradient_hash_tracks_declared_transitive_source_only(monkeypatch, tmp_path):
    """Factory wrappers invalidate when an explicitly declared math source changes."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import server

        if hasattr(server.engine, "_ensure_expansions_loaded"):
            server.engine._ensure_expansions_loaded()

    from engine.expansions import gradient_math_wave_2026 as math_wave

    math_finish = "grd_domain_coloring_singularity"
    prior_gradient = "grd_hyperprism_supernova"
    functions = server.engine.MONOLITHIC_REGISTRY[math_finish][:2]
    assert all(
        math_wave.__name__ in fn._spb_picker_dependency_modules
        for fn in functions
    )
    assert all(
        not hasattr(fn, "_spb_picker_dependency_modules")
        for fn in server.engine.MONOLITHIC_REGISTRY[prior_gradient][:2]
    )

    dependency_source = tmp_path / "gradient_math_wave_2026.py"
    dependency_source.write_bytes(b"gradient-math-wave-version-one")
    monkeypatch.setattr(math_wave, "__file__", str(dependency_source))

    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    math_before = server._picker_finish_renderer_hash("monolithic", math_finish)
    prior_before = server._picker_finish_renderer_hash("monolithic", prior_gradient)
    unrelated_before = server._picker_finish_renderer_hash("base", "ceramic")

    dependency_source.write_bytes(b"gradient-math-wave-version-two")
    server._PICKER_RENDERER_HASH_MEMO.clear()
    server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
    math_after = server._picker_finish_renderer_hash("monolithic", math_finish)
    prior_after = server._picker_finish_renderer_hash("monolithic", prior_gradient)
    unrelated_after = server._picker_finish_renderer_hash("base", "ceramic")

    try:
        assert math_before != math_after
        assert prior_before == prior_after
        assert unrelated_before == unrelated_after
    finally:
        server._PICKER_RENDERER_HASH_MEMO.clear()
        server._PICKER_RENDERER_MODULE_HASH_MEMO.clear()
