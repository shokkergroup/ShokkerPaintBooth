import json
from pathlib import Path

import pytest

from scripts.smart_tga_inspection_union import merge_runs


def _run(root: Path, name: str, records: list[dict]) -> Path:
    path = root / name
    path.mkdir()
    (path / "inspection_records.json").write_text(json.dumps(records), encoding="utf-8")
    return path


def test_inspection_union_requires_explicit_duplicate_winner_and_records_provenance(tmp_path):
    first = _run(tmp_path, "cycle_a", [
        {"paint_label": "family/shared.tga", "success": True, "marker": "a"},
        {"paint_label": "family/unique_a.tga", "success": True},
    ])
    second = _run(tmp_path, "cycle_b", [
        {"paint_label": "family/shared.tga", "success": True, "marker": "b"},
        {"paint_label": "family/unique_b.tga", "success": True},
    ])

    with pytest.raises(ValueError, match="duplicate successful records"):
        merge_runs([first, second], {})

    records, provenance = merge_runs(
        [first, second], {"family/shared.tga": "cycle_b"}
    )
    by_label = {record["paint_label"]: record for record in records}
    assert by_label["family/shared.tga"]["marker"] == "b"
    assert by_label["family/shared.tga"]["_union_source_run"] == str(second.resolve())
    assert provenance["family/shared.tga"]["policy"] == "explicit_selection"
    assert provenance["family/shared.tga"]["successful_candidate_count"] == 2
    assert len(records) == 3


def test_inspection_union_prefers_a_unique_success_over_failures(tmp_path):
    failed = _run(tmp_path, "failed", [{
        "paint_label": "family/retry.tga", "success": False, "error": "missing",
    }])
    passed = _run(tmp_path, "passed", [{
        "paint_label": "family/retry.tga", "success": True, "marker": "good",
    }])

    records, provenance = merge_runs([failed, passed], {})
    assert records[0]["marker"] == "good"
    assert provenance["family/retry.tga"]["policy"] == "unique_success"


def test_inspection_union_rejects_unused_or_ambiguous_selection(tmp_path):
    run = _run(tmp_path, "only", [{"paint_label": "family/one.tga", "success": True}])
    with pytest.raises(ValueError, match="did not match duplicate labels"):
        merge_runs([run], {"family/missing.tga": "only"})
