"""Promote one exact-model historical artwork fact after checking archived evidence."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REVIEW = HERE / 'research/road/ferrari296_primary_2026-10-10'
manifest = json.loads((REVIEW / 'review-manifest.json').read_text(encoding='utf-8'))
for entry in manifest['files']:
    raw = (REVIEW / entry['name']).read_bytes()
    assert len(raw) == entry['bytes']
    assert hashlib.sha256(raw).hexdigest() == entry['sha256'], entry['name']
proposal = json.loads((REVIEW / 'proposed-facts.json').read_text(encoding='utf-8'))
assert len(proposal['facts']) == 1
fact = proposal['facts'][0]
assert fact['car_ids'] == ['ferrari296gt3']
assert fact['topic'] == 'paint-artwork-history'
assert not fact['actionable_paint_restriction'] and not fact['uv_mapping_verified']
source = proposal['sources']['release_2024_s3']
assert hashlib.sha256((REVIEW / source['source_file']).read_bytes()).hexdigest() == source['sha256']
text = (REVIEW / 'release-2024-s3.html.txt').read_text(encoding='utf-8')
assert '383: Ferrari 296 GT3\n384: The vehicle body vinyl texture has been updated.\n385: Ferrari 488 GTE' in text
promoted = dict(fact)
promoted.update(text=fact['text'] + ' This is historical vehicle artwork, not a verified downloadable template revision or current painting requirement. It does not verify current appearance, numberboard/decal/material changes, UV positions or compatibility. This update alone is insufficient reason to replace or modify your template.',
                evidence_level='official-documentation',
                release={'year': 2024, 'season': 3, 'label': '2024 Season 3'},
                checked_date='2026-10-10', template_revision_verified=False,
                can_target_panels=False)
out = HERE / 'research/ferrari296_primary/runtime_facts.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'schema': 'spb-car-research-facts/1',
    'sources': {'release_2024_s3': dict(source, url=source['final_url'],
        evidence_file=(REVIEW / source['source_file']).relative_to(HERE).as_posix())},
    'facts': [promoted], 'unknowns': {'ferrari296gt3': [
        'Reviewed official manual and releases establish no numberboard interaction, forced-decal workaround, small-section UV locations or current template revision.']},
    'limitations': ['Historical vehicle artwork is separate from template revision and current simulator appearance.']},
    indent=2) + '\n', encoding='utf-8')
print(json.dumps({'verified_receipt_hashes': len(manifest['files']), 'promoted': fact['id'], 'UV_maps': 0}))
