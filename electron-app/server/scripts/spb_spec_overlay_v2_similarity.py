"""Palette/channel/rotation/reflection/translation-invariant live asset gate."""
from pathlib import Path
import sys,json,itertools,hashlib,time,inspect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np
from concurrent.futures import ProcessPoolExecutor,as_completed
from scripts.spb_iridescent_insects_similarity_gate import _features,_structure,_corr,_d4_variants,_phase_response
from engine.spec_overlay_v2.catalog import definitions

def signatures(image):
    return [(_features(a),_structure(a)) for a in [image]+[np.repeat(image[:,:,c:c+1],3,axis=2) for c in range(3)]]

def compare(left,right):
    # Combined signature is channel invariant; individual channels also cross
    # compare so swapping M/R/Cc cannot create a new surface.
    score=0.
    for ai,a in enumerate(left):
        candidates=right if ai else right[:1]
        for b in candidates:
            score=max(score,abs(_corr(a[0][0],b[0][0])),_corr(a[0][1],b[0][1]))
            for rotated in _d4_variants(b[1]):score=max(score,_corr(a[1],rotated),_phase_response(a[1],rotated))
    return float(score)

def worker_init(cache):
    global WORKER_CACHE
    cv2.setNumThreads(1);WORKER_CACHE=cache

def worker_pair(pair):
    a,b=pair;scores=[round(compare(x,y),5) for x,y in zip(WORKER_CACHE[a],WORKER_CACHE[b])];score=max(scores)
    return {'left':a,'right':b,'score':score,'whole_detail_picker':scores,'verdict':'reject' if score>=.68 else 'owner_review' if score>=.55 else 'pass'}

def gate_fingerprint():
    return hashlib.sha256(''.join(inspect.getsource(fn) for fn in (signatures,compare,_features,_structure,_corr,_d4_variants,_phase_response)).encode()).hexdigest()

def main():
    items=definitions()['items'];work=ROOT/'_spec_overlays_v2_work'/'bake';cache={};hashes={}
    old_hashes=json.loads((work/'similarity_assets.json').read_text()) if (work/'similarity_assets.json').exists() else {}
    old_rows=json.loads((work/'similarity.json').read_text()) if (work/'similarity.json').exists() else []
    previous={(r['left'],r['right']):r for r in old_rows}
    contract=work/'similarity_contract.json'
    if not contract.exists() or json.loads(contract.read_text()).get('algorithm')!=gate_fingerprint():previous={}
    for row in items:
        pid=row['id'];native=cv2.imread(str(work/(pid+'.png')));picker=cv2.imread(str(ROOT/'thumbnails/spec_patterns_combined'/(pid+'_160.png')))
        hashes[pid]=hashlib.sha256(native.tobytes()+picker.tobytes()).hexdigest()
        cache[pid]=[signatures(native),signatures(native[768:1280,768:1280]),signatures(picker)]
    rows=[];pending=[];reused=0;start=time.perf_counter()
    for a,b in itertools.combinations([p['id'] for p in items],2):
        prior=previous.get((a,b)) or previous.get((b,a))
        if prior and hashes[a]==old_hashes.get(a) and hashes[b]==old_hashes.get(b):rows.append(prior);reused+=1
        else:pending.append((a,b))
    print(f'Reusing {reused} byte-identical asset pairs; comparing {len(pending)} changed pairs.',flush=True)
    if pending:
        # Bounded CPU workers execute the identical gate; no thresholds or
        # comparisons are removed. Old pairs are reusable only by asset hash.
        with ProcessPoolExecutor(max_workers=4,initializer=worker_init,initargs=(cache,)) as pool:
            jobs=[pool.submit(worker_pair,pair) for pair in pending]
            for job in as_completed(jobs):
                rows.append(job.result())
                if len(rows)%100==0:
                    print(f'{len(rows)} pairs; reused {reused}; elapsed {time.perf_counter()-start:.1f}s',flush=True)
                    (work/'similarity.progress.json').write_text(json.dumps(rows))
    rows.sort(key=lambda r:-r['score']);(work/'similarity.json').write_text(json.dumps(rows,indent=2))
    (work/'similarity_assets.json').write_text(json.dumps(hashes,indent=2))
    contract.write_text(json.dumps({'algorithm':gate_fingerprint(),'threshold_reject':.68,'threshold_owner_review':.55},indent=2))
    print(json.dumps({'pairs':len(rows),'reject':sum(r['score']>=.68 for r in rows),'review':sum(.55<=r['score']<.68 for r in rows),'top':rows[:6]},indent=2))
if __name__=='__main__':main()
