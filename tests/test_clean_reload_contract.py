"""Focused regressions for the 2026-09-01 clean-reload repair."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

from server_health import check_registry_sizes
from server_routes.thumbnail_status import (
    build_thumbnail_inventory,
    register_thumbnail_status_routes,
)


ROOT = Path(__file__).resolve().parents[1]


def _touch_png(root: Path, category: str, name: str) -> None:
    directory = root / category
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(b"not-decoded-by-inventory")


def test_thumbnail_inventory_never_offsets_a_missing_base_with_pattern_surplus(tmp_path):
    engine = SimpleNamespace(
        BASE_REGISTRY={"base_a": object(), "base_b": object()},
        PATTERN_REGISTRY={"pattern_a": object()},
        MONOLITHIC_REGISTRY={"mono_a": object()},
    )
    _touch_png(tmp_path, "base", "base_a.png")
    _touch_png(tmp_path, "base", "obsolete_base.png")
    _touch_png(tmp_path, "pattern", "pattern_a.png")
    for index in range(5):
        _touch_png(tmp_path, "pattern", f"obsolete_pattern_{index}.png")
    _touch_png(tmp_path, "monolithic", "mono_a.png")

    report = build_thumbnail_inventory(str(tmp_path), engine)

    assert report["categories"]["bases"]["missing_count"] == 1
    assert report["categories"]["bases"]["missing_sample"] == ["base_b"]
    assert report["categories"]["bases"]["stale_count"] == 1
    assert report["categories"]["patterns"]["stale_count"] == 5
    assert report["missing_count"] == 1
    assert report["present_total"] == 3
    assert report["expected_total"] == 4


def test_thumbnail_status_uses_live_registries_not_stale_canonical_snapshot(tmp_path):
    thumbs = tmp_path / "thumbnails"
    server_dir = tmp_path / "server"
    server_dir.mkdir(exist_ok=True)
    (server_dir / "finish_ids_canonical.json").write_text(
        json.dumps({"bases": ["old_a", "old_b"], "patterns": [], "specials": []}),
        encoding="utf-8",
    )
    engine = SimpleNamespace(
        BASE_REGISTRY={"live_base": object()},
        PATTERN_REGISTRY={"live_pattern": object()},
        MONOLITHIC_REGISTRY={"live_mono": object()},
    )
    _touch_png(thumbs, "base", "live_base.png")
    _touch_png(thumbs, "pattern", "live_pattern.png")
    _touch_png(thumbs, "monolithic", "live_mono.png")

    app = Flask(__name__)
    register_thumbnail_status_routes(
        app,
        engine_getter=lambda: engine,
        thumbnail_dir_getter=lambda: str(thumbs),
        server_dir_getter=lambda: str(server_dir),
    )
    payload = app.test_client().get("/api/thumbnail-status").get_json()

    assert payload["inventory_source"] == "live_runtime_registries"
    assert payload["expected"] == {"bases": 1, "patterns": 1, "specials": 1, "total": 3}
    assert payload["missing_count"] == 0
    assert payload["canonical_used"] is False
    assert payload["catalog_snapshot"] == {"bases": 2, "patterns": 0, "specials": 0, "total": 2}
    assert payload["catalog_snapshot_used_for_runtime_coverage"] is False


def test_health_checks_keep_minimum_gates_without_stale_upper_warnings(caplog):
    caplog.set_level(logging.WARNING, logger="shokker_v5")

    issues = check_registry_sizes(
        {str(i): None for i in range(995)},
        {str(i): None for i in range(718)},
        {str(i): None for i in range(2_897)},
    )

    assert issues == []
    assert "unusually large" not in caplog.text
    assert "too small" in check_registry_sizes({}, {}, {})[0]


def test_reload_sources_acknowledge_profiler_beacon_and_fix_console_mojibake():
    server_source = (ROOT / "server.py").read_text(encoding="utf-8")
    launcher = (ROOT / "START_SERVER.bat").read_text(encoding="utf-8")

    assert "@app.route('/spb-prof', methods=['GET'])" in server_source
    assert "def _spb_profiler_beacon_sink():" in server_source
    assert "return ('', 204)" in server_source
    assert "'/spb-prof'," in server_source
    assert "SHOKKER PAINT BOOTH - SUPERVISED BACKEND" in launcher
    assert all(ord(char) < 128 for char in launcher)


def test_server_v5_reports_modular_fusions_and_has_no_dead_clean_boot_hook():
    source = (ROOT / "server_v5.py").read_text(encoding="utf-8")

    assert "import engine.fusions as _fusion_mod" in source
    assert "FUSION_REGISTRY = _fusion_mod.FUSION_REGISTRY" in source
    assert "from clean_boot import clean_boot" not in source
    assert "Clean boot skipped" not in source


def test_local_server_contract_is_loopback_and_quiet_outside_debug():
    config_source = (ROOT / "config.py").read_text(encoding="utf-8")
    server_source = (ROOT / "server_v5.py").read_text(encoding="utf-8")

    assert 'DEFAULT_HOST: str = "127.0.0.1"' in config_source
    assert "_srv4 = make_server(CFG.HOST, port, app, threaded=CFG.THREADED)" in server_source
    assert "if debug:" in server_source


def test_spec_cache_startup_queues_hash_aware_verification_not_raw_count_gate():
    source = (ROOT / "server.py").read_text(encoding="utf-8")
    start = source.index("def _start_thumbnail_background_jobs():")
    end = source.index("\n_start_thumbnail_background_jobs()", start + 1)
    block = source[start:end]

    assert "spec_count < expected" not in block
    assert "metal_count < expected" not in block
    assert "Spec pattern thumbnail verification queued" in block
    assert "target=_prebake_spec_patterns" in block
