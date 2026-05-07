from __future__ import annotations

import json
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest


def test_finish_visual_audit_smoke_generates_reports():
    from scripts import finish_visual_audit

    out_dir = Path(".pytest-tmp") / "finish_visual_audit_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = finish_visual_audit.main([
        "--ids",
        "cx_hyperflip_red_blue,hex_mandala,micro_sparkle",
        "--size",
        "64",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    report = out_dir / "report.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["count"] == 3
    assert {row["id"] for row in payload["rows"]} == {
        "cx_hyperflip_red_blue",
        "hex_mandala",
        "micro_sparkle",
    }
    assert (out_dir / "contact_sheet.png").exists()
    assert (out_dir / "spec_sheet.png").exists()


def test_spb_visual_workbench_smoke_generates_html_and_full_assets():
    from scripts import spb_visual_workbench

    out_dir = Path(".pytest-tmp") / "spb_visual_workbench_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = spb_visual_workbench.main([
        "--ids",
        "copper,cx_hyperflip_red_blue,circuitboard,micro_sparkle",
        "--size",
        "64",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert report["count"] == 4
    assert (out_dir / "index.html").exists()
    assert (out_dir / "paint_contact_sheet.jpg").exists()
    assert (out_dir / "spec_contact_sheet.jpg").exists()
    html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "PASS" in html
    assert "FAIL" in html
    assert "wrong-description" in html
    assert "render-time-too-long" in html
    assert "owner_review_decisions.json" in html
    assert "spb-workbench-review:" in html
    rows = {row["id"]: row for row in report["rows"]}
    assert rows["copper"]["kind"] == "base"
    assert rows["cx_hyperflip_red_blue"]["kind"] == "monolithic"
    assert rows["circuitboard"]["kind"] == "pattern"
    assert rows["micro_sparkle"]["kind"] == "spec_pattern"
    for row in rows.values():
        assert row["status"] in {"OK", "WARN"}
        assert (out_dir / row["files"]["paint_full"]).exists()
        assert (out_dir / row["files"]["detail_crop"]).exists()


def test_spb_rebuild_triage_smoke_generates_owner_review_package():
    from scripts import spb_rebuild_triage

    out_dir = Path(".pytest-tmp") / "spb_rebuild_triage_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = spb_rebuild_triage.main([
        "--ids",
        "copper,circuitboard,micro_sparkle",
        "--size",
        "64",
        "--out-dir",
        str(out_dir),
        "--min-score",
        "0",
    ])
    assert rc == 0
    report = json.loads((out_dir / "triage_report.json").read_text(encoding="utf-8"))
    assert report["catalog_count"] >= 3
    assert report["candidate_count"] >= 3
    assert (out_dir / "review_candidates.html").exists()
    assert (out_dir / "rebuild_candidates_review.md").exists()
    first = report["candidates"][0]
    assert "desc" in first
    assert "reasons" in first
    assert "metrics" in first


def test_runtime_sync_has_no_leftover_temp_artifacts():
    tmp_files = list(Path("electron-app/server").rglob("*.tmp-*"))
    assert tmp_files == []


