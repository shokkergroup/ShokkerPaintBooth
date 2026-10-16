"""Promote a dated ALL-Dirt-Modified logo note, explicitly including 358."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
review = here / 'research/oval/dirtmodified358_primary_2026-10-10'
manifest = json.loads((review / 'review-manifest.json').read_text(encoding='utf-8'))
for e in manifest['files']:
    raw = (review / e['name']).read_bytes()
    assert len(raw) == e['bytes'] and hashlib.sha256(raw).hexdigest() == e['sha256'], e['name']
checks = {
    'release-2021-s3-p2.html.txt': '75: Dirt Modified\n76: (ALL) World of Outlaws contingency logos have been updated to match the 2021 season.\n77: Dirt Sprint Car',
    'release-2021-s1.html.txt': '379: Dirt Modified\n380: - NEW CAR!\n381: - - The Dirt Modified is now available for racing!\n382: - - This vehicle includes two classes:\n383: - - - Dirt Big Block Modified\n384: - - - Dirt 358 Modified',
}
for name, exact in checks.items():
    assert exact in (review / name).read_text(encoding='utf-8'), name
proposal = json.loads((review / 'proposed-facts.json').read_text(encoding='utf-8'))
assert len(proposal['facts']) == 1
f = proposal['facts'][0]
assert f['car_ids'] == ['dirtmodified-358'] and f['applicability']['variant_exclusive'] is False
assert f['applicability']['binding_source_id'] == 'release_2021_s1'
assert not f['actionable_paint_restriction'] and not f['uv_mapping_verified']
sources = {}
for key, source in proposal['sources'].items():
    assert hashlib.sha256((review / source['source_file']).read_bytes()).hexdigest() == source['sha256']
    sources[key] = dict(source, url=source['final_url'], evidence_file=(review / source['source_file']).relative_to(here).as_posix())
f = dict(f, evidence_level='official-documentation', checked_date='2026-10-10',
    release={'year': 2021, 'season': 3, 'patch': 2, 'label': '2021 Season 3 Patch 2'},
    template_revision_verified=False, can_target_panels=False)
f['text'] += ' This is dated family-wide artwork history, not a 358-exclusive feature. The official launch names Big Block and 358 as the Dirt Modified classes, binding the ALL statement to the 358. It does not establish current appearance, forced or removable decals, logo placement, numberboard or control-layer behavior, a downloadable template revision, shared templates, material/export rules, UV positions or compatibility with your open file. This update alone is insufficient reason to replace or modify your template.'
out = here / 'research/dirt358_primary/runtime_facts.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'schema': 'spb-car-research-facts/1', 'sources': sources, 'facts': [f],
    'unknowns': {'dirtmodified-358': ['The historical family-wide logo update supplies no current paint restriction, forced/removable branding rule, numberboard/control workaround, template revision or UV location.']},
    'limitations': ['Exact 358 coverage uses an explicit ALL Dirt Modified release and official two-class launch; other Dirt/Modified sections are excluded. No sibling record is promoted here.']}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'verified_artifacts': len(manifest['files']), 'promoted_exact_358_facts': 1, 'verified_uv_maps': 0}))
