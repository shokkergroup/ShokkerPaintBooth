from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import spb_wilds_110_bake as wilds_bake
from scripts.spb_verify_wilds_release_sync import (
    CRITICAL_RUNTIME_FILES,
    verify_exact_two_copy,
)
from scripts.spb_wilds_release_gate import (
    acquire_exclusive_lock,
    validate_wilds_110_census,
    verify_picker_snapshot_postconditions,
)
from scripts.spb_wilds_110_bake import MONOLITHIC_CARD_SIZE


def _exact_lanes():
    return {
        "cryptid": [f"fc_{i:02d}" for i in range(20)],
        "morpho": [f"fm_{i:02d}" for i in range(50)],
        "bloom": [f"fb_{i:02d}" for i in range(20)],
        "petri": [f"fp_{i:02d}" for i in range(20)],
    }


def _callable_registry(lanes):
    def spec_fn(*_args):
        return None

    def paint_fn(*_args):
        return None

    return {fid: (spec_fn, paint_fn) for ids in lanes.values() for fid in ids}


def test_canonical_census_rejects_missing_or_noncallable_registry_entry():
    lanes = _exact_lanes()
    registry = _callable_registry(lanes)
    assert len(validate_wilds_110_census(lanes, registry)) == 110

    missing = dict(registry)
    missing.pop("fp_19")
    with pytest.raises(RuntimeError, match="missing=.*fp_19"):
        validate_wilds_110_census(lanes, missing)

    invalid = dict(registry)
    invalid["fm_00"] = (None, lambda *_args: None)
    with pytest.raises(RuntimeError, match="non-callable=.*fm_00"):
        validate_wilds_110_census(lanes, invalid)


def test_fresh_stage_and_current_bake_gate_cannot_reuse_stale_png(tmp_path: Path):
    old_stage = tmp_path / "wilds_110_real_engine_thumbnails"
    stale = old_stage / "monolithic" / "fc_00.png"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"stale-png")

    stage = wilds_bake._prepare_unique_stage(tmp_path)
    assert stage != old_stage
    assert list(stage.iterdir()) == []

    # Even if a caller retries inside one stage, the per-ID helper unlinks the
    # expected output and requires a manifest proving this exact invocation.
    retry_stale = stage / "monolithic" / "fc_00.png"
    retry_stale.parent.mkdir(parents=True)
    retry_stale.write_bytes(b"stale-retry")

    class NoOpBaker:
        @staticmethod
        def main():
            return None

    with pytest.raises(RuntimeError, match="current bake did not write"):
        wilds_bake._run_current_bake(NoOpBaker, "fc_00", stage)
    assert not retry_stale.exists()


def test_release_lock_contention_waits_then_fails_closed(tmp_path: Path):
    lock = tmp_path / "picker_split" / "_baker.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("other-pid", encoding="ascii")
    started = time.monotonic()
    acquired = acquire_exclusive_lock(
        lock, stale_secs=3600, wait_secs=0.06, poll_secs=0.01
    )
    elapsed = time.monotonic() - started
    assert acquired is None
    assert elapsed >= 0.045


