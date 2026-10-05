"""Owner 2026-10-02: no category request may generate a thumbnail."""
import io
import logging
import uuid
from pathlib import Path
from threading import Lock

from flask import Flask
from PIL import Image

from server_routes.swatch_routes import register_swatch_routes


def test_actual_picker_route_is_read_only_and_reuses_offline_master(tmp_path):
    tmp_path = tmp_path / uuid.uuid4().hex
    tmp_path.mkdir()
    calls = []
    quality_calls = []
    def render(*args):
        calls.append(args)
        image = Image.new('RGB', (1024, 512), (212, 32, 154))
        image.paste((18, 195, 62), (512, 0, 1024, 512))
        buf = io.BytesIO()
        image.save(buf, 'PNG')
        return buf.getvalue()
    class Engine:
        BASE_REGISTRY = {'picker-test': {}}
        PATTERN_REGISTRY = {}
        MONOLITHIC_REGISTRY = {}
    app = Flask(__name__)
    register_swatch_routes(app, engine_getter=lambda: Engine,
        thumbnail_dir_getter=lambda: str(tmp_path), swatch_folder_getter=lambda: str(tmp_path),
        swatch_cache={}, swatch_cache_lock=Lock(), swatch_cache_token=lambda: 'engine-v1',
        render_swatch_bytes=render, render_fast_split_swatch_bytes=render,
        render_picker_split_snapshot_bytes=render, picker_split_static_path=lambda *a: '',
        read_picker_split_png_bytes=lambda *a: b'', truthy_env=lambda *a: False,
        normalize_spec_result_to_rgba=lambda *a: None, invoke_monolithic_spec_fn=lambda *a: None,
        logger=logging.getLogger('picker-test'), picker_finish_renderer_hash=lambda *a: 'finish-v1',
        quality_write_guard=lambda items: quality_calls.append(items))
    url = '/api/swatch/base/picker-test?color=abcdef&size=256&mode=split&source=faithful-v1'
    with app.test_client() as client:
        assert client.get(url + '&baked=1').status_code == 503
        assert calls == []
        assert quality_calls == []
        # Explicit bake, followed by repeated categories and enlargement.
        baked = client.get(url)
        assert baked.status_code == 200
        assert len(calls) == 1
        assert len(quality_calls) == 1
        for _ in range(3):
            response = client.get(url + '&baked=1')
            assert response.data == baked.data
            assert response.headers['X-SPB-Swatch-Source'] == 'faithful-disk'
            assert 'immutable' in response.headers['Cache-Control']
        assert client.get(url.replace('size=256', 'size=512') + '&baked=1').status_code == 200
        assert len(calls) == 1
        assert len(quality_calls) == 1, 'Reading a bake must not re-run the publication gate'


def test_startup_build_and_sync_cover_current_picker_format():
    root = Path(__file__).resolve().parents[1]
    startup = (root / 'server_v5.py').read_text(encoding='utf8')
    warm = startup[startup.index('def _boot_swatch_warm()'):]
    assert '"scripts", "bake_faithful_picker.py"' in warm
    assert '[sys.executable, script]' in warm
    supervisor = (root / 'spb_server_supervisor.py').read_text(encoding='utf8')
    assert '"SPB_NO_BOOT_SWATCH_WARM": "1"' not in supervisor
    build = (root / 'electron-app/copy-server-assets.js').read_text(encoding='utf8')
    assert 'tests/picker_baked_loading_contract.cjs' in build
    assert "'scripts/spb_picker_catalog.cjs'), '--check'" in build
    assert "'scripts/bake_faithful_picker.py'), '--check'" in build
    manifest = (root / 'scripts/runtime-sync-manifest.json').read_text(encoding='utf8')
    for item in ['scripts/bake_faithful_picker.py', 'thumbnails/faithful_picker_catalog.json',
                 'thumbnails/swatch_cache/faithful_split_v1']:
        assert item in manifest


def test_offline_baker_caches_current_output_without_promoting_a_release(monkeypatch, tmp_path):
    # A missing publication review must not force already-exposed picker cards
    # back onto live rendering. This cache operation must never change verdicts.
    from scripts import bake_faithful_picker as baker
    tmp_path = tmp_path / uuid.uuid4().hex
    tmp_path.mkdir()
    calls = []
    class Server:
        THUMBNAIL_DIR = str(tmp_path)
        @staticmethod
        def _require_wilds_picker_write_quality(*args):
            raise AssertionError('Cache baking attempted release promotion')
        @staticmethod
        def _render_picker_split_snapshot_bytes(*args):
            calls.append(args)
            buf = io.BytesIO()
            Image.new('RGB', (1024, 512), (71, 32, 114)).save(buf, 'PNG')
            return buf.getvalue()
    monkeypatch.setattr(baker, 'load_server', lambda: Server)
    monkeypatch.setattr(baker, 'identity_for', lambda item: ['v1', 'base', item['id'], item['color'], 42])
    item = {'type': 'base', 'id': 'picker-test', 'color': 'abcdef'}
    assert baker.bake_one(item) == ('base:picker-test', None)
    assert baker.bake_one(item) == ('base:picker-test', None)
    assert len(calls) == 1
    from server_routes.faithful_swatch import faithful_paths
    assert baker.bake_pair_ready(faithful_paths(tmp_path / 'swatch_cache', baker.identity_for(item)), verify=True)
