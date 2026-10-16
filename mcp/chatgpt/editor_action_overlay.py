"""Explicit, hash-bound private editor acceptance overlay."""
from pathlib import Path
import hashlib
import json


def load(port):
    if port != 59910:
        raise ValueError('Editor acceptance is private59910 only')
    lane = Path(__file__).resolve().parent / 'editor-action-integration'
    manifest = json.loads((lane / 'overlay-manifest.json').read_bytes())
    if not manifest.get('syntax_pass'):
        raise ValueError('Editor overlay has not passed syntax checks')
    result = {}
    for item in manifest['files']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid editor overlay path')
        path = lane / 'assets' / relative
        raw = path.read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Changed editor overlay: ' + item['path'])
        result['/' + item['path']] = {'path': path, 'sha256': item['sha256'], 'bytes': raw}
    return result


def polite_redo(port, baseline):
    if port != 59910:
        raise ValueError('Polite Redo acceptance is private59910 only')
    lane = Path(__file__).resolve().parent / 'polite-redo-intent'
    proof = json.loads((lane / 'stage-proof.json').read_bytes())
    routes = json.loads((lane / 'route-proof.json').read_bytes())
    original = baseline.get('/js/spb-offline-answer.js')
    if not routes.get('pass') or not proof.get('syntax_pass') or not original or original['sha256'] != proof['baseline_sha256']:
        raise ValueError('Polite Redo baseline/checks do not match')
    path = lane / 'candidate/js/spb-offline-answer.js'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != proof['candidate_sha256']:
        raise ValueError('Polite Redo candidate changed')
    return {'/js/spb-offline-answer.js': {'path': path, 'sha256': digest, 'bytes': raw}}


def empty_redo(port, baseline):
    if port != 59910:
        raise ValueError('Empty Redo acceptance is private59910 only')
    lane = Path(__file__).resolve().parent / 'redo-empty-answer'
    proof = json.loads((lane / 'stage-proof.json').read_bytes())
    claims = json.loads((lane / 'claim-proof.json').read_bytes())
    original = baseline.get('/js/spb-offline-answer.js')
    if not claims.get('pass') or not proof.get('syntax_pass') or not original or original['sha256'] != proof['baseline_sha256']:
        raise ValueError('Empty Redo baseline/checks do not match')
    path = lane / 'candidate/js/spb-offline-answer.js'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != proof['candidate_sha256'] or digest != claims['candidate_sha256']:
        raise ValueError('Empty Redo candidate changed')
    return {'/js/spb-offline-answer.js': {'path': path, 'sha256': digest, 'bytes': raw}}


def output_advice(port, baseline):
    if port != 59910:
        raise ValueError('Output advice acceptance is private59910 only')
    lane = Path(__file__).resolve().parent / 'body-output-consistency'
    proof = json.loads((lane / 'retrieval-stage-proof.json').read_bytes())
    tested = json.loads((lane / 'retrieval-proof.json').read_bytes())
    item = next(x for x in proof['files'] if x['path'] == 'js/spb-offline-answer.js')
    original = baseline.get('/js/spb-offline-answer.js')
    if not tested.get('pass') or not proof.get('syntax_pass') or not original or original['sha256'] != item['baseline_sha256']:
        raise ValueError('Output advice baseline/checks do not match')
    path = lane / 'candidate/js/spb-offline-answer.js'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    tested_hash = next((value for key, value in tested['sources'].items()
                        if key.replace('\\', '/') == 'mcp/chatgpt/body-output-consistency/candidate/js/spb-offline-answer.js'), None)
    if digest != item['candidate_sha256'] or digest != tested_hash:
        raise ValueError('Output advice candidate changed')
    return {'/js/spb-offline-answer.js': {'path': path, 'sha256': digest, 'bytes': raw}}


