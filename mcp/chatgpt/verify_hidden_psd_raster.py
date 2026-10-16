"""Reproduce actual ARCA loss and test exact route proposal without a live edit."""
import base64
import hashlib
import io
import json
import logging
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image
from flask import Flask
from psd_tools import PSDImage
from psd_raster_candidate import candidate, rasterize_leaf_pixels

state = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
fixture = ROOT / '_release_evidence/chatgpt-dev/59910/fixtures/official-arca/ARCA Chevy SS.psd'
project = ROOT / '_release_evidence/chatgpt-dev/59910/projects/ARCA saved design options reopened - private59910.spbproj'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(fixture) == '232e7d9c446e8681d1393f123463449043fc1e2058bc6cc5565190271b2ba093'
psd = PSDImage.open(fixture)
leaf = psd[0][1][22]
assert leaf.name == 'car_pattern_001.tga'
assert not leaf.parent.visible and leaf.visible
visibility = [(id(l), l.visible) for l in psd.descendants()]
before = leaf.composite(force=True).convert('RGBA')
assert before.getchannel('A').getbbox() is None
saved = next(l for l in json.loads(project.read_text())['layers'] if l['id'] == 'psd_23')
saved_image = Image.open(io.BytesIO(base64.b64decode(saved['imgData'].split(',')[1]))).convert('RGBA')
assert saved_image.getchannel('A').getbbox() is None
expected = rasterize_leaf_pixels(leaf).convert('RGBA')
assert expected.getchannel('A').getbbox() is not None
assert expected.tobytes() == leaf.topil().convert('RGBA').tobytes()

# Exercise both actual route bodies with this real leaf under its hidden parent.
source_path = ROOT / 'server_routes/psd_import_routes.py'
namespace = {'__name__': 'private_hidden_psd_candidate'}
source = candidate(source_path.read_text(encoding='utf-8'))
exec(compile(source, str(source_path), 'exec'), namespace)
namespace['iter_leaf_layers'] = lambda _: [({'layer_key': '0.1.22', 'path': saved['path']}, leaf)]
app = Flask(__name__)
namespace['register_psd_import_routes'](app, require_internal_request=lambda: (True, None),
    sanitize_path=lambda path: (path, None), get_cached_psd=lambda _: psd, logger=logging.getLogger(__name__))
client = app.test_client()
single = client.post('/api/psd-layer', json={'psd_path': str(fixture), 'layer_path': ['Paintable Area', 'Car Patterns', leaf.name]})
bulk = client.post('/api/psd-rasterize-all', json={'psd_path': str(fixture)})
assert single.status_code == bulk.status_code == 200
for data in [single.get_json()['image'], bulk.get_json()['layers']['0.1.22']['image']]:
    actual = Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')
    assert actual.tobytes() == expected.tobytes()
assert visibility == [(id(l), l.visible) for l in psd.descendants()]

class Facade:
    visible = False
    def composite(self, force=False):
        assert force
        return expected
assert rasterize_leaf_pixels(Facade()) is expected
assert candidate(source_path.read_text(encoding='utf-8')) == source
try:
    candidate(source)
except ValueError:
    pass
else:
    raise AssertionError('Already patched source must not be patched twice')

receipt = {
    'pass': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
    'source_sha256': sha(source_path), 'fixture_sha256': sha(fixture), 'saved_project_sha256': sha(project),
    'candidate_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'leaf': leaf.name, 'saved_and_original_route_alpha_empty': True,
    'corrected_single_and_bulk_route_pixels_match_source': True,
    'all_49_node_visibility_flags_unchanged': len(visibility) == 49,
    'facade_signature_preserved': True,
    'scope': 'Real ARCA leaf, both route bodies, hidden ancestor. Bulk traversal reduced to one leaf; no native reimport or live installation yet. Existing saved empty rasters require explicit source recovery.'
}
assert receipt['all_49_node_visibility_flags_unchanged']
name = 'hidden-psd-raster-' + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ') + '.json'
(state / name).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'receipt': name, 'scope': receipt['scope']}))
