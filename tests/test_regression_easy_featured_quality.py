import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_featured_collections_are_three_unique_quality_gated_eights():
    result = subprocess.run(
        ["node", "scripts/spb_easy_featured_audit.js"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout[result.stdout.index("{"):])
    assert payload["ok"] is True
    assert payload["uniqueCount"] == 24
    assert [row["count"] for row in payload["collections"]] == [8, 8, 8]


def test_featured_collections_precede_the_generic_starter_shelf():
    source = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")
    collection = source.index("{ tag: 'candy',")
    starter = source.index("STARTER SHELF <span>")
    assert collection < starter
    assert "Number(row.overallQuality || 0) >= 85" in source
    assert "row.priority === 'FIX'" in source

