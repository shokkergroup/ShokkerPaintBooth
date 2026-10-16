"""Live post-correction context and native Offline; manual current-agent reply."""
from pathlib import Path
import json
out=Path(__file__).resolve().parents[2]/'_codex_mcp_work/chatgpt-dev/59910'
def payload(n):
 j=json.loads((out/n).read_text(encoding='utf-8'));assert not j['result'].get('isError');return json.loads(next(x['text'] for x in j['result']['content'] if x['type']=='text'))
w=payload('geometry-boundary-wait-2026-10-10T21-53-32-251Z.json');p=payload('geometry-boundary-context-warm-2026-10-10T21-54-12-727Z.json');r=payload('geometry-boundary-reply-2026-10-10T21-54-33-504Z.json')
assert w['reply_to']==13 and not w['request_intent']['mutation_allowed']
g=p['editor_capabilities']['panel_locations'];assert g['status']=='current' and g['parts']==[] and g['withheld_library_parts']==8
status=p['paint']['status']['data'];assert status['parts']==[] and status['library_parts_withheld']==8
assert not status['car']['identity_verified'] and not status['car']['geometry_verified']
assert r['shown_in_app'] is True
online=(out/'geometry-boundary-online-native-chat.txt').read_text(encoding='utf-8');offline=(out/'geometry-boundary-offline-native-chat.txt').read_text(encoding='utf-8')
assert 'cannot verify the hood’s exact position' in online
assert offline.count('I cannot identify an exact hood location from the current stored map')==2
assert 'No map was built and no paint was changed.' in offline
result={'pass':True,'scope':'Private live MCP context plus native Offline after layout warming; current-agent manual reply, not another installed-client inference',
 'seq':13,'library_boxes_withheld':8,'library_coordinates_absent':True,'heuristic_identity_qualified':True,'offline_refuses_unverified_hood':True,
 'limits':['Raw legacy map/status/action behavior needs Claude review; this changes common/Offline context.',
 'Final nested old-page snapshot guard added afterward is component-tested against actual receipt.',
 'No full-resolution paint, calibrated UV, shared adoption or actual Claude inference claim.']}
(out/'geometry-boundary-native-acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
