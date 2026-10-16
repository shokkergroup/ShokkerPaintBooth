"""Promote exact GT3 history with corrected banner scope; preserve archived proposals."""
from pathlib import Path
import hashlib, json, re
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent
review=HERE/'research/road/fordmustanggt3_primary_2026-10-10'
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=load(review/'review-manifest.json')
for row in manifest['files']:
 p=review/row['name'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['name']
proposal=load(review/'proposed-facts.json');assert len(proposal['facts'])==3
current=next(c for c in load(HERE/'build/knowledge.json')['cars'] if c['id']=='fordmustanggt3')
prior=load(review/'existing-compiled-entry.json')['car']
assert all(current[k]==prior[k] for k in ['id','name','paint_folder','template_metadata'])
sources={}
for key,source in proposal['sources'].items():
 p=review/source['source_file'];assert sha(p)==source['sha256'] and source['http_status']==200
 sources[key]={**source,'url':source['final_url'],'evidence_file':p.relative_to(HERE).as_posix()}
checks=[('release-2024-s3-p1.html.txt',89,99,['95: Fixed some display issues with the window banner at different camera distances.','96: The IMSA decal layer is now appropriately used for IMSA events.'],'Global Mazda MX-5 Cup'),('release-2024-s4-p2.html.txt',67,69,['68: A flaming hot new paint pattern is now available for this car.'],'Hyundai Elantra N TCR'),('release-2025-s4-p2.html.txt',88,90,['89: Fixed an issue where the windshield wiper controls were not highlighted in the Options menu.'],'Ford Mustang GT4')]
for file,start,end,lines,next_heading in checks:
 text=(review/file).read_text(encoding='utf-8').splitlines();assert text[start-1]==f'{start}: Ford Mustang GT3' and text[end-1]==f'{end}: {next_heading}'
 assert all(line in text[start:end-1] for line in lines)
 raw_text=re.sub(r'\s+',' ',BeautifulSoup((review/file.replace('.txt','')).read_bytes(),'html.parser').get_text(' ',strip=True))
 assert all(line.split(': ',1)[1] in raw_text for line in lines)
facts=[]
for original in proposal['facts']:
 assert original['car_ids']==['fordmustanggt3'] and not original['actionable_paint_restriction'] and not original['uv_mapping_verified']
 f={**original,'topic':'paint-artwork-history','evidence_level':'official-documentation','checked_date':'2026-10-11','template_revision_verified':False,'can_target_panels':False}
 season=3 if '2024-s3' in f['id'] else 4
 f['release']={'year':2024,'season':season,'patch':1 if season==3 else 2,'label':f'2024 Season {season} Patch {1 if season==3 else 2}'}
 f['text']+=' This is exact-model historical artwork information, not a current editing, forced/removable decal, template-revision, compatibility or UV rule; it does not apply to Mustang GT4, FR500S, NASCAR Mustang or Ford GT GT3.'
 if 'window-banner' in f['id']:f['text']+=' Camera-distance display is not evidence of a Paint Shop preview repair.'
 if 'paint-pattern' in f['id']:f['text']+=' The source does not identify a pattern number, downloadable asset or SPB finish.'
 facts.append(f)
out=HERE/'research/fordmustanggt3_primary';out.mkdir(exist_ok=True)
data={'schema':'spb-car-research-facts/1','sources':sources,'facts':facts,'unknowns':{'fordmustanggt3':['Current controls/forced decals/template revisions/compatibility/UV positions remain unverified.']},'limitations':['2025 Season4Patch2 exact GT3 entry changes wiper menu highlighting only; GT4 damping and neighboring artwork are excluded.','Window banner camera-distance display must not be classified as Paint Shop preview history.']}
raw=(json.dumps(data,indent=2)+'\n').encode()
target=out/'runtime_facts.json'
if target.exists():assert target.read_bytes()==raw,'Existing promotion drift; re-review instead of overwrite'
else:target.write_bytes(raw)
proof={'pass':True,'verified_artifacts':len(manifest['files']),'car_id':'fordmustanggt3','promoted_facts':[f['id'] for f in facts],'corrected_banner_topic':'paint-artwork-history','runtime_facts_sha256':sha(target),'manifest_sha256':sha(review/'review-manifest.json'),'scope':'Three dated exact-GT3 artwork facts; no current rule/control/template/UV authority. Frozen proposal preserved; source compile/runtime retrieval next.'}
(out/'parent-review.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pass':True,'verified_artifacts':len(manifest['files']),'facts':len(facts),'banner_not_paint_shop_preview':True}))
