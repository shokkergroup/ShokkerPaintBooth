"""Material-content gate; UI creation/Sync and persistence have separate proofs."""
import copy

import numpy as np
import pytest

from engine.zone_material_instances import apply_instances


def fixture():
    paint = np.arange(12 * 12 * 3, dtype=np.uint16).reshape(12, 12, 3).astype(np.uint8)
    spec = np.arange(12 * 12 * 4, dtype=np.uint16).reshape(12, 12, 4).astype(np.uint8)
    spec[1:3, 1:3, 3] = 0
    record = dict(version=2, documentWidth=12, documentHeight=12,
                  sourceBbox=dict(x1=1, y1=1, x2=3, y2=3),
                  instanceBbox=dict(x1=7, y1=5, x2=9, y2=7))
    return paint, spec, record


def test_exact_translation_preserves_raw_spec_alpha_and_outside():
    paint, spec, record = fixture()
    p, s = apply_instances(paint, spec, [dict(material_instances=[record])], source_paint=np.zeros_like(paint))
    for original, output in ((paint, p), (spec, s)):
        expected = original.copy()
        expected[5:7, 7:9] = original[1:3, 1:3]
        np.testing.assert_array_equal(output, expected)
        assert not np.shares_memory(output, original)
    assert np.all(s[5:7, 7:9, 3] == 0)
    assert np.any(s[5:7, 7:9, :3] != 0)


@pytest.mark.parametrize("angle,k", [(90, -1), (180, 2), (270, 1), (360, 0)])
def test_quarter_turns_are_exact(angle, k):
    paint, spec, record = fixture()
    record["rotation"] = angle
    p, s = apply_instances(paint, spec, [dict(material_instances=[record])], source_paint=np.zeros_like(paint))
    np.testing.assert_array_equal(p[5:7, 7:9], np.rot90(paint[1:3, 1:3], k))
    np.testing.assert_array_equal(s[5:7, 7:9], np.rot90(spec[1:3, 1:3], k))


def test_mask_holes_preserve_destination_and_input():
    paint, spec, record = fixture()
    mask = np.ones((12, 12), np.float32)
    mask[1, 1] = 0
    original_mask = mask.copy()
    p, s = apply_instances(paint, spec, [dict(material_instances=[record])], [mask], source_paint=np.zeros_like(paint))
    np.testing.assert_array_equal(p[5, 7], paint[5, 7])
    np.testing.assert_array_equal(s[5, 7], spec[5, 7])
    np.testing.assert_array_equal(mask, original_mask)


def test_preview_coordinates_and_destination_clipping():
    paint, spec, record = fixture()
    record["documentWidth"] = record["documentHeight"] = 24
    record["sourceBbox"] = dict(x1=2, y1=2, x2=6, y2=6)
    record["instanceBbox"] = dict(x1=-2, y1=10, x2=2, y2=14)
    p, s = apply_instances(paint, spec, [dict(material_instances=[record])], source_paint=np.zeros_like(paint))
    np.testing.assert_array_equal(p[5:7, 0], paint[1:3, 2])
    np.testing.assert_array_equal(s[5:7, 0], spec[1:3, 2])


def test_sources_are_read_before_any_copy_and_export_has_real_channels():
    paint, spec, record = fixture()
    second = copy.deepcopy(record)
    second["sourceBbox"] = copy.deepcopy(record["instanceBbox"])
    second["instanceBbox"] = dict(x1=9, y1=9, x2=11, y2=11)
    layers = []
    p, s = apply_instances(paint, spec, [dict(name="Paint", material_instances=[record, second])], export_layers=layers, source_paint=np.zeros_like(paint))
    np.testing.assert_array_equal(p[9:11, 9:11], paint[5:7, 7:9])
    np.testing.assert_array_equal(s[9:11, 9:11], spec[5:7, 7:9])
    assert len(layers) == 2
    np.testing.assert_array_equal(layers[0]["spec"][5:7, 7:9], spec[1:3, 1:3])
    assert np.count_nonzero(layers[0]["mask"]) == 4


def test_spec_only_material_does_not_clone_untouched_source_art():
    paint, spec, record = fixture()
    p, s = apply_instances(paint, spec, [dict(material_instances=[record])], source_paint=paint)
    np.testing.assert_array_equal(p, paint)
    np.testing.assert_array_equal(s[5:7, 7:9], spec[1:3, 1:3])


def test_only_material_authored_paint_transfers():
    paint, spec, record = fixture()
    source = paint.copy()
    source[1, 1] = [0, 0, 0]
    p, _ = apply_instances(paint, spec, [dict(material_instances=[record])], source_paint=source)
    expected = paint.copy()
    expected[5, 7] = paint[1, 1]
    np.testing.assert_array_equal(p, expected)


def test_actual_preview_route_forwards_records_before_rendering():
    import ast
    from pathlib import Path
    tree = ast.parse(Path("server.py").read_text(encoding="utf-8"))
    route = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "preview_render_endpoint")
    block = next(n for n in ast.walk(route) if isinstance(n, ast.If)
                 and ast.unparse(n.test) == "isinstance(z.get('material_instances'), list)")
    code = compile(ast.fix_missing_locations(ast.Module(body=[block], type_ignores=[])), "actual-preview-forwarding", "exec")
    _, _, record = fixture()
    for value in ([record], None, "legacy"):
        context = dict(z={"material_instances": value}, zone_obj={})
        exec(code, context)
        assert context["zone_obj"].get("material_instances") == (value if isinstance(value, list) else None)


@pytest.mark.parametrize("change", [lambda r:r.update(version=1), lambda r:r.update(documentWidth=0),
    lambda r:r.update(rotation=float("nan")), lambda r:r.update(instanceBbox={}), lambda r:r.update(muted=True)])
def test_legacy_or_invalid_records_cannot_activate_old_paint_snapshots(change):
    paint, spec, record = fixture()
    change(record)
    p, s = apply_instances(paint, spec, [dict(material_instances=[record])], source_paint=np.zeros_like(paint))
    assert p is paint and s is spec
