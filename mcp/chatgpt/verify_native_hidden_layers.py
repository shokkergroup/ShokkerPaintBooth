"""Verify a native saved reimport against original PSD pixels, not UI labels."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys

from PIL import Image
from psd_tools import PSDImage

root = Path(__file__).resolve().parents[2]
projects = root / '_release_evidence/chatgpt-dev/59910/projects'
name = sys.argv[1]
assert Path(name).name == name and name.endswith('.spbproj')
saved_path = projects / name
saved = json.loads(saved_path.read_text(encoding='utf-8'))
before_path = projects / 'ARCA saved design options reopened - private59910.spbproj'
before = json.loads(before_path.read_text(encoding='utf-8'))
fixture = root / '_release_evidence/chatgpt-dev/59910/fixtures/official-arca/ARCA Chevy SS.psd'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(fixture) == '232e7d9c446e8681d1393f123463449043fc1e2058bc6cc5565190271b2ba093'
psd = PSDImage.open(fixture)
assert len(saved['layers']) == len(before['layers']) == 42
patterns = []
for source in psd[0][1]:
    if source.is_group():
        continue
    row = next(l for l in saved['layers'] if l['name'] == source.name)
    old = next(l for l in before['layers'] if l['id'] == row['id'])
    image = Image.open(io.BytesIO(base64.b64decode(row['imgData'].split(',')[1]))).convert('RGBA')
    old_image = Image.open(io.BytesIO(base64.b64decode(old['imgData'].split(',')[1]))).convert('RGBA')
    assert old_image.getchannel('A').getbbox() is None
    expected = source.topil().convert('RGBA')
    assert image.size == expected.size
    assert image.tobytes() == expected.tobytes(), source.name
    assert image.getchannel('A').getbbox() is not None
    assert row['visible'] is False and row['ownVisible'] is True
    assert row['groupChain'] == old['groupChain']
    patterns.append({'id': row['id'], 'name': row['name'], 'pixel_sha256': hashlib.sha256(image.tobytes()).hexdigest()})
assert len(patterns) == 24
assert [(l['id'], l['visible']) for l in saved['layers']] == [(l['id'], l['visible']) for l in before['layers']]
receipt = {'pass': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
    'native_saved_project': name, 'project_sha256': sha(saved_path), 'original_failed_project_sha256': sha(before_path),
    'fixture_sha256': sha(fixture), 'patterns': patterns,
    'recovered_patterns_matching_original_pixels': 24, 'all_42_layer_visibility_flags_preserved': True,
    'scope': 'Native private59910 source import and Save. All24 formerly empty pattern rasters exactly match source. Does not repair existing saved projects, prove visible design edits, or establish material/geometry interpretation.'}
dest = root / '_codex_mcp_work/chatgpt-dev/59910' / ('native-hidden-raster-' + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ') + '.json')
dest.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'receipt': dest.name, 'recovered_patterns': len(patterns)}))
