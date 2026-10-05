from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.spb_refresh_wilds_shipping_scorecard import CATEGORY_BY_PREFIX, _scorecard_parts
from scripts.spb_workbook_compute_m6 import CATEGORY_PROFILES
from scripts.spb_workbook_compute_m7 import WEIGHTS
from engine.paint_v2.surface_intent import CATEGORY_INTENT, FINE_STRUCTURAL_COLOR


ROOT = Path(__file__).resolve().parents[1]


def test_shipping_scorecard_carries_the_exact_wilds_110_category_census():
    _header, scorecard, _tail = _scorecard_parts(ROOT / "paint-booth-0-catalog-scorecard.js")
    expected = {
        "👣 FRACTURED CRYPTID": 20,
        "🦋 FRACTURED MORPHO": 50,
        "🌸 FRACTURED BLOOM": 20,
        "🧫 FRACTURED PETRI": 20,
    }
    actual = {category: 0 for category in expected}
    ids = []
    for key, entry in scorecard.items():
        if not key.startswith("monolithic:"):
            continue
        finish_id = key.split(":", 1)[1]
        if any(finish_id.startswith(prefix) for prefix in CATEGORY_BY_PREFIX):
            ids.append(finish_id)
            actual[entry.get("category")] = actual.get(entry.get("category"), 0) + 1
            for field in (
                "paintFineEnergy", "paintColorPopulation", "specMRange",
                "specRRange", "specCcRange", "specChannelIndependence",
            ):
                assert isinstance(entry.get(field), (int, float)), (finish_id, field)
    assert len(ids) == len(set(ids)) == 110
    assert actual == expected


def test_wilds_scorecard_refresh_command_is_fixed_to_standard_512_audit_size():
    source = (ROOT / "scripts" / "spb_refresh_wilds_shipping_scorecard.py").read_text(
        encoding="utf-8"
    )
    assert re.search(r"AUDIT_SIZE\s*=\s*512", source)
    assert "if args.size != AUDIT_SIZE" in source


def test_cryptid_shipping_category_has_the_same_structural_color_intent_contract():
    assert CATEGORY_PROFILES["👣 FRACTURED CRYPTID"] == {
        "specCcRange": "HI",
        "specChannelIndependence": "HI",
    }


def test_wilds_use_fine_structural_color_without_spec_thumbnail_or_clone_exemption():
    categories = (
        "👣 FRACTURED CRYPTID", "🦋 FRACTURED MORPHO",
        "🌸 FRACTURED BLOOM", "🧫 FRACTURED PETRI",
    )
    assert all(CATEGORY_INTENT[category] == FINE_STRUCTURAL_COLOR for category in categories)
    assert WEIGHTS[FINE_STRUCTURAL_COLOR] == {"m5": 0.375, "m6": 0.625}