def _picker_args(**overrides):
    values = dict(
        wilds_110=False,
        ids=None,
        category=None,
        key=None,
        limit=0,
        type="all",
        package_alpha=False,
        warm_cache=False,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_wilds_selection_is_110_even_when_scorecard_category_resolves_only_90(monkeypatch):
    import rebuild_picker_swatches as picker

    ids110 = [f"wild_{i:03d}" for i in range(110)]
    ids90 = [("monolithic", fid) for fid in ids110[:90]]
    monkeypatch.setattr(picker, "canonical_wilds_110", lambda _registry: ({}, ids110))
    monkeypatch.setattr(picker, "_ids_from_categories", lambda _categories: ids90)

    category_items = picker._select_items(_picker_args(category=["Fractured Wilds"]))
    release_items = picker._select_items(_picker_args(wilds_110=True))
    assert len(category_items) == 90
    assert release_items == [("monolithic", fid) for fid in ids110]


def test_picker_release_postcondition_checks_all_110_paths_and_hashes(tmp_path: Path):
    items = [("monolithic", f"wild_{i:03d}") for i in range(110)]

    class FakeServer:
        PICKER_SNAPSHOT_RENDER_SCALE = 0.5

        def __init__(self):
            self.root = tmp_path
            self.manifest = {"finishes": {}}

        def _load_picker_split_manifest(self):
            return self.manifest

        def _picker_split_static_path(self, finish_type, finish_key):
            return str(self.root / finish_type / f"{finish_key}.png")

        @staticmethod
        def _picker_finish_renderer_hash(_finish_type, finish_key):
            return f"hash-{finish_key}"

        @staticmethod
        def _catalog_color_for_picker_swatch(_finish_type, _finish_key):
            return "888888"

    server = FakeServer()
    for finish_type, finish_key in items:
        path = Path(server._picker_split_static_path(finish_type, finish_key))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")
        server.manifest["finishes"][f"{finish_type}:{finish_key}"] = {
            "hash": f"hash-{finish_key}",
            "color_hex": "888888",
            "render_scale": 0.5,
        }

    missing_item = items[-1]
    Path(server._picker_split_static_path(*missing_item)).unlink()
    server.manifest["finishes"]["monolithic:wild_000"]["hash"] = "stale"
    errors = verify_picker_snapshot_postconditions(server, items)
    assert any("wild_109: snapshot path missing" in error for error in errors)
    assert any("wild_000: manifest hash" in error for error in errors)

    Path(server._picker_split_static_path(*missing_item)).write_bytes(b"png")
    server.manifest["finishes"]["monolithic:wild_000"]["hash"] = "hash-wild_000"
    assert verify_picker_snapshot_postconditions(server, items) == []


def test_exact_two_copy_verifier_checks_both_thumbnail_trees(tmp_path: Path):
    ids = ["fc_one", "fm_two"]
    electron = tmp_path / "electron-app" / "server"
    for fid in ids:
        for relative in (
            Path("thumbnails") / "monolithic" / f"{fid}.png",
            Path("thumbnails") / "picker_split" / "monolithic" / f"{fid}.png",
        ):
            (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
            (electron / relative).parent.mkdir(parents=True, exist_ok=True)
            payload = f"png:{relative}".encode()
            (tmp_path / relative).write_bytes(payload)
            (electron / relative).write_bytes(payload)

    report = verify_exact_two_copy(
        tmp_path, ids, critical_files=(), enforce_manifest_contract=False
    )
    assert report["ok"] is True
    assert report["verifiedPairs"] == 4

    (electron / "thumbnails" / "monolithic" / "fc_one.png").write_bytes(b"drift")
    report = verify_exact_two_copy(
        tmp_path, ids, critical_files=(), enforce_manifest_contract=False
    )
    assert report["ok"] is False
    assert any("SHA-256 drift" in error for error in report["errors"])


def _write_exact_pair(root: Path, relative: str, payload: bytes) -> None:
    electron = root / "electron-app" / "server"
    source = root / relative
    target = electron / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(payload)
    target.write_bytes(payload)


def test_quality_source_paths_extend_exact_sha_pairs_and_detect_drift(tmp_path: Path):
    ids = ["fc_one"]
    for relative in (
        "thumbnails/monolithic/fc_one.png",
        "thumbnails/picker_split/monolithic/fc_one.png",
    ):
        _write_exact_pair(tmp_path, relative, relative.encode("ascii"))
    dynamic = "engine/expansions/fractured_wilds_new_2026.py"
    _write_exact_pair(tmp_path, dynamic, b"same authored source")

    report = verify_exact_two_copy(
        tmp_path,
        ids,
        critical_files=(),
        source_paths=[dynamic],
        enforce_manifest_contract=False,
    )
    assert report["ok"] is True
    assert report["expectedPairs"] == 3
    assert report["verifiedPairs"] == 3
    assert report["qualitySourcePaths"] == [dynamic]
    assert report["qualitySourcePathCount"] == 1
    assert dynamic in {row["path"] for row in report["files"]}

    target = tmp_path / "electron-app" / "server" / dynamic
    target.write_bytes(b"stale packaged source")
    report = verify_exact_two_copy(
        tmp_path,
        ids,
        critical_files=(),
        source_paths=[dynamic],
        enforce_manifest_contract=False,
    )
    assert report["ok"] is False
    assert any(
        f"SHA-256 drift: {dynamic}" in error for error in report["errors"]
    )


@pytest.mark.parametrize(
    "source_paths, message",
    (
        (["/absolute.py"], "unsafe absolute"),
        (["C:/absolute.py"], "drive or stream"),
        (["../escape.py"], "unsafe traversal"),
        (["engine/../escape.py"], "unsafe traversal"),
        (["engine//source.py"], "non-canonical"),
        (["engine\\source.py"], "backslashes"),
        ([" engine/source.py"], "surrounding whitespace"),
        (["engine/source.py\n"], "surrounding whitespace"),
        (["engine/source.py."], "Windows-ambiguous"),
        (["engine/CON.py"], "Windows reserved name"),
        (["engine/source?.py"], "Windows filename syntax"),
        ([""], "non-empty string"),
        ([Path("engine/source.py")], "non-empty string"),
        (
            ["engine/Source.py", "engine/source.py"],
            "duplicate dynamic quality source path",
        ),
    ),
)
def test_quality_source_paths_reject_unsafe_absolute_or_duplicate_entries(
    tmp_path: Path, source_paths, message: str,
):
    with pytest.raises(RuntimeError, match=message):
        verify_exact_two_copy(
            tmp_path,
            [],
            critical_files=(),
            source_paths=source_paths,
            enforce_manifest_contract=False,
        )


def test_quality_source_already_critical_is_checked_once(tmp_path: Path):
    relative = "engine/expansions/shared.py"
    _write_exact_pair(tmp_path, relative, b"shared source")
    report = verify_exact_two_copy(
        tmp_path,
        [],
        critical_files=(relative,),
        source_paths=[relative],
        enforce_manifest_contract=False,
    )
    assert report["ok"] is True
    assert report["expectedPairs"] == 1
    assert report["verifiedPairs"] == 1
    assert report["qualitySourcePaths"] == [relative]


def test_critical_runtime_files_cover_buyer_catalog_javascript():
    assert "paint-booth-0-finish-data.js" in CRITICAL_RUNTIME_FILES
    assert "paint-booth-0-catalog-scorecard.js" in CRITICAL_RUNTIME_FILES


def test_quality_open_cli_routes_validated_source_paths_to_delivery(
    monkeypatch, capsys,
):
    from scripts import spb_verify_wilds_release_sync as release_sync

    ids = ["fc_one"]
    dynamic = ["engine/expansions/fc_one.py"]
    captured = {}
    monkeypatch.setattr(
        release_sync, "canonical_wilds_110", lambda _registry=None: ({"fixture": ids}, ids),
    )
    monkeypatch.setattr(
        release_sync,
        "validate_quality_release_manifest",
        lambda *_args, **_kwargs: {
            "status": "quality_release_lock_open",
            "owner_accepted": 1,
            "production_wired": 1,
            "source_paths": dynamic,
        },
    )

    def verified(_root, actual_ids, *, source_paths=()):
        captured["ids"] = actual_ids
        captured["source_paths"] = source_paths
        return {
            "ok": True,
            "wildsCount": 1,
            "verifiedPairs": 3,
            "expectedPairs": 3,
            "errors": [],
        }

    monkeypatch.setattr(release_sync, "verify_exact_two_copy", verified)
    assert release_sync.main([]) == 0
    assert captured == {"ids": ids, "source_paths": dynamic}
    assert "3/3 exact two-copy pairs" in capsys.readouterr().out


def test_quality_open_cli_fails_closed_on_unsafe_report_source_path(
    tmp_path: Path, monkeypatch, capsys,
):
    from scripts import spb_verify_wilds_release_sync as release_sync

    monkeypatch.setattr(release_sync, "ROOT", tmp_path)
    monkeypatch.setattr(release_sync, "canonical_wilds_110", lambda _registry=None: ({}, []))
    monkeypatch.setattr(
        release_sync,
        "validate_quality_release_manifest",
        lambda *_args, **_kwargs: {
            "status": "quality_release_lock_open",
            "owner_accepted": 0,
            "production_wired": 0,
            "source_paths": ["../escape.py"],
        },
    )
    assert release_sync.main([]) == 1
    output = capsys.readouterr().out
    assert "release path contract rejected" in output
    assert "unsafe traversal" in output


def test_picker_swatch_color_normalizer_rejects_arbitrary_or_noncanonical_text():
    import rebuild_picker_swatches as picker

    assert picker._normalize_swatch_tint_hex("#AbC") == "aabbcc"
    assert picker._normalize_swatch_tint_hex("a1B2c3") == "a1b2c3"
    for invalid in ("tomato", "#123456 trailing", "12345678", "12#", "", None):
        assert picker._normalize_swatch_tint_hex(invalid) == "888888"
def test_wilds_release_bake_uses_the_production_256px_monolithic_card_contract():
    assert MONOLITHIC_CARD_SIZE == 256
