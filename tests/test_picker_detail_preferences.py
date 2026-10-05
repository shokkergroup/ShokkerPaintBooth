import io
import json
import tempfile
from pathlib import Path
import pytest
from concurrent.futures import ThreadPoolExecutor

from flask import Flask
from PIL import Image, ImageDraw, ImageChops

from server_routes.faithful_swatch import faithful_split_bytes
from server_routes.finish_preferences import register_finish_preferences, preference_path


@pytest.fixture
def tmp_path():
    # The repository overrides pytest's fixture with one shared directory.
    # Use an explicit unique directory so repeated upgrade tests stay isolated.
    with tempfile.TemporaryDirectory(prefix='picker-preferences-', dir='tests/_runtime_harness/tmp_path') as folder:
        yield Path(folder)


def test_chip_and_enlargement_share_current_master(tmp_path):
    calls = []
    def render(size):
        calls.append(size)
        im = Image.new('RGB', (size * 2, size), '#112244')
        draw = ImageDraw.Draw(im)
        draw.rectangle((size, 0, size * 2, size), fill='#d42517')
        for x in range(0, size, 16):
            draw.ellipse((x, x // 2, x + 8, x // 2 + 8), fill='white')
        out = io.BytesIO()
        im.save(out, 'PNG')
        return out.getvalue()
    def request(size, identity=('renderer-a', 'tint', 42)):
        return faithful_split_bytes(cache_dir=tmp_path, identity=identity, size=size, render=render)
    # A chip requested FIRST may not populate a low-detail master.
    chip = Image.open(io.BytesIO(request(256)))
    big = Image.open(io.BytesIO(request(512)))
    assert calls == [512]
    assert ImageChops.difference(chip, big.resize((512, 256), Image.Resampling.BOX)).getbbox() is None
    request(48)
    assert len(calls) == 1
    request(256, ('renderer-b', 'tint', 42))
    request(256, ('renderer-b', 'tint', 43))
    assert calls == [512, 512, 512]


def app_at(path):
    app = Flask(__name__)
    register_finish_preferences(app, path=path)
    return app


def test_update_new_origin_and_old_profile_migration(tmp_path):
    path = tmp_path / 'user-data' / 'finish-preferences.json'
    old = app_at(path).test_client()
    r = old.post('/api/finish-preferences', json={
        'migrate': True, 'favorites': {'chrome': True}, 'ratings': {'chrome': 94}})
    assert r.status_code == 200
    old.post('/api/finish-preferences', json={'favorites': {'chrome': False}, 'ratings': {'chrome': 12}})
    # Simulated replacement installation / empty browser storage, same user data.
    new = app_at(path).test_client()
    assert new.get('/api/finish-preferences').json['ratings']['chrome'] == 12
    data = new.post('/api/finish-preferences', json={
        'migrate': True, 'favorites': {'chrome': True, 'vinyl': True}, 'ratings': {'chrome': 94}}).json
    assert data['favorites'] == {'chrome': False, 'vinyl': True}
    assert data['ratings']['chrome'] == 12
    assert path.with_suffix('.json.bak').exists()


def test_parallel_patches_keep_unrelated_choices(tmp_path):
    app = app_at(tmp_path / 'prefs.json')
    def save(i):
        with app.test_client() as client:
            return client.post('/api/finish-preferences', json={'ratings': {str(i): i}}).status_code
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert set(pool.map(save, range(25))) == {200}
    assert len(app.test_client().get('/api/finish-preferences').json['ratings']) == 25


def test_invalid_and_corrupt_data_never_erase_file(tmp_path):
    path = tmp_path / 'prefs.json'
    client = app_at(path).test_client()
    assert client.post('/api/finish-preferences', json={'ratings': {'x': 101}}).status_code == 400
    assert not path.exists()
    path.write_text('{broken', encoding='utf8')
    assert client.post('/api/finish-preferences', json={'favorites': {'x': True}}).status_code == 400
    assert path.read_text() == '{broken'


def test_storage_is_outside_installation(monkeypatch, tmp_path):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    assert preference_path() == tmp_path / 'ShokkerPaintBooth' / 'finish-preferences.json'
