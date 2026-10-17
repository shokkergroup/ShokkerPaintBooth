"""[11.0.2 slim download 2026-10-16] Masters do not ship: cards stay offline, hover masters are fetched once."""
import hashlib
import io
import json
import urllib.error
import uuid

import pytest
from PIL import Image

from server_routes import preview_cdn
from server_routes.faithful_swatch import faithful_paths, faithful_split_bytes

IDENTITY = ['rh-1', 'base', 'chrome', 'ffffff', 42]


def png(size, left=(210, 32, 154), right=(18, 195, 62)):
    w, h = size
    image = Image.new('RGB', size, left)
    image.paste(right, (w // 2, 0, w, h))
    stream = io.BytesIO()
    image.save(stream, 'PNG')
    return stream.getvalue()


def forbidden(_):
    raise AssertionError('browsing must never render')


@pytest.fixture
def shipped(tmp_path):
    """An installed tree: the _256 card only, like the slim installer."""
    root = tmp_path / ('slim-' + uuid.uuid4().hex)
    master, card = faithful_paths(root, IDENTITY, 256)
    card.parent.mkdir(parents=True)
    card.write_bytes(png((512, 256)))
    return root, master


def call(root, size, **kw):
    return faithful_split_bytes(cache_dir=root, identity=IDENTITY, size=size, render=forbidden,
                                cache_allowed=False, allow_render=False, **kw)


def test_small_cards_come_from_the_shipped_256_card(shipped):
    root, _ = shipped
    fetched = []
    for size in (128, 48):
        out = Image.open(io.BytesIO(call(root, size, fetch_master=fetched.append)))
        assert out.size == (size * 2, size)
        assert out.getpixel((size // 2, size // 2)) == (210, 32, 154)
        assert out.getpixel((size + size // 2, size // 2)) == (18, 195, 62)
    assert fetched == []


def test_hover_master_is_fetched_once_and_kept_in_the_profile(shipped, tmp_path):
    root, master = shipped
    profile = tmp_path / ('profile-' + uuid.uuid4().hex)
    calls = []

    def fetch(name):
        calls.append(name)
        return png((1024, 512))
    first = call(root, 512, fetch_master=fetch, download_dir=profile)
    assert Image.open(io.BytesIO(first)).size == (1024, 512)
    assert (profile / master.name).is_file() and not master.exists()
    second = call(root, 512, fetch_master=fetch, download_dir=profile)
    assert second == first and calls == [master.name]


def test_offline_hover_shows_the_card_enlarged_and_stores_nothing(shipped, tmp_path):
    root, master = shipped
    profile = tmp_path / ('profile-' + uuid.uuid4().hex)
    out = Image.open(io.BytesIO(call(root, 512, fetch_master=lambda _: None, download_dir=profile)))
    assert out.size == (1024, 512)
    assert out.getpixel((256, 256)) == (210, 32, 154) and out.getpixel((768, 256)) == (18, 195, 62)
    assert not master.exists() and not profile.exists()


def test_bad_download_is_ignored(shipped, tmp_path):
    root, _ = shipped
    profile = tmp_path / ('profile-' + uuid.uuid4().hex)
    out = call(root, 512, fetch_master=lambda _: png((300, 300)), download_dir=profile)
    assert Image.open(io.BytesIO(out)).size == (1024, 512) and not profile.exists()


def test_write_guard_blocks_storing_but_still_serves(shipped, tmp_path):
    root, _ = shipped
    profile = tmp_path / ('profile-' + uuid.uuid4().hex)
    out = call(root, 512, fetch_master=lambda _: png((1024, 512)), download_dir=profile, store_download=False)
    assert Image.open(io.BytesIO(out)).size == (1024, 512) and not profile.exists()


def test_nothing_shipped_still_refuses_to_render(tmp_path):
    with pytest.raises(FileNotFoundError):
        faithful_split_bytes(cache_dir=tmp_path / ('empty-' + uuid.uuid4().hex), identity=IDENTITY, size=256, render=forbidden,
                             allow_render=False, fetch_master=lambda _: None)


def test_cdn_rejects_odd_names_and_honours_the_switch(monkeypatch):
    monkeypatch.setattr(preview_cdn.urllib.request, 'urlopen', lambda *a, **k: (_ for _ in ()).throw(AssertionError('no network')))
    assert preview_cdn.fetch_master('../secrets.png') is None
    monkeypatch.setenv('SPB_PREVIEW_CDN_OFF', '1')
    assert preview_cdn.fetch_master('a' * 64 + '.png') is None


def test_cdn_cools_down_after_a_network_error_but_not_after_a_404(monkeypatch):
    monkeypatch.delenv('SPB_PREVIEW_CDN_OFF', raising=False)
    monkeypatch.setitem(preview_cdn._state, 'offline_until', 0.0)
    calls = []

    def missing(request, timeout, context=None):   # 11.0.3: fetch passes its TLS context
        calls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 404, 'nf', {}, None)
    monkeypatch.setattr(preview_cdn.urllib.request, 'urlopen', missing)
    name = hashlib.sha256(json.dumps(IDENTITY).encode()).hexdigest() + '.png'
    assert preview_cdn.fetch_master(name) is None and preview_cdn.fetch_master(name) is None
    assert len(calls) == 2

    def down(request, timeout, context=None):   # 11.0.3: fetch passes its TLS context
        calls.append(request.full_url)
        raise OSError('no route')
    monkeypatch.setattr(preview_cdn.urllib.request, 'urlopen', down)
    assert preview_cdn.fetch_master(name) is None and preview_cdn.fetch_master(name) is None
    assert len(calls) == 3   # second call skipped by the cool-down


def test_installed_app_route_serves_hover_without_shipped_master(monkeypatch, tmp_path):
    # The real Flask route, as the slim installer leaves it: _256 card on disk, no master.
    import logging
    import os
    import re
    from threading import Lock
    from flask import Flask
    from server_routes.swatch_routes import register_swatch_routes
    root = tmp_path / ('route-' + uuid.uuid4().hex)
    root.mkdir()
    profile = root / 'profile'
    monkeypatch.setenv('SPB_PREVIEW_CACHE_DIR', str(profile))
    renders = []

    def render(*args):
        renders.append(args)
        return png((1024, 512))

    class Engine:
        BASE_REGISTRY = {'picker-test': {}}
        PATTERN_REGISTRY = {}
        MONOLITHIC_REGISTRY = {}
    app = Flask(__name__)
    register_swatch_routes(app, engine_getter=lambda: Engine,
        thumbnail_dir_getter=lambda: str(root), swatch_folder_getter=lambda: str(root),
        swatch_cache={}, swatch_cache_lock=Lock(), swatch_cache_token=lambda: 'engine-v1',
        render_swatch_bytes=render, render_fast_split_swatch_bytes=render,
        render_picker_split_snapshot_bytes=render, picker_split_static_path=lambda *a: '',
        read_picker_split_png_bytes=lambda *a: b'', truthy_env=lambda *a: False,
        normalize_spec_result_to_rgba=lambda *a: None, invoke_monolithic_spec_fn=lambda *a: None,
        logger=logging.getLogger('picker-slim'), picker_finish_renderer_hash=lambda *a: 'finish-v1',
        quality_write_guard=lambda items: None)
    url = '/api/swatch/base/picker-test?color=abcdef&size=256&mode=split&source=faithful-v1'
    hover = url.replace('size=256', 'size=512') + '&baked=1'
    with app.test_client() as client:
        assert client.get(url).status_code == 200            # the bake (build machine)
        master = next(p for p in root.rglob('*.png') if re.fullmatch(r'[0-9a-f]{64}\.png', p.name))
        kept = master.read_bytes()
        os.replace(master, root / 'not-shipped.png')         # the installer leaves it out
        baked = len(renders)
        monkeypatch.setenv('SPB_PREVIEW_CDN_OFF', '1')        # offline
        offline = client.get(hover)
        assert offline.status_code == 200 and Image.open(io.BytesIO(offline.data)).size == (1024, 512)
        assert not profile.exists()
        assert offline.headers['Cache-Control'] == 'no-store'
        assert offline.headers['X-SPB-Swatch-Source'] == 'faithful-card-stand-in'
        monkeypatch.delenv('SPB_PREVIEW_CDN_OFF')
        monkeypatch.setattr(preview_cdn, 'fetch_master', lambda name: kept if name == master.name else None)
        online = client.get(hover)
        assert online.status_code == 200 and online.data == kept
        assert 'immutable' in online.headers['Cache-Control']
        assert (profile / master.name).read_bytes() == kept and not master.exists()
        assert client.get(url + '&baked=1').status_code == 200   # grid card still from the install
        assert len(renders) == baked, 'browsing must never render'


def test_startup_baker_does_not_rebake_an_install_that_has_cards_only(shipped, monkeypatch):
    import importlib.util
    for key in ('SHOKKER_SKIP_SPEC_PREBAKE', 'SHOKKER_SKIP_PICKER_PREBAKE', 'SPB_NO_LIVE_LINK',
                'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
        monkeypatch.delenv(key, raising=False)   # the baker sets these on import; restore after
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        'bake_faithful_picker', Path(__file__).resolve().parents[1] / 'scripts' / 'bake_faithful_picker.py')
    baker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baker)
    root, _ = shipped
    paths = faithful_paths(root, IDENTITY)
    assert baker.bake_pair_ready(paths, need_master=False)
    assert not baker.bake_pair_ready(paths), 'the packaging check must still demand masters'
