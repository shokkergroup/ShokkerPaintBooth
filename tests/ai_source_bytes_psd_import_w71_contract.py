import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types

from flask import Flask

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
CANDIDATE = ROOT / '_easy_claude_work/ai14h_w71_candidate'
ROUTE_PATH = CANDIDATE / 'server_routes/psd_import_routes.py'
SERVER_PATH = CANDIDATE / 'server.py'
FROZEN = CANDIDATE / 'frozen'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

# Inputs were captured before the candidate edit; verify they remain immutable.
freeze = json.loads((CANDIDATE / 'source-freeze.json').read_text(encoding='utf-8'))
for rel, expected in freeze['hashes'].items():
    assert sha(FROZEN / rel) == expected, f'frozen input changed: {rel}'

# Load actual helper module code, and actual import handler route code from candidate.
project_ast = ast.parse((FROZEN / 'project_routes.py').read_text(encoding='utf-8'))
fp_node = next(n for n in project_ast.body if isinstance(n, ast.FunctionDef) and n.name == '_source_fingerprint')
fp_module = ast.Module(body=[fp_node], type_ignores=[])
fp_globals = {'os':os, 'hashlib':hashlib}
exec(compile(fp_module, str(FROZEN / 'project_routes.py'), 'exec'), fp_globals)
_source_fingerprint = fp_globals['_source_fingerprint']

spec = importlib.util.spec_from_file_location('w71_psd_import_routes', ROUTE_PATH)
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)
route._source_fingerprint = _source_fingerprint

# Execute the real _get_cached_psd function body extracted from candidate server.py
# without importing/starting the application server.
server_ast = ast.parse(SERVER_PATH.read_text(encoding='utf-8'))
loader_node = next(n for n in server_ast.body if isinstance(n, ast.FunctionDef) and n.name == '_get_cached_psd')
loader_module = ast.Module(body=[loader_node], type_ignores=[])
loader_globals = {'os': os, '_psd_cache': {}}
exec(compile(loader_module, str(SERVER_PATH), 'exec'), loader_globals)

parse_count = {'n': 0}
class FakePSD:
    width = 7
    height = 5
    def __init__(self, content): self.content = content
    def __len__(self): return 1
    def composite(self): return FakeImage(self.content)
class FakeImage:
    def __init__(self, content): self.content = content
    def save(self, buf, fmt): buf.write(b'PNG:' + hashlib.sha256(self.content).digest())
def open_psd(path):
    parse_count['n'] += 1
    return FakePSD(Path(path).read_bytes())
psd_tools = types.ModuleType('psd_tools')
psd_tools.PSDImage = types.SimpleNamespace(open=open_psd)
sys.modules['psd_tools'] = psd_tools

cache_loader = loader_globals['_get_cached_psd']
app = Flask('w71-contract')
class Log:
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
route.build_layer_tree = lambda psd, width, height: [{'layer_key':'test-layer','testMarker':hashlib.sha256(psd.content).hexdigest()}]
route.register_psd_import_routes(
    app,
    require_internal_request=lambda: (True, None),
    sanitize_path=lambda p: (str(Path(p).resolve()), None),
    get_cached_psd=cache_loader,
    logger=Log(),
)
client = app.test_client()

with tempfile.TemporaryDirectory() as td:
    source = Path(td) / 'same-path.psd'
    source.write_bytes(b'first psd bytes')
    # Pin mtime so both the old response cache and old parser cache would collide.
    fixed_ns = 1_700_000_000_000_000_000
    os.utime(source, ns=(fixed_ns, fixed_ns))
    def ask():
        return client.post('/api/psd-import', json={'psd_path': str(source), 'thumbnail_size': 32}, headers={'X-Shokker-Internal':'1'})

    r1 = ask()
    assert r1.status_code == 200, (r1.status_code, r1.get_json())
    body1 = r1.get_json()
    sha1 = _source_fingerprint(str(source))['sha256']
    assert body1['sourceBytesSha256'] == sha1
    assert b'first psd bytes' not in r1.data, 'raw source bytes must not be echoed in response'
    assert {'success','width','height','layers','composite','psd_path'}.issubset(body1), 'legacy response keys must remain'
    assert parse_count['n'] == 1

    # Identical current bytes reuse the route response without a second parse.
    r1b = ask()
    assert r1b.status_code == 200 and r1b.get_json()['sourceBytesSha256'] == sha1
    assert parse_count['n'] == 1

    # Same path AND exactly preserved mtime, different bytes: both digest-aware
    # response and parser caches must invalidate and deliver the new parse.
    source.write_bytes(b'second psd bytes, different hidden layer data')
    os.utime(source, ns=(fixed_ns, fixed_ns))
    sha2 = _source_fingerprint(str(source))['sha256']
    assert sha2 != sha1
    r2 = ask()
    assert r2.status_code == 200, (r2.status_code, r2.get_json())
    body2 = r2.get_json()
    assert body2['sourceBytesSha256'] == sha2
    assert body2['composite'] != body1['composite'], 'response should come from replacement parsed bytes'
    assert b'second psd bytes' not in r2.data, 'raw source bytes must not be echoed in response'
    assert parse_count['n'] == 2

    # Replacement during handler parsing/compositing is rejected and not returned
    # under the original digest. This actual handler seam calls the live route code.
    source.write_bytes(b'third initial')
    os.utime(source, ns=(fixed_ns, fixed_ns))
    mutate = {'enabled': True}
    original_builder = route.build_layer_tree
    def mutating_builder(psd, width, height):
        result = original_builder(psd, width, height)
        if mutate['enabled']:
            mutate['enabled'] = False
            source.write_bytes(b'changed while parse was in progress')
            os.utime(source, ns=(fixed_ns, fixed_ns))
        return result
    route.build_layer_tree = mutating_builder
    r3 = ask()
    assert r3.status_code == 409 and 'changed during import' in r3.get_json().get('error',''), (r3.status_code, r3.get_json())
    route.build_layer_tree = original_builder
    assert 'sourceBytesSha256' not in r3.get_json()

    # Stable retry succeeds and returns the actual current byte digest.
    r4 = ask()
    assert r4.status_code == 200 and r4.get_json()['sourceBytesSha256'] == _source_fingerprint(str(source))['sha256']

print(json.dumps({'status':'PASS','cases':5,'parseCount':parse_count['n'],'cacheSameMtimeReplacement':'reparsed','changeDuringParse':'409 rejected','transfer':'digest metadata only; no raw file bytes in response'}, indent=2))
