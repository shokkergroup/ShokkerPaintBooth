"""Verify frozen native Send + current MCP evidence, without another inference."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
files = []


def read(name):
    p = out / name
    files.append(p)
    return json.loads(p.read_text(encoding='utf-8'))


def text(name):
    p = out / name
    files.append(p)
    return p.read_text(encoding='utf-8')


for suffix in ['', 'arca-', 'arca-online-']:
    before = read('named-material-native-' + suffix + 'before.json')
    after = read('named-material-native-' + suffix + 'after.json')
    assert before['port'] == after['port'] == 59910
    assert before['paint'] == after['paint'] and len(before['paint']) == 8
    assert before['fixture_hashes'] == after['fixture_hashes'] and len(before['fixture_hashes']) == 2
    assert before['focused'] == before['context_focused']
    assert after['focused'] == after['context_focused']

single = read('named-material-native-dom.json')
assert single['native_send'] and single['before'] == single['after']
assert 'Windshield Banner' in single['before']['selection']
assert 'Paintable Area / Sponsors: None' in text('named-material-native.txt')
arca = read('named-material-native-arca-dom.json')
assert arca['native_sends'] == 3 and arca['before'] == arca['after']
duplicates = text('named-material-native-arca-duplicates.txt')
assert 'That name matches 4 current layers.' in duplicates
for identity in ['psd_0', 'psd_37', 'psd_38', 'psd_40']:
    assert '[' + identity + ']' in duplicates
assert duplicates.count('no stored Layer Material assignment (hidden; no material contribution)') == 3
exact = text('named-material-native-arca-exact.txt').split('- generic: What material is on Paintable Area / Base Paint?', 1)[1]
assert 'Paintable Area / Base Paint: None' in exact and 'psd_37' not in exact
missing = text('named-material-native-arca-missing.txt').split('- generic: What material is on Sponsors?', 1)[1]
assert 'cannot find an exact loaded layer' in missing and 'not substituted the selected layer' in missing
assert 'Sponsors: None' not in missing
assert single['before']['source'] != arca['before']['source']

online = read('named-material-native-online-dom.json')
assert online['native_send'] and online['model_inferences'] == 1 and online['before'] == online['after']
sent = text('named-material-native-online-sent.txt')
assert 'Sending…' in sent and 'Your draft stays here' in sent
assert 'What material is on Base Paint? Explain only.' in sent.split('- textbox "Tell ChatGPT what you want', 1)[1]
working = text('named-material-native-online-working.txt')
assert 'ChatGPT is working on it' in working and 'Sending…' not in working
assert 'textbox "Tell ChatGPT what you want… (Enter sends)"\n' in working
answer = text('named-material-native-online-answer.txt')
assert 'Last answer received from ChatGPT.' in answer and 'four loaded layers' in answer
assert 'All four have no Layer Material assigned.' in answer

worker = read('subscription-listener-turn-2026-10-11T02-11-56-828Z.json')
assert worker['authentication'] == 'ChatGPT' and worker['apiFallback'] is False
assert worker['exitCode'] == 0 and not worker['errors']
assert [c['tool'] for c in worker['calls']] == ['spb_wait_for_message', 'spb_assistant_context', 'spb_reply']
assert all(c['status'] == 'completed' and not c['result'].get('isError') for c in worker['calls'])
wait, context, reply = worker['calls']
assert context['arguments'] == {'query': online['query'], 'include_paint': True}
packet = json.loads(context['result']['content'][0]['text'])
named = packet['editor_capabilities']['layer_materials']['named_layers']
assert named['matched_layers'] == 4 and named['ambiguous'] is True
assert all(r['state'] == 'none' for r in named['records'])
assert sum(r['visible'] is False for r in named['records']) == 3
assert reply['arguments']['reply_to'] == worker['reply_to'] == json.loads(wait['result']['content'][0]['text'])['reply_to']
assert json.loads(reply['result']['content'][0]['text'])['shown_in_app'] is True
assert reply['arguments']['text'] in answer
for name in ['named-material-native.jpg', 'named-material-native-arca-duplicates.jpg', 'named-material-native-online-answer.jpg']:
    p = out / name
    assert p.read_bytes().startswith(b'\xff\xd8\xff')
    files.append(p)

proof = {'checked_at': online['checked_at'], 'native_offline_sends': 4, 'native_subscription_sends': 1,
         'actual_model_turns': 1, 'api_fallback': False, 'source_switch_invalidates_old_target': True,
         'exact_paint_fields_per_phase': 8, 'retained_original_fixtures': 2,
         'artifact_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
         'limits': ['Private Chrome59910 acceptance; shared/package adoption and installed Claude parity remain open.',
                    'Named stored materials and exposed state preservation; not final pixel/simulator output verification.',
                    'One bounded worker stops after its reply; persistent startup/wake and arbitrary crash recovery not proved.']}
(out / 'named-material-native-acceptance.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict({k: v for k, v in proof.items() if k not in ['artifact_hashes', 'limits']}, verified_artifacts=len(proof['artifact_hashes']))))
