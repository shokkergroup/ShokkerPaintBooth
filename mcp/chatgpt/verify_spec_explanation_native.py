"""Native Offline topic/clarification plus actual MCP advice gate and context."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
QUERY = 'And what does spec amount 0% mean? Please explain only.'


def packet(pattern):
    files = sorted(OUT.glob(pattern))
    assert len(files) == 1, (pattern, len(files))
    return files[0], json.loads(files[0].read_text(encoding='utf-8'))


def value(pattern):
    file, p = packet(pattern)
    assert p['port'] == 59910 and not p['result'].get('isError'), file
    return json.loads(next(c['text'] for c in p['result']['content'] if c['type'] == 'text'))


before = value('spec-explanation-offline-repeat-before-*.json')
offline = value('spec-explanation-offline-repeat-after-*.json')
online = value('spec-explanation-online-after-*.json')
assert {k:v for k,v in before.items() if k != 'convo'} == {k:v for k,v in offline.items() if k != 'convo'}, 'Offline paint state must stay exact'
assert offline['convo']['history'][:len(before['convo']['history'])] == before['convo']['history']
assert [h['said'] for h in offline['convo']['history'][len(before['convo']['history']):]] == ['What are my current checker pattern settings? Explain only.', QUERY]
for key in ('last_change', 'last_colour_region', 'last_offer', 'last_target', 'live_changes', 'pending'):
    assert before['convo'][key] == offline['convo'][key], key
for key in before:
    if key not in ('car', 'editor_capabilities', 'convo'):
        assert offline[key] == online[key], key
assert offline['convo'] == online['convo'], 'Online question must not create an Offline edit target'
for key, old in before['editor_capabilities'].items():
    new = online['editor_capabilities'][key]
    if key == 'panel_locations':
        assert {k:v for k,v in old.items() if k != 'status'} == {k:v for k,v in new.items() if k != 'status'}
    else:
        assert old == new, key
assert online['car']['parts_not_known_yet'] == ['left side', 'right side', 'hood', 'roof', 'trunk']
text = (OUT / 'spec-explanation-offline-repeat-chat.txt').read_text(encoding='utf-8')
last = text.rsplit(QUERY, 1)[1]
for part in ('Diner Checkerboard', 'Pattern spec amount: 0%', '0% leaves that contribution off', 'does not switch off the underlying spec map', 'paint opacity and paint strength are separate', 'alpha lighting mask stays separate', 'Stored layer restriction: Body', 'Nothing has been changed or queued'):
    assert part in last, part
assert 'Pattern scale:' not in last, 'Spec follow-up should not become a scale answer'
stale = (OUT / 'spec-explanation-offline-stale-chat.txt').read_text(encoding='utf-8').rsplit(QUERY, 1)[1]
assert 'selected zone changed' in stale and 'Zone 1 which has no primary pattern' in stale
assert '0% leaves that contribution off' not in stale

inbox = value('explain-only-online-inbox-*.json')
context = value('explain-only-online-context-*.json')
assert inbox['messages'][-1]['text'] == QUERY
assert inbox['request_intent'] == context['request_intent']
assert inbox['request_intent']['explicit'] and inbox['request_intent']['mutation_allowed'] is False
assert context['editor_capabilities']['pattern_controls'] == online['editor_capabilities']['pattern_controls']
contract = context['editor_capabilities']['pattern_controls']['spec_amount_contract']
assert contract['scope'] == 'Primary pattern only' and 'Secondary pattern amounts' in contract['limits']
_, refused = packet('explain-only-online-write-refusal-*.json')
assert refused['result']['isError']
assert 'current buyer message is advice only' in refused['result']['content'][0]['text']
_, reply = packet('explain-only-online-reply-*.json')
assert not reply['result'].get('isError') and reply['arguments']['reply_to'] == inbox['reply_to']
chat = (OUT / 'spec-explanation-online-chat.txt').read_text(encoding='utf-8')
assert reply['arguments']['text'] in chat and '✦ ChatGPT (connected)' in chat

first = Image.open(OUT / 'spec-explanation-offline-before-preview.png').convert('RGBA')
assert first.size == (256, 256)
for name in ('spec-explanation-offline-after-preview.png', 'spec-explanation-online-after-preview.png'):
    other = Image.open(OUT / name).convert('RGBA')
    assert other.size == first.size
    assert all(ImageChops.difference(first, other).getextrema()[i] == (0, 0) for i in range(4)), name
_, cleanup = packet('project-cleanup-2026-10-10.json')
directory = Path(cleanup['directory'])
assert directory.resolve().is_relative_to(ROOT.resolve())
kept = {r['file']:r for r in cleanup['projects'] if r['action'] == 'keep'}
assert set(p.name for p in directory.glob('*.spbproj')) == set(kept)
assert all(hashlib.sha256((directory / n).read_bytes()).hexdigest() == r['sha256'] for n,r in kept.items())
result = {
    'pass': True, 'port': 59910, 'native_Offline_spec_followup_and_stale_selection_clarification': True,
    'native_MCP_explicit_advice_intent_and_write_refusal': True,
    'current_model_receives_common_renderer_contract_and_replies_in_app': True,
    'exposed_mutable_settings_and_layer_zone_summaries_exact': True,
    'preview_all_256_RGBA_pixels_exact': True, 'three_original_projects_only': True,
    'screenshots': ['spec-explanation-offline-repeat.png', 'spec-explanation-online.png'],
    'negative': 'relay-notice-followup-inbox-2026-10-10T19-05-06-715Z.json',
    'limits': 'One retained 3-layer fixture, bounded current primary-pattern settings and selected topic. Actual existing renderer numeric endpoints/alpha/secondary independence are separately tested, with a stub plate and no full render. Existing status warmed derived unnamed panels; no car geometry certification. Actual Claude inference/shared adoption/general arbitrary conversations/secondary-pattern inventory and raw raster/full-output acceptance remain open. No API calls, project saves or paint/render operations were performed; write attempt used current scale and was refused by the advice gate.',
}
(OUT / 'spec-explanation-native-acceptance.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:result[k] for k in ('pass', 'native_Offline_spec_followup_and_stale_selection_clarification', 'native_MCP_explicit_advice_intent_and_write_refusal', 'preview_all_256_RGBA_pixels_exact', 'three_original_projects_only')}))
