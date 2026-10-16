"""Check the frozen private idle lifecycle receipt and six exact source hashes."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
receipt = here.parents[1] / '_codex_mcp_work/chatgpt-dev/59910/subscription-lifecycle-acceptance.json'
proof = json.loads(receipt.read_text(encoding='utf-8'))
assert proof['schema'] == 'spb-subscription-lifecycle-acceptance/1'
assert proof['port'] == 59910 and proof['pass'] and not proof['apiFallback']
assert proof['model_inferences_started'] == 0
assert proof['before'] == proof['after'] and len(proof['before']['fixtures']) == 2
assert len(proof['artifact_hashes']) == 6
for name, digest in proof['artifact_hashes'].items():
    assert '/' not in name and '\\' not in name
    assert hashlib.sha256((here / name).read_bytes()).hexdigest() == digest, name
assert proof['first']['running']['instance'] != proof['second']['running']['instance']
assert proof['second']['old_stop_ignored']
for phase in (proof['first'], proof['second']):
    assert phase['exitCode'] == 0
    assert phase['running']['process_present'] and phase['running']['active'] is None
    assert phase['running']['availability'] == 'unverified'
    assert not phase['before_stop']['stop_requested']
    assert phase['after_request']['stop_requested']
    assert phase['stop']['instance'] == phase['running']['instance']
    assert phase['stop']['pid'] == phase['running']['pid']
    assert phase['terminal']['state'] == 'owner_stop' and not phase['terminal']['active']
    assert phase['terminal']['last']['model_inferences_started'] == 0
    assert sum(e.get('state') == 'waiting_without_inference' for e in phase['events']) >= 2
    assert all(e['model_inferences_started'] == 0 for e in phase['events'])
    assert phase['events'][-1]['stopped'] == 'owner_stop'
    assert phase['events'][-1]['handled'] == 0
print(json.dumps({'pass': True, 'real_idle_stops': 2, 'distinct_restart_instances': True,
    'old_stop_ignored': True, 'idle_inferences': 0, 'pending_and_two_fixtures_preserved': True,
    'source_hashes': 6, 'persistent_customer_availability': False}))
