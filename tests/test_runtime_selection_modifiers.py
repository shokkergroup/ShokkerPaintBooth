"""Legacy selection APIs must use real mask history through the shared engine."""
import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
FUNCS = ("growSelection", "shrinkSelection", "smoothSelection")

@pytest.fixture(scope="module")
def harness():
    result = subprocess.run(
        ["node", "tests/_runtime_harness/selection_modifiers.mjs"],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(result.stdout)

@pytest.mark.parametrize("func", FUNCS)
def test_legacy_modifier_captures_exact_mask_before_one_commit(harness, func):
    result = harness[func]["changed"]
    assert result["changed"] and result["committed"]
    assert result["history"] == [{"index": 0, "mask": result["original"]}]
    assert result["wrongHistory"] == []

@pytest.mark.parametrize("func", FUNCS)
def test_legacy_modifier_noop_preserves_mask_and_history(harness, func):
    result = harness[func]["empty"]
    assert not result["changed"] and not result["committed"]
    assert result["history"] == []
    assert result["wrongHistory"] == []
