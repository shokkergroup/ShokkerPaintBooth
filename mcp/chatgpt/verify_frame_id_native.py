"""Frozen Oct10 native frame-ID evidence; no model, browser or paint writes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
PROJECTS = ROOT / '_release_evidence/chatgpt-dev/59910/projects'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

model_name = 'layered-model-probe-2026-10-10T12-40-17-818Z.json'
model = read(OUT / model_name)
assert model['exitCode'] == 0 and model['apiFallback'] is False
writes = [c for c in model['calls'] if c['tool'] == 'spb_do']
assert len(writes) == 1
assert writes[0]['arguments']['frame']['ops'][0]['target'] == {'kind': 'layer', 'layers': ['psd_0']}
names = ['Layered protection baseline', 'Layered frame-ID successor after', 'Layered frame-ID successor undo']
baseline, after, undo = [read(PROJECTS / (n + ' - private59910.spbproj')) for n in names]
assert len(baseline['layers']) == 3
assert baseline['layers'] == after['layers'] == undo['layers']
assert baseline['config']['zones'] == undo['config']['zones']
assert len(after['config']['zones']) == len(baseline['config']['zones']) + 1
added = [z for z in after['config']['zones'] if z not in baseline['config']['zones']]
assert len(added) == 1 and added[0]['sourceLayers'] == ['psd_0']
assert added[0]['sourceLayerBindings']['psd_0']['parts'] == ['Body']
before = read(OUT / model['fixtureReceipt'])
post = read(OUT / 'paint-resume-model-post-2026-10-10T12-41-19-161Z.json')
restored = read(OUT / 'paint-resume-model-undo-2026-10-10T12-44-19-856Z.json')
pixels = [(OUT / r['images'][0]['file']).read_bytes() for r in (before, post, restored)]
assert pixels[0] != pixels[1] and pixels[0] == pixels[2]
result = {
    'model_receipt': model_name,
    'scope': 'Synthetic three-layer fixture on private59910; native saved source records and tool JPEG preview. Not full output/export or UV proof.',
    'source_layers_exact': True,
    'added_zone_bound_to_body_id': True,
    'undo_zones_exact': True,
    'undo_preview_bytes_exact': True,
    'before_sha256': hashlib.sha256(pixels[0]).hexdigest(),
    'after_sha256': hashlib.sha256(pixels[1]).hexdigest(),
    'rendered_protected_artwork_preservation': 'unverified; fresh tool checker reports 756 estimated changed pixels',
}
(OUT / 'frame-id-native-successor-acceptance.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
