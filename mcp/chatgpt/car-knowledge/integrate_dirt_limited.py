"""Promote one dated ALL-family artwork note; no current placement instruction."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
review = here / 'research/oval/dirtlatemodel350_primary_2026-10-10'
manifest = json.loads((review / 'review-manifest.json').read_text(encoding='utf-8'))
for entry in manifest['files']:
    raw = (review / entry['name']).read_bytes()
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], entry['name']
pdf_text = (review / 'release-2019-s2-p2.pdf.txt').read_text(encoding='utf-8')
page = pdf_text.split('--- PDF page 3 ---', 1)[1]
assert page.index('Dirt Late Model') < page.index('(ALL) - Passenger-side WOO decal') < page.index('TRACKS:')
assert 'has been moved up to where it was located last season.' in page
binding = (review / 'release-2025-s4.html.txt').read_text(encoding='utf-8')
assert '301: Dirt Late Model\n302: (Limited) - Reduced the stiffness of the rear quarter panels and the rear frame.\n303: Dirt Micro Sprint Car' in binding
proposal = json.loads((review / 'proposed-facts.json').read_text(encoding='utf-8'))
assert len(proposal['facts']) == 1
f = proposal['facts'][0]
assert f['car_ids'] == ['dirtlatemodel-350'] and f['applicability']['variant_exclusive'] is False
assert not f['actionable_paint_restriction'] and not f['uv_mapping_verified']
sources = {}
for key, source in proposal['sources'].items():
    assert hashlib.sha256((review / source['source_file']).read_bytes()).hexdigest() == source['sha256']
    sources[key] = dict(source, url=source['final_url'], evidence_file=(review / source['source_file']).relative_to(here).as_posix())
f = dict(f, evidence_level='official-documentation', checked_date='2026-10-10',
         release={'year': 2019, 'season': 2, 'patch': 2, 'label': 'Archived 2019 Season 2 Patch 2 (filename label; exact event date not printed)'},
         template_revision_verified=False, can_target_panels=False)
f['text'] += ' This is dated family-wide artwork history, not a Limited-exclusive feature. It is not a current instruction to move a logo. The archive filename supplies the release label; no exact printed patch event date is established. The official Limited-tagged family entry confirms name scope only; its physics change is not a painting fact. This note supplies no current placement, measured offset, forced/removable branding, decal controls, numberboard, material/export rules, downloadable template revision, shared-template compatibility or verified UV mapping. Inspect the actual loaded template before any change.'
out = here / 'research/dirt_limited_primary/runtime_facts.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'schema': 'spb-car-research-facts/1', 'sources': sources, 'facts': [f],
    'unknowns': {'dirtlatemodel-350': ['Historical ALL-family decal movement supplies no current placement instruction, decal-control rule, template revision, compatibility or UV location.']},
    'limitations': ['Parent visually inspected archived PDF page 3 and independently checked 16 receipt-bound artifacts. Only exact Limited record promoted; Pro/Super and Dallara template-control claims excluded.']}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'verified_artifacts': len(manifest['files']), 'promoted_exact_limited_facts': 1, 'verified_uv_maps': 0}))
