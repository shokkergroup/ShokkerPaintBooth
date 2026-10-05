"""Owner 2026-09-17: current high-detail bakes survive repeat picker opens."""
import hashlib
import io
import json
import uuid
import pytest

from PIL import Image
from server_routes.faithful_swatch import faithful_split_bytes


@pytest.fixture
def fresh_cache(tmp_path):
    # SPB's runtime harness can reuse tmp_path between test runs. A cold-cache
    # assertion needs its own namespace; old bakes must not falsify render counts.
    path = tmp_path / ('faithful-' + uuid.uuid4().hex)
    path.mkdir()
    return path


def master():
    image = Image.new('RGB', (1024, 512), (210, 32, 154))
    image.paste((18, 195, 62), (512, 0, 1024, 512))
    stream = io.BytesIO()
    image.save(stream, 'PNG')
    return stream.getvalue()


def test_existing_bake_reads_even_when_quality_guard_disallows_writes(fresh_cache):
    tmp_path = fresh_cache
    kwargs = dict(cache_dir=tmp_path, identity=['finish-a', 'base', 'a', 'ffffff', 42], size=256)
    first = faithful_split_bytes(**kwargs, render=lambda _: master())
    def forbidden(_):
        raise AssertionError('An existing bake must never render again')
    assert faithful_split_bytes(**kwargs, render=forbidden, cache_allowed=False) == first
    assert faithful_split_bytes(**{**kwargs, 'size': 512}, render=forbidden, cache_allowed=False) == master()


def test_old_full_detail_bake_migrates_without_render(fresh_cache):
    tmp_path = fresh_cache
    old = ['global-old', 'finish-a', 'base', 'a', 'ffffff', 42]
    faithful_split_bytes(cache_dir=tmp_path, identity=old, size=512, render=lambda _: master())
    def forbidden(_):
        raise AssertionError('Migration must reuse the current master')
    result = faithful_split_bytes(cache_dir=tmp_path, identity=old[1:], legacy_identity=old,
                                  size=256, render=forbidden)
    image = Image.open(io.BytesIO(result))
    assert image.size == (512, 256)
    assert image.getpixel((255, 128)) == (210, 32, 154)
    assert image.getpixel((256, 128)) == (18, 195, 62)
    key = hashlib.sha256(json.dumps(['faithful-v1', *old[1:]]).encode()).hexdigest()
    assert (tmp_path / 'faithful_split_v1' / (key + '.png')).exists()


def test_changed_finish_and_explicit_nocache_render_fresh(fresh_cache):
    tmp_path = fresh_cache
    calls = []
    def render(size):
        calls.append(size)
        return master()
    for identity, read in [(['a-v1'], True), (['a-v1'], True), (['a-v2'], True), (['a-v2'], False)]:
        faithful_split_bytes(cache_dir=tmp_path, identity=identity, size=256,
                             render=render, read_allowed=read)
    assert calls == [512, 512, 512]


def test_engine_change_preserves_content_addressed_bakes(fresh_cache):
    # Exercise the actual startup function without booting the entire server.
    import ast
    import logging
    import os
    from pathlib import Path
    root = fresh_cache
    cache = root / 'swatch_cache'
    stable = cache / 'faithful_split_v1'
    stable.mkdir(parents=True)
    (stable / 'current.png').write_bytes(b'current immutable image')
    (cache / '_fingerprint.txt').write_text('old-engine')
    (cache / 'old-global.png').write_bytes(b'legacy')
    outside = root / 'unrelated.png'
    outside.write_bytes(b'untouched')
    source = Path(__file__).resolve().parents[1] / 'server.py'
    tree = ast.parse(source.read_text(encoding='utf8'))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_check_swatch_cache_freshness')
    namespace = {'THUMBNAIL_DIR': str(root), 'os': os, 'logging': logging,
                 '_external_write_denial': lambda *args: False,
                 '_engine_files_fingerprint': lambda: 'new-engine',
                 '_spb_swallow': lambda where, error: (_ for _ in ()).throw(error)}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), namespace)
    namespace['_check_swatch_cache_freshness']()
    assert (stable / 'current.png').read_bytes() == b'current immutable image'
    assert not (cache / 'old-global.png').exists()
    assert outside.read_bytes() == b'untouched'
    assert (cache / '_fingerprint.txt').read_text() == 'new-engine'
