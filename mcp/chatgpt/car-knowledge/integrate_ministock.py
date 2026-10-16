"""Promote exact asphalt rear-sponsor history after independent receipt/scope checks."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
review = here / 'research/oval/ministock_primary_2026-10-10'
manifest_path = review / 'review-manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
for entry in manifest['files']:
    raw = (review / entry['name']).read_bytes()
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], entry['name']
patch = (review / 'release-2024-s4-p2.html.txt').read_text(encoding='utf-8')
assert '82: Mini Stock\n83:' in patch and '85: Paint pattern texture files have been updated for improved placement of rear sponsors.' in patch
assert patch.index('82: Mini Stock') < patch.index('85: Paint pattern texture') < patch.index('89: [Legacy] Dallara DW12')
launch = (review / 'release-2024-s4.html.txt').read_text(encoding='utf-8')
assert '335: Mini Stock\n336: NEW CAR!\n337: The Mini Stock, a new Asphalt Oval car' in launch
later = (review / 'release-2026-s1.html.txt').read_text(encoding='utf-8')
assert '340: Mini Stock\n341: iRacing setups have been updated.\n342: Mercedes-AMG GT3 2020' in later
proposal = json.loads((review / 'proposed-facts.json').read_text(encoding='utf-8'))
assert len(proposal['facts']) == 1
f = proposal['facts'][0]
assert f['car_ids'] == ['ministock'] and f['applicability']['excluded_car_ids'] == ['dirtministock']
assert not f['uv_mapping_verified'] and not f['actionable_paint_restriction']
sources = {}
for key, source in proposal['sources'].items():
    assert hashlib.sha256((review / source['source_file']).read_bytes()).hexdigest() == source['sha256']
    sources[key] = dict(source, url=source['final_url'], evidence_file=(review / source['source_file']).relative_to(here).as_posix())
f = dict(f, evidence_level='official-documentation', checked_date='2026-10-10',
    release={'year': 2024, 'season': 4, 'patch': 2, 'label': '2024 Season 4 Patch 2 [2024.09.17.02]'},
    template_revision_verified=False, can_target_panels=False)
f['text'] += ' This dated artwork repair belongs to exact asphalt Mini Stock, not Dirt Mini Stock. It does not establish current rear-sponsor positions, movable/forced logos, custom-paint controls, a downloadable PSD revision, the newest installed template, compatibility, material/export rules or UV geometry. The 2026 Season 1 Mini Stock entry reviewed here changes setups only; its nearby Dallara template update is a different car. Inspect the actual current template before changing artwork.'
out = here / 'research/ministock_primary/runtime_facts.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'schema': 'spb-car-research-facts/1', 'sources': sources, 'facts': [f],
    'unknowns': {'ministock': ['Dated rear-sponsor artwork history establishes no current placement/control, downloadable PSD revision, compatibility or UV location.']},
    'limitations': ['Parent independently checked 15 artifact hashes and exact model/neighboring headings; only exact asphalt history promoted.']}, indent=2) + '\n', encoding='utf-8')
receipt = {'schema': 'spb-car-primary-parent-review/1', 'car_id': 'ministock', 'verified_artifacts': len(manifest['files']),
    'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(), 'promoted_facts': [f['id']],
    'excluded_car_ids': ['dirtministock', 'dallarair18'], 'current_placement_verified': False,
    'latest_template_verified': False, 'verified_uv_maps': 0}
(out.parent / 'parent-review.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'verified_artifacts': len(manifest['files']), 'promoted_exact_asphalt_history_facts': 1, 'verified_uv_maps': 0}))
