"""Reconcile two native ChatGPT waiting/answer cycles with actual MCP receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'


def packet(pattern):
    files = sorted(OUT.glob(pattern))
    assert len(files) == 1, (pattern, len(files))
    return files[0], json.loads(files[0].read_text(encoding='utf-8'))


def value(pattern):
    file, p = packet(pattern)
    assert p['port'] == 59910 and not p['result'].get('isError'), file
    return file, json.loads(next(x['text'] for x in p['result']['content'] if x['type'] == 'text'))


question = 'Explain my current checker pattern settings without changing anything.'
followup = 'And what does spec amount 0% mean? Please explain only.'
warning = 'ChatGPT is not listening yet, so your message is waiting for it.'
texts = {k: (OUT / ('relay-notice-' + k + '-chat.txt')).read_text(encoding='utf-8')
         for k in ('waiting', 'answered', 'followup-waiting', 'followup-answered')}
assert warning in texts['waiting'] and question in texts['waiting']
assert warning not in texts['answered'] and question in texts['answered']
assert texts['followup-waiting'].count(warning) == 1
assert question in texts['followup-waiting'] and followup in texts['followup-waiting']
assert warning not in texts['followup-answered']
assert question in texts['followup-answered'] and followup in texts['followup-answered']
assert 'Last answer received from ChatGPT' in texts['answered']
assert 'Last answer received from ChatGPT' in texts['followup-answered']
receipts = []
for label, text in (('', question), ('-followup', followup)):
    file, inbox = value('relay-notice' + label + '-inbox-*.json')
    receipts.append(file.name)
    assert inbox['messages'][-1]['text'] == text
    file, reply = packet('relay-notice' + label + '-reply-*.json')
    assert not reply['result'].get('isError')
    assert reply['arguments']['reply_to'] == inbox['reply_to']
    assert reply['arguments']['text'] in texts['followup-answered']
    receipts.append(file.name)

_, before = packet('relay-notice-before-*.json')
_, after = value('relay-notice-after-*.json')
_, final = value('relay-notice-final-state-*.json')
assert before['state'] == after, 'First conversation must preserve every exposed field'
# include_paint reads spb_status, whose existing CAR.ensure(false) warms derived
# unnamed panel observations. Verify this explicit difference, not a paint edit.
assert final['car'] and final['car']['parts_not_known_yet'] == ['left side', 'right side', 'hood', 'roof', 'trunk']
assert final['editor_capabilities']['panel_locations']['status'] == 'current'
for key in before['state']:
    if key not in ('car', 'editor_capabilities'):
        assert before['state'][key] == final[key], key
for key, old in before['state']['editor_capabilities'].items():
    new = final['editor_capabilities'][key]
    if key == 'panel_locations':
        assert {k:v for k,v in old.items() if k != 'status'} == {k:v for k,v in new.items() if k != 'status'}
    else:
        assert old == new, key
_, context = value('relay-notice-followup-live-context-*.json')
assert context['paint']['state']['data']['layers'] == final['layers']
assert context['paint']['state']['data']['zones'] == final['zones']
assert context['editor_capabilities']['pattern_controls'] == final['editor_capabilities']['pattern_controls']
turns = context['conversation']['turns']
assert any(t['role'] == 'assistant' and t.get('reply_to') == 28 for t in turns)
assert turns[-1]['text'] == followup

_, cleanup = packet('project-cleanup-2026-10-10.json')
projects = Path(cleanup['directory'])
assert projects.resolve().is_relative_to(ROOT.resolve())
retained = {x['file']: x for x in cleanup['projects'] if x['action'] == 'keep'}
assert set(p.name for p in projects.glob('*.spbproj')) == set(retained)
assert all(hashlib.sha256((projects / name).read_bytes()).hexdigest() == row['sha256']
           for name, row in retained.items())
result = {
    'pass': True, 'port': 59910, 'native_current_model_ChatGPT_MCP': True,
    'waiting_warning_present_before_each_answer': True,
    'matching_reply_retires_only_its_waiting_warning': True,
    'later_unanswered_warning_survives_previous_answer': True,
    'two_customer_questions_and_actual_answers_remain_visible': True,
    'all_exposed_mutable_paint_settings_and_summaries_exact': True,
    'derived_observation_change': 'Existing spb_status CAR.ensure(false) warmed unnamed panel observations and panel_locations status; no named parts are calibrated.',
    'layer_count': len(final['layers']), 'zone_count': len(final['zones']),
    'live_context_and_current_history': True,
    'three_original_projects_only': True,
    'receipts': receipts, 'screenshot': 'relay-notice-followup-answered.png',
    'limits': 'Native current-model ChatGPT two-turn acceptance on one private document; no paint edits, render, model API or project saves. Exposed mutable settings/summaries are exact; no raw raster or pixel parity claim. Live context calls existing spb_status and warms derived unnamed panels; no verified UV geometry. Other-provider/document/racing POST/malformed acknowledgement/restored-note/kill guards are generated-candidate tests. The explicit e.helper mismatch guard was added after the native run and is component-tested. Existing untracked/restored historical notes retain their text. Shared adoption, actual Claude/model parity and unattended setup remain open. Follow-up explain-only classifier returned unspecified and is the next separate gap; no mutation occurred.',
}
(OUT / 'relay-notice-native-acceptance.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ('pass', 'port', 'waiting_warning_present_before_each_answer', 'all_exposed_mutable_paint_settings_and_summaries_exact', 'three_original_projects_only')}))
