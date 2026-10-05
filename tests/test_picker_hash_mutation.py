"""In-place registry wiring must not retain a stale picker identity."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace


def test_in_place_callback_and_material_changes_invalidate_hash(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'finish_colors_lookup', SimpleNamespace(get_finish_colors=lambda _: None))
    source = Path(__file__).resolve().parents[1] / 'server.py'
    tree = ast.parse(source.read_text(encoding='utf8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_picker_finish_renderer_hash')
    def paint_a(): pass
    def paint_b(): pass
    entry = {'paint_fn': paint_a, 'M': 20, 'R': 40, 'CC': 60}
    namespace = dict(engine=SimpleNamespace(BASE_REGISTRY={'finish': entry}, MONOLITHIC_REGISTRY={}, PATTERN_REGISTRY={}),
        _PICKER_RENDERER_HASH_MEMO={}, _PICKER_ENGINE_READY=False, PICKER_SNAPSHOT_RENDER_SCALE=0.5,
        PICKER_SNAPSHOT_SOURCE_CANVAS=2048, PICKER_SNAPSHOT_SIZE=48, json=json,
        _append_picker_renderer_fn_hash=lambda parts, fn: parts.append(fn.__name__),
        _spb_swallow=lambda *args: None)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    hash_for = namespace['_picker_finish_renderer_hash']
    first = hash_for('base', 'finish')
    entry['paint_fn'] = paint_b
    second = hash_for('base', 'finish')
    assert second != first
    entry['CC'] = 90
    third = hash_for('base', 'finish')
    assert third != second
    assert hash_for('base', 'finish') == third
