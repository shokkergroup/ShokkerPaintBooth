from __future__ import annotations

import json
from pathlib import Path


PARADIGM_MASTERCLASS_BASE_IDS = [
    "p_superfluid",
    "p_coronal",
    "p_seismic",
    "p_hypercane",
    "p_geomagnetic",
    "p_non_euclidean",
    "p_time_reversed",
    "p_programmable",
    "p_erised",
    "p_schrodinger",
]


def test_paradigm_masterclass_bases_are_detailed_and_spec_dynamic():
    from scripts import spb_visual_workbench

    out_dir = Path(".pytest-tmp") / "paradigm_masterclass_bases"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(PARADIGM_MASTERCLASS_BASE_IDS),
        "--kind",
        "base",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0

    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(PARADIGM_MASTERCLASS_BASE_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.030
    assert min(row["residual_energy"] for row in rows) > 0.014
    assert min(
        row["spec_m_range"] + row["spec_r_range"] + row["spec_cc_range"]
        for row in rows
    ) >= 285.0
    assert min(max(row["spec_m_range"], row["spec_r_range"], row["spec_cc_range"]) for row in rows) >= 115.0
    assert min(row["spec_r_range"] for row in rows) >= 115.0
    assert min(row["spec_cc_range"] for row in rows) >= 65.0
