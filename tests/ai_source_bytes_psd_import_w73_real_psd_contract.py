from __future__ import annotations
import ast, base64, hashlib, importlib.util, json, os, sys, tempfile, types
from pathlib import Path
from flask import Flask
from PIL import Image
from psd_tools import PSDImage

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'electron-app/server'))
FROZEN = ROOT / '_easy_claude_work/ai14h_w73_review/frozen'
CAND = ROOT / '_easy_claude_work/ai14h_w71_candidate'
ROUTE_PATH = FROZEN / 'candidate-psd_import_routes.py'
SERVER_PATH = FROZEN / 'server.py'
API_FILE = ROOT / 'docs/handoff_reports/AI_HELPER_14H_SOURCE_BYTES_PSD_IMPORT_W71_CANDIDATE_2026-10-04.json'

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def extract_function(source_path: Path, name: str, globals_dict: dict):
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, str(source_path), 'exec'), globals_dict)
    return globals_dict[name]

# Use the actual source fingerprint helper from the pre-edit frozen project route.
project_tree = ast.parse((FROZEN / 'project_routes.py').read_text(encoding='utf-8'))
fp_node = next(n for n in project_tree.body if isinstance(n, ast.FunctionDef) and n.name == '_source_fingerprint')
fp_globals = {'os': os, 'hashlib': hashlib}
exec(compile(ast.Module(body=[fp_node], type_ignores=[]), str(FROZEN / 'project_routes.py'), 'exec'), fp_globals)
source_fingerprint = fp_globals['_source_fingerprint']

# Load candidate route and actual candidate server cache loader without starting server.
spec = importlib.util.spec_from_file_location('w73_candidate_psd_import_route', ROUTE_PATH)
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)
route._source_fingerprint = source_fingerprint
cache_globals = {'os': os, '_psd_cache': {}}
get_cached_psd = extract_function(SERVER_PATH, '_get_cached_psd', cache_globals)

app = Flask('w73-real-psd')
class Log:
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
route.register_psd_import_routes(
    app,
    require_internal_request=lambda: (True, None),
    sanitize_path=lambda p: (str(Path(p).resolve()), None),
    get_cached_psd=get_cached_psd,
    logger=Log(),
)
client = app.test_client()
real_open = PSDImage.open
parse_count = {'n': 0}
def counted_open(path, *args, **kwargs):
    parse_count['n'] += 1
    return real_open(path, *args, **kwargs)
PSDImage.open = staticmethod(counted_open)

def make_psd(path: Path, hidden_rgb, visible_rgb=(200, 10, 20)):
    psd = PSDImage.new('RGB', (8, 8), (0, 0, 0))
    psd.append(psd.create_pixel_layer(Image.new('RGBA', (8, 8), (*visible_rgb, 255)), name='Paint'))
    hidden = psd.create_pixel_layer(Image.new('RGBA', (8, 8), (*hidden_rgb, 255)), name='Hidden Secret')
    hidden.visible = False
    psd.append(hidden)
    psd.save(path)
    return path.read_bytes()

def ask(path: Path):
    return client.post('/api/psd-import', json={'psd_path': str(path), 'thumbnail_size': 32}, headers={'X-Shokker-Internal': '1'})

def set_fixed_mtime(path: Path, ns: int):
    os.utime(path, ns=(ns, ns))

def names(payload):
    return json.dumps(payload.get('layers', []), sort_keys=True)

