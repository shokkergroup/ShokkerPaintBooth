"""Fail-closed Neon Underground v4 visual/material/live-contract gates."""
from __future__ import annotations

from functools import lru_cache
import importlib
import inspect
import json
from pathlib import Path
import re

import cv2
import numpy as np

from engine.expansions.neon_catalog_2026 import BASE_IDS, NEON_FINISHES
from engine.expansions.neon_underground_v4.catalog import CATALOG, ORDER, module_name


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def _built(finish_id: str):
    return importlib.import_module(module_name(finish_id)).build()


def _structure(image: np.ndarray) -> np.ndarray:
    rgb = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    thumb = cv2.resize(lum, (48, 48), interpolation=cv2.INTER_AREA)
    thumb -= thumb.mean()
    return (thumb / max(float(np.linalg.norm(thumb)), 1e-7)).ravel()


def test_v4_catalog_and_live_adapter_are_one_exact_25_finish_contract():
    assert len(ORDER) == len(set(ORDER)) == 25
    assert tuple(CATALOG) == ORDER
    assert tuple(NEON_FINISHES) == ORDER
    assert len({row[1] for row in CATALOG.values()}) == 25
    for finish_id in ORDER:
        stem, name, swatch, desc = CATALOG[finish_id]
        live = NEON_FINISHES[finish_id]
        assert live == (module_name(finish_id), "build", name, swatch, desc)
        module = importlib.import_module(module_name(finish_id))
        assert module.__name__.endswith("." + stem)
        assert callable(module.build)


def test_v4_user_facing_rows_use_the_authored_names_and_swatches():
    source = (ROOT / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
    for finish_id in ORDER:
        _stem, name, swatch, _desc = CATALOG[finish_id]
        rows = re.findall(
            rf'\{{\s*id:\s*"{re.escape(finish_id)}"[^\n]+\}}', source,
        )
        assert rows
        assert any(f'name: "{name}"' in row and f'swatch: "{swatch}"' in row for row in rows)


def test_v4_shipping_scorecard_promotes_the_official_all_pass_m7_proof():
    report = json.loads(
        (ROOT / "_neon_v4_work" / "official_m7" / "report.json").read_text(encoding="utf-8")
    )
    assert report["all_pass_85"] is True

    source = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\});", source, flags=re.S)
    assert match is not None
    scorecard = json.loads(re.sub(r"//[^\n]*", "", match.group(1)))

    for finish_id in ORDER:
        key = ("base:" if finish_id in BASE_IDS else "monolithic:") + finish_id
        proof = report["byFinish"][key]
        row = scorecard[key]
        expected = int(round(float(proof["composite"])))
        assert proof["pass_85"] is True
        assert row["status"] == "OK"
        assert row["priority"] == "PASS"
        assert row["reasonFlags"] == ""
        assert row["overallQuality"] == expected
        assert row["paintQuality"] == expected
        assert row["specQuality"] == expected
        assert row["m7Composite"] == proof["composite"]
        assert row["m7Pass85"] is True


def test_v4_uses_no_quantile_equalization_or_v3_renderer_imports():
    for finish_id in ORDER:
        module = importlib.import_module(module_name(finish_id))
        source = inspect.getsource(module)
        assert "neon_underground_v3" not in source
        assert "np.quantile(" not in source
        assert "np.percentile(" not in source


def test_v4_all25_have_neon_presence_broad_hierarchy_and_physical_spec():
    structures = {}
    for finish_id in ORDER:
        result = _built(finish_id)
        assert result.finish_id == finish_id
        assert result.paint.shape == result.paint_b.shape == result.spec.shape == (1024, 1024, 3)
        assert result.paint.dtype == result.paint_b.dtype == np.float32
        assert result.spec.dtype == np.uint8
        assert result.elapsed_seconds <= 3.0

        saturation = result.paint.max(axis=2) - result.paint.min(axis=2)
        value = result.paint.max(axis=2)
        assert float(np.mean((saturation > 0.35) & (value > 0.22))) >= 0.01
        lum = result.paint.mean(axis=2).astype(np.float32)
        broad = cv2.GaussianBlur(lum, (0, 0), 30.0)
        assert float(np.std(broad) / max(float(np.std(lum)), 1e-7)) >= 0.35

        fine = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 3.0))
        gy, gx = np.gradient(lum)
        gradient = np.sqrt(gx * gx + gy * gy)
        active_rows = []
        for top in range(0, 1024, 64):
            row = []
            for left in range(0, 1024, 64):
                region = np.s_[top:top + 64, left:left + 64]
                row.append(bool(
                    float(np.std(lum[region])) > 0.006
                    and (float(np.mean(fine[region])) > 0.0015
                         or float(np.mean(gradient[region])) > 0.0035)
                ))
            active_rows.append(row)
        active = np.asarray(active_rows, np.uint8)
        assert float(np.mean(active)) >= 0.55
        components, _labels, stats, _centroids = cv2.connectedComponentsWithStats(1 - active, 8)
        largest_dead = int(stats[1:, cv2.CC_STAT_AREA].max()) if components > 1 else 0
        assert float(largest_dead / active.size) <= 0.30

        angle_delta = float(np.mean(np.abs(result.paint - result.paint_b)))
        assert angle_delta >= 0.045
        for channel in range(3):
            values, counts = np.unique(result.spec[..., channel], return_counts=True)
            shares = counts.astype(np.float64) / counts.sum()
            assert len(values) >= 8
            assert float(np.std(result.spec[..., channel])) >= 20.0
            # Fixed physical thresholds must retain organic, unequal populations.
            assert float(np.max(shares) - np.min(shares)) >= 0.02
        structures[finish_id] = _structure(result.paint)

    worst = -1.0
    for index, finish_a in enumerate(ORDER):
        for finish_b in ORDER[index + 1:]:
            worst = max(worst, float(np.dot(structures[finish_a], structures[finish_b])))
    assert worst < 0.75
