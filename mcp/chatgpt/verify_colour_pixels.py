"""Check saved lossless DOM preview pixels and actual read-only MCP receipts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
files = {kind: STATE / f'colour-edge-{kind}-native.png' for kind in ('before', 'after', 'undo')}
images = {kind: np.array(Image.open(file).convert('RGBA')) for kind, file in files.items()}
a, b, u = [images[k] for k in ('before', 'after', 'undo')]
assert a.shape == b.shape == u.shape, 'Compare equal-sized actual previews; never resize evidence'
changed = np.any(a != b, axis=2)
neutral = (a[:, :, 0] >= 220) & (a[:, :, 0] == a[:, :, 1]) & (a[:, :, 1] == a[:, :, 2]) & (a[:, :, 3] == 255)
navy = np.all(a[:, :, :3] == [25, 55, 110], axis=2)
assert changed.any() and not (neutral & changed).any()
assert navy.any() and (navy & changed).sum() == navy.sum()
assert np.array_equal(a, u), 'Undo must restore every displayed RGBA pixel'
assert files['before'].read_bytes() == files['undo'].read_bytes(), 'Actual PNG data URI bytes must also match'
receipts = {}
for kind in ('before', 'after', 'undo'):
    candidates = sorted(STATE.glob(f'paint-colour-edge-{kind}-*.json'))
    assert candidates
    file = candidates[-1]
    data = json.loads(file.read_text(encoding='utf-8'))
    receipts[kind] = {'file': file.name, 'data': {c['tool']: json.loads(c['text']) for c in data['calls'] if c['tool'] != 'spb_preview'}}
before = receipts['before']['data']['spb_get_state']
after = receipts['after']['data']['spb_get_state']
undo = receipts['undo']['data']['spb_get_state']
assert before['zones'] == undo['zones'], 'Undo restores the measured zone identities/order/settings too'
assert len(after['zones']) == len(before['zones']) + 1
check = receipts['after']['data']['spb_check']
assert check['last_change']['still_applied'] and not check['last_change']['taken_back_by_check']
assert check['measured']['verdict'] == 'ok' and not check['measured']['findings']
assert check['measured']['scope']['colour_target'] == 'navy'
assert check['measured']['coverage']['unit'] == 'preview' and check['measured']['coverage']['pct'] <= 100
assert not receipts['undo']['data']['spb_check']['last_change']['still_applied']
out = {'verified_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Disposable flat colour fixture; displayed 128x128 PNG previews, not full-resolution paint export or layered artwork',
       'size': [a.shape[1], a.shape[0]], 'changed_pixels': int(changed.sum()), 'protected_neutral_core_pixels': int(neutral.sum()), 'protected_neutral_core_changed': int((neutral & changed).sum()),
       'solid_navy_pixels': int(navy.sum()), 'solid_navy_changed': int((navy & changed).sum()), 'undo_changed_pixels': int(np.any(a != u, axis=2).sum()), 'undo_png_bytes_identical': True, 'zone_state_restored': True,
       'files': {k: {'file': v.name, 'sha256': hashlib.sha256(v.read_bytes()).hexdigest()} for k, v in files.items()},
       'mcp_receipts': {k: v['file'] for k, v in receipts.items()}, 'applied_coverage': check['measured']['coverage']}
destination = STATE / 'colour-edge-pixel-acceptance.json'
destination.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ('size', 'changed_pixels', 'protected_neutral_core_changed', 'solid_navy_changed', 'undo_changed_pixels', 'undo_png_bytes_identical', 'zone_state_restored')}))
