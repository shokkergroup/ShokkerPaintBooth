from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_finish_visual_audit_smoke_generates_reports():
    from scripts import finish_visual_audit

    out_dir = Path(".pytest-tmp") / "finish_visual_audit_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = finish_visual_audit.main([
        "--ids",
        "cx_hyperflip_red_blue,hex_mandala,micro_sparkle",
        "--size",
        "64",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    report = out_dir / "report.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["count"] == 3
    assert {row["id"] for row in payload["rows"]} == {
        "cx_hyperflip_red_blue",
        "hex_mandala",
        "micro_sparkle",
    }
    assert (out_dir / "contact_sheet.png").exists()
    assert (out_dir / "spec_sheet.png").exists()


def test_runtime_sync_has_no_leftover_temp_artifacts():
    tmp_files = list(Path("electron-app/server").rglob("*.tmp-*"))
    assert tmp_files == []


def test_root_temp_junk_cleanup_is_narrow_and_effective():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "cleanup-root-temp-junk.py"
    victim = root / "ZzTst_01"
    wrong_content = root / "ZzTst_02"
    wrong_suffix = root / "ZzTst03.txt"
    for path in (victim, wrong_content, wrong_suffix):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        victim.write_text("blat", encoding="utf-8")
        wrong_content.write_text("keep", encoding="utf-8")
        wrong_suffix.write_text("blat", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(script), "--delete"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        assert "ZzTst_01" in result.stdout
        assert not victim.exists()
        assert wrong_content.exists()
        assert wrong_suffix.exists()
    finally:
        for path in (victim, wrong_content, wrong_suffix):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def test_spec_pattern_quality_gate_clears_shipping_catalog():
    from scripts import audit_spec_pattern_quality

    out_dir = Path(".pytest-tmp") / "spec_pattern_quality_gate"
    rc = audit_spec_pattern_quality.main([
        "--size",
        "160",
        "--threshold",
        "96",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert payload["count"] >= 250
    assert payload["threshold"] == 96.0
    assert payload["rebuild_required_count"] == 0


def test_regular_pattern_quality_gate_clears_shipping_catalog():
    from scripts import audit_pattern_quality

    out_dir = Path(".pytest-tmp") / "regular_pattern_quality_gate"
    rc = audit_pattern_quality.main([
        "--size",
        "160",
        "--threshold",
        "88",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert payload["count"] >= 300
    assert payload["threshold"] == 88.0
    assert payload["rebuild_required_count"] == 0


def test_regular_pattern_picker_categories_are_curated():
    root = Path(__file__).resolve().parents[1]
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
console.log(JSON.stringify(vm.runInContext('PATTERN_GROUPS', ctx)));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    groups = json.loads(result.stdout)
    group_names = set(groups)

    removed = {
        "PARADIGM - Digital Reality",
        "PARADIGM - Physics Exploits",
        "Nature-Inspired",
        "Tribal & Cultural",
        "Advanced Geometric",
    }
    assert removed.isdisjoint(group_names)
    assert not any("Final Collection" in name for name in group_names)
    assert groups["PARADIGM"] == [
        "circuitboard",
        "holographic",
        "p_tessellation",
        "p_topographic",
        "soundwave",
        "caustic",
        "dimensional",
        "fresnel_ghost",
        "neural",
        "p_plasma",
    ]
    assert "tribal_celtic_spiral" in groups["Artistic & Cultural"]
    natural_group = next(ids for name, ids in groups.items() if "Natural Textures" in name)
    math_group = next(ids for name, ids in groups.items() if "Mathematical & Fractal" in name)
    assert "nature_water_ripple_pat" in natural_group
    assert "hypocycloid" in math_group
    assert "geo_hilbert_curve" in math_group
