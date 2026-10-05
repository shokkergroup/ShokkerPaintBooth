from __future__ import annotations

import cv2
import json
import numpy as np

from scripts.spb_finish_identity import (
    validate_identity_contract,
    validate_identity_key_uniqueness,
)
from scripts.spb_iridescent_insects_similarity_gate import _identity_similarity


def _pattern(size: int = 256) -> np.ndarray:
    image = np.zeros((size, size, 3), np.uint8)
    for y in range(0, size, 32):
        for x in range(0, size, 32):
            value = 70 + ((x // 32 + y // 32) % 4) * 50
            cv2.ellipse(image, (x + 11, y + 17), (7, 3), (x - y) % 180, 0, 360,
                        (value, 255 - value, 40 + value // 2), -1)
            cv2.line(image, (x + 2, y + 4), (x + 27, y + 25),
                     (255 - value, 30 + value // 2, value), 2)
    return image


def _contract() -> dict:
    marks = [
        {"name": "facet", "role": "forms the nested optical chamber"},
        {"name": "seam", "role": "separates adjacent hard shell plates"},
        {"name": "pore", "role": "anchors a dark respiratory opening"},
        {"name": "rail", "role": "routes the photogenic capillary"},
        {"name": "rim", "role": "catches the wet cuticle highlight"},
    ]
    return {
        "schema": "spb-finish-identity/1",
        "finish_id": "test_finish",
        "display_name": "Test Lantern Armor",
        "promise": "Faceted lantern chambers interrupt a hard plated shell.",
        "reference_physics": {
            "mechanism": "Layered photogenic tissue and reflecting urate bodies shape emission.",
            "sources": ["peer-reviewed light-organ morphology paper"],
        },
        "carrier_grammar": "Interlocked chambers nested inside offset abdominal plates.",
        "spec_grammar": "Each chamber layer owns a different response while shell seams stay dry.",
        "native_scale_px": [8, 30],
        "mark_types": marks,
        "material_binding": {
            "M": ["facet", "seam"],
            "R": ["pore", "rail"],
            "Cc": ["rim", "facet"],
        },
        "material_tiers": ["soot", "satin", "amber", "copper", "wet", "quenched"],
        "nearest_neighbors": [
            {"finish_id": "firefly_lantern", "difference": "plates replace complete glyph modules"},
            {"finish_id": "beetle_click", "difference": "no bead trains or circular lantern organs"},
        ],
        "name_truth": {
            "visible_evidence": ["faceted chambers", "hard shell seams", "photogenic rails"],
            "hidden_title_verdict": "pass",
        },
        "construction_key": "offset-shell-nested-chambers",
        "spec_key": "chamber-layer-shell-seam-binding",
    }


def test_contract_requires_name_bound_anatomy_and_material_ownership():
    assert validate_identity_contract(_contract(), "test_finish").ok
    broken = _contract()
    broken["material_binding"] = {"M": ["facet"], "R": ["facet"], "Cc": ["facet"]}
    verdict = validate_identity_contract(broken, "test_finish")
    assert not verdict.ok
    assert any("every named paint feature" in error for error in verdict.errors)


def test_contract_keys_cannot_reuse_another_finish(tmp_path):
    accepted = _contract()
    accepted["finish_id"] = "accepted_finish"
    path = tmp_path / "identity_contract.json"
    path.write_text(json.dumps(accepted), encoding="utf-8")
    verdict = validate_identity_key_uniqueness(_contract(), [path])
    assert not verdict.ok
    assert any("construction_key duplicates" in error for error in verdict.errors)
    assert any("spec_key duplicates" in error for error in verdict.errors)


def test_palette_and_spec_channel_swaps_are_the_same_design():
    original = _pattern()
    palette_swap = original[..., [2, 0, 1]]
    result = _identity_similarity(original, palette_swap)
    assert result.transformed >= 0.97


def test_rotation_and_phase_shift_are_the_same_design():
    original = _pattern()
    rotated = np.rot90(original)
    shifted = np.roll(original, (64, 96), axis=(0, 1))
    assert _identity_similarity(original, rotated).transformed >= 0.97
    assert _identity_similarity(original, shifted).phased >= 0.97


def test_unrelated_constructions_do_not_trip_exact_copy_gate():
    original = _pattern()
    other = np.zeros_like(original)
    for x in range(8, 256, 24):
        cv2.circle(other, (x, (x * 7) % 241 + 7), 5 + (x // 24) % 4,
                   (20 + x % 200, 240 - x % 180, 100), -1)
    result = _identity_similarity(original, other)
    assert result.transformed < 0.97
    assert result.phased < 0.97
