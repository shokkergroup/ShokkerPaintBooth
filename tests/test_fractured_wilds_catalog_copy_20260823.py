"""Buyer-facing catalog guardrails for the 2026-08-23 Wilds rebuild."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wilds_catalog_has_all_110_unique_finish_descriptions_without_macro_copy():
    source = (ROOT / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
    rows = re.findall(
        r'^\s*\{ id: "((?:fc|fmo|fbl|fpe)_[^"]+)", name: "[^"]+", desc: "([^"]+)"',
        source,
        flags=re.MULTILINE,
    )
    assert len(rows) == 110
    assert len({finish_id for finish_id, _ in rows}) == 110

    # The owner's fine-feature doctrine is 8--32 px at 2048. Do not let old
    # macro-pattern promises creep back into the buyer-facing descriptions.
    banned = re.compile(r"\b(?:huge|large|broad|chunky|massive|great)\b", re.IGNORECASE)
    offenders = {finish_id: desc for finish_id, desc in rows if banned.search(desc)}
    assert offenders == {}


def test_all_110_wilds_catalog_swatches_are_canonical_six_digit_hex():
    source = (ROOT / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
    rows = re.findall(
        r'^\s*\{ id: "((?:fc|fmo|fbl|fpe)_[^"]+)", name: "[^"]+", '
        r'desc: "[^"]+", swatch: "([^"]+)" \},',
        source,
        flags=re.MULTILINE,
    )
    assert len(rows) == 110
    assert len({finish_id for finish_id, _ in rows}) == 110

    invalid = {
        finish_id: swatch
        for finish_id, swatch in rows
        if re.fullmatch(r"#[0-9a-fA-F]{6}", swatch) is None
    }
    assert invalid == {}


def test_wilds_atlas_promises_structural_identity_and_real_angle_color_flip():
    source = (ROOT / "js" / "spb-finish-atlas.js").read_text(encoding="utf-8")
    for category in (
        "👣 FRACTURED CRYPTID",
        "🦋 FRACTURED MORPHO",
        "🌸 FRACTURED BLOOM",
        "🧫 FRACTURED PETRI",
        "🌿 FRACTURED WILDS",
    ):
        match = re.search(rf"'{re.escape(category)}': '([^']+)'", source)
        assert match, category
        description = match.group(1).lower()
        assert any(word in description for word in ("fine", "micro")), category
        assert "angle" in description, category
        assert any(word in description for word in ("flip", "exchange", "trade")), category