def test_root_temp_junk_cleanup_is_narrow_and_effective():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "cleanup-root-temp-junk.py"
    victim = root / "ZzTst_01"
    wrong_content = root / "ZzTst_02"
    wrong_suffix = root / "ZzTst03.txt"
    for path in (victim, wrong_content, wrong_suffix):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        victim.write_text("blat", encoding="utf-8")
        wrong_content.write_text("keep", encoding="utf-8")
        wrong_suffix.write_text("blat", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(script), "--delete"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        assert "ZzTst_01" in result.stdout
        assert not victim.exists()
        assert wrong_content.exists()
        assert wrong_suffix.exists()
    finally:
        for path in (victim, wrong_content, wrong_suffix):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def test_pytest_capture_is_disabled_to_avoid_root_blat_artifacts():
    root = Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    pytest_block = text.split("[tool.pytest.ini_options]", 1)[1].split("[tool.", 1)[0]

    assert '"--capture=no"' in pytest_block
    assert '"no:cacheprovider"' in pytest_block


def test_spec_pattern_quality_gate_clears_shipping_catalog():
    from scripts import audit_spec_pattern_quality

    out_dir = Path(".pytest-tmp") / "spec_pattern_quality_gate"
    rc = audit_spec_pattern_quality.main([
        "--size",
        "160",
        "--threshold",
        "96",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert payload["count"] >= 250
    assert payload["threshold"] == 96.0
    assert payload["rebuild_required_count"] == 0


def test_regular_pattern_quality_gate_clears_shipping_catalog():
    from scripts import audit_pattern_quality

    out_dir = Path(".pytest-tmp") / "regular_pattern_quality_gate"
    rc = audit_pattern_quality.main([
        "--size",
        "160",
        "--threshold",
        "88",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert payload["count"] >= 300
    assert payload["threshold"] == 88.0
    assert payload["rebuild_required_count"] == 0


def test_regular_pattern_picker_categories_are_curated():
    root = Path(__file__).resolve().parents[1]
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
console.log(JSON.stringify(vm.runInContext('PATTERN_GROUPS', ctx)));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    groups = json.loads(result.stdout)
    group_names = set(groups)

    removed = {
        "PARADIGM - Digital Reality",
        "PARADIGM - Physics Exploits",
        "Nature-Inspired",
        "Tribal & Cultural",
        "Advanced Geometric",
    }
    assert removed.isdisjoint(group_names)
    assert not any("Final Collection" in name for name in group_names)
    assert groups["PARADIGM"] == [
        "circuitboard",
        "holographic",
        "p_tessellation",
        "p_topographic",
        "soundwave",
        "caustic",
        "dimensional",
        "fresnel_ghost",
        "neural",
        "p_plasma",
    ]
    assert "tribal_celtic_spiral" in groups["Artistic & Cultural"]
    natural_group = next(ids for name, ids in groups.items() if "Natural Textures" in name)
    math_group = next(ids for name, ids in groups.items() if "Mathematical & Fractal" in name)
    assert "nature_water_ripple_pat" in natural_group
    assert "hypocycloid" in math_group
    assert "geo_hilbert_curve" in math_group


def test_pattern_compatibility_aliases_are_machine_readable_not_silent_copies():
    import shokker_engine_v2 as eng

    alias_maps = {
        **eng._PATTERN_FALLBACKS,
        **eng._UI_PATTERN_ALIASES,
    }
    missing = []
    bad = {}
    for alias_id, target_id in alias_maps.items():
        alias_entry = eng.PATTERN_REGISTRY.get(alias_id)
        target_entry = eng.PATTERN_REGISTRY.get(target_id)
        if not isinstance(alias_entry, dict) or not isinstance(target_entry, dict):
            missing.append((alias_id, target_id))
            continue
        problems = []
        if alias_entry is target_entry:
            problems.append("same object as target")
        if alias_entry.get("_spb_alias_of") != target_id:
            problems.append("missing _spb_alias_of")
        if alias_entry.get("_spb_alias_kind") not in {"compatibility_fallback", "ui_id_alias"}:
            problems.append("missing _spb_alias_kind")
        if not alias_entry.get("_spb_alias_reason"):
            problems.append("missing _spb_alias_reason")
        if problems:
            bad[alias_id] = problems

    assert missing == []
    assert bad == {}


def test_pattern_expansion_refuses_generic_noop_fallback_on_builder_failure(monkeypatch):
    import engine.pattern_expansion as pattern_expansion

    fake_module = types.ModuleType("engine.expansion_patterns")

    def _boom(_ids):
        raise RuntimeError("synthetic expansion builder failure")

    fake_module.build_expansion_entries = _boom
    monkeypatch.setitem(sys.modules, "engine.expansion_patterns", fake_module)

    with pytest.raises(RuntimeError, match="refusing to degrade"):
        pattern_expansion._build_new_patterns()


@pytest.mark.parametrize(
    ("base_entry", "match"),
    [
        (
            {"M": 10, "R": 20, "CC": 16, "paint_fn": "missing_paint"},
            "refusing to register a no-op fallback",
        ),
        (
            {"M": 10, "R": 20, "CC": 16, "paint_fn": lambda paint, *args: paint, "_resolve_paint_fn": "paint_missing"},
            "refusing to register a no-op fallback",
        ),
    ],
)
def test_24k_expansion_refuses_unresolved_paint_fn_noop_fallback(monkeypatch, base_entry, match):
    import engine.expansions.arsenal_24k as arsenal_24k

    fake_engine = types.SimpleNamespace(BASE_REGISTRY={}, PATTERN_REGISTRY={}, MONOLITHIC_REGISTRY={})
    monkeypatch.setattr(arsenal_24k, "EXPANSION_BASES", {"broken_24k_base": dict(base_entry)})
    monkeypatch.setattr(arsenal_24k, "EXPANSION_PATTERNS", {})
    monkeypatch.setattr(arsenal_24k, "EXPANSION_MONOLITHICS", {})

    with pytest.raises(RuntimeError, match=match):
        arsenal_24k.integrate_expansion(fake_engine)


def test_v5_registry_refuses_missing_pattern_expansion_registry(monkeypatch):
    import engine.registry as registry

    fake_module = types.ModuleType("engine.pattern_expansion")

    def _missing(_name):
        raise RuntimeError("synthetic expansion registry import failure")

    fake_module.__getattr__ = _missing
    monkeypatch.setitem(sys.modules, "engine.pattern_expansion", fake_module)

    with pytest.raises(RuntimeError, match="refusing to continue"):
        registry._build_registries()


def test_lazy_engine_load_refuses_missing_pattern_expansion_registry(monkeypatch):
    import shokker_engine_v2 as eng

    fake_module = types.ModuleType("engine.pattern_expansion")
    original_loaded = eng._expansions_loaded
    monkeypatch.setitem(sys.modules, "engine.pattern_expansion", fake_module)
    monkeypatch.setattr(eng, "_expansions_loaded", False)

    with pytest.raises(RuntimeError, match="refusing to render with missing expansion patterns"):
        eng._ensure_expansions_loaded()

    assert eng._expansions_loaded is False
    monkeypatch.setattr(eng, "_expansions_loaded", original_loaded)


def test_catalog_fallback_candidates_are_not_silent_monolithic_renderers():
    import shokker_engine_v2 as eng

    eng._ensure_expansions_loaded()
    wired = getattr(eng, "CATALOG_FALLBACK_WIRED_TO", {})
    candidates = getattr(eng, "CATALOG_FALLBACK_CANDIDATES_TO", {})
    unwired = getattr(eng, "CATALOG_UNWIRED_MONOLITHIC_IDS", set())
    resolved_candidates = [
        finish_id
        for finish_id in sorted(candidates)
        if finish_id in eng.MONOLITHIC_REGISTRY
        or finish_id in eng.BASE_REGISTRY
        or finish_id in eng.FINISH_REGISTRY
        or finish_id in eng.PATTERN_REGISTRY
    ]
    unresolved = [
        finish_id
        for finish_id in sorted(candidates)
        if finish_id not in eng.MONOLITHIC_REGISTRY
        and finish_id not in eng.BASE_REGISTRY
        and finish_id not in eng.FINISH_REGISTRY
    ]

    assert wired == {}
    assert candidates
    assert all(candidate is None for candidate in candidates.values())
    assert resolved_candidates == []
    assert set(candidates) <= unwired
    assert unresolved, "Expected at least one legacy/catalog-only monolithic fallback candidate"

    zone = {"name": "Catalog Fallback Trust Zone", "color": "everything", "finish": unresolved[0]}
    with pytest.raises(ValueError, match="Unknown finish"):
        eng._validate_zone_render_ids(zone, 0)


def test_catalog_fallback_diagnostics_do_not_keep_substitute_resolver():
    root = Path(__file__).resolve().parents[1]
    src = (root / "shokker_engine_v2.py").read_text(encoding="utf-8")

    assert "def _resolve_fallback(" not in src
    assert "CATALOG_FALLBACK_WIRED_IDS" not in src
    assert "CATALOG_FALLBACK_WIRED_TO" not in src
    assert "_PREFIX_ROUTES" not in src
    assert "_EV_EXPLICIT" not in src
    assert "_pick_from_pool" not in src


@pytest.mark.parametrize(
    ("zone_update", "match"),
    [
        ({"base": "missing_base_for_trust_test", "finish": None}, "Unknown base"),
        ({"base": "gloss", "finish": None, "pattern": "missing_pattern_for_trust_test"}, "Unknown pattern"),
        ({"finish": "missing_finish_for_trust_test"}, "Unknown finish"),
    ],
)
def test_engine_rejects_unknown_renderer_ids_before_fallback(zone_update, match):
    import shokker_engine_v2 as eng

    eng._ensure_expansions_loaded()
    zone = {"name": "Trust Zone", "color": "everything", "finish": "gloss", "intensity": "100"}
    zone.update(zone_update)
    with pytest.raises(ValueError, match=match):
        eng._validate_zone_render_ids(zone, 0)


def test_preview_render_rejects_unknown_ids_before_gray_fallback(tmp_path):
    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    tmp_path.mkdir(parents=True, exist_ok=True)
    paint_path = tmp_path / "preview_trust.png"
    paint = np.zeros((32, 32, 4), dtype=np.uint8)
    paint[:, :, 0] = 230
    paint[:, :, 3] = 255
    Image.fromarray(paint).save(paint_path)

    zones = [
        {
            "name": "Preview Trust Zone",
            "color": "everything",
            "base": "gloss",
            "pattern": "missing_pattern_for_preview_trust_test",
            "finish": None,
            "intensity": "100",
        }
    ]
    with pytest.raises(ValueError, match="Unknown pattern"):
        eng.preview_render(str(paint_path), zones, seed=42, preview_scale=1.0)


def test_preview_render_surfaces_renderer_errors_instead_of_gray_fallback(tmp_path, monkeypatch):
    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    paint_path = tmp_path / "preview_renderer_error.png"
    paint = np.zeros((32, 32, 4), dtype=np.uint8)
    paint[:, :, 0] = 230
    paint[:, :, 3] = 255
    Image.fromarray(paint).save(paint_path)

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic preview renderer failure")

    monkeypatch.setattr(eng, "build_multi_zone", _boom)

    zones = [{"name": "Preview Error Zone", "color": "everything", "base": "gloss"}]
    with pytest.raises(RuntimeError, match="synthetic preview renderer failure"):
        eng.preview_render(str(paint_path), zones, seed=42, preview_scale=1.0)


def test_swatch_api_rejects_unknown_renderer_id_instead_of_placeholder_png(app_client):
    response = app_client.get("/api/swatch/base/missing_base_swatch_trust_test?nocache=1")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "Unknown swatch base" in payload["message"]


def test_swatch_api_rejects_unknown_dynamic_monolithic_prefix_instead_of_generic_gradient(app_client):
    response = app_client.get(
        "/api/swatch/monolithic/grad_missing_dynamic_swatch_trust_test?nocache=1"
    )

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "Unknown swatch monolithic" in payload["message"]


def test_swatch_api_allows_cataloged_dynamic_monolithic_colors(app_client):
    response = app_client.get("/api/swatch/monolithic/grad_fire_fade?nocache=1&size=32")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert len(response.data) > 100


def test_swatch_api_rejects_unknown_static_thumbnail_instead_of_serving_stale_png(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    from PIL import Image

    thumb_root = tmp_path / "thumbs"
    stale_dir = thumb_root / "base"
    stale_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), (30, 30, 30)).save(stale_dir / "missing_static_swatch_trust_test.png")

    monkeypatch.setattr(server_module, "THUMBNAIL_DIR", str(thumb_root))
    with server_module._SWATCH_CACHE_LOCK:
        server_module._SWATCH_CACHE.clear()

    response = app_client.get(
        "/api/swatch/base/missing_static_swatch_trust_test?prefer=static&nocache=1"
    )

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "Unknown swatch base" in payload["message"]


def test_swatch_api_surfaces_renderer_error_instead_of_placeholder_png(app_client, server_module, monkeypatch):
    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic swatch renderer failure")

    monkeypatch.setitem(
        server_module.engine.BASE_REGISTRY,
        "broken_base_swatch_trust_test",
        {"M": 80, "R": 90, "CC": 16, "paint_fn": _boom_paint},
    )

    response = app_client.get("/api/swatch/base/broken_base_swatch_trust_test?nocache=1")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "synthetic swatch renderer failure" in payload["message"]


def test_pattern_swatch_rejects_empty_texture_result_instead_of_generic_swatch(
    app_client,
    server_module,
    monkeypatch,
):
    def _empty_texture(*args, **kwargs):
        return {}

    monkeypatch.setitem(
        server_module.engine.PATTERN_REGISTRY,
        "broken_empty_pattern_swatch_trust_test",
        {"texture_fn": _empty_texture},
    )

    response = app_client.get(
        "/api/swatch/pattern/broken_empty_pattern_swatch_trust_test?nocache=1"
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "returned no pattern data" in payload["message"]


def test_review_swatch_surfaces_image_decode_error_instead_of_placeholder_png(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    review_dir = tmp_path / "for_review_swatch_trust"
    review_dir.mkdir(parents=True, exist_ok=True)
    broken_image = review_dir / "broken_review_pattern.png"
    broken_image.write_text("not a png", encoding="utf-8")
    monkeypatch.setattr(server_module.CFG, "PATTERN_FOR_REVIEW_DIR", str(review_dir))

    response = app_client.get("/api/swatch/review?image=broken_review_pattern.png")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "review_swatch_render_failed"
    assert payload["image"] == "broken_review_pattern.png"
    assert "Review swatch image renderer failed" in payload["message"]


def test_legacy_swatch_rejects_unknown_base_before_stale_cache_png(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    from PIL import Image

    swatch_dir = tmp_path / "legacy_swatches"
    swatch_dir.mkdir(exist_ok=True)
    Image.new("RGB", (64, 64), (40, 40, 40)).save(
        swatch_dir / "missing_legacy_base_trust_test_none.png"
    )
    monkeypatch.setattr(server_module, "SWATCH_FOLDER", str(swatch_dir))

    response = app_client.get("/swatch/missing_legacy_base_trust_test/none")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert "Unknown base" in payload["error"]


def test_legacy_pattern_swatch_rejects_no_texture_renderer_instead_of_placeholder(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(server_module, "SWATCH_FOLDER", str(tmp_path / "legacy_swatches"))
    monkeypatch.setitem(
        server_module.engine.PATTERN_REGISTRY,
        "missing_texture_legacy_pattern_trust_test",
        {"name": "Missing Texture Legacy Pattern"},
    )

    response = app_client.get("/swatch/pattern/missing_texture_legacy_pattern_trust_test")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert "Pattern has no texture renderer" in payload["error"]


def test_legacy_mono_swatch_rejects_unknown_finish_before_stale_cache_png(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    from PIL import Image

    swatch_dir = tmp_path / "legacy_mono_swatches"
    swatch_dir.mkdir(exist_ok=True)
    cache_name = f"{server_module._swatch_cache_token()}_mono_missing_legacy_mono_trust_test.png"
    Image.new("RGB", (64, 64), (50, 50, 50)).save(swatch_dir / cache_name)
    monkeypatch.setattr(server_module, "SWATCH_FOLDER", str(swatch_dir))

    response = app_client.get("/swatch/mono/missing_legacy_mono_trust_test")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert "Unknown monolithic" in payload["error"]


def test_legacy_mono_swatch_rejects_empty_spec_instead_of_neutral_fallback(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    def _empty_spec(*args, **kwargs):
        return None

    def _paint_identity(paint, *args, **kwargs):
        return paint

    monkeypatch.setattr(server_module, "SWATCH_FOLDER", str(tmp_path / "legacy_mono_swatches"))
    monkeypatch.setitem(
        server_module.engine.MONOLITHIC_REGISTRY,
        "empty_spec_legacy_mono_trust_test",
        (_empty_spec, _paint_identity),
    )

    response = app_client.get("/swatch/mono/empty_spec_legacy_mono_trust_test")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert "returned no spec data" in payload["error"]
    assert "empty_spec_legacy_mono_trust_test" in payload["error"]


def test_swatch_api_rejects_malformed_monolithic_spec_shape_instead_of_resizing(
    app_client,
    server_module,
    monkeypatch,
):
    import numpy as np

    def _bad_spec(shape, mask, seed, strength):
        h, w = shape
        return (
            np.ones((h - 1, w), dtype=np.float32) * 180,
            np.ones((h, w), dtype=np.float32) * 40,
            np.ones((h, w), dtype=np.float32) * 16,
        )

    def _paint_identity(paint, *args, **kwargs):
        return paint

    monkeypatch.setitem(
        server_module.engine.MONOLITHIC_REGISTRY,
        "bad_spec_shape_mono_swatch_trust_test",
        (_bad_spec, _paint_identity),
    )

    response = app_client.get(
        "/api/swatch/monolithic/bad_spec_shape_mono_swatch_trust_test?nocache=1"
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "Invalid M channel shape" in payload["message"]
    assert "bad_spec_shape_mono_swatch_trust_test" in payload["message"]


def test_swatch_api_rejects_missing_monolithic_spec_channel_instead_of_defaulting(
    app_client,
    server_module,
    monkeypatch,
):
    import numpy as np

    def _missing_cc_spec(shape, mask, seed, strength):
        h, w = shape
        return (
            np.ones((h, w), dtype=np.float32) * 180,
            np.ones((h, w), dtype=np.float32) * 40,
        )

    def _paint_identity(paint, *args, **kwargs):
        return paint

    monkeypatch.setitem(
        server_module.engine.MONOLITHIC_REGISTRY,
        "missing_spec_channel_mono_swatch_trust_test",
        (_missing_cc_spec, _paint_identity),
    )

    response = app_client.get(
        "/api/swatch/monolithic/missing_spec_channel_mono_swatch_trust_test?nocache=1"
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "Missing strict spec channel(s): CC" in payload["message"]
    assert "missing_spec_channel_mono_swatch_trust_test" in payload["message"]


def test_split_swatch_right_side_requires_real_spec_preview(
    app_client,
    server_module,
    monkeypatch,
):
    import numpy as np

    def _missing_cc_spec(shape, mask, seed, strength):
        h, w = shape
        return (
            np.ones((h, w), dtype=np.float32) * 180,
            np.ones((h, w), dtype=np.float32) * 40,
        )

    def _paint_identity(paint, *args, **kwargs):
        return paint

    monkeypatch.setitem(
        server_module.engine.MONOLITHIC_REGISTRY,
        "missing_spec_channel_split_contract_test",
        (_missing_cc_spec, _paint_identity),
    )

    response = app_client.get(
        "/api/swatch/monolithic/missing_spec_channel_split_contract_test?mode=split&nocache=1"
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "swatch_render_failed"
    assert "Missing strict spec channel(s): CC" in payload["message"]
    assert "missing_spec_channel_split_contract_test" in payload["message"]


def test_spec_pattern_preview_rejects_unknown_static_thumbnail_instead_of_serving_stale_png(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    from PIL import Image

    thumb_root = tmp_path / "thumbs_spec_preview"
    stale_dir = thumb_root / "spec_patterns"
    stale_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (194, 64), (40, 40, 40)).save(
        stale_dir / "missing_spec_preview_trust_test.png"
    )

    monkeypatch.setattr(server_module, "THUMBNAIL_DIR", str(thumb_root))

    response = app_client.get("/api/spec-pattern-preview/missing_spec_preview_trust_test")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "spec_pattern_preview_failed"
    assert "Unknown spec pattern" in payload["message"]


def test_spec_pattern_preview_surfaces_renderer_error_instead_of_gray_placeholder(
    app_client,
    server_module,
    monkeypatch,
):
    import engine.spec_patterns as spec_patterns

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic spec preview renderer failure")

    monkeypatch.setitem(
        spec_patterns.PATTERN_CATALOG,
        "broken_spec_preview_trust_test",
        _boom,
    )

    response = app_client.get("/api/spec-pattern-preview/broken_spec_preview_trust_test?v=1")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "spec_pattern_preview_failed"
    assert "synthetic spec preview renderer failure" in payload["message"]


def test_spec_pattern_metal_preview_surfaces_renderer_error_instead_of_gray_placeholder(
    app_client,
    monkeypatch,
):
    import engine.spec_patterns as spec_patterns

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic spec metal renderer failure")

    monkeypatch.setitem(
        spec_patterns.PATTERN_CATALOG,
        "broken_spec_metal_preview_trust_test",
        _boom,
    )

    response = app_client.get(
        "/api/spec-pattern-preview-metal/broken_spec_metal_preview_trust_test?v=1"
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "spec_pattern_preview_failed"
    assert "synthetic spec metal renderer failure" in payload["message"]


def test_thumbnail_regen_rejects_unknown_base_instead_of_queueing_background_failure(app_client):
    response = app_client.post("/api/thumb-regen/base/missing_thumb_regen_base_trust_test")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "thumbnail_regen_failed"
    assert payload["finish_type"] == "base"
    assert payload["id"] == "missing_thumb_regen_base_trust_test"
    assert "Unknown thumbnail base" in payload["message"]


def test_thumbnail_regen_surfaces_renderer_error_instead_of_queueing_background_failure(
    app_client,
    server_module,
    monkeypatch,
):
    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic thumbnail regen renderer failure")

    monkeypatch.setitem(
        server_module.engine.BASE_REGISTRY,
        "broken_thumb_regen_base_trust_test",
        {"M": 80, "R": 90, "CC": 16, "paint_fn": _boom_paint},
    )

    response = app_client.post("/api/thumb-regen/base/broken_thumb_regen_base_trust_test")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "thumbnail_regen_failed"
    assert "synthetic thumbnail regen renderer failure" in payload["message"]


def test_spec_preview_composite_rejects_unknown_stack_pattern(app_client):
    response = app_client.post(
        "/api/spec-preview-composite",
        json={
            "base_finish": "chrome",
            "zone_spec_stack": [
                {"pattern": "definitely_missing_spec_pattern", "opacity": 70},
            ],
        },
    )

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "spec_preview_composite_failed"
    assert payload["pattern"] == "definitely_missing_spec_pattern"
    assert "Unknown spec pattern" in payload["message"]


def test_spec_preview_composite_surfaces_stack_renderer_error(
    app_client,
    monkeypatch,
):
    import engine.spec_patterns as spec_patterns

    def _boom_spec(*args, **kwargs):
        raise RuntimeError("broken composite spec stack layer")

    monkeypatch.setitem(
        spec_patterns.PATTERN_CATALOG,
        "spb_broken_composite_spec_layer",
        _boom_spec,
    )

    response = app_client.post(
        "/api/spec-preview-composite",
        json={
            "base_finish": "chrome",
            "zone_spec_stack": [
                {"pattern": "spb_broken_composite_spec_layer", "opacity": 70},
            ],
        },
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "spec_preview_composite_failed"
    assert payload["pattern"] == "spb_broken_composite_spec_layer"
    assert "Spec preview composite renderer failed" in payload["message"]
    assert "broken composite spec stack layer" in payload["message"]


def test_mix_finish_spec_rejects_unknown_finish_instead_of_neutral_fallback():
    import numpy as np
    from engine.compose import mix_finishes

    shape = (8, 8)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises(ValueError, match="Unknown mix finish spec ID"):
        mix_finishes(
            shape,
            mask,
            7,
            1.0,
            ["copper", "missing_mix_finish_trust_test"],
            [0.5, 0.5],
            monolithic_registry={},
        )


def test_mix_finish_spec_rejects_invalid_monolithic_spec_instead_of_neutral_fallback():
    import numpy as np
    from engine.compose import mix_finishes
    from engine.core import paint_none

    shape = (8, 8)
    mask = np.ones(shape, dtype=np.float32)

    def _invalid_spec(*args, **kwargs):
        return np.zeros(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="returned invalid spec shape"):
        mix_finishes(
            shape,
            mask,
            7,
            1.0,
            ["invalid_mix_spec_trust_test", "invalid_mix_spec_trust_test"],
            [0.5, 0.5],
            monolithic_registry={
                "invalid_mix_spec_trust_test": (_invalid_spec, paint_none),
            },
        )


def test_compose_pattern_texture_error_is_not_silently_base_only(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_finish
    from engine.core import paint_none

    def _boom_texture(*args, **kwargs):
        raise RuntimeError("synthetic pattern texture failure")

    monkeypatch.setitem(
        registry.PATTERN_REGISTRY,
        "spb_broken_pattern_texture_trust_test",
        {"texture_fn": _boom_texture, "paint_fn": paint_none, "desc": "broken trust test"},
    )

    shape = (12, 12)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Pattern texture renderer failed .*synthetic pattern texture failure"):
        compose_finish(
            "gloss",
            "spb_broken_pattern_texture_trust_test",
            shape,
            mask,
            7,
            1.0,
            dither=False,
        )


def test_compose_stacked_pattern_texture_error_is_not_skipped(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_finish_stacked
    from engine.core import paint_none

    def _boom_texture(*args, **kwargs):
        raise RuntimeError("synthetic stacked texture failure")

    monkeypatch.setitem(
        registry.PATTERN_REGISTRY,
        "spb_broken_stacked_texture_trust_test",
        {"texture_fn": _boom_texture, "paint_fn": paint_none, "desc": "broken stacked trust test"},
    )

    shape = (12, 12)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Stacked pattern texture renderer failed .*synthetic stacked texture failure"):
        compose_finish_stacked(
            "gloss",
            [{"id": "spb_broken_stacked_texture_trust_test", "opacity": 1.0}],
            shape,
            mask,
            7,
            1.0,
            dither=False,
        )


def test_pattern_fit_zone_resizes_full_texture_into_small_mask(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_finish
    from engine.core import paint_none

    def _full_canvas_gradient(shape, mask, seed, sm):
        h, w = shape
        pv = np.tile(np.linspace(0.0, 1.0, w, dtype=np.float32), (h, 1))
        return {
            "pattern_val": pv,
            "R_pattern": pv,
            "M_pattern": np.zeros_like(pv),
            "R_range": 90.0,
            "M_range": 0.0,
        }

    monkeypatch.setitem(
        registry.PATTERN_REGISTRY,
        "spb_fit_zone_gradient_trust_test",
        {"texture_fn": _full_canvas_gradient, "paint_fn": paint_none, "desc": "fit-zone trust test"},
    )

    shape = (16, 16)
    mask = np.zeros(shape, dtype=np.float32)
    mask[6:10, 10:14] = 1.0

    spec = compose_finish(
        "gloss",
        "spb_fit_zone_gradient_trust_test",
        shape,
        mask,
        7,
        1.0,
        pattern_fit_zone=True,
        dither=False,
    )

    fitted = np.asarray(spec)[6:10, 10:14, 1].astype(np.int16)
    assert int(fitted[:, -1].mean()) - int(fitted[:, 0].mean()) >= 35
    assert int(fitted.max()) - int(fitted.min()) >= 45


@pytest.mark.parametrize(
    ("stack_kw", "match"),
    [
        (
            "spec_pattern_stack",
            "Unknown spec pattern 'missing_compose_spec_pattern_trust_test' in spec_pattern_stack",
        ),
        (
            "overlay_spec_pattern_stack",
            "Overlay spec pattern stack failed.*Unknown spec pattern 'missing_compose_spec_pattern_trust_test'",
        ),
        (
            "third_overlay_spec_pattern_stack",
            "Named overlay spec pattern stack failed \\[third_overlay_spec_pattern_stack\\].*Unknown spec pattern 'missing_compose_spec_pattern_trust_test'",
        ),
    ],
)
def test_compose_unknown_spec_pattern_layers_fail_loudly(stack_kw, match):
    import numpy as np
    from engine.compose import compose_finish

    shape = (12, 12)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises((ValueError, RuntimeError), match=match):
        compose_finish(
            "gloss",
            "none",
            shape,
            mask,
            7,
            1.0,
            **{stack_kw: [{"pattern": "missing_compose_spec_pattern_trust_test", "opacity": 1.0}]},
            dither=False,
        )


def test_compose_stacked_unknown_spec_pattern_layers_fail_loudly():
    import numpy as np
    from engine.compose import compose_finish_stacked

    shape = (12, 12)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises(ValueError, match="Unknown spec pattern 'missing_stacked_spec_pattern_trust_test'"):
        compose_finish_stacked(
            "gloss",
            [],
            shape,
            mask,
            7,
            1.0,
            spec_pattern_stack=[
                {"pattern": "missing_stacked_spec_pattern_trust_test", "opacity": 1.0},
            ],
            dither=False,
        )


def test_compose_overlay_spec_pattern_error_is_not_silently_neutral(monkeypatch):
    import numpy as np
    from engine import spec_patterns
    from engine.compose import compose_finish

    def _boom_spec_pattern(*args, **kwargs):
        raise RuntimeError("synthetic overlay spec pattern failure")

    monkeypatch.setitem(
        spec_patterns.PATTERN_CATALOG,
        "spb_broken_overlay_spec_pattern_trust_test",
        _boom_spec_pattern,
    )

    shape = (12, 12)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Overlay spec pattern stack failed.*synthetic overlay spec pattern failure"):
        compose_finish(
            "gloss",
            "none",
            shape,
            mask,
            7,
            1.0,
            overlay_spec_pattern_stack=[
                {
                    "pattern": "spb_broken_overlay_spec_pattern_trust_test",
                    "opacity": 1.0,
                    "scale": 0.5,
                }
            ],
            dither=False,
        )


def test_compose_stacked_overlay_spec_pattern_error_is_not_swallowed(monkeypatch):
    import numpy as np
    from engine import spec_patterns
    from engine.compose import compose_finish_stacked

    def _boom_spec_pattern(*args, **kwargs):
        raise RuntimeError("synthetic stacked overlay spec failure")

    monkeypatch.setitem(
        spec_patterns.PATTERN_CATALOG,
        "spb_broken_stacked_overlay_spec_trust_test",
        _boom_spec_pattern,
    )

    shape = (12, 12)
    mask = np.ones(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Overlay spec pattern stack failed.*synthetic stacked overlay spec failure"):
        compose_finish_stacked(
            "gloss",
            [],
            shape,
            mask,
            7,
            1.0,
            overlay_spec_pattern_stack=[
                {
                    "pattern": "spb_broken_stacked_overlay_spec_trust_test",
                    "opacity": 1.0,
                    "scale": 0.5,
                }
            ],
            dither=False,
        )


def test_mix_finish_paint_surfaces_renderer_error_instead_of_unmodified_paint(
    monkeypatch,
):
    import numpy as np
    from engine import compose
    from engine import registry

    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic mix paint renderer failure")

    monkeypatch.setitem(
        registry.BASE_REGISTRY,
        "broken_mix_paint_trust_test",
        {"M": 40, "R": 80, "CC": 16, "paint_fn": _boom_paint},
    )
    paint = np.full((8, 8, 3), 0.5, dtype=np.float32)
    mask = np.ones((8, 8), dtype=np.float32)

    with pytest.raises(RuntimeError, match="synthetic mix paint renderer failure"):
        compose.mix_finish_paint(
            paint,
            (8, 8),
            mask,
            7,
            1.0,
            0.0,
            ["copper", "broken_mix_paint_trust_test"],
            [0.5, 0.5],
            monolithic_registry={},
        )


def test_mix_paint_preview_rejects_unknown_finish_instead_of_gray_preview(app_client):
    response = app_client.post(
        "/api/mix-paint-preview",
        json={
            "finish_ids": ["copper", "missing_mix_preview_trust_test"],
            "weights": [0.5, 0.5],
        },
    )

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"] == "mix_paint_preview_failed"
    assert payload["finish_id"] == "missing_mix_preview_trust_test"


def test_mix_paint_preview_surfaces_swatch_error_instead_of_gray_preview(
    app_client,
    server_module,
    monkeypatch,
):
    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic mix preview swatch failure")

    monkeypatch.setitem(
        server_module.engine.BASE_REGISTRY,
        "broken_mix_preview_trust_test",
        {"M": 40, "R": 80, "CC": 16, "paint_fn": _boom_paint},
    )

    response = app_client.post(
        "/api/mix-paint-preview",
        json={
            "finish_ids": ["copper", "broken_mix_preview_trust_test"],
            "weights": [0.5, 0.5],
        },
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"] == "mix_paint_preview_failed"
    assert payload["finish_id"] == "broken_mix_preview_trust_test"
    assert "synthetic mix preview swatch failure" in payload["message"]


def test_compose_paint_mod_base_paint_error_is_not_silently_unmodified(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_paint_mod

    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic base paint mod failure")

    monkeypatch.setitem(
        registry.BASE_REGISTRY,
        "broken_base_paint_mod_trust_test",
        {"M": 80, "R": 90, "CC": 16, "paint_fn": _boom_paint},
    )

    shape = (8, 8)
    paint = np.full((*shape, 4), 0.5, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Base paint renderer failed .*synthetic base paint mod failure"):
        compose_paint_mod(
            "broken_base_paint_mod_trust_test",
            "none",
            paint,
            shape,
            mask,
            7,
            1.0,
            bb,
        )


def test_compose_paint_mod_stacked_base_paint_error_is_not_silently_unmodified(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_paint_mod_stacked

    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic stacked base paint mod failure")

    monkeypatch.setitem(
        registry.BASE_REGISTRY,
        "broken_stacked_base_paint_mod_trust_test",
        {"M": 80, "R": 90, "CC": 16, "paint_fn": _boom_paint},
    )

    shape = (8, 8)
    paint = np.full((*shape, 4), 0.5, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Stacked base paint renderer failed .*synthetic stacked base paint mod failure"):
        compose_paint_mod_stacked(
            "broken_stacked_base_paint_mod_trust_test",
            [],
            paint,
            shape,
            mask,
            7,
            1.0,
            bb,
        )


def test_compose_paint_mod_pattern_paint_error_is_not_silently_reverted(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_paint_mod

    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic pattern paint mod failure")

    monkeypatch.setitem(
        registry.PATTERN_REGISTRY,
        "broken_pattern_paint_mod_trust_test",
        {"paint_fn": _boom_paint},
    )

    shape = (8, 8)
    paint = np.full((*shape, 4), 0.5, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Pattern paint renderer failed .*synthetic pattern paint mod failure"):
        compose_paint_mod(
            "gloss",
            "broken_pattern_paint_mod_trust_test",
            paint,
            shape,
            mask,
            7,
            1.0,
            bb,
        )


def test_compose_paint_mod_stacked_pattern_paint_error_is_not_silently_reverted(monkeypatch):
    import numpy as np
    from engine import registry
    from engine.compose import compose_paint_mod_stacked

    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic stacked pattern paint mod failure")

    monkeypatch.setitem(
        registry.PATTERN_REGISTRY,
        "broken_stacked_pattern_paint_mod_trust_test",
        {"paint_fn": _boom_paint},
    )

    shape = (8, 8)
    paint = np.full((*shape, 4), 0.5, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Stacked pattern paint renderer failed .*synthetic stacked pattern paint mod failure"):
        compose_paint_mod_stacked(
            "gloss",
            [{"id": "broken_stacked_pattern_paint_mod_trust_test", "opacity": 1.0}],
            paint,
            shape,
            mask,
            7,
            1.0,
            bb,
        )


def test_pattern_layer_rejects_unknown_pattern_with_explicit_error(app_client):
    response = app_client.get("/api/pattern-layer?pattern=missing_pattern_layer_trust_test")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "pattern_layer_failed"
    assert payload["pattern"] == "missing_pattern_layer_trust_test"
    assert "Unknown pattern layer pattern" in payload["message"]


def test_pattern_layer_surfaces_texture_renderer_error(
    app_client,
    server_module,
    monkeypatch,
):
    def _boom_texture(*args, **kwargs):
        raise RuntimeError("synthetic pattern layer texture failure")

    monkeypatch.setitem(
        server_module.engine.PATTERN_REGISTRY,
        "broken_pattern_layer_trust_test",
        {"texture_fn": _boom_texture},
    )

    response = app_client.get("/api/pattern-layer?pattern=broken_pattern_layer_trust_test")

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert payload["error"] == "pattern_layer_failed"
    assert payload["pattern"] == "broken_pattern_layer_trust_test"
    assert "Pattern layer texture renderer failed" in payload["message"]
    assert "synthetic pattern layer texture failure" in payload["message"]


@pytest.mark.parametrize("builder_name", ["build_multi_zone", "build_helmet_spec", "build_suit_spec"])
def test_render_builders_reject_unknown_ids_before_mask_skip_or_downgrade(tmp_path, builder_name):
    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    paint_path = tmp_path / f"{builder_name}_trust.png"
    paint = np.zeros((24, 24, 4), dtype=np.uint8)
    paint[:, :, 0] = 230
    paint[:, :, 3] = 255
    Image.fromarray(paint).save(paint_path)

    zones = [
        {
            "name": "Unmatched Trust Zone",
            "color": "#00ff00",
            "base": "gloss",
            "pattern": "missing_pattern_hidden_by_mask_or_helmet_suit",
            "finish": None,
            "intensity": "100",
        }
    ]

    builder = getattr(eng, builder_name)
    with pytest.raises(ValueError, match="Unknown pattern"):
        builder(str(paint_path), str(tmp_path), zones, seed=42)


@pytest.mark.parametrize(
    ("registry_name", "finish_id", "match"),
    [
        ("MONOLITHIC_REGISTRY", "broken_monolithic_for_trust_test", "Monolithic finish"),
        ("FINISH_REGISTRY", "broken_legacy_for_trust_test", "Legacy finish"),
    ],
)
def test_build_multi_zone_surfaces_selected_renderer_failures(tmp_path, monkeypatch, registry_name, finish_id, match):
    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    paint_path = tmp_path / f"{finish_id}.png"
    paint = np.zeros((24, 24, 4), dtype=np.uint8)
    paint[:, :, 0] = 230
    paint[:, :, 3] = 255
    Image.fromarray(paint).save(paint_path)

    def _boom_spec(*args, **kwargs):
        raise RuntimeError(f"synthetic {finish_id} failure")

    def _noop_paint(paint_arr, *args, **kwargs):
        return paint_arr

    monkeypatch.setitem(getattr(eng, registry_name), finish_id, (_boom_spec, _noop_paint))

    zones = [{"name": "Broken Renderer Zone", "color": "everything", "finish": finish_id, "intensity": "100"}]
    with pytest.raises(RuntimeError, match=match):
        eng.build_multi_zone(str(paint_path), str(tmp_path), zones, seed=42)


def test_build_multi_zone_rejects_malformed_monolithic_spec_instead_of_resizing(tmp_path, monkeypatch):
    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    paint_path = tmp_path / "malformed_mono_spec_trust.png"
    paint = np.zeros((24, 24, 4), dtype=np.uint8)
    paint[:, :, 0] = 230
    paint[:, :, 3] = 255
    Image.fromarray(paint).save(paint_path)

    def _bad_spec(shape, *args, **kwargs):
        h, w = shape
        return (
            np.zeros((h, w + 1), dtype=np.float32),
            np.zeros((h, w), dtype=np.float32),
            np.zeros((h, w), dtype=np.float32),
        )

    def _noop_paint(paint_arr, *args, **kwargs):
        return paint_arr

    monkeypatch.setitem(
        eng.MONOLITHIC_REGISTRY,
        "bad_shape_monolithic_for_trust_test",
        (_bad_spec, _noop_paint),
    )

    zones = [
        {
            "name": "Malformed Monolithic Spec Zone",
            "color": "everything",
            "finish": "bad_shape_monolithic_for_trust_test",
            "intensity": "100",
        }
    ]
    with pytest.raises(RuntimeError, match="Monolithic finish 'bad_shape_monolithic_for_trust_test' failed"):
        eng.build_multi_zone(str(paint_path), str(tmp_path), zones, seed=42)


def test_monolithic_pattern_overlay_paint_surfaces_texture_renderer_failure(monkeypatch):
    import numpy as np
    import shokker_engine_v2 as eng

    def _boom_texture(*args, **kwargs):
        raise RuntimeError("synthetic overlay texture failure")

    monkeypatch.setitem(
        eng.PATTERN_REGISTRY,
        "broken_overlay_pattern_for_trust_test",
        {"texture_fn": _boom_texture, "paint_fn": eng.paint_none},
    )

    h = w = 24
    paint = np.full((h, w, 3), 0.45, dtype=np.float32)
    mask = np.ones((h, w), dtype=np.float32)
    bb = np.zeros((h, w), dtype=np.float32)

    with pytest.raises(RuntimeError, match="Pattern overlay paint texture renderer failed"):
        eng.overlay_pattern_paint(
            paint,
            "broken_overlay_pattern_for_trust_test",
            (h, w),
            mask,
            42,
            1.0,
            bb,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("second_base", "missing_overlay_base", "Unknown second_base"),
        ("third_base_color_source", "mono:missing_special_overlay", "Unknown third_base_color_source"),
        ("fourth_base_pattern", "missing_overlay_pattern", "Unknown fourth_base_pattern"),
    ],
)
def test_engine_rejects_unknown_base_overlay_ids_before_silent_drop(field, value, message):
    import shokker_engine_v2 as eng

    zone = {
        "name": "Overlay Trust Zone",
        "color": "remaining",
        "base": "gloss",
        "pattern": "none",
        "intensity": "100",
        "second_base_strength": 1.0,
        "third_base_strength": 1.0,
        "fourth_base_strength": 1.0,
        field: value,
    }

    with pytest.raises(ValueError, match=message):
        eng._validate_all_zone_render_ids([zone])


def test_engine_accepts_regular_special_and_color_source_overlay_matrix():
    import shokker_engine_v2 as eng

    zone = {
        "name": "Overlay Matrix Zone",
        "color": "remaining",
        "base": "gloss",
        "pattern": "none",
        "intensity": "100",
        "second_base": "mono:firefly",
        "second_base_strength": 1.0,
        "second_base_color_source": "overlay",
        "third_base": "f_metallic",
        "third_base_strength": 0.8,
        "third_base_color_source": "mono:firefly",
        "fourth_base": "gloss",
        "fourth_base_strength": 0.6,
        "fourth_base_pattern": "speed_lines",
        "fifth_base_color_source": "mono:firefly",
        "fifth_base_strength": 0.5,
    }

    eng._validate_all_zone_render_ids([zone])


def test_second_base_overlay_surfaces_mono_paint_renderer_failure(tmp_path, monkeypatch):
    import contextlib
    import io

    import numpy as np
    import pytest
    import shokker_engine_v2 as eng
    from PIL import Image

    def _flat_spec(shape, mask, seed, strength):
        h, w = shape
        return (
            np.full((h, w), 40, dtype=np.float32),
            np.full((h, w), 80, dtype=np.float32),
            np.full((h, w), 16, dtype=np.float32),
        )

    def _boom_paint(*args, **kwargs):
        raise RuntimeError("synthetic second overlay mono paint failure")

    monkeypatch.setitem(
        eng.MONOLITHIC_REGISTRY,
        "broken_second_overlay_mono_trust_test",
        (_flat_spec, _boom_paint),
    )

    h = w = 32
    source = np.full((h, w, 4), 255, dtype=np.uint8)
    source[:, :, :3] = [255, 0, 0]
    source_path = tmp_path / "second_overlay_mono_failure.png"
    Image.fromarray(source).save(source_path)

    zone = {
        "name": "Broken second overlay mono",
        "color": "everything",
        "base": "gloss",
        "pattern": "none",
        "intensity": "100",
        "second_base": "gloss",
        "second_base_color_source": "mono:broken_second_overlay_mono_trust_test",
        "second_base_strength": 1.0,
    }

    eng._validate_all_zone_render_ids([zone])
    with pytest.raises(RuntimeError, match="2nd base overlay paint renderer failed"):
        with contextlib.redirect_stdout(io.StringIO()):
            eng.build_multi_zone(
                str(source_path),
                str(tmp_path / "out"),
                [zone],
                seed=123,
                preview_mode=True,
            )


@pytest.mark.parametrize(
    ("field_prefix", "expected"),
    [
        ("third", "3rd base overlay paint renderer failed"),
        ("fourth", "4th base overlay paint renderer failed"),
        ("fifth", "5th base overlay paint renderer failed"),
    ],
)
def test_later_base_overlays_surface_mono_paint_renderer_failure(field_prefix, expected):
    import contextlib
    import io

    import numpy as np
    import pytest

    from engine.compose import compose_paint_mod

    def _flat_spec(shape, mask, seed, strength):
        h, w = shape
        return (
            np.full((h, w), 40, dtype=np.float32),
            np.full((h, w), 80, dtype=np.float32),
            np.full((h, w), 16, dtype=np.float32),
        )

    def _boom_paint(*args, **kwargs):
        raise RuntimeError(f"synthetic {field_prefix} overlay mono paint failure")

    shape = (24, 24)
    paint = np.full((shape[0], shape[1], 3), 0.5, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    kwargs = {
        f"{field_prefix}_base": "gloss",
        f"{field_prefix}_base_color_source": "mono:broken_later_overlay_mono_trust_test",
        f"{field_prefix}_base_strength": 1.0,
        "monolithic_registry": {
            "broken_later_overlay_mono_trust_test": (_flat_spec, _boom_paint),
        },
    }

    with pytest.raises(RuntimeError, match=expected):
        with contextlib.redirect_stdout(io.StringIO()):
            compose_paint_mod(
                "gloss",
                "none",
                paint,
                shape,
                mask,
                seed=123,
                pm=1.0,
                bb=0.0,
                **kwargs,
            )


@pytest.mark.parametrize(
    ("field_prefix", "ordinal"),
    [
        ("second", "2nd"),
        ("third", "3rd"),
        ("fourth", "4th"),
        ("fifth", "5th"),
    ],
)
def test_stacked_base_overlays_surface_mono_paint_renderer_failure(field_prefix, ordinal):
    import numpy as np
    import pytest

    from engine.compose import compose_paint_mod_stacked

    def _flat_spec(shape, mask, seed, strength):
        h, w = shape
        return (
            np.full((h, w), 40, dtype=np.float32),
            np.full((h, w), 80, dtype=np.float32),
            np.full((h, w), 16, dtype=np.float32),
        )

    def _boom_paint(*args, **kwargs):
        raise RuntimeError(f"synthetic stacked {field_prefix} overlay mono paint failure")

    shape = (24, 24)
    paint = np.full((shape[0], shape[1], 3), 0.5, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    kwargs = {
        f"{field_prefix}_base": "gloss",
        f"{field_prefix}_base_color_source": "mono:broken_stacked_overlay_mono_trust_test",
        f"{field_prefix}_base_strength": 1.0,
        "monolithic_registry": {
            "broken_stacked_overlay_mono_trust_test": (_flat_spec, _boom_paint),
        },
    }

    with pytest.raises(RuntimeError, match=f"{ordinal} stacked base overlay paint renderer failed"):
        compose_paint_mod_stacked(
            "gloss",
            [{"id": "speed_lines", "opacity": 0.75}],
            paint,
            shape,
            mask,
            seed=123,
            pm=1.0,
            bb=0.0,
            **kwargs,
        )


@pytest.mark.parametrize("composer_name", ["compose_paint_mod", "compose_paint_mod_stacked"])
@pytest.mark.parametrize("field_prefix", ["second", "third", "fourth", "fifth"])
def test_solid_color_base_overlays_replace_paint_at_full_tint(composer_name, field_prefix):
    import contextlib
    import io

    import numpy as np

    from engine import compose as compose_mod

    shape = (24, 24)
    paint = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    paint[:, :, 2] = 1.0
    mask = np.ones(shape, dtype=np.float32)
    kwargs = {
        f"{field_prefix}_base": "gloss",
        f"{field_prefix}_base_color": [1.0, 1.0, 0.0],
        f"{field_prefix}_base_color_source": "solid",
        f"{field_prefix}_base_strength": 1.0,
        f"{field_prefix}_base_blend_mode": "tint",
    }

    composer = getattr(compose_mod, composer_name)
    args = (
        ("gloss", "none", paint.copy(), shape, mask)
        if composer_name == "compose_paint_mod"
        else ("gloss", [], paint.copy(), shape, mask)
    )
    with contextlib.redirect_stdout(io.StringIO()):
        out = composer(*args, seed=123, pm=1.0, bb=0.0, **kwargs)

    assert np.allclose(out[:, :, 0], 1.0)
    assert np.allclose(out[:, :, 1], 1.0)
    assert np.allclose(out[:, :, 2], 0.0)


@pytest.mark.parametrize("field_prefix", ["third", "fourth", "fifth"])
def test_build_multi_zone_color_source_only_later_base_overlays_stack_over_second(tmp_path, field_prefix):
    import contextlib
    import io

    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    h = w = 32
    source = np.zeros((h, w, 4), dtype=np.uint8)
    source[:, :, :3] = [20, 40, 180]
    source[:, :, 3] = 255
    source_path = tmp_path / f"{field_prefix}_color_source_overlay_source.png"
    Image.fromarray(source).save(source_path)

    zone = {
        "name": f"{field_prefix} color-source-only overlay over second",
        "color": "everything",
        "base": "gloss",
        "pattern": "none",
        "intensity": "100",
        "second_base_color_source": "solid",
        "second_base_color": [1.0, 0.0, 0.0],
        "second_base_strength": 1.0,
        "second_base_blend_mode": "tint",
        f"{field_prefix}_base_color_source": "solid",
        f"{field_prefix}_base_color": [1.0, 1.0, 0.0],
        f"{field_prefix}_base_strength": 1.0,
        f"{field_prefix}_base_blend_mode": "tint",
    }

    with contextlib.redirect_stdout(io.StringIO()):
        paint, _spec = eng.build_multi_zone(
            str(source_path),
            str(tmp_path / f"{field_prefix}_overlay_out"),
            [zone],
            seed=7,
            preview_mode=True,
        )

    paint_unit = paint.astype(np.float32) / 255.0 if paint.max() > 1.5 else paint.astype(np.float32)
    mean_rgb = paint_unit[:, :, :3].mean(axis=(0, 1))
    assert mean_rgb[0] > 0.95
    assert mean_rgb[1] > 0.95
    assert mean_rgb[2] < 0.05


def test_mono_prefixed_base_registry_special_overlay_matrix_renders(tmp_path):
    import contextlib
    import io

    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    h = w = 48
    source = np.full((h, w, 4), 255, dtype=np.uint8)
    source[:, :, :3] = [255, 0, 0]
    source_path = tmp_path / "mono_prefixed_overlay_matrix.png"
    Image.fromarray(source).save(source_path)

    source_layer_mask = np.zeros((h, w), dtype=np.float32)
    source_layer_mask[:, : w // 2] = 1.0
    zone = {
        "name": "Tracked SPB-9 overlay matrix",
        "color": {"color_rgb": [255, 0, 0], "tolerance": 12},
        "base": "mono:firefly_glow",
        "pattern": "carbon_fiber",
        "intensity": "100",
        "source_layer_mask": source_layer_mask,
        "second_base": "mono:firefly_glow",
        "second_base_color_source": "overlay",
        "second_base_strength": 1.0,
        "second_base_blend_mode": "tint",
        "second_base_pattern": "speed_lines",
        "third_base": "f_metallic",
        "third_base_color_source": "mono:firefly_glow",
        "third_base_strength": 0.8,
        "third_base_blend_mode": "pattern_vivid",
        "fourth_base": "gloss",
        "fourth_base_color_source": "solid",
        "fourth_base_color": [1.0, 0.1, 0.1],
        "fourth_base_strength": 0.6,
        "fifth_base": "f_metallic",
        "fifth_base_color_source": "mono:firefly_glow",
        "fifth_base_strength": 0.5,
        "fifth_base_blend_mode": "tint",
    }

    eng._validate_all_zone_render_ids([zone])
    with contextlib.redirect_stdout(io.StringIO()):
        preview_paint, preview_spec = eng.build_multi_zone(
            str(source_path),
            str(tmp_path / "preview"),
            [dict(zone)],
            seed=123,
            preview_mode=True,
        )
        final_paint, final_spec, final_masks, export_layers = eng.build_multi_zone(
            str(source_path),
            str(tmp_path / "final"),
            [dict(zone)],
            seed=123,
            preview_mode=False,
            export_layers=True,
        )

    default_spec = np.array([5, 100, 16], dtype=np.float32)
    for paint, spec in ((preview_paint, preview_spec), (final_paint, final_spec)):
        active_paint_delta = np.mean(np.abs(paint[:, : w // 2].astype(float) - source[:, : w // 2, :3].astype(float)))
        inactive_paint_delta = np.mean(np.abs(paint[:, w // 2 :].astype(float) - source[:, w // 2 :, :3].astype(float)))
        active_spec_delta = np.mean(np.abs(spec[:, : w // 2, :3].astype(float) - default_spec))
        inactive_spec_delta = np.mean(np.abs(spec[:, w // 2 :, :3].astype(float) - default_spec))
        assert active_paint_delta > 25.0
        assert inactive_paint_delta < 1.0
        assert active_spec_delta > 10.0
        assert inactive_spec_delta < 1.0

    assert len(final_masks) == 1
    assert final_masks[0].sum() == pytest.approx(float(source_layer_mask.sum()))
    assert len(export_layers) == 1
    assert export_layers[0]["mask"].sum() == pytest.approx(float(source_layer_mask.sum()))


def test_metallic_standard_shipping_bases_render_without_signature_errors(tmp_path):
    import contextlib
    import io

    import numpy as np
    import shokker_engine_v2 as eng
    from PIL import Image

    work_dir = tmp_path / "metallic_standard_shipping_bases"
    work_dir.mkdir(parents=True, exist_ok=True)

    h = w = 48
    source = np.zeros((h, w, 4), dtype=np.uint8)
    source[:, :, :3] = [184, 32, 26]
    source[:, :, 3] = 255
    source_path = work_dir / "metallic_standard_source.png"
    Image.fromarray(source).save(source_path)

    metallic_standard_ids = eng._SPB_BASE_GROUPS_SHIPPING["Metallic Standard"]
    assert "candy_apple" in metallic_standard_ids

    overbusy_paint = []
    flat_spec = []
    with contextlib.redirect_stdout(io.StringIO()):
        for base_id in metallic_standard_ids:
            zone = {
                "name": f"Metallic Standard {base_id}",
                "color": "everything",
                "base": base_id,
                "pattern": "none",
                "intensity": "100",
            }
            paint, spec, _masks = eng.build_multi_zone(
                str(source_path),
                str(work_dir / base_id),
                [zone],
                seed=42,
            )
            assert paint.shape == (h, w, 3)
            assert spec.shape[:2] == (h, w)
            assert spec.shape[2] in (3, 4)
            assert np.isfinite(paint).all()
            assert np.isfinite(spec).all()

            paint_unit = paint.astype(np.float32) / 255.0 if paint.max() > 1.5 else paint.astype(np.float32)
            luma = paint_unit.mean(axis=2)
            luma_span = float(np.percentile(luma, 99) - np.percentile(luma, 1))
            luma_std = float(luma.std())
            metallic_range = float(spec[:, :, 0].astype(np.float32).max() - spec[:, :, 0].astype(np.float32).min())

            if luma_std > 0.10 or luma_span > 0.40:
                overbusy_paint.append((base_id, round(luma_std, 4), round(luma_span, 4)))
            if metallic_range < 40.0:
                flat_spec.append((base_id, round(metallic_range, 2)))

    assert overbusy_paint == []
    assert flat_spec == []


def test_spb15_clean_standard_metals_do_not_bake_in_block_texture():
    import numpy as np

    from engine.paint_v2.metallic_flake import (
        paint_copper_metallic_v2,
        paint_standard_metallic_v2,
        spec_copper_metallic,
        spec_standard_metallic,
    )
    from engine.paint_v2.metallic_standard import (
        paint_candy_apple_v2,
        paint_green_flake_v2,
        spec_candy_apple,
        spec_green_flake,
    )

    h = w = 192
    shape = (h, w)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    neutral = np.full((h, w, 3), 0.18, dtype=np.float32)

    cases = {
        "candy_apple": (paint_candy_apple_v2, spec_candy_apple, (0.16, 0.0, 0.0), (0.010, 0.006)),
        "copper": (paint_copper_metallic_v2, spec_copper_metallic, (0.58, 0.26, 0.09), (0.035, 0.055)),
        "green_flake": (paint_green_flake_v2, spec_green_flake, (0.0, 0.34, 0.0), (0.030, 0.050)),
        "metallic": (paint_standard_metallic_v2, spec_standard_metallic, (0.16, 0.16, 0.16), (0.030, 0.045)),
    }

    failures = {}
    for base_id, (paint_fn, spec_fn, expected_min, limits) in cases.items():
        rgb = np.clip(paint_fn(neutral.copy(), shape, mask, 7301, 1.0, bb), 0, 1)
        spec = spec_fn(shape, 7301, 1.0, 120, 80)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        luma_std = float(luma.std())
        channels = rgb.reshape(-1, 3).mean(axis=0)
        m_channel = np.asarray(spec[0] if isinstance(spec, tuple) else spec[:, :, 0], dtype=np.float32)

        max_std, max_fine = limits
        problems = []
        if luma_std >= max_std:
            problems.append(("luma_std", round(luma_std, 5)))
        if fine_energy >= max_fine:
            problems.append(("fine_energy", round(fine_energy, 5)))
        if float(m_channel.max() - m_channel.min()) < 12.0:
            problems.append(("flat_metallic_spec", round(float(m_channel.max() - m_channel.min()), 3)))
        for idx, floor in enumerate(expected_min):
            if float(channels[idx]) < floor:
                problems.append((f"channel_{idx}_too_low", round(float(channels[idx]), 5)))
        if base_id == "candy_apple" and not (channels[0] > channels[1] * 6.0 and channels[0] > channels[2] * 12.0):
            problems.append(("not_dark_red_candy", [round(float(v), 5) for v in channels]))
        if base_id == "copper" and not (channels[0] > channels[1] > channels[2]):
            problems.append(("not_warm_copper_order", [round(float(v), 5) for v in channels]))
        if base_id == "green_flake" and not (channels[1] > channels[0] * 4.0 and channels[1] > channels[2] * 6.0):
            problems.append(("not_green_dominant", [round(float(v), 5) for v in channels]))
        if problems:
            failures[base_id] = problems

    assert failures == {}


def test_spb15_metallic_standard_picker_copy_matches_clean_base_intent():
    root = Path(__file__).resolve().parents[1]
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
const wanted = Object.fromEntries(
  vm.runInContext('BASES', ctx)
    .filter((row) => ['copper', 'green_flake', 'metallic'].includes(row.id))
    .map((row) => [row.id, { name: row.name, desc: row.desc }])
);
console.log(JSON.stringify(wanted));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    rows = json.loads(result.stdout)
    assert rows["copper"]["desc"].lower().startswith("clean warm copper metallic base")
    assert rows["green_flake"]["name"] == "Kryptonite Green"
    assert "heavy shard texture" in rows["green_flake"]["desc"]
    assert "controlled fine sheen" in rows["metallic"]["desc"]


def test_spb15_reworked_metallic_standard_flakes_are_not_square_tiled():
    import numpy as np

    from engine.paint_v2.metallic_standard import (
        paint_blue_ice_flake_v2,
        paint_bronze_flake_v2,
        paint_fire_flake_v2,
        paint_gunmetal_flake_v2,
        paint_original_metal_flake_v2,
        spec_blue_ice_flake,
        spec_bronze_flake,
        spec_fire_flake,
        spec_gunmetal_flake,
        spec_original_metal_flake,
    )

    h = w = 192
    shape = (h, w)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    neutral = np.full((h, w, 3), 0.18, dtype=np.float32)
    cases = {
        "original_metal_flake": (paint_original_metal_flake_v2, spec_original_metal_flake),
        "blue_ice_flake": (paint_blue_ice_flake_v2, spec_blue_ice_flake),
        "bronze_flake": (paint_bronze_flake_v2, spec_bronze_flake),
        "gunmetal_flake": (paint_gunmetal_flake_v2, spec_gunmetal_flake),
        "fire_flake": (paint_fire_flake_v2, spec_fire_flake),
    }

    failures = {}
    for base_id, (paint_fn, spec_fn) in cases.items():
        rgb = np.clip(paint_fn(neutral.copy(), shape, mask, 7301, 1.0, bb), 0, 1)
        spec = spec_fn(shape, 7301, 1.0, 120, 80)
        luma = rgb.mean(axis=2)
        fine_energy = float(np.abs(np.diff(luma, axis=1)).mean() + np.abs(np.diff(luma, axis=0)).mean())
        m_channel = np.asarray(spec[0] if isinstance(spec, tuple) else spec[:, :, 0], dtype=np.float32)
        problems = []
        if fine_energy >= 0.008:
            problems.append(("square_tile_energy", round(fine_energy, 5)))
        if float(m_channel.max() - m_channel.min()) < 12.0:
            problems.append(("flat_metallic_spec", round(float(m_channel.max() - m_channel.min()), 3)))
        if problems:
            failures[base_id] = problems

    assert failures == {}


def test_paint_technique_drip_gravity_is_bounded_runtime_and_visible():
    import time

    import numpy as np
    from engine.paint_v2.paint_technique import paint_drip_gravity, spec_drip_gravity

    h = w = 1024
    shape = (h, w)
    paint = np.full((h, w, 3), 0.45, dtype=np.float32)
    mask = np.ones((h, w), dtype=np.float32)
    bb = np.zeros((h, w), dtype=np.float32)

    start = time.perf_counter()
    out = paint_drip_gravity(paint.copy(), shape, mask, 42, 1.0, bb)
    paint_elapsed = time.perf_counter() - start
    start = time.perf_counter()
    spec = spec_drip_gravity(shape, 42, 1.0, 20, 72)
    spec_elapsed = time.perf_counter() - start

    assert paint_elapsed < 4.0
    assert spec_elapsed < 4.0
    assert float(np.abs(out - paint).max()) > 0.05
    assert float(out.std()) > 0.01
    assert max(float(np.asarray(channel).std()) for channel in spec) > 8.0


def test_paint_technique_brush_stroke_reads_as_broad_bristle_strokes():
    import numpy as np
    from engine.paint_v2.paint_technique import paint_brush_stroke, spec_brush_stroke

    h = w = 512
    shape = (h, w)
    paint = np.full((h, w, 3), 0.45, dtype=np.float32)
    mask = np.ones((h, w), dtype=np.float32)
    bb = np.zeros((h, w), dtype=np.float32)

    out = paint_brush_stroke(paint.copy(), shape, mask, 42, 1.0, bb)
    spec = spec_brush_stroke(shape, 42, 1.0, 12, 84)
    luma = out.mean(axis=2)

    broad_vertical_variation = float(luma.mean(axis=1).std())
    fine_bristle_variation = float(np.mean(np.abs(np.diff(luma, axis=1))))
    assert float(np.abs(out - paint).max()) > 0.05
    assert broad_vertical_variation > 0.010
    assert fine_bristle_variation > 0.006
    assert max(float(np.asarray(channel).std()) for channel in spec) > 12.0


def test_all_paint_techniques_are_visible_non_noops():
    import numpy as np
    from engine.paint_v2 import paint_technique

    h = w = 256
    shape = (h, w)
    paint = np.full((h, w, 3), 0.45, dtype=np.float32)
    mask = np.ones((h, w), dtype=np.float32)
    bb = np.zeros((h, w), dtype=np.float32)
    cases = {
        "paint_drip_gravity": (paint_technique.paint_drip_gravity, paint_technique.spec_drip_gravity),
        "paint_splatter_loose": (paint_technique.paint_splatter_loose, paint_technique.spec_splatter_loose),
        "paint_sponge_stipple": (paint_technique.paint_sponge_stipple, paint_technique.spec_sponge_stipple),
        "paint_roller_streak": (paint_technique.paint_roller_streak, paint_technique.spec_roller_streak),
        "paint_spray_fade": (paint_technique.paint_spray_fade, paint_technique.spec_spray_fade),
        "paint_brush_stroke": (paint_technique.paint_brush_stroke, paint_technique.spec_brush_stroke),
    }

    failures = {}
    for base_id, (paint_fn, spec_fn) in cases.items():
        out = paint_fn(paint.copy(), shape, mask, 99, 1.0, bb)
        spec = spec_fn(shape, 99, 1.0, 12, 84)
        paint_delta = float(np.abs(out - paint).max())
        paint_std = float(out.std())
        spec_std = max(float(np.asarray(channel).std()) for channel in spec)
        problems = []
        if paint_delta <= 0.05:
            problems.append(("paint_delta", round(paint_delta, 4)))
        if paint_std <= 0.01:
            problems.append(("paint_std", round(paint_std, 4)))
        if spec_std <= 8.0:
            problems.append(("spec_std", round(spec_std, 4)))
        if problems:
            failures[base_id] = problems

    assert failures == {}


def test_base_overlay_hsb_values_are_sent_in_live_preview_payload():
    import shutil

    if shutil.which("node") is None:
        pytest.skip("node not available; skipping JS payload harness")

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", str(root / "tests" / "_runtime_harness" / "overlay_only_zone_payload.mjs")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)

    second = payload["special_overlay_solid_color"][0]
    assert second["second_base_hue_shift"] == 42
    assert second["second_base_saturation"] == 18
    assert second["second_base_brightness"] == -12

    fifth = payload["fifth_layer_special_color"][0]
    assert fifth["fifth_base_hue_shift"] == -35
    assert fifth["fifth_base_saturation"] == 22
    assert fifth["fifth_base_brightness"] == 9


def test_zone_box_transform_runtime_commits_base_pattern_and_overlay_targets():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", str(root / "tests" / "_runtime_harness" / "zone_transform_targets.mjs")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)
    for target in ("base", "pattern", "second_base", "spec_pattern_0"):
        row = payload[target]
        assert row["state"]["offsetX"] == pytest.approx(0.25)
        assert row["state"]["offsetY"] == pytest.approx(0.75)
        assert row["state"]["scale"] == pytest.approx(860 / 2048)
        assert row["state"]["rotation"] == 90
        assert row["undo"] == 1
        assert row["renderZones"] == 1
        assert row["preview"] == 1
        assert row["drawTransformHandles"] >= 1


def test_spec_overlay_targets_are_valid_placement_layers():
    root = Path(__file__).resolve().parents[1]
    zones_src = (root / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
    assert "function _isPlacementLayerTarget(layer)" in zones_src
    assert "/^spec_pattern_\\d+$/" in zones_src
    assert "placementLayer = _isPlacementLayerTarget(layer) ? layer : 'none';" in zones_src


def test_live_preview_overlay_hsb_hash_and_server_forwarding_are_pinned():
    root = Path(__file__).resolve().parents[1]
    canvas_src = (root / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    required_hash_fields = [
        "secondBaseHueShift", "secondBaseSaturation", "secondBaseBrightness",
        "thirdBaseHueShift", "thirdBaseSaturation", "thirdBaseBrightness",
        "fourthBaseHueShift", "fourthBaseSaturation", "fourthBaseBrightness",
        "fifthBaseHueShift", "fifthBaseSaturation", "fifthBaseBrightness",
    ]
    missing_hash_fields = [
        field for field in required_hash_fields
        if f"{field}: z.{field}" not in canvas_src
    ]
    assert missing_hash_fields == []

    server_src = (root / "server.py").read_text(encoding="utf-8")
    for suffix in ("hue_shift", "saturation", "brightness"):
        assert f'f"{{_pfx}}_{suffix}"' in server_src
    preview_match = re.search(
        r"@app\.route\('/preview-render'.*?def preview_render_endpoint\(\):(.*?)(?=\n@app\.route)",
        server_src,
        flags=re.S,
    )
    assert preview_match is not None
    preview_body = preview_match.group(1)
    missing_overlay_spec_stacks = [
        key for key in (
            "spec_pattern_stack",
            "overlay_spec_pattern_stack",
            "third_overlay_spec_pattern_stack",
            "fourth_overlay_spec_pattern_stack",
            "fifth_overlay_spec_pattern_stack",
        )
        if f'zone_obj["{key}"]' not in preview_body
    ]
    assert missing_overlay_spec_stacks == []


def test_psd_layer_export_decodes_source_layer_rgb_like_render_paths():
    root = Path(__file__).resolve().parents[1]
    server_src = (root / "server.py").read_text(encoding="utf-8")

    route_patterns = {
        "preview_render": r"@app\.route\('/preview-render'.*?def preview_render_endpoint\(\):(.*?)(?=\n@app\.route)",
        "render": r"@app\.route\('/render'.*?def render\(\):(.*?)(?=\n@app\.route)",
        "export_to_photoshop": r"@app\.route\('/api/export-to-photoshop'.*?def export_to_photoshop\(\):(.*?)(?=\n@app\.route)",
        "export_psd_layers": r"@app\.route\('/export-psd-layers'.*?def export_psd_layers\(\):(.*?)(?=\n@app\.route)",
    }

    missing = []
    for route_name, pattern in route_patterns.items():
        match = re.search(pattern, server_src, flags=re.S)
        assert match is not None, route_name
        body = match.group(1)
        if "source_layer_mask" not in body:
            missing.append((route_name, "source_layer_mask"))
        if (
            "source_layer_rgb_png" not in body
            or ('z["source_layer_rgb"]' not in body and 'zone_obj["source_layer_rgb"]' not in body)
        ):
            missing.append((route_name, "source_layer_rgb_png"))

    assert missing == []


def test_psd_source_layer_mask_decode_rejects_truncated_rle(server_module):
    with pytest.raises(ValueError, match="source_layer_mask.*cover 2 of 4 pixels"):
        server_module._decode_rle_mask_payload(
            {"width": 2, "height": 2, "runs": [[255, 2]]},
            "source_layer_mask",
        )


def test_region_and_spatial_mask_decoders_reject_truncated_rle(server_module):
    with pytest.raises(ValueError, match="region_mask.*cover 2 of 4 pixels"):
        server_module._decode_rle_mask_payload(
            {"width": 2, "height": 2, "runs": [[255, 2]]},
            "region_mask",
        )

    with pytest.raises(ValueError, match="spatial_mask.*cover 2 of 4 pixels"):
        server_module._decode_spatial_mask_payload(
            {"width": 2, "height": 2, "runs": [[1, 2]]},
            "spatial_mask",
        )

    with pytest.raises(ValueError, match="spatial_mask.*invalid spatial mask value"):
        server_module._decode_spatial_mask_payload(
            {"width": 1, "height": 1, "runs": [[9, 1]]},
            "spatial_mask",
        )


def test_psd_source_layer_rgb_decode_rejects_malformed_png(server_module):
    with pytest.raises(ValueError, match="source_layer_rgb_png.*invalid layer RGB PNG"):
        server_module._decode_source_layer_rgb_payload(
            "data:image/png;base64,not-valid-base64!",
            "source_layer_rgb_png",
        )


def test_psd_source_layer_decode_paths_fail_loudly_instead_of_dropping_layer_scope():
    root = Path(__file__).resolve().parents[1]
    server_src = (root / "server.py").read_text(encoding="utf-8")

    route_patterns = {
        "preview_render": r"@app\.route\('/preview-render'.*?def preview_render_endpoint\(\):(.*?)(?=\n@app\.route)",
        "render": r"@app\.route\('/render'.*?def render\(\):(.*?)(?=\n@app\.route)",
        "export_to_photoshop": r"@app\.route\('/api/export-to-photoshop'.*?def export_to_photoshop\(\):(.*?)(?=\n@app\.route)",
        "export_psd_layers": r"@app\.route\('/export-psd-layers'.*?def export_psd_layers\(\):(.*?)(?=\n@app\.route)",
    }

    for route_name, pattern in route_patterns.items():
        match = re.search(pattern, server_src, flags=re.S)
        assert match is not None, route_name
        body = match.group(1)
        assert "_decode_rle_mask_payload" in body, route_name
        assert "_decode_source_layer_rgb_payload" in body, route_name
        assert 'pop("source_layer_mask", None)' not in body, route_name
        assert 'pop("source_layer_rgb", None)' not in body, route_name


def test_zone_mask_decode_paths_fail_loudly_instead_of_dropping_zone_scope():
    root = Path(__file__).resolve().parents[1]
    server_src = (root / "server.py").read_text(encoding="utf-8")

    route_patterns = {
        "preview_render": r"@app\.route\('/preview-render'.*?def preview_render_endpoint\(\):(.*?)(?=\n@app\.route)",
        "render": r"@app\.route\('/render'.*?def render\(\):(.*?)(?=\n@app\.route)",
        "export_to_photoshop": r"@app\.route\('/api/export-to-photoshop'.*?def export_to_photoshop\(\):(.*?)(?=\n@app\.route)",
        "export_psd_layers": r"@app\.route\('/export-psd-layers'.*?def export_psd_layers\(\):(.*?)(?=\n@app\.route)",
    }

    for route_name, pattern in route_patterns.items():
        match = re.search(pattern, server_src, flags=re.S)
        assert match is not None, route_name
        body = match.group(1)
        assert "_decode_rle_mask_payload" in body, route_name
        assert 'except Exception:\n                    z.pop("region_mask", None)' not in body, route_name
        if route_name != "export_psd_layers":
            assert "_decode_spatial_mask_payload" in body, route_name
            assert 'except Exception:\n                    z.pop("spatial_mask", None)' not in body, route_name


def test_preview_render_rejects_bad_region_mask_instead_of_dropping_scope(app_client, tmp_paint_file):
    response = app_client.post(
        "/preview-render",
        json={
            "paint_file": tmp_paint_file,
            "zones": [
                {
                    "name": "Bad Region Mask",
                    "color": "everything",
                    "base": "gloss",
                    "region_mask": {"width": 2, "height": 2, "runs": [[255, 2]]},
                }
            ],
        },
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert "region_mask decode failed" in payload["error"]
    assert "cover 2 of 4 pixels" in payload["error"]


def test_psd_layer_export_forwards_layer_masks_and_base_overlay_stack_to_engine():
    root = Path(__file__).resolve().parents[1]
    server_src = (root / "server.py").read_text(encoding="utf-8")
    match = re.search(
        r"@app\.route\('/export-psd-layers'.*?def export_psd_layers\(\):(.*?)(?=\n@app\.route)",
        server_src,
        flags=re.S,
    )
    assert match is not None
    body = match.group(1)

    assert 'zone_obj["source_layer_mask"] = z["source_layer_mask"]' in body
    assert 'zone_obj["source_layer_rgb"] = z["source_layer_rgb"]' in body
    required_pattern_placement_forwards = [
        'zone_obj["pattern_offset_x"]',
        'zone_obj["pattern_offset_y"]',
        'zone_obj["pattern_flip_h"]',
        'zone_obj["pattern_flip_v"]',
        'zone_obj["pattern_placement"]',
        'zone_obj["pattern_fit_zone"] = True',
        'zone_obj["pattern_manual"] = True',
        'zone_obj["base_color_fit_zone"] = True',
    ]
    missing_pattern_placement = [
        needle for needle in required_pattern_placement_forwards if needle not in body
    ]
    assert missing_pattern_placement == []
    required_spec_stack_forwards = [
        '"spec_pattern_stack"',
        '"overlay_spec_pattern_stack"',
        '"third_overlay_spec_pattern_stack"',
        '"fourth_overlay_spec_pattern_stack"',
        '"fifth_overlay_spec_pattern_stack"',
        "zone_obj[_stack_key] = z.get(_stack_key, [])",
    ]
    missing_spec_stacks = [needle for needle in required_spec_stack_forwards if needle not in body]
    assert missing_spec_stacks == []
    assert 'for _pfx in ("second_base", "third_base", "fourth_base", "fifth_base"):' in body
    assert "if len(result) != 4:" in body
    assert "expected build_multi_zone(export_layers=True)" in body
    assert "zone_layers = []" not in body

    required_overlay_forwards = [
        'zone_obj[_pfx] = _has_base',
        'zone_obj[f"{_pfx}_color"]',
        'zone_obj[f"{_pfx}_color_source"]',
        'zone_obj[f"{_pfx}_strength"]',
        'zone_obj[f"{_pfx}_pattern"]',
        'f"{_pfx}_spec_strength"',
        'f"{_pfx}_pattern_opacity"',
        'f"{_pfx}_pattern_flip_h"',
        'f"{_pfx}_fit_zone"',
    ]
    missing = [needle for needle in required_overlay_forwards if needle not in body]
    assert missing == []


def test_psd_layer_runtime_payload_keeps_overlay_matrix_fields():
    import shutil

    if shutil.which("node") is None:
        pytest.skip("node not available; skipping JS PSD overlay payload harness")

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", str(root / "tests" / "_runtime_harness" / "psd_layer_overlay_payload.mjs")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)["payload"]

    assert payload["source_layer_mask"] == "rle:8x4:32"
    assert payload["source_layer_rgb_png"] == "layer-rgb-png"
    assert payload["overlay_spec_pattern_stack"][0]["pattern"] == "sparkle_galaxy_swirl"
    assert payload["third_overlay_spec_pattern_stack"][0]["pattern"] == "radiator_grille_mesh"
    assert payload["fourth_overlay_spec_pattern_stack"][0]["pattern"] == "spec_carbon_weave"
    assert payload["fifth_overlay_spec_pattern_stack"][0]["pattern"] == "spec_diffraction_grating"
    assert payload["second_base"] == "mono:firefly_glow"
    assert payload["third_base_color_source"] == "mono:firefly_glow"
    assert payload["fourth_base_pattern_flip_h"] is True
    assert payload["fifth_base_hue_shift"] == -18
