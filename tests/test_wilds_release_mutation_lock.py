from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from scripts import spb_wilds_quality_release_lock as quality
from scripts import spb_wilds_release_gate as release


SYNTHETIC_IDS = ["wild_alpha", "wild_beta"]


def test_single_wilds_write_requires_the_full_quality_census(monkeypatch):
    monkeypatch.setattr(
        release,
        "declared_wilds_110",
        lambda: ({"fixture": SYNTHETIC_IDS}, list(SYNTHETIC_IDS)),
    )
    calls = []

    sentinel_registry = {"wild_alpha": object(), "wild_beta": object()}

    def validate(manifest, expected_ids, *, root=None, registry=None):
        calls.append((manifest, list(expected_ids), root, registry))
        return {"status": "quality_release_lock_open"}

    monkeypatch.setattr(quality, "validate_quality_release_manifest", validate)
    report = release.require_wilds_quality_release_for_items(
        [("monolithic", "wild_alpha")],
        manifest_path="owner.json",
        registry=sentinel_registry,
    )
    assert calls == [("owner.json", SYNTHETIC_IDS, None, sentinel_registry)]
    assert report["targeted_wilds"] == ["wild_alpha"]


def test_non_wilds_write_does_not_require_wilds_manifest(monkeypatch):
    monkeypatch.setattr(
        release,
        "declared_wilds_110",
        lambda: ({"fixture": SYNTHETIC_IDS}, list(SYNTHETIC_IDS)),
    )
    monkeypatch.setattr(
        quality,
        "validate_quality_release_manifest",
        lambda *_args, **_kwargs: pytest.fail("non-Wilds write reached Wilds lock"),
    )
    assert release.require_wilds_quality_release_for_items(
        [("monolithic", "ordinary_finish"), ("pattern", "wild_alpha")]
    ) is None


def test_canonical_census_never_reinstalls_legacy_renderers(monkeypatch):
    from engine.expansions import fractured_bloom_2026 as bloom
    from engine.expansions import fractured_morpho_2026 as morpho
    from engine.expansions import fractured_petri_2026 as petri
    from engine.expansions import fractured_themes_2026 as themes
    from engine.expansions import fractured_themes_fix_2026 as themes_fix

    _lanes, ids = release.declared_wilds_110()

    def spec(*_args, **_kwargs):
        return "approved-spec"

    def paint(*_args, **_kwargs):
        return "approved-paint"

    registry = {fid: (spec, paint) for fid in ids}
    before = {fid: tuple(map(id, registry[fid])) for fid in ids}

    def forbidden_install(*_args, **_kwargs):
        pytest.fail("canonical census reinstalled a legacy renderer")

    for module in (themes, themes_fix, morpho, bloom, petri):
        monkeypatch.setattr(module, "install_into_engine", forbidden_install)

    _actual_lanes, actual_ids = release.canonical_wilds_110(registry)
    assert actual_ids == ids
    assert {fid: tuple(map(id, registry[fid])) for fid in ids} == before


def test_server_public_and_batch_writers_guard_before_render(monkeypatch):
    monkeypatch.setenv("SHOKKER_SKIP_PICKER_PREBAKE", "1")
    monkeypatch.setenv("SHOKKER_SKIP_SPEC_PREBAKE", "1")
    server = importlib.import_module("server")

    class Locked(RuntimeError):
        pass

    guarded_manifests = []

    def blocked(_items, manifest_path=None):
        guarded_manifests.append(manifest_path)
        raise Locked("owner accepted 0/110")

    monkeypatch.setattr(server, "_require_wilds_picker_write_quality", blocked)
    monkeypatch.setattr(
        server,
        "_render_picker_split_snapshot_bytes",
        lambda *_args, **_kwargs: pytest.fail("render began before quality lock"),
    )
    monkeypatch.setattr(
        server,
        "picker_split_needs_rebuild",
        lambda *_args, **_kwargs: pytest.fail("batch inspected targets before quality lock"),
    )

    with pytest.raises(Locked, match="owner accepted 0/110"):
        server.save_picker_split_snapshot("monolithic", "wild_alpha")
    with pytest.raises(Locked, match="owner accepted 0/110"):
        server.bake_picker_split_batch(
            [("monolithic", "wild_alpha")],
            wilds_quality_manifest="review.json",
        )
    with pytest.raises(Locked, match="owner accepted 0/110"):
        server.warm_picker_split_swatch_cache([
            ("monolithic", "wild_alpha", "112233"),
        ], wilds_quality_manifest="review.json")
    monkeypatch.setitem(server.engine.MONOLITHIC_REGISTRY, "wild_alpha", (lambda: None, lambda: None))
    with pytest.raises(Locked, match="owner accepted 0/110"):
        server._validate_thumbnail_regen_request("monolithic", "wild_alpha")
    assert guarded_manifests == [None, "review.json", "review.json", None]


def test_chunk_workers_receive_the_selected_quality_manifest(monkeypatch):
    picker = importlib.import_module("rebuild_picker_swatches")
    captured = {}

    def worker(command, *, cwd):
        captured["command"] = command
        captured["cwd"] = cwd
        result_path = Path(command[command.index("--result-file") + 1])
        result_path.write_text(
            json.dumps({"baked": 1, "skipped": 0, "errors": 0}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(picker.subprocess, "call", worker)
    assert picker._run_chunked(
        [("monolithic", "wild_alpha")],
        False,
        50,
        "review/custom-owner.json",
    ) == (1, 0, 0)
    command = captured["command"]
    manifest_index = command.index("--wilds-quality-manifest")
    assert command[manifest_index + 1] == "review/custom-owner.json"
