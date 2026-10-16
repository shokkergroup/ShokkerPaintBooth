"""Compare real MCP inspection to saved native pixels and no-edit receipts."""
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
assert len(names) == 2 and all(Path(n).name == n and n.endswith('.json') for n in names)
records = [json.loads((evidence / n).read_text()) for n in names]
def call(record, tool):
    raw = next(c['text'] for c in record['calls'] if c['tool'] == tool)
    return json.JSONDecoder().raw_decode(raw)[0]
state = [call(r, 'spb_get_state') for r in records]
assert state[0]['layers'] == state[1]['layers']
assert state[0]['zones'] == state[1]['zones']
assert [(i['name'], i['sha256']) for i in records[0]['images'] if i['name'] != 'raw_layer_before_effects'] == [(i['name'], i['sha256']) for i in records[1]['images'] if i['name'] != 'raw_layer_before_effects']
report = call(records[1], 'spb_inspect_layer')
project = json.loads((root / '_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj').read_text())
layer = next(l for l in project['layers'] if l['id'] == 'psd_23')
pixels = np.asarray(Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA'))
flat = pixels.reshape(-1, 4); valid = flat[:, 3] > 0; rgb = flat[valid, :3].astype(np.int32)
assert report['nontransparent_pixels'] == int(valid.sum()) == 4194304
assert report['fully_opaque_pixels'] == int((flat[:, 3] == 255).sum()) == 4194304
bins = (rgb[:, 0] >> 4) * 256 + (rgb[:, 1] >> 4) * 16 + (rgb[:, 2] >> 4)
counts = np.bincount(bins, minlength=4096)
top = sorted(range(4096), key=lambda k: -counts[k])[:3]
expected = []
for k in top:
    colour = np.floor(rgb[bins == k].mean(axis=0) + 0.5).astype(int)
    expected.append({'colour': '#' + ''.join(f'{n:02x}' for n in colour), 'share_of_nontransparent_pixels_pct': np.floor(counts[k] / valid.sum() * 10000 + 0.5) / 100})
assert report['palette'][:3] == expected
assert report['layer']['hidden'] is True and report['opaque_full_canvas'] is True and report['geometry_verified'] is False
ui = (evidence / 'layer-inspection-offline.txt').read_text(encoding='utf-8')
assert 'Layer pixels' in ui and '4194304 nontransparent' in ui
assert all(p['colour'] in ui for p in expected)
assert 'Read the full article' not in ui and 'Paint by numbers' not in ui
receipt = {'pass': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'receipts': names,
    'complete_alpha_scan_matches_native_saved_pixels': True, 'dominant_palette_matches_independent_numpy_scan': True,
    'native_offline_same_facts_no_unrelated_guide_or_article_link': True,
    'all_42_layer_records_five_zones_and_returned_paint_spec_previews_unchanged': True,
    'scope': 'Native Offline answer and actual MCP inspection on hidden ARCA pattern. Raw source before effects; not model inference, UV geometry, full scheme or old-project recovery.'}
name = 'native-layer-inspection-' + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ') + '.json'
(evidence / name).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'receipt': name}))
