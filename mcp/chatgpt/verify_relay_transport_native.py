"""Bind a deliberate private outage, Offline answer and reconnect to exact paint state."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
here = root / 'mcp/chatgpt'

def obj(name):
    return json.loads((out / name).read_text(encoding='utf-8'))

def txt(name):
    return (out / name).read_text(encoding='utf-8')

before, after = [obj(f'named-material-native-arca-transport-{phase}.json') for phase in ['before', 'after']]
assert before['port'] == after['port'] == 59910
assert before['paint'] == after['paint'] and len(before['paint']) == 8
assert before['fixture_hashes'] == after['fixture_hashes'] and len(before['fixture_hashes']) == 2
dom_before, dom_after = [obj(f'relay-transport-native-{phase}.json') for phase in ['before', 'after']]
assert all(dom_before[k] == dom_after[k] for k in ['history', 'layers', 'selected'])
assert dom_before['draft'] == 'Where can I download the Mini Stock template?'
assert dom_after['draft'] == 'How do I open that template?'
assert 'Waiting for ChatGPT' in dom_after['connection']
assert 'could not be checked' not in dom_after['connection']
outage = txt('relay-transport-native-outage.txt')
assert 'The connection to SPB could not be checked' in outage
assert 'button "Use Offline Helper"' in outage
assert 'Where can I download the Mini Stock template?' in outage
assert 'connected and listening' not in outage
offline = txt('relay-transport-native-offline.txt')
assert 'Offline Helper' in offline and 'Where can I download the Mini Stock template?' in offline
answer = txt('relay-transport-native-offline-answer.txt')
assert 'HTTP check 2026-10-09' in answer and 'Mini Stock.psd (2048 × 2048)' in answer
assert 'do not certify the latest installed-build template or UV locations' in answer
assert 'built-in guidance · no AI used' in answer
server = obj('relay-transport-native-server.json')
assert server['port'] == 59910 and server['deliberate_test'] and not server['draft_submitted']
assert server['stopped_pid'] != server['restarted_pid'] and server['model_inferences'] == 0
assert server['restored_status']['inbox'] == server['restored_status']['inflight'] == 0
assert not server['restored_status']['listening']
names = ['relay-transport-native-server.json', 'relay-transport-native-before.json',
         'relay-transport-native-after.json', 'relay-transport-native-outage.txt',
         'relay-transport-native-offline.txt', 'relay-transport-native-offline-answer.txt',
         'relay-transport-native-reconnected.txt', 'relay-transport-native-outage.jpg',
         'relay-transport-native-offline-answer.jpg', 'relay-transport-native-reconnected.jpg',
         'named-material-native-arca-transport-before.json', 'named-material-native-arca-transport-after.json']
for name in names:
    if name.endswith('.jpg'):
        assert (out / name).read_bytes().startswith(b'\xff\xd8\xff')
files = [out / n for n in names] + [here / n for n in ['relay_transport_edits.py', 'test_relay_transport.cjs']]
hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
receipt = out / 'relay-transport-native-acceptance.json'
if '--freeze' in sys.argv:
    receipt.write_text(json.dumps({'schema': 'spb-relay-transport-native-acceptance/1',
        'actual_private_server_outage': True, 'native_offline_sends': 1,
        'model_inferences': 0, 'paint_fields': 8, 'original_fixtures': 2,
        'artifact_hashes': hashes, 'limits': ['Transport outage/reconnect, not a provider rate-limit test.',
            'Offline answer consumed already loaded local reference, not a cold-start/cache guarantee.',
            'ChatGPT panel native; Claude shared components only. Installed/package adoption open.',
            'Restored server and waiting badge do not prove a model listener is ready.',
            'Exposed paint state, not full raster or simulator verification.']}, indent=2) + '\n', encoding='utf-8')
assert obj(receipt.name)['artifact_hashes'] == hashes
print(json.dumps({'pass': True, 'actual_private_outage_and_reconnect': True,
    'native_offline_sends': 1, 'drafts_retained': 2, 'model_inferences': 0,
    'paint_fields_unchanged': 8, 'fixtures_unchanged': 2, 'frozen_artifacts': len(hashes)}))