def topic_readiness(port, baseline):
    if port != 59910:
        raise ValueError('Topic readiness is private59910 only')
    lane = Path(__file__).resolve().parent / 'body-output-consistency'
    proof = json.loads((lane / 'private-topic/stage-proof.json').read_bytes())
    tested_raw = (lane / 'topic-readiness-proof.json').read_bytes()
    if not proof.get('syntax_pass') or not json.loads(tested_raw).get('pass') or hashlib.sha256(tested_raw).hexdigest() != proof['topic_proof_sha256']:
        raise ValueError('Topic readiness evidence changed')
    result = {}
    root = Path(__file__).resolve().parents[2]
    for item in proof['files']:
        name = item['path']
        predecessor = baseline.get('/' + name)
        old_hash = predecessor['sha256'] if predecessor else hashlib.sha256((root / name).read_bytes()).hexdigest()
        path = lane / 'private-topic/assets' / name
        raw = path.read_bytes()
        if old_hash != item['baseline_sha256'] or hashlib.sha256(raw).hexdigest() != item['candidate_sha256']:
            raise ValueError('Topic readiness asset/baseline changed: ' + name)
        result['/' + name] = {'path': path, 'bytes': raw, 'sha256': item['candidate_sha256']}
    return result


def concise_reference(port, baseline):
    if port != 59910:
        raise ValueError('Concise reference is private59910 only')
    lane = Path(__file__).resolve().parent / 'body-output-consistency/concise-reference'
    proof = json.loads((lane / 'stage-proof.json').read_bytes())
    tested = json.loads((lane / 'component-proof.json').read_bytes())
    name = '/mcp/chatgpt/car-knowledge/offline-answer.js'
    raw = (lane / 'offline-answer.js').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not proof.get('syntax_pass') or not tested.get('pass') or tested['cars'] != 192 or baseline[name]['sha256'] != proof['private_baseline_sha256'] or digest != proof['candidate_sha256'] or digest != tested['candidate_sha256']:
        raise ValueError('Concise reference predecessor/evidence changed')
    return {name: {'path': lane / 'offline-answer.js', 'bytes': raw, 'sha256': digest}}


def reference_history(port, baseline):
    if port != 59910:
        raise ValueError('Reference history is private59910 only')
    lane = Path(__file__).resolve().parent / 'body-output-consistency/reference-history'
    stage = json.loads((lane / 'stage-proof.json').read_bytes())
    tested = json.loads((lane / 'component-proof.json').read_bytes())
    name = '/js/spb-pro-ai.js'
    raw = (lane / 'spb-pro-ai.js').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not stage.get('syntax_pass') or not tested.get('pass') or tested.get('cases') != 9 or baseline[name]['sha256'] != stage['private_predecessor_sha256'] or digest != stage['candidate_sha256'] or digest != tested['candidate_sha256']:
        raise ValueError('Reference history predecessor/evidence changed')
    return {name: {'path': lane / 'spb-pro-ai.js', 'bytes': raw, 'sha256': digest}}


def paint_availability(port, baseline):
    if port != 59910:
        raise ValueError('Paint availability is private59910 only')
    lane = Path(__file__).resolve().parent / 'body-output-consistency/paint-availability'
    stage = json.loads((lane / 'stage-proof.json').read_bytes())
    tested = json.loads((lane / 'component-proof.json').read_bytes())
    name = '/mcp/chatgpt/car-knowledge/offline-answer.js'
    raw = (lane / 'offline-answer.js').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    predecessor = next(p['source_sha256'] for p in stage['predecessors'] if p['label'] == 'private')
    if not stage.get('syntax_pass') or not tested.get('pass') or tested.get('cars') != 192 or baseline[name]['sha256'] != predecessor or digest != stage['candidate_sha256'] or digest != tested['candidate_sha256']:
        raise ValueError('Paint availability predecessor/evidence changed')
    return {name: {'path': lane / 'offline-answer.js', 'bytes': raw, 'sha256': digest}}


def reference_dock(port, baseline):
    if port != 59910:
        raise ValueError('Reference dock is private59910 only')
    lane = Path(__file__).resolve().parent / 'body-output-consistency/reference-dock'
    stage = json.loads((lane / 'stage-proof.json').read_bytes())
    tested = json.loads((lane / 'component-proof.json').read_bytes())
    if not stage.get('syntax_pass') or not tested.get('pass') or tested.get('cases') != 12:
        raise ValueError('Reference dock evidence unavailable')
    result = {}
    for row in stage['files']:
        name = '/' + row['path']
        path = lane / Path(row['path']).name
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        key = 'candidate_sha256' if name == '/js/spb-pro-ai.js' else 'builder_sha256'
        if baseline[name]['sha256'] != row['source_sha256'] or digest != row['candidate_sha256'] or digest != tested[key]:
            raise ValueError('Reference dock predecessor/evidence changed: ' + name)
        result[name] = {'path': path, 'bytes': raw, 'sha256': digest}
    return result
