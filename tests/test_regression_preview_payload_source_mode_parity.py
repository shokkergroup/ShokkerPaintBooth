"""Regression guard — the LIVE PREVIEW payload must carry the same base-colour
contract as the full-render payload.

Owner 2026-09-03: *"I selected SOUL CORE EMERALD as Base Material. The Base Color
when I click USE SOURCE PAINT - it's making it the greenish color from the Soul
Core Emerald ... When you click USE SOURCE PAINT ... it should look IDENTICAL in
the LIVE PREVIEW to the SOURCE PAINT."*

Root cause: `paint-booth-5-api-render.js::_applyBaseColorMode` (full render) sends
`base_color_explicit` when the user CHOSE a mode; the second builder inside
`paint-booth-3-canvas.js` (live preview) never did. The engine (2026-08-30 rule)
turns an unflagged 'source' on a monolithic into 'finish', so the preview showed
the finish's own paint while the full render honoured Use Source Paint.

Second symptom (same family): the zone panel displayed 'Use finish's own color'
for every zone without a saved mode, but both builders send an unsaved mode as
'source' and the engine renders a regular BASE (gloss) as the car's own paint.
The panel must show what will actually render.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read(rel):
    return (REPO / rel).read_bytes().decode("utf-8", errors="surrogateescape")


def test_live_preview_builder_sends_explicit_flag_like_full_render():
    canvas = _read("paint-booth-3-canvas.js")
    api = _read("paint-booth-5-api-render.js")
    assert "if (z.baseColorModeExplicit) zoneObj.base_color_explicit = true;" in api
    assert "if (z.baseColorModeExplicit) zoneObj.base_color_explicit = true;" in canvas, (
        "paint-booth-3-canvas.js live-preview builder lost the base_color_explicit flag; "
        "an explicit Use Source Paint on a monolithic finish will render the finish's own paint"
    )


def test_zone_panel_default_mode_matches_what_renders():
    src = _read("paint-booth-2-state-zones.js")
    assert "const _baseColorMode = (zone.baseColorMode || (zone.finish ? 'finish' : 'source'));" in src
    assert "const _baseColorMode = (zone.baseColorMode || 'finish');" not in src


def test_color_lab_is_opt_in_so_a_picked_solid_colour_renders_exactly():
    """Owner 2026-09-03: "click USE SOLID COLOR then PICK the solid red ... it's DARKENING it".
    With base_color_depth present the engine runs the COLOR LAB candy pipeline, which
    multiplies the colour over the finish's own value structure (never the flat colour).
    Choosing a mode or picking a colour must NOT switch the Lab on; only the Lab sliders do."""
    src = _read("paint-booth-2-state-zones.js")
    assert "_spbEnsureColorLab(index);   // [SPB COLOR LAB]" not in src
    assert "new picks get the Lab" not in src
    # the sliders still engage it deliberately
    assert src.count("_spbEnsureColorLab(index);") >= 4


def test_engine_honours_explicit_source_on_monolithic():
    """The engine side of the contract: explicit source keeps the car's paint."""
    import io, contextlib
    import numpy as np
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import shokker_engine_v2 as eng
    src = eng.__file__ and None  # placeholder to keep the import referenced
    h = w = 64
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[..., 0] = 220; rgb[..., 1] = 40; rgb[..., 2] = 40      # a red car
    from PIL import Image
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), "spb_explicit_probe.png")
    Image.fromarray(rgb).save(tmp)

    def mean_diff(zone):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            out = eng.preview_render(tmp, [zone], seed=42, preview_scale=1.0)
        p = np.asarray(out[0]).astype(np.float32)[..., :3]
        return float(np.abs(p - rgb.astype(np.float32)).mean())

    base = dict(name="z", color="remaining", finish="fs_core_emerald", pattern="none",
                intensity="100", base_color_strength=1, base_spec_strength=1)
    explicit = mean_diff(dict(base, base_color_mode="source", base_color_explicit=True))
    own = mean_diff(dict(base, base_color_mode="finish", base_color_explicit=True))
    assert explicit < 12.0, f"explicit source should keep the car's paint (mean diff {explicit:.1f})"
    assert own > explicit + 10.0, f"finish mode should differ from the car's paint (own {own:.1f} vs source {explicit:.1f})"
