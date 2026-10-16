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

run = read('context-session-probe-2026-10-10T20-59-42-484Z.json')
assert run['exitCode'] == 0 and not run['errors']
assert run['authentication'] == 'ChatGPT' and run['apiFallback'] is False
assert run['isolatedSubscription'] and run['userConfigIgnored']
assert run['chosenModel'] == 'gpt-6.1-sol'
assert [c['tool'] for c in run['calls']] == ['spb_wait_for_message', 'spb_assistant_context', 'spb_reply']
assert all(c['status'] == 'completed' for c in run['calls'])
inbox = text_result(run['calls'][0])
reply = run['calls'][2]
assert inbox['reply_to'] == reply['arguments']['reply_to'] == 4
assert run['calls'][1]['arguments']['query'] == inbox['messages'][-1]['text']
assert inbox['request_intent']['mutation_allowed'] is False
assert text_result(reply)['shown_in_app'] is True and run['delivery']['pass']
assert ' '.join(reply['arguments']['text'].split()) in ' '.join((OUT / 'subscription-native-chat.txt').read_text(encoding='utf-8').split())

before = read('paint-subscription-before-2026-10-10T20-57-23-792Z.json')
after = read('paint-subscription-after-2026-10-10T21-00-37-088Z.json')
def state(receipt):
    return json.loads(next(c['text'] for c in receipt['calls'] if c['tool'] == 'spb_get_state'))
a, b = state(before), state(after)
keys = ['car','grid','layers','max_zones','paint_colours','selected_zone','template_identity','zones','editor_capabilities','recent_changes']
assert {k:a[k] for k in keys} == {k:b[k] for k in keys}
selection = a['editor_capabilities']['layer_materials']['selection']['records']
assert len(selection) == 1 and selection[0]['name'] == 'Sponsors' and selection[0]['state'] == 'none'
assert 'gloss (Gloss)' in a['zones'][4]['look'] and 'only on layer: Body' in a['zones'][4]['covers']
x = np.asarray(Image.open(OUT / before['images'][0]['file']).convert('RGBA'))
y = np.asarray(Image.open(OUT / after['images'][0]['file']).convert('RGBA'))
assert np.array_equal(x, y)
cleanup = read('project-cleanup-2026-10-10.json')
kept = [r for r in cleanup['projects'] if r['action'] == 'keep']
assert len(kept) == 2
for r in kept:
    assert hashlib.sha256((Path(cleanup['directory']) / r['file']).read_bytes()).hexdigest() == r['sha256']
result = {'pass':True,'scope':'One actual private59910 ChatGPT-plan reply from the installed newer client',
          'fresh_buyer_seq':4,'native_reply_shown':True,'paint_settings_exact':True,
          'decoded_returned_preview_exact':True,'preview_size':list(x.shape[:2]),'new_project_saves':0,
          'retained_fixture_hashes_match':True,'api_fallback':False,
          'negative':'Older PATH CLI0.124.0 rejected the configured model before any MCP call; retained failure receipt.',
          'limits':['Authenticated preflight does not establish model entitlement or active listening.',
                    'One bounded read-only exchange; no automatic next-message wake, reconnect, writes or installer acceptance.',
                    f'Returned preview is a{x.shape[1]}x{x.shape[0]} JPEG; this is not full-resolution source/spec-output proof.',
                    'Commercial direct Sign in with ChatGPT eligibility remains unverified.']}
(OUT / 'subscription-native-acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
