"""Verify and import six metadata observations without changing prior research."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROAD = HERE / 'research/road'
REPORT = ROAD / 'successor_2026-10-10/report.json'
report = json.loads(REPORT.read_text())
assert report['schema'] == 'spb-road-successor-review/1'
for rel, digest in report['input_sha256'].items():
    assert hashlib.sha256((ROAD / rel.replace('\\', '/')).read_bytes()).hexdigest() == digest

def metadata(car):
    return json.loads((ROAD / 'template_metadata' / (car+'.json')).read_text())
def layers(car):
    return {x['path']: x for x in metadata(car)['psds'][0]['layers']}
for car in ['amvantagegt4', 'raygr22']:
    fresh = json.loads((ROAD / 'successor_2026-10-10' / (car+'-alpha-inspection.json')).read_text())
    old = metadata(car)
    assert fresh['archive_sha256'] == old['archive_sha256']
    assert fresh['psds'][0]['sha256'] == old['psds'][0]['sha256']
    assert fresh['psds'][0]['channels'] == 4
    assert fresh['psds'][0]['alpha_channel_names'] == ['Transparency']
aston = layers('amvantagegt4')
for name in ['car_pattern_001 Spec.tga', 'car_pattern_002 Spec.tga']:
    matching = [v for k,v in aston.items() if k.startswith('Custom Spec Map /') and k.endswith('/ '+name)]
    assert len(matching) == 1 and matching[0]['visible'] is False
kia = layers('kiaoptima'); guides = 'Turn Off Before Exporting TGA / '
assert kia[guides+'car_mandatory']['bbox'] == [-28,-222,2193,2057]
assert all(guides+n in kia for n in ['Sponsor Block Locations','Number Block Locations'])
nissan = layers('nissangtpzxt')
assert all(nissan[guides+n]['kind']=='group' and nissan[guides+n]['visible'] is False for n in ['Sponsor Blocks','Number Blocks'])
assert any(k.startswith(guides+'Sponsor Blocks /') and v['visible'] for k,v in nissan.items())
assert guides+'New Wire' in nissan
porsche = layers('porsche718gt4')
assert all('Custom Spec Map / '+n in porsche for n in ['Green Channel Roughness / Base Color','Red Channel Metallic / Base Color','Blue Channel Clearcoat / Base Paint'])
radical = layers('radical-sr8')
assert 'Custom Spec Map / Red Channel Metallic / Parrts' in radical and guides+'Stamp Bits' in radical

facts=[]; sources={}; unknowns={}
for finding in report['findings']:
    if finding['status'] != 'new-specific-metadata-observation':
        continue
    assert not finding['uv_mapping_verified'] and not finding['variant_layout_equivalence_verified']
    car=finding['car_id']
    facts.append(dict(id=finding['proposed_fact_id'], text=finding['text']+' '+finding['remaining_uncertainty'],
                      car_ids=[car], scope='car', topic=finding['topic'], source_ids=finding['source_ids'],
                      evidence_level='official-template-metadata', checked_date='2026-10-10',
                      uv_mapping_verified=False, variant_layout_equivalence_verified=False))
    for sid in finding['source_ids']:
        src=dict(report['sources'][sid]); src['evidence_file']=str((ROAD/'successor_2026-10-10'/src['evidence_file']).resolve().relative_to(HERE)).replace('\\','/')
        sources[sid]=src
assert len(facts)==6 and {f['car_ids'][0] for f in facts}=={'amvantagegt4','kiaoptima','nissangtpzxt','porsche718gt4','radical-sr8','raygr22'}
out=HERE/'research/road_successor/runtime_facts.json';out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(dict(schema=json.loads((ROAD/'runtime_facts.json').read_text())['schema'],checked_date='2026-10-10',sources=sources,facts=facts,
                              limitations=['File-structure observations only; no new revision, export-bit-depth or UV compatibility authority.'],unknowns=unknowns),indent=2)+'\n')
print(json.dumps(dict(verified_and_imported_facts=len(facts), prior_research_unchanged=True, output=str(out.relative_to(HERE)))))
