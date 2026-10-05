"""Flask test-client tests for /api/ai/misses and /api/ai/learned-elements (+ learned-cars) and the merge_learned_elements script.  WP10 2026-10-03.
Run only this file:  python -m pytest tests/test_ai_car_routes_elements.py -q
All data goes to tmp_path via SPB_AI_DIR / SPB_LEARNED_ELEMENTS / SPB_AI_MISSES / SPB_LEARNED_CARS; the real %APPDATA% is never touched."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

flask = pytest.importorskip('flask')


@pytest.fixture()
def work(tmp_path):
    # tests/conftest.py overrides tmp_path with ONE shared directory, so give every test its own empty subfolder
    import shutil, uuid
    d = Path(tmp_path) / ('wp10_' + uuid.uuid4().hex[:10])
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def env(work, monkeypatch):
    tmp_path = work
    monkeypatch.setenv('SPB_AI_DIR', str(tmp_path))
    monkeypatch.setenv('SPB_LEARNED_ELEMENTS', str(tmp_path / 'learned_elements.json'))
    monkeypatch.setenv('SPB_AI_MISSES', str(tmp_path / 'ai_misses.jsonl'))
    monkeypatch.setenv('SPB_LEARNED_CARS', str(tmp_path / 'learned_cars.json'))
    from server_routes.ai_car_routes import register_ai_car_routes
    app = flask.Flask('t')
    register_ai_car_routes(app)
    return app.test_client(), tmp_path


def _files(tmp):
    return sorted(p.name for p in tmp.iterdir())


# ----------------------------------------------------------------------------- learned-elements
def test_elements_get_empty(env):
    c, _ = env
    j = c.get('/api/ai/learned-elements').get_json()
    assert j == {'ok': True, 'v': 1, 'rows': []}


def test_elements_post_persist_get_forget(env):
    c, tmp = env
    r = c.post('/api/ai/learned-elements', json={'key': 'ARCA Chevy/SS', 'kind': 'numbers', 'boxes': [[0.1, 0.2, 0.2, 0.3]], 'source': 'teach'})
    assert r.status_code == 200 and r.get_json() == {'ok': True, 'key': 'arcachevyss', 'boxes': 1}
    disk = json.loads((tmp / 'learned_elements.json').read_text(encoding='utf-8'))
    assert disk['rows'][0]['key'] == 'arcachevyss' and disk['rows'][0]['boxes'] == [[0.1, 0.2, 0.2, 0.3]] and disk['rows'][0]['n'] == 1
    rows = c.get('/api/ai/learned-elements').get_json()['rows']
    assert len(rows) == 1 and rows[0]['source'] == 'teach'
    c.post('/api/ai/learned-elements', json={'key': 'arcachevyss', 'kind': 'numbers', 'boxes': [[0.4, 0.4, 0.5, 0.5]]})
    rows = c.get('/api/ai/learned-elements').get_json()['rows']
    assert len(rows) == 1 and rows[0]['n'] == 2 and rows[0]['boxes'] == [[0.4, 0.4, 0.5, 0.5]]      # same key+kind replaces, n counts
    r = c.post('/api/ai/learned-elements', json={'key': 'arcachevyss', 'kind': 'numbers', 'forget': True})
    assert r.status_code == 200 and r.get_json()['ok'] is True
    assert c.get('/api/ai/learned-elements').get_json()['rows'] == []
    assert json.loads((tmp / 'learned_elements.json').read_text(encoding='utf-8'))['rows'] == []


def test_elements_clamp_and_box_rules(env):
    c, _ = env
    boxes = [[-1, -1, 0.1, 0.1], [0.5, 0.5, 0.4, 0.9], [0, 0, 1, 1], ['a', 1, 2, 3], 7, [0.2, 0.2, 0.3, 0.3]] + [[0.1, 0.1, 0.12, 0.12]] * 20
    j = c.post('/api/ai/learned-elements', json={'key': 'k', 'kind': 'numbers', 'boxes': boxes}).get_json()
    assert j['ok'] and j['boxes'] <= 12
    rows = c.get('/api/ai/learned-elements').get_json()['rows']
    assert [0.0, 0.0, 0.1, 0.1] in rows[0]['boxes'] and [0.2, 0.2, 0.3, 0.3] in rows[0]['boxes']
    assert [0, 0, 1, 1] not in rows[0]['boxes'] and len(rows[0]['boxes']) <= 12      # whole-sheet box (> 0.3 area) refused


@pytest.mark.parametrize('body', [
    {},                                                                      # missing everything
    {'kind': 'numbers', 'boxes': [[0, 0, .1, .1]]},                          # missing key
    {'key': 'k', 'boxes': [[0, 0, .1, .1]]},                                 # missing kind
    {'key': 'k', 'kind': 'numbers'},                                         # no boxes, not forget
    {'key': 'k', 'kind': 'sponsors', 'boxes': [[0, 0, .1, .1]]},             # unsupported kind
    {'key': 'k', 'kind': 'numbers', 'boxes': 'nope'},                        # wrong type
    {'key': 'k', 'kind': 'numbers', 'boxes': 5},
    {'key': 'k', 'kind': 'numbers', 'boxes': [[0, 0, 1, 1]]},                # too big
    {'key': '../..', 'kind': 'numbers', 'boxes': [[0, 0, .1, .1]]},          # key sanitises to nothing
    {'key': '', 'kind': 'numbers', 'boxes': [[0, 0, .1, .1]]},
])
def test_elements_invalid_rejected_nothing_written(env, body):
    c, tmp = env
    r = c.post('/api/ai/learned-elements', json=body)
    assert r.status_code < 500 and r.get_json()['ok'] is False
    assert 'learned_elements.json' not in _files(tmp)


def test_elements_non_json_and_list_bodies(env):
    c, tmp = env
    for kw in ({'data': 'not json', 'content_type': 'text/plain'}, {'data': '{broken', 'content_type': 'application/json'}, {'json': [1, 2, 3]}, {'json': 'str'}):
        r = c.post('/api/ai/learned-elements', **kw)
        assert r.status_code < 500 and r.get_json()['ok'] is False
    assert 'learned_elements.json' not in _files(tmp)


def test_elements_path_traversal_key_is_flattened(env):
    c, tmp = env
    j = c.post('/api/ai/learned-elements', json={'key': '..\\..\\evil/../Windows', 'kind': 'numbers', 'boxes': [[0.1, 0.1, 0.2, 0.2]]}).get_json()
    assert j['ok'] and j['key'] == 'evilwindows'
    assert _files(tmp) == ['learned_elements.json']                        # nothing escaped the data dir, no stray files
    assert not (tmp.parent / 'evil').exists() and not (tmp.parent.parent / 'evil').exists()


def test_elements_oversized_payload_bounded(env):
    c, tmp = env
    big = [[0.1, 0.1, 0.2, 0.2]] * 100000
    j = c.post('/api/ai/learned-elements', json={'key': 'big', 'kind': 'numbers', 'boxes': big}).get_json()
    assert j['ok'] and j['boxes'] == 12                                    # capped at 12 boxes per row
    assert (tmp / 'learned_elements.json').stat().st_size < 4000
    for i in range(450):                                                   # row store is capped at 400
        c.post('/api/ai/learned-elements', json={'key': 'car%d' % i, 'kind': 'numbers', 'boxes': [[0.1, 0.1, 0.2, 0.2]]})
    assert len(c.get('/api/ai/learned-elements').get_json()['rows']) == 400


def test_origin_guard_blocks_remote_page(env):
    c, tmp = env
    for method, url in (('get', '/api/ai/learned-elements'), ('get', '/api/ai/misses')):
        assert getattr(c, method)(url, headers={'Origin': 'https://evil.example'}).status_code == 403
    for url, body in (('/api/ai/learned-elements', {'key': 'k', 'kind': 'numbers', 'boxes': [[0, 0, .1, .1]]}), ('/api/ai/misses', {'text': 'x'})):
        assert c.post(url, json=body, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert _files(tmp) == []
    assert c.get('/api/ai/misses', headers={'Origin': 'http://localhost:59876'}).status_code == 200


# ----------------------------------------------------------------------------- misses (append-only JSONL)
def test_misses_get_empty(env):
    c, _ = env
    assert c.get('/api/ai/misses').get_json() == {'ok': True, 'misses': []}


def test_misses_post_append_only_jsonl(env):
    c, tmp = env
    assert c.post('/api/ai/misses', json={'text': 'make it sparkle like a disco', 'why': 'unknown look word'}).get_json() == {'ok': True}
    first = (tmp / 'ai_misses.jsonl').read_bytes()
    assert c.post('/api/ai/misses', json={'text': 'second  sentence\n  here', 'why': 'w2'}).get_json()['ok']
    raw = (tmp / 'ai_misses.jsonl').read_bytes()
    assert raw.startswith(first) and len(raw) > len(first)                 # earlier bytes untouched, new line appended
    lines = raw.decode('utf-8').splitlines()
    assert len(lines) == 2
    rows = [json.loads(x) for x in lines]
    assert rows[0]['t'] == 'make it sparkle like a disco' and rows[0]['w'] == 'unknown look word' and isinstance(rows[0]['at'], int)
    assert rows[1]['t'] == 'second sentence here'                          # whitespace collapsed
    got = c.get('/api/ai/misses').get_json()['misses']
    assert [m['t'] for m in got] == [rows[0]['t'], rows[1]['t']]
    assert (tmp / 'ai_misses.jsonl').read_bytes().startswith(raw)          # GET does not modify


def test_misses_text_and_why_truncated(env):
    c, tmp = env
    c.post('/api/ai/misses', json={'text': 'x' * 5000, 'why': 'y' * 500})
    row = json.loads((tmp / 'ai_misses.jsonl').read_text(encoding='utf-8').splitlines()[0])
    assert len(row['t']) == 200 and len(row['w']) == 60


@pytest.mark.parametrize('body', [{}, {'text': ''}, {'text': '   \n '}, {'why': 'no text'}, {'text': None}])
def test_misses_invalid_nothing_written(env, body):
    c, tmp = env
    r = c.post('/api/ai/misses', json=body)
    assert r.status_code < 500 and r.get_json() == {'ok': False}
    assert 'ai_misses.jsonl' not in _files(tmp)


def test_misses_non_json_and_list_bodies(env):
    c, tmp = env
    for kw in ({'data': 'plain words', 'content_type': 'text/plain'}, {'data': '{bad', 'content_type': 'application/json'}, {'json': ['a', 'b']}, {'json': 'a string'}, {'json': 42}):
        r = c.post('/api/ai/misses', **kw)
        assert r.status_code < 500, kw          # a JSON array / scalar body used to 500 (body.get on a list) - [WP10 2026-10-03]
        assert r.get_json()['ok'] is False
    assert 'ai_misses.jsonl' not in _files(tmp)


def test_misses_rotation_keeps_newest(env):
    c, tmp = env
    f = tmp / 'ai_misses.jsonl'
    f.write_text('\n'.join(json.dumps({'t': 'old%d' % i, 'w': '', 'at': 1}) for i in range(5000)) + '\n' + ('z' * 2200000) + '\n', encoding='utf-8')
    assert c.post('/api/ai/misses', json={'text': 'fresh'}).get_json()['ok']
    lines = f.read_text(encoding='utf-8').splitlines()
    assert len(lines) <= 2001 and json.loads(lines[-1])['t'] == 'fresh'


# ----------------------------------------------------------------------------- learned-cars (older route, smoke)
def test_cars_roundtrip_and_traversal(env):
    c, tmp = env
    assert c.get('/api/ai/learned-cars').get_json() == {'ok': True, 'v': 1, 'cars': []}
    body = {'folder': 'C:/x/../stockcars chevySS/car.tga', 'parts': {'left side': {'box': [0, 0, 0.5, 0.5]}}, 'source': 'taught'}
    j = c.post('/api/ai/learned-cars', json=body).get_json()
    assert j['ok'] and j['id'] == 'learned-chevyss' or j['id'].startswith('learned-')
    assert len(c.get('/api/ai/learned-cars').get_json()['cars']) == 1
    for bad in ({}, {'parts': {}}, {'parts': {'a': {'box': [0.5, 0.5, 0.1, 0.1]}}}, [1]):
        assert c.post('/api/ai/learned-cars', json=bad).get_json()['ok'] is False
    assert len(c.get('/api/ai/learned-cars').get_json()['cars']) == 1
    assert _files(tmp) == ['learned_cars.json']


# ----------------------------------------------------------------------------- merge_learned_elements.py
def _load_merge():
    spec = importlib.util.spec_from_file_location('merge_learned_elements', ROOT / 'scripts' / 'ai_atlas' / 'merge_learned_elements.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_merge_script_dry_run_write_idempotent(work):
    tmp_path = work
    m = _load_merge()
    src, out = tmp_path / 'learned_elements.json', tmp_path / 'out' / 'atlas.json'
    rows = {'v': 1, 'rows': [
        {'key': 'ARCA Chevy', 'kind': 'numbers', 'boxes': [[0.101, 0.2, 0.2, 0.3], [0.6, 0.6, 0.7, 0.7]], 'source': 'teach', 'n': 2, 'at': 1},
        {'key': 'arcachevy', 'kind': 'numbers', 'boxes': [[0.104, 0.2, 0.2, 0.3]], 'source': 'ai', 'n': 1, 'at': 2},       # same rounded box -> same proposal
        {'key': 'fordmustang', 'kind': 'numbers', 'boxes': [[0.3, 0.3, 0.4, 0.4]], 'source': 'confirm', 'n': 1, 'at': 3},
        {'key': 'bad', 'kind': 'sponsors', 'boxes': [[0, 0, .1, .1]]},
        {'key': 'bad2', 'kind': 'numbers', 'boxes': [[.5, .5, .1, .1]]},
        'junk']}
    src.write_text(json.dumps(rows), encoding='utf-8')
    before_in = src.read_bytes()
    code, msg = m.run(src, out, write=False)
    assert code == 0 and msg.startswith('DRY RUN') and not out.exists()
    code, msg = m.run(src, out, write=True)
    assert code == 0 and out.exists() and src.read_bytes() == before_in      # input never touched
    a = json.loads(out.read_text(encoding='utf-8'))
    assert a['proposals_only'] is True and sorted(a['cars']) == ['arcachevy', 'fordmustang']
    props = a['cars']['arcachevy']['numbers']
    assert len(props) == 2
    p = [e for e in props if e['box'] == [0.1, 0.2, 0.2, 0.3]][0]
    assert p['sources'] == {'buyer': 2, 'ai': 1} and p['count'] == 3
    snap = out.read_bytes()
    code, msg = m.run(src, out, write=True)                                  # second run: no change
    assert code == 0 and 'no change' in msg and out.read_bytes() == snap
    assert m.run(src, out, write=True)[0] == 0 and out.read_bytes() == snap
    rows['rows'][0]['n'] = 5                                                 # a re-confirmation raises the count only
    src.write_text(json.dumps(rows), encoding='utf-8')
    m.run(src, out, write=True)
    a2 = json.loads(out.read_text(encoding='utf-8'))
    assert [e for e in a2['cars']['arcachevy']['numbers'] if e['box'] == [0.1, 0.2, 0.2, 0.3]][0]['sources']['buyer'] == 5
    assert m.run(tmp_path / 'missing.json', out, write=True)[0] == 1
