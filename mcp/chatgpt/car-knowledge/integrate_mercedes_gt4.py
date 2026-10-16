"""Promote the exact GT4 historical artwork note after independent receipt checks."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
REVIEW=HERE/'research/road/mercedes_gt4_primary_2026-10-10'
manifest=json.loads((REVIEW/'review-manifest.json').read_text(encoding='utf-8'))
for e in manifest['files']:
    raw=(REVIEW/e['name']).read_bytes()
    assert len(raw)==e['bytes'] and hashlib.sha256(raw).hexdigest()==e['sha256'], e['name']
proposal=json.loads((REVIEW/'proposed-facts.json').read_text(encoding='utf-8'))
assert len(proposal['facts'])==1
f=proposal['facts'][0]
assert f['car_ids']==['mercedesamggt4'] and f['topic']=='paint-artwork-history'
assert not f['actionable_paint_restriction'] and not f['uv_mapping_verified']
source=proposal['sources']['release_2023_s3']
assert hashlib.sha256((REVIEW/source['source_file']).read_bytes()).hexdigest()==source['sha256']
text=(REVIEW/'release-2023-s3.html.txt').read_text(encoding='utf-8')
assert '470: Mercedes-AMG GT4\n471: IWC logos have been added to paint schemes.\n472: Mercedes-AMG W13 E Performance' in text
assert 'paint pattern #28' not in f['text']
promoted=dict(f)
promoted.update(text=f['text']+' This is historical scheme artwork, not a verified downloadable template revision or current painting requirement. It does not establish whether these logos are forced, removable, present on a custom paint or still displayed today, nor where they lie on the sheet. It does not verify numberboard behavior, material channels, UV positions or template compatibility. This update alone is insufficient reason to replace or modify your template.',
    evidence_level='official-documentation',release={'year':2023,'season':3,'label':'2023 Season 3'},
    checked_date='2026-10-10',template_revision_verified=False,can_target_panels=False)
out=HERE/'research/mercedes_gt4_primary/runtime_facts.json';out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'schema':'spb-car-research-facts/1','sources':{'release_2023_s3':dict(source,url=source['final_url'],evidence_file=(REVIEW/source['source_file']).relative_to(HERE).as_posix())},'facts':[promoted],
    'unknowns':{'mercedesamggt4':['Reviewed manual and releases establish no forced-decal workaround, numberboard interaction, specific small-section UV positions or current downloadable template revision.']},
    'limitations':['GT3 2020 pattern renumbering and Ford GT GT3 decal/template changes do not apply to this exact GT4 record. Historical scheme artwork is separate from current template requirements.']},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'verified_receipt_hashes':len(manifest['files']),'promoted':f['id'],'UV_maps':0}))
