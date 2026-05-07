from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image

from engine.expansions import owner_review_atmosphere


OWNER_CONFIRMED_ATMOSPHERE_REBUILD_IDS = [
    "acid_rain",
    "black_ice",
    "blizzard",
    "desert_mirage",
    "dew_drop",
    "dust_storm",
    "ember_glow",
    "fog_bank",
    "frost_bite",
    "frozen_lake",
    "hail_damage",
    "heat_wave",
    "hurricane",
    "lightning_strike",
    "liquid_metal",
    "magma_flow",
    "meteor_shower",
    "monsoon",
    "ocean_floor",
    "oil_slick",
    "permafrost",
    "solar_wind",
    "tidal_wave",
    "tornado_alley",
    "volcanic_glass",
]


def test_owner_confirmed_atmosphere_specials_have_paint_spec_detail_and_budget():
    from scripts import spb_visual_workbench

    out_dir = Path(".pytest-tmp") / "atmosphere_owner_review"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_ATMOSPHERE_REBUILD_IDS),
        "--kind",
        "monolithic",
        "--size",
        "96",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_ATMOSPHERE_REBUILD_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert max(row["render_ms"] for row in rows) < 450.0
    assert min(row["paint_luma_std"] for row in rows) > 0.010
    assert min(row["fine_energy"] for row in rows) > 0.004
    assert min(row["color_population"] for row in rows) >= 3
    assert min(row["spec_m_range"] for row in rows) >= 45.0
    assert min(row["spec_r_range"] for row in rows) >= 35.0

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.997


def test_owner_confirmed_atmosphere_respects_zone_mask():
    shape = (64, 64)
    paint = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    paint[:, :, 0] = 0.22
    paint[:, :, 1] = 0.34
    paint[:, :, 2] = 0.46
    mask = np.zeros(shape, dtype=np.float32)
    mask[16:48, 16:48] = 1.0
    outside = mask < 0.5

    for finish_id, (_, paint_fn) in owner_review_atmosphere.OWNER_REVIEW_ATMOSPHERE_MONOLITHICS.items():
        rendered = paint_fn(paint.copy(), shape, mask, seed=7301, pm=1.0, bb=0.0)
        np.testing.assert_allclose(
            rendered[outside],
            paint[outside],
            atol=1e-6,
            err_msg=f"{finish_id} changed paint outside the zone mask",
        )
