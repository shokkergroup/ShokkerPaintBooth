"""Verify native layer-scoped recolour against lossless previews and saved alpha.

Opaque artwork preservation is exact; translucent edge appearance is reported,
not silently excluded from an all-pixels preservation claim.
"""
import base64
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[2]
evidence = root / '_codex_mcp_work/chatgpt-dev/59910'
names = ['paint-region-fixed-before-2026-10-10T04-01-38-472Z.json',
         'paint-region-fixed-after-2026-10-10T04-02-50-591Z.json',
         'paint-region-fixed-undo-2026-10-10T04-03-53-723Z.json']
records = [json.loads((evidence / n).read_text()) for n in names]
def tool(r, name):
    return json.JSONDecoder().raw_decode(next(c['text'] for c in r['calls'] if c['tool'] == name))[0]
state = [tool(r, 'spb_get_state') for r in records]
assert len(state[0]['layers']) == 42 and all(s['layers'] == state[0]['layers'] for s in state)
assert [len(s['zones']) for s in state] == [5, 6, 5]
assert state[0]['zones'] == state[2]['zones']
def settings(z):
    return {k: v for k, v in z.items() if k not in ['i', 'cells', 'share_pct', 'visible_pct']}
assert [settings(z) for z in state[0]['zones']] == [settings(z) for z in state[1]['zones'][1:]]
for name in ['spec_map', 'raw_layer_before_effects']:
    hashes = [next(i['sha256'] for i in r['images'] if i['name'] == name) for r in records]
    assert len(set(hashes)) == 1
paths = [evidence / f'region-fixed-{k}-native.png' for k in ['before', 'after', 'undo']]
a, b, u = [np.asarray(Image.open(p).convert('RGBA')).astype(np.int16) for p in paths]
assert a.shape == b.shape == u.shape == (1024, 1024, 4)
assert np.array_equal(a, u) and paths[0].read_bytes() == paths[2].read_bytes()
delta = np.max(abs(a - b), axis=2)
red = (a[:, :, 0] > 180) & (a[:, :, 1] < 50) & (a[:, :, 2] < 50)
green = (a[:, :, 1] > 180) & (a[:, :, 0] < 50) & (a[:, :, 2] < 50)
blue = (a[:, :, 2] > 180) & (a[:, :, 0] < 50) & (a[:, :, 1] < 50)
assert np.count_nonzero(red & (delta > 20)) > 250000
assert not np.any(delta[green]) and not np.any(delta[blue])
assert np.array_equal(a[:, :, 3], b[:, :, 3])
project = json.loads((root / '_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj').read_text())
artwork = []
for layer in project['layers']:
    if int(layer['id'].split('_')[1]) <= 23 or layer.get('visible') is False or layer['name'].lower() in ['mask', 'wire']:
        continue
    assert layer['opacity'] == 255
    im = Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA')
    mask = Image.new('L', (2048, 2048)); mask.paste(im.getchannel('A'), tuple(layer['bbox'][:2]))
    alpha = np.asarray(mask.resize((1024, 1024), Image.Resampling.BOX))
    opaque = alpha == 255
    assert opaque.any() and not np.any(delta[opaque]), layer['name']
    artwork.append({'id': layer['id'], 'name': layer['name'], 'fully_opaque_preview_pixels': int(opaque.sum()),
                    'opaque_changed': 0, 'partial_alpha_pixels_changed_over_20': int(np.count_nonzero((alpha > 0) & (alpha < 255) & (delta > 20)))})
assert len(artwork) == 7
check = tool(records[1], 'spb_check')
assert check['last_change']['still_applied'] and check['measured']['spec_px'] == 0
assert check['measured']['findings'], 'Preserve the coarse warning; this is not a clean broad acceptance'
ui = (evidence / 'region-fixed-after.txt').read_text(encoding='utf-8')
assert 'Your logos are untouched' in ui
out = {'pass': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'receipts': names,
       'red_core_changed': int(np.count_nonzero(red & (delta > 20))),
       'green_core_unchanged': int(green.sum()), 'blue_core_unchanged': int(blue.sum()), 'artwork': artwork,
       'all_42_layer_records_unchanged': True, 'five_existing_zone_settings_preserved': True,
       'one_scoped_zone_added': True, 'raw_pattern_and_spec_preview_unchanged': True,
       'native_undo_restores_state_and_lossless_preview_bytes': True,
       'unresolved': {'coarse_checker_findings': check['measured']['findings'],
                      'ui_disagrees_with_check': True, 'partial_alpha_edges_require_review': True},
       'scope': 'Native Offline Send/Run/Undo on ARCA with1024px lossless displayed output. Exact opaque artwork/green/blue preservation; partial-alpha edge changes are not adjudicated. Not full-resolution export, complete scheme or broad release acceptance.'}
(evidence / 'native-layer-region.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ['pass', 'red_core_changed', 'green_core_unchanged', 'blue_core_unchanged', 'unresolved']}))
