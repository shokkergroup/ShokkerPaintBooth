"""Regression proof for Easy Whole Car's browser -> preview -> engine bridge.

The browser payload was correct, but ``/preview-render`` rebuilt each zone from
an older allowlist and silently discarded the four material-mix fields.  This
test exercises the real Flask route and captures exactly what reaches the
engine boundary.
"""

from __future__ import annotations

import numpy as np
import pytest


def test_preview_route_preserves_whole_car_material_stack(
    app_client, server_module, tmp_paint_file, monkeypatch
):
    captured = {}

    def fake_preview_render(_paint_file, zones, **_kwargs):
        captured["zones"] = zones
        paint = np.zeros((8, 8, 3), dtype=np.uint8)
        spec = np.zeros((8, 8, 4), dtype=np.uint8)
        return paint, spec, 1.0

    monkeypatch.setattr(server_module.engine, "preview_render", fake_preview_render)

    response = app_client.post(
        "/preview-render",
        json={
            "paint_file": tmp_paint_file,
            "preview_scale": 0.25,
            "seed": 51,
            "zones": [
                {
                    "name": "Whole Car · Chrome + Candy",
                    "color": "everything",
                    "intensity": "100",
                    "material_stack": [
                        {"id": "chrome", "registry_type": "base", "weight": 1 / 3},
                        {"id": "candy", "registry_type": "base", "weight": 2 / 3},
                    ],
                    "material_stack_mode": "auto_trace",
                    "material_stack_amount": 0.75,
                    "material_scale": 0.6,
                }
            ],
        },
    )

    assert response.status_code == 200, response.get_json(silent=True)
    assert len(captured["zones"]) == 1
    zone = captured["zones"][0]
    assert zone["material_stack"] == [
        {"id": "chrome", "registry_type": "base", "weight": pytest.approx(1 / 3)},
        {"id": "candy", "registry_type": "base", "weight": pytest.approx(2 / 3)},
    ]
    assert zone["material_stack_mode"] == "auto_trace"
    assert zone["material_stack_amount"] == pytest.approx(0.75)
    assert zone["material_scale"] == pytest.approx(0.6)
    assert "base" not in zone and "finish" not in zone

