"""Native spec-only M7 branch using the existing overlay-quality formula unchanged.
See docs/SPEC_OVERLAYS_V2_2026-09-06.md for the predeclared metric contract.
No paint metrics are fabricated for a renderer which does not author paint.
"""
from pathlib import Path
import sys,json,hashlib,importlib
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np
from scripts.spb_finish_identity import validate_identity_contract
from scripts.audit_spec_pattern_quality import _grade,_structure_and_channels,_channel_metrics
from engine.spec_overlay_v2.catalog import definitions
from scripts.spb_spec_overlay_v2_similarity import gate_fingerprint

def compute():
    catalog=definitions();work=ROOT/'_spec_overlays_v2_work/bake';stats={r['id']:r for r in json.loads((work/'stats.json').read_text())};pairs=json.loads((work/'similarity.json').read_text());out={};detail={}
    family_names={f['id']:f['name'] for f in catalog['families']}
    if json.loads((work/'similarity_contract.json').read_text()).get('algorithm')!=gate_fingerprint():raise ValueError('Stale similarity algorithm evidence')
    similarity_assets=json.loads((work/'similarity_assets.json').read_text())
    reviews=json.loads((work/'name-review.json').read_text())
    features=json.loads((work/'feature-coverage.json').read_text())
    feature_fingerprints=json.loads((work/'feature-fingerprints.json').read_text())
    for item in catalog['items']:
        pid=item['id'];module=importlib.import_module('engine.spec_overlay_v2.designs.'+pid[6:]);identity=validate_identity_contract(module.IDENTITY_CONTRACT,pid)
        if not identity.ok:out['spec_pattern:'+pid]={'composite':None,'intent':'spec_overlay_native','tier':'unreviewed','reason':list(identity.errors)};continue
        stat=stats[pid];path=work/(pid+'.png');picker=ROOT/'thumbnails/spec_patterns_combined'/(pid+'_160.png')
        if stat.get('renderer_fingerprint')!=module.render._spb_source_fingerprint:raise ValueError('Stale standard render: '+pid)
        if stat.get('standard_sha256')!=hashlib.sha256(path.read_bytes()).hexdigest() or stat.get('picker_sha256')!=hashlib.sha256(picker.read_bytes()).hexdigest():raise ValueError('Changed render assets: '+pid)
        review=reviews.get(pid,{})
        if review.get('standard_sha256')!=stat['standard_sha256'] or review.get('picker_sha256')!=stat['picker_sha256']:raise ValueError('Stale visual name review: '+pid)
        if review.get('verdict')!='pass':raise ValueError('Pending or rejected visual name review: '+pid)
        if feature_fingerprints.get(pid)!=stat['renderer_fingerprint']:raise ValueError('Stale named-feature probe: '+pid)
        if len(features.get(pid,[]))<5 or any(not m['finite'] or m['mean_coverage']<.002 for m in features[pid]):raise ValueError('Missing named feature: '+pid)
        own=[r for r in pairs if pid in (r['left'],r['right'])]
        if len(own)!=len(catalog['items'])-1:raise ValueError('Incomplete category similarity evidence: '+pid)
        nearest=max(own,key=lambda r:r['score']);nearest_id=nearest['right'] if nearest['left']==pid else nearest['left']
        native_bgr=cv2.imread(str(path));picker_bgr=cv2.imread(str(picker))
        if hashlib.sha256(native_bgr.tobytes()+picker_bgr.tobytes()).hexdigest()!=similarity_assets.get(pid):raise ValueError('Stale category comparison: '+pid)
        rgb=cv2.cvtColor(native_bgr,cv2.COLOR_BGR2RGB).astype(np.float32)/255
        structure,channels=_structure_and_channels(rgb);stds,spans,corr=_channel_metrics(channels)
        meta={**item,'category':family_names[item['family']]}
        grade=_grade(pid,meta,cv2.resize(structure,(512,512),interpolation=cv2.INTER_AREA),nearest['score'],nearest_id,stds,spans,corr,stat['seconds']*1000,85)
        flags=list(grade.flags)
        if nearest['score']>=.55:flags.append('IDENTITY_REBUILD')
        if stat['seconds']>3:flags.append('RENDER_BUDGET')
        components={k:getattr(grade,k) for k in ('intent','originality','wow','detail','coverage','physics')}
        accepted=grade.score>=85 and not flags
        out['spec_pattern:'+pid]={'composite':grade.score,'preCloneComposite':grade.score,'clonePenalty':1.,'cloneSize':1,'intent':'spec_overlay_native','tier':'keeper' if accepted else 'fix','components':components,'componentsUsed':list(components),'shipReady':accepted,'flags':flags,'category':meta['category'],'source':'audit_spec_pattern_quality.py unchanged native overlay formula','standard_sha256':stat['standard_sha256'],'picker_sha256':stat['picker_sha256']}
        detail[pid]={**asdict(grade),'flags':flags,'shipReady':accepted}
    (work/'quality.json').write_text(json.dumps(detail,indent=2),encoding='utf-8');return out

if __name__=='__main__':
    result=compute();weak=[{'id':pid,'composite':r['composite'],'flags':r.get('flags',r.get('reason'))} for pid,r in result.items() if not r.get('shipReady')]
    if '--emit-ui' in sys.argv:
        if weak:raise ValueError('Cannot promote UI quality metadata with unaccepted candidates.')
        payload={pid.split(':',1)[1]:{'score':r['composite'],'shipReady':True,'components':r['components']} for pid,r in result.items()}
        (ROOT/'js/spec-overlays/quality-data.js').write_text('window.SPB_SPEC_OVERLAY_QUALITY = '+json.dumps(payload,indent=2)+';\n',encoding='utf-8')
    print(json.dumps({'scored':sum(r['composite'] is not None for r in result.values()),'accepted':sum(r.get('shipReady',False) for r in result.values()),'weak_count':len(weak),'first_weak':weak[:8]},indent=2))
