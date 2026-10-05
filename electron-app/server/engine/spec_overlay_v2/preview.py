"""Canonical applied-spec previews; no paint profile and no invented RGB spec.

SPB-105 v2 tick 3. Owner requested truthful previews and the Bases experience.
The same targets/coverage and explicit strength used by composition drive the
preview. The monochrome material study is an illustrative lighting model, not
an iRacing screenshot. Raw M/R/Cc inspectors never average channels together.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json,threading
import cv2
import numpy as np
from PIL import Image,ImageDraw
from .catalog import definitions
from .contract import apply_material
ROOT=Path(__file__).resolve().parent
_PREVIEW_LOCK=threading.RLock()
REFERENCES={'neutral':(128,128,128),'chrome':(245,20,16),'matte':(10,230,240),'no_coat':(110,100,0)}

@lru_cache(maxsize=1)
def _metadata():
    legacy=json.loads((ROOT/'legacy_catalog.json').read_text(encoding='utf-8'))['items']
    return {row['id']:row for row in legacy+definitions()['items']}

def definition(pid):return _metadata().get(pid,{'id':pid,'defaults':{},'defaultOpacity':.5,'defaultRange':40})

def render_native(pid,seed=42,params=None,reference='neutral',strength=None,settings=None):
    from engine.spec_patterns import PATTERN_CATALOG
    from engine.compose import _apply_spec_pattern_to_channels,_cached_spec_pattern_array
    from engine.gpu import to_cpu
    if pid not in PATTERN_CATALOG:
        from engine.spec_pattern_aliases import SPEC_PATTERN_ALIASES
        pid=SPEC_PATTERN_ALIASES.get(pid,pid)
    meta=definition(pid);fn=PATTERN_CATALOG[pid];settings=settings or {}
    amount=meta.get('defaultOpacity',50)/100. if strength is None else min(1.,max(0.,float(strength)))
    fields=np.asarray(_cached_spec_pattern_array(fn,pid,(2048,2048),int(seed),1.,
        settings.get('params',meta.get('defaults',{}) if params is None else params),
        settings.get('scale',1),settings.get('rotation',0),settings.get('offset_x',.5),
        settings.get('offset_y',.5),settings.get('box_size',100)),np.float32)
    if not np.isfinite(fields).all():raise ValueError('Non-finite material field: '+pid)
    base=REFERENCES.get(reference,REFERENCES['neutral'])
    planes=[np.full((2048,2048),v,np.float32) for v in base]
    channels=settings.get('channels','MRC')
    if settings.get('muted') or not channels:amount=0
    if fields.ndim==3 and fields.shape[2]==4:applied=apply_material(fields,*planes,amount,channels)
    else:applied=_apply_spec_pattern_to_channels(fields,*planes,settings.get('range',meta.get('defaultRange',40)),amount,settings.get('blend_mode','normal'),channels)
    return fields,np.rint(np.clip(np.stack([to_cpu(v) for v in applied],axis=2),0,255)).astype(np.uint8)

def material_study(spec):
    """Neutral curved coupon under a broad white source; illustrative only."""
    spec=spec.astype(np.float32)/255;m=spec[:,:,0];r=np.maximum(spec[:,:,1],.065);cc=spec[:,:,2]
    h,w=m.shape;x=np.linspace(-1,1,w,dtype=np.float32)[None,:]
    incidence=np.exp(-((x-.17)/(.12+.7*r))**2)
    coat=np.where(cc>15/255,np.exp(-((x+.25)/(.08+.85*cc))**2)*(.28+.28*(1-cc)),0)
    response=.12+.24*(1-m)+(.12+.52*m)*incidence+coat
    tone=np.uint8(np.clip(response**(1/1.6),0,1)*255)
    return np.repeat(tone[:,:,None],3,axis=2)

def detail_crop(array):return array[768:1280,768:1280]

@lru_cache(maxsize=8)
def _applied_cached(pid,seed,reference,strength,settings):
    return render_native(pid,seed=seed,reference=reference,strength=strength,settings=json.loads(settings))[1]

def image(pid,kind='combined',size=160,seed=42,reference='neutral',strength=None,settings=None):
    # Bound native allocations during a wall of simultaneous thumbnail loads;
    # paired study/map requests share the exact same applied material buffer.
    with _PREVIEW_LOCK:applied=_applied_cached(pid,seed,reference,strength,json.dumps(settings or {},sort_keys=True))
    if kind=='channels':
        detail=cv2.resize(detail_crop(applied),(64,64),interpolation=cv2.INTER_AREA)
        canvas=Image.new('RGB',(194,64),(30,30,30))
        for index,x in enumerate((0,65,130)):
            channel=np.repeat(detail[:,:,index:index+1],3,axis=2);canvas.paste(Image.fromarray(channel),(x,0))
        draw=ImageDraw.Draw(canvas)
        for label,x in [('M',2),('R',67),('Cc',132)]:draw.text((x,52),label,fill='white',stroke_width=1,stroke_fill='black')
        return canvas
    detail=applied if kind=='whole' else detail_crop(applied)
    if kind=='visual':detail=material_study(detail)
    return Image.fromarray(cv2.resize(detail,(int(size),int(size)),interpolation=cv2.INTER_AREA),'RGB')

@lru_cache(maxsize=64)
def _hash_files(signature):
    h=hashlib.sha256()
    for name,_,_ in signature:h.update(Path(name).read_bytes())
    return h.hexdigest()

def dependency_fingerprint(fn):
    paths=[ROOT/'preview.py',ROOT/'contract.py',ROOT/'compose.py',ROOT/'catalog.json',ROOT/'legacy_catalog.json',ROOT.parent/'compose.py']
    if getattr(fn,'_spb_overlay_version',1)==2:
        return hashlib.sha256((getattr(fn,'_spb_source_fingerprint','')+_hash_files(tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths))).encode()).hexdigest()
    paths.extend([ROOT.parent/'spec_pattern_families/overhaul_2026.py',ROOT.parent/'spec_pattern_families/semantic_overlays_2026.py'])
    return _hash_files(tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths))
