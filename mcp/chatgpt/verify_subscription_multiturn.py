"""Bounded ChatGPT-plan listener proof; does not claim unattended availability."""
from pathlib import Path
import hashlib, json
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'

def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

def text_result(call):
    return json.loads(next(c['text'] for c in call['result']['content'] if c['type'] == 'text'))

run = read('context-session-probe-2026-10-10T21-45-44-527Z.json')
assert run['exitCode'] == 0 and not run['errors']
assert run['authentication'] == 'ChatGPT' and run['apiFallback'] is False
assert run['isolatedSubscription'] and run['userConfigIgnored']
assert run['chosenModel'] == 'gpt-6.1-sol'
assert [c['tool'] for c in run['calls']] == ['spb_wait_for_message', 'spb_assistant_context', 'spb_reply'] * 2
assert all(c['status'] == 'completed' for c in run['calls'])
sequences = []
for offset in (0, 3):
    inbox = text_result(run['calls'][offset]); context = run['calls'][offset + 1]; reply = run['calls'][offset + 2]
    assert inbox['reply_to'] == reply['arguments']['reply_to']
    sequences.append(inbox['reply_to'])
    assert context['arguments']['query'] == inbox['messages'][-1]['text']
    assert inbox['request_intent']['mutation_allowed'] is False
    assert text_result(reply)['shown_in_app'] is True
    assert ' '.join(reply['arguments']['text'].split()) in ' '.join((OUT / 'subscription-multiturn-native-chat.txt').read_text(encoding='utf-8').split())
assert sequences == [7, 10] and run['delivery']['pass'] and run['delivery']['delivered'] == 2

before = read('paint-subscription-multiturn-before-2026-10-10T21-45-37-611Z.json')
after = read('paint-subscription-multiturn-after-2026-10-10T21-46-41-064Z.json')
def state(receipt):
    return json.loads(next(c['text'] for c in receipt['calls'] if c['tool'] == 'spb_get_state'))
a, b = state(before), state(after)
keys = ['grid','layers','max_zones','paint_colours','selected_zone','zones','recent_changes']
assert {k:a[k] for k in keys} == {k:b[k] for k in keys}
assert {k:v for k,v in a['template_identity'].items() if k!='recognized_layout'} == {k:v for k,v in b['template_identity'].items() if k!='recognized_layout'}
assert {k:v for k,v in a['editor_capabilities'].items() if k!='panel_locations'} == {k:v for k,v in b['editor_capabilities'].items() if k!='panel_locations'}
assert a['car'] is None and b['car']['recognised_as']=='NASCAR Cup Chevrolet SS (recognised by layout)'

assert len(a['layers']) == 42
x = np.asarray(Image.open(OUT / before['images'][0]['file']).convert('RGBA'))
y = np.asarray(Image.open(OUT / after['images'][0]['file']).convert('RGBA'))
assert np.array_equal(x, y)
cleanup = read('project-cleanup-2026-10-10.json')
kept = [r for r in cleanup['projects'] if r['action'] == 'keep']
assert len(kept) == 2
for r in kept:
    assert hashlib.sha256((Path(cleanup['directory']) / r['file']).read_bytes()).hexdigest() == r['sha256']
result = {'pass':True,'scope':'Two successive actual private59910 ChatGPT-plan replies in one installed-client session',
          'fresh_buyer_sequences':sequences,'fresh_context_each_turn':True,'native_replies_shown':2,
          'paint_settings_exact':True,'derived_metadata_changed':['car','template_identity.recognized_layout','editor_capabilities.panel_locations'],'decoded_returned_preview_exact':True,'preview_size':list(x.shape[:2]),
          'new_project_saves':0,'retained_fixture_hashes_match':True,'api_fallback':False,
          'limits':['Bounded worker stops after two replies; unattended reconnect is not proven.',
                    'Legacy recognition warmed and mislabelled the verified ARCA source as NASCAR Cup; geometry/identity context guards staged afterward, not proven by this run.',
                    'Returned preview is768px JPEG, not full-resolution raster or simulator proof.',
                    'Shared/package adoption and actual Claude parity remain open.']}
(OUT / 'subscription-multiturn-native-acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
