"""Integrity contracts for the 25-finish Neon evidence slate and live adapters."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

from engine.paint_v2 import surface_intent
from scripts import spb_workbook_compute_m6
from scripts.spb_neon_oil_slick_pilot_m7 import CANDIDATES


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "_neon_oil_slick_reset_work"
EXPECTED_KEYS = (
    "base:neon_electric_blue",
    "base:neon_orange_hazard",
    "base:neon_red_alert",
    "monolithic:neon2_quarter_mile_weave",
    "monolithic:neon2_torque_scar",
    "base:neon_blacklight",
    "monolithic:neon2_phantom_mica",
    "monolithic:neon2_frequency_fault",
    "base:neon_cyber_yellow",
    "base:neon_dual_glow",
    "base:neon_ice_white",
    "monolithic:neon2_emberwake_delam",
    "base:neon_pink_blaze",
    "base:neon_rainbow_tube",
    "base:neon_toxic_green",
    "monolithic:neon2_sign_tubes",
    "monolithic:neon2_circuit_city",
    "monolithic:neon2_rain",
    "monolithic:neon2_laser_web",
    "monolithic:neon2_splatter",
    "monolithic:neon2_wireframe",
    "monolithic:neon2_plasma_tubes",
    "monolithic:neon2_honeycomb",
    "monolithic:neon2_flow_tubes",
    "monolithic:neon2_synthwave_sun",
)


def _json(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_isolated_slate_has_exactly_25_importable_unique_routes() -> None:
    assert tuple(candidate["key"] for candidate in CANDIDATES) == EXPECTED_KEYS
    assert len({candidate["slug"] for candidate in CANDIDATES}) == 25
    for candidate in CANDIDATES:
        module = importlib.import_module(candidate["module"])
        assert callable(getattr(module, candidate["builder"]))


def test_historical_isolated_slate_evidence_and_official_m7_remain_immutable() -> None:
    m7 = _json("official_isolated_m7.json")
    review = _json("slate_review.json")

    # These are historical, pre-promotion evidence records. Their unwired flags
    # remain true for that run even though the same builders are live now.
    assert m7["status"] == "ISOLATED-OWNER-REVIEW-NOT-WIRED"
    assert m7["shipping_state_changed"] is False
    assert m7["all_pass_85"] is True
    assert set(m7["byFinish"]) == set(EXPECTED_KEYS)
    assert all(row["composite"] >= 85.0 for row in m7["byFinish"].values())

    assert review["candidate_count"] == 25
    assert review["unique_finish_ids"] is True
    assert review["all_evidence_complete"] is True
    assert review["all_mechanical_green"] is True
    assert review["all_official_isolated_m7_ge_85"] is True
    assert review["shipping_state_changed"] is False
    assert review["mapped_car_proof"].startswith("PENDING")


def test_neon_v3_is_dead_last_authority_on_every_live_selection_route() -> None:
    from engine.expansions.neon_catalog_2026 import BASE_IDS, LIVE_PAIRS, MONOLITHIC_IDS
    from engine.registry import BASE_REGISTRY, FUSION_REGISTRY, MONOLITHIC_REGISTRY

    assert len(BASE_IDS) == 10
    assert len(LIVE_PAIRS) == 25
    assert len(MONOLITHIC_IDS) == 15
    assert all(BASE_REGISTRY[fid]["paint_fn"] is LIVE_PAIRS[fid][1] for fid in BASE_IDS)
    assert all(MONOLITHIC_REGISTRY[fid] is LIVE_PAIRS[fid] for fid in LIVE_PAIRS)
    assert all(FUSION_REGISTRY[fid] is LIVE_PAIRS[fid] for fid in MONOLITHIC_IDS)


def test_neon_metric_contract_matches_the_causal_fine_structure_intent() -> None:
    assert surface_intent.get_intent("Neon") == surface_intent.FINE_STRUCTURAL_COLOR
    assert spb_workbook_compute_m6.CATEGORY_PROFILES["Neon"] == {
        "paintColorPopulation": spb_workbook_compute_m6.HI,
        "paintSaturationMean": spb_workbook_compute_m6.HI,
        "specRRange": spb_workbook_compute_m6.HI,
        "specCcRange": spb_workbook_compute_m6.HI,
    }
