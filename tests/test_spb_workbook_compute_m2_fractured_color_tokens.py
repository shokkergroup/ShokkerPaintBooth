from scripts.spb_workbook_compute_m2 import token_applies_to_category


def test_fractured_bloom_and_petri_ignore_ordinary_color_name_intent():
    for category in (
        "👣 FRACTURED CRYPTID", "🦋 FRACTURED MORPHO",
        "🌸 FRACTURED BLOOM", "🧫 FRACTURED PETRI",
    ):
        for token in ("white", "rose", "amber", "gold", "black"):
            assert token_applies_to_category(token, category) is False


def test_explicit_wilds_recipe_contract_supersedes_generic_structural_tokens():
    for category in (
        "👣 FRACTURED CRYPTID", "🦋 FRACTURED MORPHO",
        "🌸 FRACTURED BLOOM", "🧫 FRACTURED PETRI",
    ):
        assert token_applies_to_category("flake", category) is False
        assert token_applies_to_category("fracture", category) is False
        assert token_applies_to_category("dust", category) is False


def test_color_name_intent_still_applies_outside_fractured_bloom_and_petri():
    assert token_applies_to_category("white", "Surface & Grain") is True
    assert token_applies_to_category("amber", "Prizm") is True
