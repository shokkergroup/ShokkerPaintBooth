from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts import spb_wilds_global_catalog_collision_audit as audit
from scripts import spb_wilds_candidate_collision_audit as candidate_audit
from scripts import spb_wilds_retained_picker_contact as picker_contact
from scripts.spb_wilds_explicit_rebuild_evidence import _local_thickness_stats


def _write_thumb(path: Path, value: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((24, 24, 3), value, np.uint8)
    cv2.line(image, (2, 3), (21, 18), (255 - value,) * 3, 2, cv2.LINE_AA)
    assert cv2.imwrite(str(path), image)


def test_catalog_rows_excludes_old_wilds_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    _write_thumb(tmp_path / "thumbnails" / "base" / "ordinary.png", 50)
    _write_thumb(tmp_path / "thumbnails" / "base" / "fc_old_wilds.png", 90)

    rows = audit._catalog_rows(("base",), include_wilds=False)
    assert [row["stem"] for row in rows] == ["ordinary"]

    rows = audit._catalog_rows(("base",), include_wilds=True)
    assert {row["stem"] for row in rows} == {"ordinary", "fc_old_wilds"}


def test_manifest_fails_closed_on_unknown_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema": "wrong", "candidates": []}),
                    encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported candidate manifest schema"):
        audit._manifest_candidates(path)


def test_manifest_binds_exact_id_to_declared_module(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    paint = np.zeros((32, 32, 3), np.float32)
    paint[::2, :, 0] = 1.0
    fake = SimpleNamespace(
        IDS=("fpe_exact",),
        clear_cache=lambda: None,
        _authored=lambda _fid: (paint, np.zeros((32, 32, 3), np.uint8)),
        debug_hue_null=lambda _fid: paint,
    )
    monkeypatch.setattr(audit.importlib, "import_module", lambda _name: fake)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "schema": "spb-wilds-retained/1",
        "candidates": [{
            "id": "fpe_exact", "module": "fake.module", "ids_attr": "IDS",
        }],
    }), encoding="utf-8")

    resolved, rows = audit._manifest_candidates(path)
    assert resolved == path
    assert [row["id"] for row in rows] == ["fpe_exact"]

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidates"][0]["id"] = "fpe_missing"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="absent from"):
        audit._manifest_candidates(path)


def test_local_thickness_gate_distinguishes_fine_marks_from_macro_fills():
    fine = np.zeros((512, 512), np.float32)
    cv2.line(fine, (16, 256), (496, 256), 1.0, 2, cv2.LINE_8)
    macro = np.zeros_like(fine)
    cv2.rectangle(macro, (40, 200), (472, 240), 1.0, -1)

    fine_stats = _local_thickness_stats(fine)
    macro_stats = _local_thickness_stats(macro)
    assert fine_stats["owner_8_32_local_scale_pass"] is True
    assert 7.5 <= fine_stats["local_thickness_native_px_p50"] <= 16.0
    assert macro_stats["owner_8_32_local_scale_pass"] is False
    assert macro_stats["local_thickness_native_px_p90"] > 32.5


def test_small_candidate_contact_has_no_unused_black_columns():
    cards = [np.full((24, 18, 3), index * 20, np.uint8) for index in range(4)]
    contact = candidate_audit._contact(cards, columns=10)
    assert contact.shape == (24, 4 * 18, 3)

    with pytest.raises(ValueError, match="empty Wilds contact"):
        candidate_audit._contact([], columns=10)


def test_buyer_picker_reconstruction_preserves_actual_two_to_one_card():
    image = np.zeros((32, 32, 3), np.float32)
    image[:, :, 1] = 1.0
    display = picker_contact._display_reconstruction(image, 96, 48)
    assert display.shape == (picker_contact.CARD, picker_contact.CARD, 3)
    assert float(display[:30].max()) < 0.05
    center = display[picker_contact.CARD // 2 - 10:picker_contact.CARD // 2 + 10]
    assert float(center[:, :, 1].mean()) > 0.95
