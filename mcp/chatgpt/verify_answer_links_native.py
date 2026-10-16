"""Freeze/check one actual native ChatGPT reply rendered by the common formatter."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
out = root / '_codex_mcp_work/chatgpt-dev/59910'

def obj(name):
    return json.loads((out / name).read_text(encoding='utf-8'))

url = 'https://ir-core-sites.iracing.com/members/member_images/cars/car_templates/191_template_MNSTK.zip'
query = 'Where can I download the Mini Stock template? Use a Markdown link and tell me whether it is verified as the latest version.'
names = ['answer-links-native-before.json', 'answer-links-native-sent.txt',
         'answer-links-native-answer.txt', 'answer-links-native-answer.jpg', 'answer-links-native-dom.json',
         'named-material-native-arca-source-links-before.json',
         'named-material-native-arca-source-links-after.json',
         'subscription-listener-turn-2026-10-11T02-50-02-004Z.json']
before, after = [obj(f'named-material-native-arca-source-links-{phase}.json') for phase in ['before', 'after']]
assert before['port'] == after['port'] == 59910
assert before['paint'] == after['paint'] and len(before['paint']) == 8
assert before['fixture_hashes'] == after['fixture_hashes'] and len(before['fixture_hashes']) == 2
assert obj('answer-links-native-before.json')['existing_reply_url_links'] == 0
dom = obj('answer-links-native-dom.json')
assert dom['native_send'] and dom['model_inferences'] == 1 and dom['port'] == 59910
assert dom['before'] == dom['after'] and dom['dom_fields_unchanged']
assert dom['link'] == {'href': url, 'rel': 'noopener noreferrer', 'target': '_blank',
                       'text': 'official iRacing Mini Stock template ZIP'}
assert not dom['clicked'] and not dom['downloaded']
assert (out / 'answer-links-native-answer.jpg').read_bytes().startswith(b'\xff\xd8\xff')
assert 'Sending' in (out / 'answer-links-native-sent.txt').read_text(encoding='utf-8')
assert '/url: ' + url in (out / 'answer-links-native-answer.txt').read_text(encoding='utf-8')
worker = obj(names[-1])
assert worker['authentication'] == 'ChatGPT' and not worker['apiFallback']
assert worker['port'] == 59910 and worker['exitCode'] == 0 and not worker['errors']
assert [c['tool'] for c in worker['calls']] == ['spb_wait_for_message', 'spb_assistant_context', 'spb_reply']
assert all(c['status'] == 'completed' and not c['result'].get('isError') for c in worker['calls'])
context, reply = worker['calls'][1:]
assert context['arguments'] == {'query': query, 'include_paint': True}
guide = json.loads(context['result']['content'][0]['text'])['car_reference']['car']['template_download']
assert guide['url'] == url and guide['available'] and not guide['latest_revision_verified']
assert '[official iRacing Mini Stock template ZIP](' + url + ')' in reply['arguments']['text']
assert 'not verified as the latest version' in reply['arguments']['text']
assert reply['arguments']['reply_to'] == worker['reply_to']
assert json.loads(reply['result']['content'][0]['text'])['shown_in_app']
files = [out / n for n in names] + [here / n for n in ['answer_links_edits.py', 'test_answer_links.cjs']]
hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
receipt = out / 'answer-links-native-acceptance.json'
if '--freeze' in sys.argv:
    receipt.write_text(json.dumps({'schema': 'spb-answer-links-native-acceptance/1',
        'native_chatgpt_replies': 1, 'claude_component_tests_only': True,
        'paint_fields': 8, 'original_fixtures': 2, 'artifact_hashes': hashes,
        'limits': ['Private staged formatter; shared/package/installed Claude adoption open.',
                   'Visible navigation only; no download or current-version verification.',
                   'Bounded lightweight URL/Markdown links, not a full Markdown renderer.',
                   'Exposed-state preservation is not complete raster or simulator proof.']}, indent=2) + '\n', encoding='utf-8')
assert obj(receipt.name)['artifact_hashes'] == hashes
print(json.dumps({'pass': True, 'native_chatgpt_replies': 1, 'model_inferences': 1,
                  'paint_fields_unchanged': 8, 'original_fixtures_unchanged': 2,
                  'exact_visible_official_link': True, 'frozen_artifacts': len(hashes)}))
