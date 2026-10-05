"""Decision integrity; uses temporary records, never real owner reviews."""
import importlib.util,json,uuid
from pathlib import Path
import pytest
PATH=Path(__file__).resolve().parents[1]/'_era120_work/concept_review_api.py'
spec=importlib.util.spec_from_file_location('concept_review_api_test',PATH)
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)

@pytest.fixture
def records(tmp_path,monkeypatch):
    root=tmp_path/uuid.uuid4().hex/'review'
    for folder in ('briefs','records','decisions'):(root/folder).mkdir(parents=True)
    row=dict(id='test_only',name='Test',idea='Test',category='BAD & RAD',stage='awaiting_review',asset_sha256={'paint':'p1','spec':'s1'})
    for folder in ('briefs','records'):(root/folder/'test_only.json').write_text(json.dumps(row))
    (root.parent/'manifest.json').write_text(json.dumps({'items':[row]}))
    monkeypatch.setattr(api,'ROOT',root)
    return root,row

def test_decision_survives_reload_and_keeps_notes(records):
    root,row=records
    data=dict(id=row['id'],version=api.version(row),decision='pass',note='Keep blue; refine rim.')
    api.decide(data)
    assert api.catalog()['items'][0]['decision']['note']==data['note']
    api.decide({**data,'decision':'reject','note':'New artwork'})
    assert api.catalog()['items'][0]['decision']['decision']=='reject'
    assert len(json.loads((root/'decisions/test_only.json').read_text()))==2

def test_replacement_does_not_inherit_approval(records):
    root,row=records;old=api.version(row)
    api.decide(dict(id=row['id'],version=old,decision='pass'))
    row['asset_sha256']['paint']='p2'
    (root/'records/test_only.json').write_text(json.dumps(row))
    assert api.catalog()['items'][0]['decision'] is None
    with pytest.raises(ValueError,match='changed'):
        api.decide(dict(id=row['id'],version=old,decision='pass'))

def test_unknown_and_unbuilt_cannot_be_approved(records):
    root,row=records
    with pytest.raises(ValueError):api.decide(dict(id='../other',decision='pass'))
    (root/'records/test_only.json').unlink()
    brief=json.loads((root/'briefs/test_only.json').read_text());brief.pop('asset_sha256')
    (root/'briefs/test_only.json').write_text(json.dumps(brief))
    with pytest.raises(ValueError,match='not ready'):api.decide(dict(id=row['id'],decision='pass'))

def test_approved_chrome_is_protected(records):
    root,row=records;row['stage']='approved_procedural'
    (root/'records/test_only.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='already owner-approved'):
        api.decide(dict(id=row['id'],version=api.version(row),decision='reject'))
