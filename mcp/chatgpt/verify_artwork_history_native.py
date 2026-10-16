"""Check recorded UI separation of artwork history and template revision."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
before = json.loads((E / 'artwork-history-native-before.json').read_text(encoding='utf-8'))
after = json.loads((E / 'artwork-history-native-after.json').read_text(encoding='utf-8'))
assert before == after, 'Exposed DOM paint view changed'
assert 'ARCA Chevy SS.tga' in before['source']
chat = (E / 'artwork-history-native-chat.txt').read_text(encoding='utf-8')
assert '2024 Season 3' in chat and 'This is historical vehicle artwork' in chat
assert 'not a verified downloadable template revision' in chat
assert 'insufficient reason to replace or modify your template' in chat
assert 'No verified template revision history is recorded here yet' in chat
assert 'Ferrari 296 GT3.psd (2048 × 2048)' in chat
assert chat.count('body vinyl texture was updated') == 1
receipt = json.loads((E / 'car-knowledge-mcp-2026-10-11T00-34-55-628Z.json').read_text(encoding='utf-8'))
for packet in [receipt['artwork'], receipt['artworkContext']['car_reference']]:
    assert packet['car']['id'] == 'ferrari296gt3'
    fact = next(f for f in packet['car']['facts'] if f['id'] == 'ferrari296gt3-body-vinyl-artwork-update-2024-s3')
    assert not fact['template_revision_verified'] and not fact['uv_mapping_verified']
result = {'pass': True, 'native_Offline_answers': 2, 'actual_MCP_car_and_context': True,
    'artwork_template_history_separate': True, 'DOM_paint_view_exact': True,
    'knowledge_sha256': hashlib.sha256((ROOT / 'mcp/chatgpt/car-knowledge/build/knowledge.json').read_bytes()).hexdigest(),
    'limits': ['No installed model inference or shared Claude adoption measured here',
               'DOM view comparison is not full-resolution/simulator verification',
               'Dated artwork statement establishes no current template revision or UV map']}
(E / 'artwork-history-native-acceptance.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
