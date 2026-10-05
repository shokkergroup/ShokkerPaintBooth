"""SPB-89 owner-rating I/O unit tests (tick 70).

Exercises the parser + formatter + writer in `owner_rating_io.py` without
spinning up Flask. Catches regressions in:
  * The regex parser dropping or mis-extracting entries
  * The formatter emitting invalid JS literal syntax
  * The writer corrupting the file (atomic-write semantics)

Adds 3 tests to the suite — combined with the 13 doctrine/perf tests,
the regression net now includes the rating-capture path.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make the helper module importable
SERVER_DIR = Path(__file__).resolve().parent.parent / "electron-app" / "server"
sys.path.insert(0, str(SERVER_DIR))

from owner_rating_io import (
    VALID_RATING_STATUSES,
    VALID_SCORE_KEYS,
    parse_owner_ratings_js,
    format_rating_entry,
    write_owner_ratings_file,
)


SAMPLE_JS = """// header comment
const PICKER_OWNER_RATINGS = {
  "monolithic:solar_wind": {
    status: "keeper",
    source: "owner brief 2026-05-06",
    notes: "Atmosphere keeper: aurora-like ribbons plus sparse particle energy.",
    scores: {
      patternDesign: 88,
      uniqueness: 86,
      specDetail: 82,
      renderTime: 78,
      intentFit: 92,
      sponsorSafety: 72,
      overall: 87
    }
  },
  "monolithic:x_ray": {
    status: "rework_spec",
    source: "owner brief 2026-05-06",
    notes: "Promising direction, but spec is only about one-third of the way there.",
    scores: {
      patternDesign: 68,
      uniqueness: 78,
      specDetail: 36,
      renderTime: 72,
      intentFit: 84,
      sponsorSafety: 52,
      overall: 61
    }
  }
};

if (typeof window !== 'undefined') window.PICKER_OWNER_RATINGS = PICKER_OWNER_RATINGS;
"""


def test_parse_extracts_all_entries():
    """The regex should find both entries in the sample."""
    entries = parse_owner_ratings_js(SAMPLE_JS)
    assert set(entries.keys()) == {"monolithic:solar_wind", "monolithic:x_ray"}
    assert 'status: "keeper"' in entries["monolithic:solar_wind"]
    assert 'specDetail: 36' in entries["monolithic:x_ray"]


def test_format_rating_entry_basic():
    """Basic emit: status + source + notes + scores."""
    out = format_rating_entry(
        status="keeper",
        source="owner click 2026-05-16",
        notes="lands the spec rework",
        scores={"patternDesign": 75, "overall": 80, "renderTime": 60},
    )
    assert 'status: "keeper"' in out
    assert 'source: "owner click 2026-05-16"' in out
    assert 'notes: "lands the spec rework"' in out
    assert "scores: {" in out
    assert "patternDesign: 75" in out
    assert "overall: 80" in out
    assert "renderTime: 60" in out
    # Score keys must come from VALID_SCORE_KEYS — try injecting an unknown one
    out_unknown = format_rating_entry(
        status="watch", source="x", notes="", scores={"madeUpKey": 50, "overall": 70}
    )
    assert "madeUpKey" not in out_unknown
    assert "overall: 70" in out_unknown


def test_format_rating_escapes_quotes():
    """Notes / source must escape embedded double-quotes."""
    out = format_rating_entry(
        status="watch",
        source='owner with "tricky" quote',
        notes='also "quoted" content here',
        scores={},
    )
    assert 'source: "owner with \\"tricky\\" quote"' in out
    assert 'notes: "also \\"quoted\\" content here"' in out


def test_format_rating_omits_empty_notes_and_empty_scores():
    """No notes/scores → no notes/scores lines."""
    out = format_rating_entry("watch", "src", "", {})
    assert "notes:" not in out
    assert "scores:" not in out


def test_roundtrip_through_writer(tmp_path):
    """Write entries, parse the result, confirm they survive."""
    entries = parse_owner_ratings_js(SAMPLE_JS)
    # Add a new entry via the formatter
    entries["monolithic:test_new"] = format_rating_entry(
        status="keeper", source="test 2026-05-16",
        notes="round-trip", scores={"overall": 85, "patternDesign": 75},
    )
    out_path = tmp_path / "out.js"
    write_owner_ratings_file(entries, str(out_path))
    written = out_path.read_text(encoding="utf-8")
    parsed = parse_owner_ratings_js(written)
    # All 3 entries survive
    assert set(parsed.keys()) == {"monolithic:solar_wind", "monolithic:x_ray", "monolithic:test_new"}
    # The new one's content is intact
    assert "round-trip" in parsed["monolithic:test_new"]
    assert "overall: 85" in parsed["monolithic:test_new"]
    # File has the standard JS shape
    assert "const PICKER_OWNER_RATINGS = {" in written
    assert "if (typeof window" in written


def test_writer_sorts_entries_for_stable_diffs(tmp_path):
    """Output ordering should be alphabetical by fid so re-saves diff cleanly."""
    entries = {
        "monolithic:zebra": format_rating_entry("watch", "z", "", {}),
        "monolithic:apple": format_rating_entry("keeper", "a", "", {}),
        "monolithic:mango": format_rating_entry("reject", "m", "", {}),
    }
    out_path = tmp_path / "sorted.js"
    write_owner_ratings_file(entries, str(out_path))
    txt = out_path.read_text(encoding="utf-8")
    apple_idx = txt.index("monolithic:apple")
    mango_idx = txt.index("monolithic:mango")
    zebra_idx = txt.index("monolithic:zebra")
    assert apple_idx < mango_idx < zebra_idx


def test_writer_is_atomic(tmp_path):
    """No `.tmp` leftover after a successful write."""
    entries = {"monolithic:smoke": format_rating_entry("watch", "smoke", "", {})}
    out_path = tmp_path / "atomic.js"
    write_owner_ratings_file(entries, str(out_path))
    assert out_path.exists()
    assert not (tmp_path / "atomic.js.tmp").exists()


def test_valid_status_enum_matches_documented():
    """The enum used by the route must include the 5 statuses the UI lists."""
    expected = {"keeper", "watch", "rework_paint", "rework_spec", "reject"}
    assert VALID_RATING_STATUSES == expected


def test_valid_score_keys_match_documented():
    """The 7 score categories must match what existing ratings file uses."""
    expected = {"patternDesign", "uniqueness", "specDetail", "renderTime",
                "intentFit", "sponsorSafety", "overall"}
    assert VALID_SCORE_KEYS == expected
