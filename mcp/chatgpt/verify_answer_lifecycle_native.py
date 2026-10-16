"""Reconcile actual completed answers, rapid repeats, clarification and recovery."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
FIRST = 'What are my current checker pattern settings? Explain only.'
FOLLOW = 'And what does spec amount 0% mean? Please explain only.'


def packet(pattern):
    files = sorted(OUT.glob(pattern))
    assert len(files) == 1, (pattern, len(files))
    return files[0], json.loads(files[0].read_text(encoding='utf-8'))


def value(pattern):
    file, p = packet(pattern)
    assert p['port'] == 59910 and not p['result'].get('isError'), file
    return json.loads(next(c['text'] for c in p['result']['content'] if c['type'] == 'text'))


before = value('answer-lifecycle-native-before-*.json')
answers = value('answer-lifecycle-three-answers-state-*.json')
clarify = value('answer-lifecycle-clarification-state-*.json')
recovered = value('answer-lifecycle-recovered-state-*.json')
for state in (answers, recovered):
    assert {k:v for k,v in before.items() if k != 'convo'} == {k:v for k,v in state.items() if k != 'convo'}
hist = answers['convo']['history']
assert [h['said'] for h in hist] == [FIRST, FOLLOW, FOLLOW]
assert all(h['act'] == 'answer' for h in hist) and answers['convo']['pending'] is None
assert len(set(h['turn'] for h in hist)) == 3
timestamps = [int(h['turn'].split('-')[1]) for h in hist]
rapid_repeat_ms = timestamps[-1] - timestamps[-2]
assert 0 <= rapid_repeat_ms < 3000
assert clarify['convo']['history'][-1]['act'] == 'ask'
assert clarify['convo']['pending']['missing'] == ['answer']
assert 'selected zone changed' in clarify['convo']['pending']['asked']
assert 'Zone 1 which has no primary pattern' in clarify['convo']['pending']['asked']
assert [h['act'] for h in recovered['convo']['history']] == ['answer', 'answer', 'answer', 'ask', 'answer']
assert recovered['convo']['pending'] is None
for state in (answers, clarify, recovered):
    assert state['convo']['live_changes'] == 0
    for key in ('last_change', 'last_colour_region', 'last_offer', 'last_target'):
        assert state['convo'][key] is None
    assert state['layers'] == before['layers'] and state['zones'] == before['zones']

text = (OUT / 'answer-lifecycle-three-answers-chat.txt').read_text(encoding='utf-8')
assert text.count(FOLLOW) == 2 and text.count('Nothing has been changed or queued.') == 3
assert "Didn't do what I asked" not in text, 'Completed facts should not look like failed edits'
final_text = (OUT / 'answer-lifecycle-recovered-chat.txt').read_text(encoding='utf-8')
assert final_text.rsplit(FIRST, 1)[1].count('Nothing has been changed or queued.') == 1
assert "Didn't do what I asked" not in final_text.rsplit(FIRST, 1)[1]
context = value('answer-lifecycle-common-context-*.json')
assert context['project_design_context']['available']
assert context['project_design_context']['context'] == recovered['convo']
assert context['project_design_context']['session_only']
assert 'not approval' in context['project_design_context']['guidance']
assert context['paint']['state']['data']['layers'] == recovered['layers']
assert context['paint']['state']['data']['zones'] == recovered['zones']

first = Image.open(OUT / 'answer-lifecycle-before-preview.png').convert('RGBA')
final = Image.open(OUT / 'answer-lifecycle-after-preview.png').convert('RGBA')
assert first.size == final.size == (256, 256)
assert all(e == (0, 0) for e in ImageChops.difference(first, final).getextrema())
edited = value('answer-lifecycle-explicit-edit-state-*.json')
undone = value('answer-lifecycle-explicit-undo-state-*.json')
assert edited['convo']['history'][-1]['act'] == 'change' and edited['convo']['live_changes'] == 1
assert edited['convo']['last_change']['zone_ids'] == [recovered['editor_capabilities']['pattern_controls']['records'][0]['zone_id']]
assert undone['convo']['history'][-1]['undone'] and undone['convo']['last_change']['undone'] and undone['convo']['live_changes'] == 0
assert edited['convo']['pending'] is None and undone['convo']['pending'] is None
record = recovered['editor_capabilities']['pattern_controls']['records'][0]
changed_record = dict(edited['editor_capabilities']['pattern_controls']['records'][0])
assert changed_record.pop('scale') == .465 and record['scale'] == .6
assert changed_record == {k:v for k,v in record.items() if k != 'scale'}
assert undone['editor_capabilities']['pattern_controls'] == recovered['editor_capabilities']['pattern_controls']
assert edited['layers'] == undone['layers'] == recovered['layers']
assert edited['zones'] == undone['zones'] == recovered['zones']
arrays = {k:np.asarray(Image.open(OUT / name).convert('RGBA')) for k,name in [('before','answer-lifecycle-before-preview.png'),('edited','answer-lifecycle-edited-preview.png'),('undo','answer-lifecycle-undo-preview.png')]}
assert np.array_equal(arrays['before'], arrays['undo'])
changed = np.any(arrays['before'] != arrays['edited'], axis=2)
assert np.count_nonzero(changed) > 1000
protected = {}
for name in ('numbers', 'sponsors'):
    alpha = Image.open(ROOT / f'_release_evidence/chatgpt-dev/59910/fixtures/layered-protection-a-{name}.png').getchannel('A')
    core = alpha.resize((256, 256), Image.Resampling.LANCZOS).point(lambda x:255 if x == 255 else 0).filter(ImageFilter.MinFilter(3))
    mask = np.asarray(core) > 0
    count, harm = int(np.count_nonzero(mask)), int(np.count_nonzero(changed & mask))
    assert count > 2000 and harm == 0
    protected[name] = {'opaque_interior_preview_pixels':count, 'changed':harm}
_, cleanup = packet('project-cleanup-2026-10-10.json')
directory = Path(cleanup['directory'])
assert directory.resolve().is_relative_to(ROOT.resolve())
kept = {r['file']:r for r in cleanup['projects'] if r['action'] == 'keep'}
assert set(p.name for p in directory.glob('*.spbproj')) == set(kept)
assert all(hashlib.sha256((directory / n).read_bytes()).hexdigest() == r['sha256'] for n,r in kept.items())
result = {
    'pass': True, 'port': 59910,
    'native_three_completed_answers_are_answers_not_pending_asks': True,
    'rapid_identical_Send_events_remain_distinct': True, 'rapid_repeat_ms': rapid_repeat_ms,
    'genuine_stale_target_clarification_is_open': True, 'fresh_answer_closes_it': True,
    'shared_runtime_context_receives_same_answer_history_and_pending_state': True,
    'no_edit_or_offer_target_created_in_this_fixture': True,
    'exposed_mutable_paint_settings_and_summaries_exact': True,
    'all_256_RGBA_preview_pixels_exact': True, 'three_original_projects_only': True,
    'fresh_explicit_edit_commits_then_Undo_retires_change': True,
    'pattern_scale': '.6 -> .465 -> Undo .6', 'edited_preview_pixels': int(np.count_nonzero(changed)),
    'protected_preview_interiors': protected,
    'screenshot': 'answer-lifecycle-recovered.png',
    'negative': 'spec-explanation-offline-repeat-after-2026-10-10T19-14-57-088Z.json',
    'limits': 'Native Offline five-event factual pattern conversation plus explicit pattern edit/Undo and real read-only MCP context on one retained 3-layer fixture. Existing route/store/compiler APIs and local producer identity only; no shared source edits, model API, full render or project saves. Derived status may warm unnamed panel observations; no UV/raw raster/full-output/translucent-edge claim. Design-proposal/kill/copied-JSON feedback cases are generated Send + real kernel tests. Existing intentional soft topic slots, arbitrary async conversations, exact edit/Undo after every card type, actual Claude inference and shared adoption remain open. The actual committed zone ID is present, but the conversation last_change target label is empty; do not infer a calibrated part from it.',
}
(OUT / 'answer-lifecycle-native-acceptance.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:result[k] for k in ('pass', 'rapid_repeat_ms', 'fresh_answer_closes_it', 'shared_runtime_context_receives_same_answer_history_and_pending_state', 'all_256_RGBA_preview_pixels_exact')}))
