"""Freeze/check exact private native Offline and subscription template guidance."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
here = root / 'mcp/chatgpt'
url = 'https://ir-core-sites.iracing.com/members/member_images/cars/car_templates/191_template_MNSTK.zip'
query = 'Where can I download the Mini Stock template? Please include the link and explain whether it is verified as the latest version.'
def obj(name):
    return json.loads((out / name).read_text(encoding='utf-8'))
def txt(name):
    return (out / name).read_text(encoding='utf-8')

files = []
for label in ['download-final', 'download-online']:
    pair = [f'named-material-native-arca-{label}-{phase}.json' for phase in ['before', 'after']]
    before, after = map(obj, pair)
    assert before['port'] == after['port'] == 59910
    assert before['paint'] == after['paint'] and len(before['paint']) == 8
    assert before['fixture_hashes'] == after['fixture_hashes'] and len(before['fixture_hashes']) == 2
    files += [out / name for name in pair]
for suffix in ['first', 'followup', 'history', 'revision', 'sources']:
    files.append(out / f'template-download-native-{suffix}.txt')
first, follow = txt('template-download-native-first.txt'), txt('template-download-native-followup.txt')
assert 'Mini Stock.psd (2048 × 2048)' in first and 'HTTP check 2026-10-09' in first
assert 'do not certify the latest installed-build template' in first
assert 'Where can I get it?' in follow and follow.count('The official ZIP link is in Reference details') == 2
assert '2024 Season 4 Patch 2' in txt('template-download-native-history.txt')
assert 'not Dirt Mini Stock' in txt('template-download-native-history.txt')
assert 'No verified template revision history' in txt('template-download-native-revision.txt')
assert f'/url: {url}' in txt('template-download-native-sources.txt')
for suffix, sends in [('', 4), ('-online', 1)]:
    name = f'template-download-native{suffix}-dom.json'
    dom = obj(name)
    assert dom['port'] == 59910 and dom['native_sends'] == sends
    assert dom['before'] == dom['after'] and dom['dom_fields_unchanged']
    assert dom['before']['history'] == '0 actions'
    files.append(out / name)
sent_name, answer_name = 'template-download-native-online-sent.txt', 'template-download-native-online-answer.txt'
assert 'Sending…' in txt(sent_name) and 'Your draft stays here' in txt(sent_name)
assert url in txt(answer_name) and 'not verified as the latest revision' in txt(answer_name)
assert 'Your current source is named ARCA Chevy SS.tga' in txt(answer_name)
files += [out / sent_name, out / answer_name]
for name in ['template-download-native-sources.jpg', 'template-download-native-online-answer.jpg']:
    assert (out / name).read_bytes().startswith(b'\xff\xd8\xff')
    files.append(out / name)
mcp_name = 'template-download-mcp-2026-10-11T02-35-36-730Z.json'
mcp = obj(mcp_name)
assert mcp['paint_reads'] == mcp['model_inferences'] == 0
assert mcp['context']['car_reference']['car']['template_download'] == mcp['direct']['car']['template_download']
assert mcp['direct']['car']['template_download']['url'] == url
files.append(out / mcp_name)
worker_name = 'subscription-listener-turn-2026-10-11T02-39-10-011Z.json'
worker = obj(worker_name)
assert worker['port'] == 59910 and worker['exitCode'] == 0 and not worker['errors']
assert worker['authentication'] == 'ChatGPT' and not worker['apiFallback']
assert [c['tool'] for c in worker['calls']] == ['spb_wait_for_message', 'spb_assistant_context', 'spb_reply']
assert all(c['status'] == 'completed' and not c['result'].get('isError') for c in worker['calls'])
wait, context, reply = worker['calls']
assert context['arguments']['query'] == query and context['arguments']['include_paint']
guide = json.loads(context['result']['content'][0]['text'])['car_reference']['car']['template_download']
assert guide['url'] == url and guide['available'] and not guide['latest_revision_verified']
assert url in reply['arguments']['text'] and reply['arguments']['reply_to'] == worker['reply_to']
assert json.loads(reply['result']['content'][0]['text'])['shown_in_app']
files.append(out / worker_name)
for relative in ['car-knowledge/core.js', 'car-knowledge/offline-answer.js', 'assistant-context.cjs',
    'car-knowledge/test_template_download.cjs', 'car-knowledge/test_ministock_history.cjs',
    'car-knowledge/integrate_ministock.py', 'car-knowledge/probe_mcp.cjs',
    'car-knowledge/research/ministock_primary/runtime_facts.json',
    'car-knowledge/research/ministock_primary/parent-review.json',
    'car-knowledge/build/knowledge.json', 'car-knowledge/build/cars.json', 'car-knowledge/build/manifest.json']:
    # Native model consumed the frozen bundle, not future unrelated car additions.
    if relative.startswith('car-knowledge/build/') or relative in ['car-knowledge/core.js', 'car-knowledge/offline-answer.js', 'car-knowledge/probe_mcp.cjs', 'assistant-context.cjs']:
        archived = out / 'template-download-native-bundle' / Path(relative).name
        files.append(archived if archived.exists() else here / relative)
    else:
        files.append(here / relative)
hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
receipt = out / 'template-download-native-acceptance.json'
if '--freeze' in sys.argv:
    receipt.write_text(json.dumps({'schema': 'spb-template-download-native-acceptance/1',
        'native_offline_sends': 4, 'native_subscription_sends': 1, 'actual_model_turns': 1,
        'paint_fields_per_phase': 8, 'retained_original_fixtures': 2, 'artifact_hashes': hashes,
        'limits': ['Private staged acceptance; shared/package/installed Claude adoption remains open.',
            'Stored archive evidence is not latest-version, current-placement, compatibility or UV proof.',
            'Exact exposed state preservation, not full raster or simulator validation.',
            'The bounded worker is stopped after one reply; automatic startup/wake is open.']}, indent=2) + '\n', encoding='utf-8')
assert obj(receipt.name)['artifact_hashes'] == hashes
print(json.dumps({'pass': True, 'native_offline_sends': 4, 'native_subscription_sends': 1,
    'model_inferences': 1, 'paint_fields_per_phase': 8, 'fixtures': 2,
    'same_guide_consumed_by_model': True, 'frozen_artifacts': len(hashes)}))
