from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts import spb_wilds_retained_manifest_gate as gate


def _candidate_fixture(tmp_path: Path, suffix: str):
    root = tmp_path / suffix
    root.mkdir(parents=True, exist_ok=True)
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    for index in range(5):
        (evidence / f"contact_{index}.png").write_bytes(b"contact")
    (evidence / "evidence.json").write_text("{}\n", encoding="utf-8")
    verdict = root / "verdict.md"
    verdict.write_text(
        "KEEP-CANDIDATE. This is not owner acceptance and not production wiring.\n",
        encoding="utf-8",
    )
    scale = root / "scale.json"
    semantic = [
        {"name": f"mark_{index}", "owner_8_32_local_scale_pass": True}
        for index in range(5)
    ]
    scale.write_text(json.dumps({
        "ids": {
            "fmo_exact": {
                "mark_count": 5,
                "semantic_marks": semantic,
                "owner_feature_scale": {"pass": True},
                "spec": {
                    "M": {"std": 44}, "R": {"std": 55}, "Cc": {"std": 66},
                },
            },
        },
    }), encoding="utf-8")
    buyer = root / "fmo_exact_buyer96x48.png"
    assert cv2.imwrite(str(buyer), np.zeros((48, 96, 3), np.uint8))
    row = {
        "id": "fmo_exact",
        "family": "morpho_bio",
        "module": "fake.module",
        "ids_attr": "IDS",
        "wave": "TEST",
        "evidence_dir": str(evidence),
        "feature_scale_evidence": str(scale),
        "buyer_evidence": str(buyer),
        "verdict": str(verdict),
        "reservation": "one exclusive exact topology",
    }
    return row, scale


def test_current_retained_manifest_frozen_integrity_is_green():
    report = gate.validate_manifest(gate.DEFAULT_MANIFEST, import_modules=False)
    assert report["candidate_count"] == 1
    assert report["owner_accepted"] is False
    assert report["production_wired"] is False
    assert report["gate_reports"]["retained_pairs"] == 0


def test_candidate_scale_evidence_binds_exact_id(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    row, scale_path = _candidate_fixture(tmp_path, "bind_exact")
    result = gate._validate_candidate(row, 0, import_modules=False)
    assert result["owner_feature_scale_pass"] is True

    payload = json.loads(scale_path.read_text(encoding="utf-8"))
    payload["ids"] = {"fmo_other": next(iter(payload["ids"].values()))}
    scale_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="bind exactly this ID"):
        gate._validate_candidate(row, 0, import_modules=False)


def test_candidate_rejects_any_failed_local_mark(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    row, scale_path = _candidate_fixture(tmp_path, "failed_mark")
    payload = json.loads(scale_path.read_text(encoding="utf-8"))
    payload["ids"]["fmo_exact"]["semantic_marks"][2][
        "owner_8_32_local_scale_pass"
    ] = False
    scale_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="feature-scale failures: mark_2"):
        gate._validate_candidate(row, 0, import_modules=False)


def test_candidate_requires_literal_96x48_buyer_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    row, _scale_path = _candidate_fixture(tmp_path, "buyer_shape")
    assert cv2.imwrite(row["buyer_evidence"], np.zeros((64, 64, 3), np.uint8))
    with pytest.raises(ValueError, match="literal 96x48"):
        gate._validate_candidate(row, 0, import_modules=False)


def test_candidate_live_module_requires_exact_id_and_literal_ab(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    row, _scale_path = _candidate_fixture(tmp_path, "live_module")
    mask = np.ones((16, 16), np.float32)
    grammar = SimpleNamespace(marks=tuple(
        (f"mark_{index}", mask, "A" if index < 3 else "B")
        for index in range(5)
    ))
    fake = SimpleNamespace(
        IDS=("fmo_exact",),
        debug_grammar=lambda _fid: grammar,
        _authored=lambda _fid: (
            np.zeros((16, 16, 3), np.float32),
            np.zeros((16, 16, 3), np.uint8),
        ),
    )
    monkeypatch.setattr(gate.importlib, "import_module", lambda _name: fake)
    result = gate._validate_candidate(row, 0, import_modules=True)
    assert result["banks"] == ["A", "B"]
    assert result["buyer_evidence_exact_96x48"] is True

    assert cv2.imwrite(row["buyer_evidence"], np.full((48, 96, 3), 255, np.uint8))
    with pytest.raises(ValueError, match="buyer evidence is stale"):
        gate._validate_candidate(row, 0, import_modules=True)
    assert cv2.imwrite(row["buyer_evidence"], np.zeros((48, 96, 3), np.uint8))

    fake.IDS = ("fmo_other",)
    with pytest.raises(ValueError, match="absent from"):
        gate._validate_candidate(row, 0, import_modules=True)


def test_manifest_refuses_owner_acceptance_claim_before_any_art_checks(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema": "spb-wilds-retained/1",
        "owner_accepted": True,
        "production_wired": False,
        "candidates": [{}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="owner_accepted=false"):
        gate.validate_manifest(manifest, import_modules=False)
