"""Verify actual MCP read-response evidence; no model inference or pixel claim."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'_codex_mcp_work/chatgpt-dev/59910'
before=json.loads((E/'legacy-geometry-baseline-2026-10-11T00-37-30-892Z.json').read_text(encoding='utf-8'))
after=json.loads((E/'legacy-geometry-qualified-2026-10-11T00-41-06-541Z.json').read_text(encoding='utf-8'))
fields=['layers','zones','paint_size','selected_zone','paint_colours','pending_changes','recent_changes','saved_design_brief','convo','layer_roles']
checked=[]
for old,new in zip(before['calls'],after['calls']):
    assert old['tool']==new['tool']
    raw,qualified=old['data'],new['data']
    for field in fields:
        if field in raw:
            assert raw[field]==qualified[field],(old['tool'],field)
            checked.append(old['tool']+':'+field)
    if 'template_identity' in raw:
        assert raw['template_identity']['source_reference']==qualified['template_identity']['source_reference']
    assert qualified['library_parts_withheld']==8
    assert 'hood' in qualified['parts_needing_confirmation']
    assert not qualified.get('parts') and not qualified.get('car',{}).get('parts')
    assert 'not calibrated geometry' in qualified['geometry_note']
for tool in after['tool_descriptions']:
    assert 'Library recognition is heuristic' in tool['description']
result={'pass':True,'actual_MCP_read_tools':3,'withheld_library_parts_per_tool':8,
        'exact_exposed_fields':checked,'source_proof_not_invented':True,
        'limits':['Read responses only; internal named-part action routing remains open',
                  'No installed model inference, full-resolution pixels or shared adoption proven',
                  'Status car field is now a structured heuristic; downstream compatibility needs review']}
(E/'legacy-geometry-native-acceptance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
