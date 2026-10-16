"""Promote two exact F82 dated paint/preview notes after receipt review."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
review = here / 'research/road/bmwm4gt4_f82_primary_2026-10-10'
manifest = json.loads((review / 'review-manifest.json').read_text(encoding='utf-8'))
for e in manifest['files']:
    raw = (review / e['name']).read_bytes()
    assert len(raw) == e['bytes'] and hashlib.sha256(raw).hexdigest() == e['sha256'], e['name']
proposal = json.loads((review / 'proposed-facts.json').read_text(encoding='utf-8'))
assert len(proposal['facts']) == 2
checks = {
    'release-2021-s2-p1.html.txt': '45: BMW M4 GT4\n46: - Some vehicle parameters have been adjusted slightly to equalize competitive performance within the GT4 class.\n47: - Fixed an asymmetric issue with paint pattern 0.',
    'release-2024-s3-p1.html.txt': '70: BMW M4 GT4\n71: Fixed an issue where rain aerospray was appearing inside the cockpit in mirrors.\n72: Fixed a flickering issue with the rear windshield in the Paint Shop.\n73: Chevrolet Corvette Z06 GT3.R',
    'release-2024-s4.html.txt': '223: BMW M4 F82 GT4\n224: This vehicle has been renamed from “BMW M4 GT4” for clarity.\n225: BMW M4 GT3',
}
for name, exact in checks.items():
    assert exact in (review / name).read_text(encoding='utf-8'), name
sources = {}
for key, source in proposal['sources'].items():
    assert hashlib.sha256((review / source['source_file']).read_bytes()).hexdigest() == source['sha256']
    sources[key] = dict(source, url=source['final_url'], evidence_file=(review / source['source_file']).relative_to(here).as_posix())
facts = []
for i, f in enumerate(proposal['facts']):
    assert f['car_ids'] == ['bmwm4gt4'] and f['applicability']['binding_source_id'] == 'release_2024_s4'
    assert not f['actionable_paint_restriction'] and not f['uv_mapping_verified']
    facts.append(dict(f, topic='paint-artwork-history' if i == 0 else 'paint-preview-history',
        text=f['text'] + ' This is a dated artwork repair.' if i == 0 else f['text'] + ' This is a dated Paint Shop preview repair.',
        evidence_level='official-documentation', checked_date='2026-10-10',
        release={'year': 2021 if i == 0 else 2024, 'season': 2 if i == 0 else 3, 'patch': 1, 'label': '2021 Season 2 Patch 1' if i == 0 else '2024 Season 3 Patch 1'},
        template_revision_verified=False, can_target_panels=False))
    facts[-1]['text'] += ' It does not establish current appearance, a current fault or a workaround, a downloadable template revision, forced decals, numberboard placement, material channels, export requirements, UV positions or compatibility with your open file. It applies to the older F82, not G82 or GT3. This update alone is insufficient reason to replace or modify your template.'
out = here / 'research/bmw_f82_primary/runtime_facts.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'schema': 'spb-car-research-facts/1', 'sources': sources, 'facts': facts,
    'unknowns': {'bmwm4gt4': ['These historical repairs establish no current restriction, forced-decal/control workaround, numberboard interaction, downloadable template revision or UV location.']},
    'limitations': ['Exact historical model binding uses the official F82 rename; G82/GT3 and neighboring Ford/Corvette updates are excluded.']}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'verified_artifacts': len(manifest['files']), 'promoted_exact_f82_facts': len(facts), 'verified_uv_maps': 0}))