rows = []
try:
  with tempfile.TemporaryDirectory(prefix='spb-w73-') as td:
    source = Path(td) / 'tiny.psd'
    t_ns = 1_700_000_000_000_000_000
    a_bytes = make_psd(source, (10, 210, 30))
    set_fixed_mtime(source, t_ns)
    r_a = ask(source); assert r_a.status_code == 200, (r_a.status_code, r_a.get_json())
    body_a = r_a.get_json(); comp_a = body_a['composite']; digest_a = sha_file(source)
    assert body_a['sourceBytesSha256'] == digest_a
    assert body_a['width'] == 8 and body_a['height'] == 8
    assert 'Paint' in names(body_a) and 'Hidden Secret' in names(body_a)
    assert parse_count['n'] == 1
    assert a_bytes not in r_a.data and b'8BPS' not in r_a.data and 'rawBytes' not in body_a
    rows.append({'id':'real-PSD-import-and-no-raw-byte-transfer','status':'PASS','parseCount':parse_count['n'],'digest':digest_a,'fileBytes':len(a_bytes),'responseBytes':len(r_a.data)})

    r_a2 = ask(source); assert r_a2.status_code == 200 and r_a2.get_json()['sourceBytesSha256'] == digest_a
    assert parse_count['n'] == 1, 'same bytes should reuse response cache without parsing'
    rows.append({'id':'same-bytes-response-cache-hit','status':'PASS','parseCount':parse_count['n']})

    b_bytes = make_psd(source, (20, 40, 220))
    set_fixed_mtime(source, t_ns)
    assert source.stat().st_mtime_ns == t_ns
    digest_b = sha_file(source); assert digest_b != digest_a
    r_b = ask(source); assert r_b.status_code == 200, (r_b.status_code, r_b.get_json())
    body_b = r_b.get_json()
    assert body_b['sourceBytesSha256'] == digest_b
    assert body_b['composite'] == comp_a, 'only hidden layer bytes changed; visible composite must remain equal'
    assert parse_count['n'] == 2, 'same-path/same-mtime byte replacement must be reparsed'
    assert names(body_b) == names(body_a)
    assert b_bytes not in r_b.data and b'8BPS' not in r_b.data
    rows.append({'id':'same-path-same-mtime-hidden-layer-byte-change','status':'PASS','sameMtime':True,'digestChanged':True,'compositeEqual':True,'parseCount':parse_count['n']})

    # Race A: use an uncached path and mutate just after the actual pre-parse fingerprint.
    race_source = Path(td) / 'race-a.psd'
    make_psd(race_source, (60, 90, 140))
    race_bytes = make_psd(Path(td) / 'fixture-c.psd', (150, 80, 200))
    real_fingerprint = route._source_fingerprint
    race_once = {'done': False}
    def racing_fingerprint(path):
      result = real_fingerprint(path)
      if str(Path(path).resolve()) == str(race_source.resolve()) and not race_once['done']:
        race_once['done'] = True
        race_source.write_bytes(race_bytes)
      return result
    route._source_fingerprint = racing_fingerprint
    r_parse_race = ask(race_source)
    route._source_fingerprint = real_fingerprint
    assert r_parse_race.status_code == 409, (r_parse_race.status_code, r_parse_race.get_json())
    assert 'sourceBytesSha256' not in r_parse_race.get_json()
    PSDImage.open = staticmethod(counted_open)
    rows.append({'id':'hash-to-parser-open-race','status':'PASS','http':409,'successDigestReturned':False,'cacheBypassed':'new path'})

    r_c = ask(race_source); assert r_c.status_code == 200 and r_c.get_json()['sourceBytesSha256'] == sha_file(race_source)
    assert parse_count['n'] == 4

    # Race B: mutate after actual layer tree extraction, on another uncached source path.
    post_source = Path(td) / 'race-post.psd'
    make_psd(post_source, (30, 40, 50))
    d_bytes = make_psd(Path(td) / 'fixture-d.psd', (120, 30, 220), visible_rgb=(15, 180, 90))
    real_builder = route.build_layer_tree
    def mutating_builder(psd, width, height):
      result = real_builder(psd, width, height)
      post_source.write_bytes(d_bytes)
      route.build_layer_tree = real_builder
      return result
    route.build_layer_tree = mutating_builder
    r_post_parse = ask(post_source)
    assert r_post_parse.status_code == 409, (r_post_parse.status_code, r_post_parse.get_json())
    assert 'sourceBytesSha256' not in r_post_parse.get_json()
    rows.append({'id':'post-parse-tree-composite-race','status':'PASS','http':409,'successDigestReturned':False,'cacheBypassed':'new path'})

    r_d = ask(post_source); assert r_d.status_code == 200 and r_d.get_json()['sourceBytesSha256'] == sha_file(post_source)
    assert parse_count['n'] == 6
    rows.append({'id':'stable-retry-after-races','status':'PASS','parseCount':parse_count['n'],'digest':r_d.get_json()['sourceBytesSha256']})

    missing = ask(Path(td) / 'missing.psd')
    assert missing.status_code == 404 and 'error' in missing.get_json()
    assert 'sourceBytesSha256' not in missing.get_json()
    malformed = Path(td) / 'malformed.psd'; malformed.write_bytes(b'not a PSD: controlled malformed source')
    bad = ask(malformed)
    assert bad.status_code == 500 and 'error' in bad.get_json()
    assert 'sourceBytesSha256' not in bad.get_json()
    rows.append({'id':'missing-and-malformed-file-errors','status':'PASS','missingHttp':missing.status_code,'malformedHttp':bad.status_code,'parseCount':parse_count['n']})
finally:
  PSDImage.open = real_open

print(json.dumps({'status':'PASS','psdToolsVersion':__import__('psd_tools').__version__,'fixture':'actual generated 8x8 PSD, two real pixel layers, one hidden','cases':len(rows),'rows':rows,'actualServerCacheLoader':True,'actualCandidateFlaskHandler':True,'actualSourceFingerprint':True,'rawBytesTransferred':False,'externalCalls':0},indent=2))
