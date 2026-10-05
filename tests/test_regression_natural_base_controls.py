import json
import subprocess
from pathlib import Path

import numpy as np

from engine.compose import compose_paint_mod, compose_paint_mod_stacked


ROOT = Path(__file__).resolve().parents[1]


def _render_regular(base_strength, color_strength, *, stacked=False):
    shape = (12, 12)
    source = np.empty((12, 12, 3), dtype=np.float32)
    source[:] = [0.82, 0.68, 0.54]
    mask = np.ones(shape, dtype=np.float32)
    common = dict(
        base_id="gloss",
        paint=source.copy(),
        shape=shape,
        mask=mask,
        seed=716,
        pm=1.0,
        bb=1.0,
        base_color_mode="solid",
        base_color=[0.14, 0.42, 0.76],
        base_color_strength=color_strength,
        base_strength=base_strength,
    )
    if stacked:
        result = compose_paint_mod_stacked(all_patterns=[], **common)
    else:
        result = compose_paint_mod(pattern_id="none", **common)
    return source, np.asarray(result, dtype=np.float32)


def test_regular_base_strength_fades_complete_result_to_source():
    source, hidden = _render_regular(0.0, 1.0)
    _, quarter = _render_regular(0.25, 1.0)
    _, full = _render_regular(1.0, 1.0)
    chosen = np.array([0.14, 0.42, 0.76], dtype=np.float32)

    assert np.allclose(hidden, source, atol=1e-6)
    assert np.allclose(full, chosen, atol=1e-6)
    assert np.allclose(quarter, source * 0.75 + chosen * 0.25, atol=1e-6)


def test_color_strength_is_independent_inside_base_strength_envelope():
    source, no_color = _render_regular(1.0, 0.0)
    _, half_color = _render_regular(1.0, 0.5)
    _, full_color = _render_regular(1.0, 1.0)
    chosen = np.array([0.14, 0.42, 0.76], dtype=np.float32)

    assert np.allclose(no_color, source, atol=1e-6)
    assert np.allclose(half_color, source * 0.5 + chosen * 0.5, atol=1e-6)
    assert np.allclose(full_color, chosen, atol=1e-6)


def test_stacked_path_uses_the_same_natural_strength_contract():
    source, hidden = _render_regular(0.0, 1.0, stacked=True)
    _, half = _render_regular(0.5, 1.0, stacked=True)
    _, full = _render_regular(1.0, 1.0, stacked=True)

    assert np.allclose(hidden, source, atol=1e-6)
    assert np.allclose(half, source * 0.5 + full * 0.5, atol=1e-6)


def test_spec_scale_link_is_default_and_independence_is_explicit():
    script = r"""
const link = require('./js/zones/base-spec-scale-link.js');
const zone = { baseScale: 1, specScale: 3 };
link.applyBaseScale(zone, 0.35);
const linked = { ...zone, resolved: link.resolve(zone), independent: link.isIndependent(zone) };
link.setIndependent(zone, true);
link.applySpecScale(zone, 0.8);
link.applyBaseScale(zone, 0.5);
const independent = { ...zone, resolved: link.resolve(zone) };
link.setIndependent(zone, false);
const relinked = { ...zone, resolved: link.resolve(zone) };
process.stdout.write(JSON.stringify({ linked, independent, relinked }));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(proc.stdout)

    assert result["linked"]["baseScale"] == 0.35
    assert result["linked"]["specScale"] == 0.35
    assert result["linked"]["resolved"] == 0.35
    assert result["linked"]["independent"] is False
    assert result["independent"]["baseScale"] == 0.5
    assert result["independent"]["specScale"] == 0.8
    assert result["independent"]["resolved"] == 0.8
    assert result["relinked"]["specScale"] == 0.5
    assert result["relinked"]["resolved"] == 0.5


def test_ui_and_persistence_expose_the_explicit_spec_override():
    state = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
    config = (ROOT / "js/zones/zone-config-zone-map-controls.js").read_text(encoding="utf-8")
    dna = (ROOT / "js/zones/finish-dna-controls.js").read_text(encoding="utf-8")
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")

    assert "Independent Spec" in state
    assert "data-spec-scale-control" in state
    assert "specScaleMode" in config
    assert "specScaleMode" in dna
    assert "js/zones/base-spec-scale-link.js" in html


def test_config_round_trip_preserves_only_explicit_spec_independence():
    script = r"""
require('./js/zones/zone-config-zone-map-controls.js');
const controls = globalThis.SPBZoneConfigZoneMapControls.install();
const linked = controls.serializeZones([{ baseScale: 0.35, specScale: 0.9 }])[0];
const independent = controls.serializeZones([{
  baseScale: 0.35, specScale: 0.9, specScaleMode: 'independent'
}])[0];
const restored = controls.hydrateZones([independent])[0];
process.stdout.write(JSON.stringify({ linked, independent, restored }));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(proc.stdout)

    assert result["linked"]["specScaleMode"] == "match"
    assert result["linked"]["specScale"] == 0.35
    assert result["independent"]["specScaleMode"] == "independent"
    assert result["independent"]["specScale"] == 0.9
    assert result["restored"]["specScaleMode"] == "independent"
    assert result["restored"]["specScale"] == 0.9
