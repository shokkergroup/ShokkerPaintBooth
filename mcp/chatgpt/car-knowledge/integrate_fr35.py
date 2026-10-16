"""Independently check the successor metadata against the prior PSD inspection."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROAD = HERE / 'research/road'
FRESH = ROAD / 'successor_2026-10-10'
proposal = json.loads((FRESH / 'formularenault35-source-review.json').read_text())
evidence_path = FRESH / proposal['source']['evidence_file']
assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == proposal['source']['evidence_sha256']
fresh = json.loads(evidence_path.read_text())
prior = json.loads((ROAD / 'template_metadata/formularenault35.json').read_text())
assert fresh['archive_sha256'] == prior['archive_sha256'] == proposal['source']['archive_sha256']
assert fresh['psds'][0]['sha256'] == prior['psds'][0]['sha256'] == proposal['source']['psd_sha256']
for report in (fresh, prior):
    layers = [dict(x, name=x.get('name', x['path'].split(' / ')[-1])) for x in report['psds'][0]['layers']]
    logos = [x for x in layers if x['name'] == 'Color Change Logos']
    assert len(logos) == 1 and logos[0]['kind'] == 'group' and logos[0]['visible']
    children = [x for x in layers if x['path'].startswith(logos[0]['path'] + ' / ')]
    assert {x['name'] for x in children} == {'Layer 13', 'Layer 13 copy'}
    assert all(x['visible'] and x['kind'] != 'group' for x in children)
    assert any(x['name'] == 'Base ' and x['kind'] != 'group' for x in layers)
assert not proposal['version']['verified_release_version']
assert not proposal['version']['latest_template_for_installed_simulator_verified']
fact = proposal['proposed_fact']
out = HERE / 'research/fr35_successor/runtime_facts.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({
    'schema':'spb-car-research-facts/1', 'checked_date':'2026-10-10',
    'sources':{'official-template':dict(proposal['source'], title='Formula Renault 3.5 official template ZIP',
        evidence_file=evidence_path.relative_to(HERE).as_posix())},
    'facts':[dict(id=fact['id'], car_ids=fact['car_ids'], scope='car', topic=fact['topic'],
        text=fact['text'] + ' ' + fact['helper_implication'] + ' Template release version and latest simulator availability remain unverified.',
        source_ids=['official-template'], evidence_level='official-template-metadata', checked_date='2026-10-10',
        uv_mapping_verified=False, variant_layout_equivalence_verified=False)],
    'unknowns':{}, 'limitations':['File hierarchy only; no physical logo location or UV mapping verified.']
}, indent=2) + '\n')
print(json.dumps({'verified_fact':fact['id'], 'independent_prior_metadata_agrees':True, 'output':str(out.relative_to(HERE))}))
