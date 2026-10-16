"""Independent bounded parent review; proposals are not runtime facts."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
from bs4 import BeautifulSoup

here = Path(__file__).resolve().parent
lane = here / 'research/road/mercedesamgevogt3_primary_2026-10-10'
manifest = json.loads((lane / 'review-manifest.json').read_text(encoding='utf-8'))
assert len(manifest['files']) == 16
for row in manifest['files']:
    raw = (lane / row['name']).read_bytes()
    assert len(raw) == row['bytes']
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
scopes = json.loads((lane / 'evidence-scopes.json').read_text(encoding='utf-8'))['scopes']
assert len(scopes) == 3
for scope in scopes:
    lines = (lane / scope['local_text_file']).read_text(encoding='utf-8').splitlines()
    receipt = json.loads((lane / (scope['source_id']+'-source-receipt.json')).read_text(encoding='utf-8'))
    raw = (lane / receipt['source_file']).read_bytes()
    assert receipt['http_status'] == 200 and hashlib.sha256(raw).hexdigest() == receipt['sha256']
    soup = BeautifulSoup(raw,'html.parser',from_encoding='utf-8')
    for item in soup(['script','style']):
        item.decompose()
    raw_lines = [x.strip() for x in soup.get_text('\n').splitlines() if x.strip()]
    for quoted in scope['lines']:
        number, text = quoted.split(': ', 1)
        assert lines[int(number)-1].strip() == quoted
        assert raw_lines[int(number)-1] == text
    assert scope['heading'] == 'Mercedes-AMG GT3 2020'
result = {'schema':'spb-car-primary-parent-review/1','checked_at':datetime.now(timezone.utc).isoformat(),
    'car_id':'mercedesamgevogt3','verified_artifacts':16,'exact_headings':3,
    'manifest_sha256':hashlib.sha256((lane / 'review-manifest.json').read_bytes()).hexdigest(),
    'status':'parent checked; proposal only','promoted_facts':[],'proposed_historical_facts':3,
    'limits':['Exact GT3 2020 history only; original GT3/GT4 excluded.',
        'Historical splitter/dive-plane/pattern/IWC notes do not establish current controls or editable parts.',
        'No current availability, forced decals, PSD revision, export, compatibility or UV claims.']}
out = here / 'research/mercedesamgevogt3_parent_review'
out.mkdir(exist_ok=True)
(out / 'parent-review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pass':True,'parent_verified_artifacts':16,'exact_headings':3,'promoted_facts':0}))
