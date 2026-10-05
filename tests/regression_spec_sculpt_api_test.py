"""Spec Sculpt Lab HTTP API contracts (preview sizes, progressive preview)."""

from __future__ import annotations

import json


def test_spec_sculpt_preview_progressive_returns_both_sizes(app_client, tmp_paint_file, clean_caches):
    body = {
        "paint_file": tmp_paint_file.replace("\\", "/"),
        "iracing_id": "23371",
        "save_tga": False,
        "preview_progressive": True,
        "strict2048": False,
        "chromatic_shift": True,
        "use_custom_number": True,
        "seed": 42,
    }
    r = app_client.post(
        "/api/spec-sculpt/generate",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j.get("success") is True
    assert "previews_by_size" in j
    pbs = j["previews_by_size"]
    assert "512" in pbs and "1024" in pbs
    assert pbs["512"].get("composite")
    assert pbs["1024"].get("composite")
    prev = j.get("previews") or {}
    assert prev.get("composite")
    assert j.get("working_resolution") == [1024, 1024]


def test_spec_sculpt_preview_single_size_ignores_progressive_when_save_tga(
    app_client, tmp_paint_file, clean_caches
):
    body = {
        "paint_file": tmp_paint_file.replace("\\", "/"),
        "iracing_id": "23371",
        "save_tga": True,
        "preview_progressive": True,
        "strict2048": False,
        "chromatic_shift": True,
        "use_custom_number": True,
        "seed": 99,
    }
    r = app_client.post(
        "/api/spec-sculpt/generate",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j.get("success") is True
    assert j.get("previews_by_size") is None
    assert j.get("job_id")
