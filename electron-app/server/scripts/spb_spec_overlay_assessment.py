"""Read-only SPEC OVERLAY inventory and audit evidence; owner 2026-09-05."""
from pathlib import Path
import contextlib,io,json,sys,inspect,collections,os,argparse,time,hashlib,subprocess,itertools,urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'_spec_overlays_audit_work'

def inventory():
    OUT.mkdir(exist_ok=True)
    from scripts.audit_spec_pattern_quality import _load_ui_spec_patterns,_quiet_catalog
    specs,groups=_load_ui_spec_patterns();catalog=_quiet_catalog()
    rows=[]
    for item in specs:
        fn=catalog.get(item['id'])
        rows.append(dict(item,category=groups.get(item['id'],'UNGROUPED'),
            renderer_module=getattr(fn,'__module__',None),renderer_name=getattr(fn,'__name__',None),
            renderer_source=inspect.getsourcefile(fn) if fn else None,signature=str(inspect.signature(fn)) if fn else None))
    (OUT/'inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    result=dict(visible=len(rows),backend_catalog=len(catalog),categories=dict(collections.Counter(r['category'] for r in rows)),
        missing=[r['id'] for r in rows if not r['renderer_module']],
        renderer_modules=dict(collections.Counter(r['renderer_module'] for r in rows)))
    (OUT/'inventory_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return rows,catalog,result

def probe(rows,catalog):
    import numpy as np
    import cv2
    from PIL import Image
    from engine.spec_pattern_families import overhaul_2026 as ov
    from engine.spec_pattern_families.semantic_overlays_2026 import semantic_archetype,semantic_texture_policy
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from engine.compose import _apply_spec_pattern_to_channels,compose_finish,compose_finish_stacked
    images=OUT/'images';images.mkdir(exist_ok=True)
    def save(a,name):
        Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(images/name)
    def apply(a,base,opacity=.5,channels='MRC',fallback=None):
        fields=[None if v is None else np.full(a.shape[:2],v,np.float32) for v in base]
        return _apply_spec_pattern_to_channels(a,*fields,40,opacity**.5,'normal',channels,cc_fallback=fallback)
    result={'scope':'Existing renderers only; no rebuild or promotion. Single cold-ish call per ID, in catalog order.',
            'pythonhashseed':os.environ.get('PYTHONHASHSEED'),'rows':[]}
    previews={};crops={};native_down={};start=time.perf_counter()
    for index,row in enumerate(rows):
        pid=row['id'];fn=catalog[pid];params=row.get('defaults',{})
        before=time.perf_counter();native=fn((2048,2048),42,1.0,**params);seconds=time.perf_counter()-before
        small=fn((160,160),42,1.0,**params);down=cv2.resize(native,(160,160),interpolation=cv2.INTER_AREA)
        crop=native[896:1152,896:1152]
        previews[pid]=(small*255).astype(np.uint8);crops[pid]=(crop*255).astype(np.uint8);native_down[pid]=(down*255).astype(np.uint8)
        mats=[ov._material_for(pid,ov._stable(pid)^((seed*0x9E3779B185EBCA87)&0xffffffffffffffff)) for seed in [42,43,44,45,46,47,48,49]]
        applied=np.stack(apply(small,(128,128,128)),axis=2)
        record=dict(id=pid,name=row.get('name',pid),category=row['category'],archetype=semantic_archetype(pid),
                    policy=semantic_texture_policy(pid),seconds=seconds,finite=bool(np.isfinite(native).all()),
                    shape=list(native.shape),std_255=(native.std(axis=(0,1))*255).tolist(),
                    spans_255=((native.max(axis=(0,1))-native.min(axis=(0,1)))*255).tolist(),
                    picker_vs_native_mae_255=float(np.abs(small-down).mean()*255),
                    raw_vs_applied_neutral_mae_255=float(np.abs(small*255-applied).mean()),
                    preview_material=mats[0],materials_across_8_seeds=sorted(set(mats)),
                    explicit_defaults={k:row[k] for k in ['defaultOpacity','defaultBlendMode','defaultRange','defaultChannels'] if k in row})
        for suffix,a in [('picker',small*255),('native',down*255),('crop',crop*255),('neutral',applied)]:save(a,pid+'_'+suffix+'.png')
        result['rows'].append(record)
        if (index+1)%30==0:print('Native audit:',index+1,'/',len(rows),flush=True)
    result['render_elapsed_seconds']=time.perf_counter()-start
    # A bounded screen for reused archetypes; this is NOT the full live category ship gate.
    from scripts.spb_iridescent_insects_similarity_gate import _identity_similarity
    grouped=collections.defaultdict(list)
    for row in result['rows']:grouped[row['archetype']].append(row['id'])
    pairs=[]
    for ids in grouped.values():
        for a,b in itertools.combinations(ids,2):
            scores={}
            for label,source in [('picker',previews),('native_crop',crops),('native_down',native_down)]:
                s=_identity_similarity(source[a],source[b]);scores[label]=max(s.transformed,s.phased)
            pairs.append(dict(a=a,b=b,**scores,max_score=max(scores.values())))
    result['same_archetype_screen']={'pairs':len(pairs),'rebuild_screen_hits':sum(p['max_score']>=.68 for p in pairs),
        'review_screen_hits':sum(.55<=p['max_score']<.68 for p in pairs),'top':sorted(pairs,key=lambda p:p['max_score'],reverse=True)[:20],
        'limitation':'Shared-archetype subset, direct local renders, combined channels only. Does not certify the complete live standard/picker/per-channel identity gate.'}
    pid='hex_cells';arr=catalog[pid]((160,160),42,1.0,**next(r for r in rows if r['id']==pid).get('defaults',{}))
    fixtures={}
    for name,base in [('neutral',(128,128,128)),('chrome',(245,20,16)),('matte',(10,230,240))]:
        one=np.stack(apply(arr,base),axis=2);save(one,pid+'_'+name+'.png')
        many=[np.full(arr.shape[:2],v,np.float32) for v in base]
        for _ in range(5):many=_apply_spec_pattern_to_channels(arr,*many,40,.5**.5,'normal','MRC')
        five=np.stack(many,axis=2);save(five,pid+'_'+name+'_5stack.png')
        fixtures[name]={'one_std':one.std(axis=(0,1)).tolist(),'five_std':five.std(axis=(0,1)).tolist(),
            'one_clip_fraction':[((one[:,:,c]<=([0,0,16][c]))|(one[:,:,c]>=255)).mean().item() for c in range(3)],
            'five_clip_fraction':[((five[:,:,c]<=([0,0,16][c]))|(five[:,:,c]>=255)).mean().item() for c in range(3)]}
    result['stack_fixtures']=fixtures
    neutral=np.full_like(arr,.5);out=np.stack(apply(neutral,(128,128,128)),axis=2)
    result['neutral_unchanged']=bool(np.array_equal(out,np.full_like(out,128)))
    result['opacity_zero_unchanged']=bool(np.array_equal(np.stack(apply(arr,(128,128,128),opacity=0),axis=2),np.full_like(out,128)))
    result['channel_isolation']={c:bool(all(np.all(v==128) for i,v in enumerate(apply(arr,(128,128,128),channels=c)) if i!='MRC'.index(c))) for c in 'MRC'}
    # Actual public spec composers, the same real base/overlay and no color-pattern contribution.
    composition=[]
    for base in ['metallic','candy']:
        for mode,fn in [('single',compose_finish),('stacked',compose_finish_stacked)]:
            for ch in ['C','MRC']:
                try:
                    args=(base,'none' if mode=='single' else [],(128,128),np.ones((128,128),np.float32),42,1.0)
                    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                        plain=np.asarray(fn(*args,dither=False,spec_pattern_stack=[]))
                        added=np.asarray(fn(*args,dither=False,spec_pattern_stack=[dict(pattern=pid,opacity=.5,range=40,channels=ch,blend_mode='normal')]))
                    composition.append(dict(base=base,mode=mode,channels=ch,shape=list(added.shape),
                        mae=np.abs(added.astype(float)-plain.astype(float)).mean(axis=(0,1)).tolist(),
                        std=added.std(axis=(0,1)).tolist()))
                except Exception as e:composition.append(dict(base=base,mode=mode,channels=ch,error=str(e)))
    result['public_spec_composition']=composition
    # Existing served thumbnails; no force-bust and no import/start/restart of server.
    live=[]
    for pid in ['hex_cells','spec_holographic_oil_circuit']:
        entry={'id':pid}
        for route in ['spec-pattern-preview','spec-pattern-combined']:
            try:
                url='http://127.0.0.1:59876/api/'+route+'/'+pid
                data=urllib.request.urlopen(url,timeout=15).read();im=np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
                save(im,pid+'_served_'+route+'.png');entry[route]={'shape':list(im.shape)}
                if route=='spec-pattern-preview':entry[route]['M_R_pixels_equal_excluding_labels']=bool(np.array_equal(im[:52,:64],im[:52,65:129]))
                elif im.shape[:2]==(160,160):
                    # Routes do not pass UI defaults; compare the matching no-param call.
                    direct=(catalog[pid]((160,160),42,1.0)*255).astype(np.uint8)
                    entry[route]['served_vs_direct_mae_255']=float(np.abs(im.astype(float)-direct).mean())
            except Exception as e:entry[route]={'error':str(e)}
        live.append(entry)
    result['live_previews']=live
    result['process_seed_probes']=[json.loads(subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'--hash-probe'],cwd=ROOT,text=True)) for _ in range(2)]
    (OUT/'assessment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    summary={'native_count':len(result['rows']),'finite_valid':sum(r['finite'] and r['shape']==[2048,2048,3] for r in result['rows']),
        'archetypes':len(grouped),'material_changes_with_seed':sum(len(r['materials_across_8_seeds'])>1 for r in result['rows']),
        'render_seconds_median_p95_max':np.percentile([r['seconds'] for r in result['rows']],[50,95,100]).tolist(),
        'picker_native_mae_255_median_p95':np.percentile([r['picker_vs_native_mae_255'] for r in result['rows']],[50,95]).tolist(),
        'raw_applied_mae_255_median_p95':np.percentile([r['raw_vs_applied_neutral_mae_255'] for r in result['rows']],[50,95]).tolist(),
        'min_native_std_255':min(min(r['std_255']) for r in result['rows']),
        **{k:result[k] for k in ['same_archetype_screen','public_spec_composition','live_previews','process_seed_probes','channel_isolation','neutral_unchanged','opacity_zero_unchanged']}}
    (OUT/'probe_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['same_archetype_screen','public_spec_composition']},indent=2))

def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--probe',action='store_true');parser.add_argument('--hash-probe',action='store_true');parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.out:OUT=args.out.resolve()
    if args.hash_probe:
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            from engine.spec_patterns import PATTERN_CATALOG
            pid='hex_cells';seed=42+5000+hash(pid)%10000;a=PATTERN_CATALOG[pid]((160,160),seed,1.0)
        print(json.dumps(dict(pythonhashseed=os.environ.get('PYTHONHASHSEED'),pid=pid,seed=seed,sha256=hashlib.sha256(a.tobytes()).hexdigest())));return
    rows,catalog,result=inventory()
    if args.probe:probe(rows,catalog)
    else:print(json.dumps(result,indent=2))

if __name__=='__main__':main()
