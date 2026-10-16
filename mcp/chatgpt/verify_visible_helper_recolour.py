"""Native exact-colour recolour must preserve visible Mask and overlying artwork.

The separate subscription retry rolled itself back; do not represent these
Offline lossless captures as a model-session retained output.
"""
import base64
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[2]
evidence = root / '_codex_mcp_work/chatgpt-dev/59910'
names = sys.argv[1:]
assert len(names) == 4 and all(Path(n).name == n and n.endswith('.json') for n in names)
records = [json.loads((evidence / n).read_text()) for n in names[:3]]
session = json.loads((evidence / names[3]).read_text())
def tool(r, name):
    return json.JSONDecoder().raw_decode(next(c['text'] for c in r['calls'] if c['tool'] == name))[0]
states = [tool(r, 'spb_get_state') for r in records]
assert all(s['layers'] == states[0]['layers'] for s in states) and len(states[0]['layers']) == 42
assert states[0]['zones'] == states[2]['zones']
assert len(states[1]['zones']) == len(states[0]['zones']) + 1
assert session['exitCode'] == 0 and session['authentication'] == 'ChatGPT' and session['apiFallback'] is False
assert any(c['tool'] == 'spb_undo' and c['status'] == 'completed' for c in session['calls'])
for image_name in ['raw_layer_before_effects', 'spec_map']:
    assert len({next(i['sha256'] for i in r['images'] if i['name'] == image_name) for r in records}) == 1
files = [evidence / ('helper-ownership-' + k + '-native.png') for k in ['before', 'after', 'undo']]
a, b, u = [np.asarray(Image.open(p).convert('RGBA')).astype(np.int16) for p in files]
assert a.shape == b.shape == u.shape == (1024, 1024, 4)
assert np.array_equal(a, u) and files[0].read_bytes() == files[2].read_bytes()
delta = np.max(abs(a - b), axis=2)
red = (a[:, :, 0] > 180) & (a[:, :, 1] < 50) & (a[:, :, 2] < 50)
green = (a[:, :, 1] > 180) & (a[:, :, 0] < 50) & (a[:, :, 2] < 50)
blue = (a[:, :, 2] > 180) & (a[:, :, 0] < 50) & (a[:, :, 1] < 50)
brown = np.all(a[:, :, :3] == [83, 71, 65], axis=2)
assert np.count_nonzero(red & (delta > 20)) > 200000
assert not np.any(delta[green]) and not np.any(delta[blue])
assert brown.sum() > 157000 and not np.any(delta[brown]), 'The original Mask spill must be gone exactly'
assert np.array_equal(a[:, :, 3], b[:, :, 3])
project = json.loads((root / '_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj').read_text())
visible = {l['id'] for l in states[0]['layers'] if not l.get('hidden', False)}
artwork = []
for l in project['layers']:
    if int(l['id'].split('_')[1]) <= 23 or l['id'] not in visible:
        continue
    im = Image.open(io.BytesIO(base64.b64decode(l['imgData'].split(',')[1]))).convert('RGBA')
    mask = Image.new('L', (2048, 2048)); mask.paste(im.getchannel('A'), tuple(l['bbox'][:2]))
    alpha = np.asarray(mask.resize((1024, 1024), Image.Resampling.BOX))
    opaque = alpha == 255
    assert opaque.any() and not np.any(delta[opaque]), l['name']
    artwork.append({'id': l['id'], 'name': l['name'], 'opaque_preview_pixels': int(opaque.sum()),
                    'opaque_changed': 0, 'partial_alpha_changed_over_20': int(np.count_nonzero((alpha > 0) & (alpha < 255) & (delta > 20)))})
assert any(l['name'] == 'Mask' for l in artwork)
check = tool(records[1], 'spb_check')
out = {'pass': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'receipts': names,
       'red_core_changed': int(np.count_nonzero(red & (delta > 20))), 'green_core_unchanged': int(green.sum()),
       'blue_core_unchanged': int(blue.sum()), 'brown_Mask_pixels_unchanged': int(brown.sum()), 'artwork': artwork,
       'layer_records_spec_raw_pattern_unchanged': True, 'undo_exact_state_and_lossless_png': True,
       'measured_findings': check['measured'].get('findings'),
       'scope': 'Native Offline exact-colour Run and1024px lossless preview. Separate actual subscription retry used MCP Undo after an edge warning; its restored state is independently checked. Opaque visible artwork and guides preserved exactly; partial-alpha edges reported separately. Not full-resolution export, complete scheme, other template coverage or shared release.'}
(evidence / 'native-visible-helper-recolour.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ['pass', 'red_core_changed', 'brown_Mask_pixels_unchanged', 'measured_findings']}))
