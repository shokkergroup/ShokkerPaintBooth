"""Exact-engine H10-I11 proof through a temporary in-memory registry entry."""
from pathlib import Path
import tempfile,time,sys,cv2,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import shokker_engine_v2 as engine
from engine.expansions.fractured_houdini_marble_rose_i11_2026 import paint_marble_rose_i11,spec_marble_rose_i11
FID='__houdini_h10_i11_probe__';SOURCE=2048
def paint(p,shape,mask,seed=None,pm=1.,bb=None):return paint_marble_rose_i11(p,shape,mask,42 if seed is None else int(seed),pm,bb)
def spec(shape,mask,seed=None,sm=1.):
 h,w=map(int,shape);mrc=spec_marble_rose_i11((h,w),42 if seed is None else int(seed),sm,0,0);cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(cov,0,1)*255;return out
old=engine.MONOLITHIC_REGISTRY.get(FID);engine.MONOLITHIC_REGISTRY[FID]=(spec,paint)
with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as t:path=Path(t.name)
try:
 Image.new('RGB',(SOURCE,SOURCE),(136,136,136)).save(path);zone={'name':'H10I11Probe','color':[.533,.533,.533],'intensity':100,'base_strength':1.,'base_spec_strength':1.,'base_color_mode':'authored_swatch','base_color':[1.,1.,1.],'region_mask':np.ones((SOURCE,SOURCE),np.float32),'apply_area_shape_only':True,'finish':FID};beg=time.perf_counter();p,s,elapsed=engine.preview_render(str(path),[zone],seed=42,preview_scale=.5);wall=time.perf_counter()-beg
finally:
 path.unlink(missing_ok=True)
 if old is None:engine.MONOLITHIC_REGISTRY.pop(FID,None)
 else:engine.MONOLITHIC_REGISTRY[FID]=old
p=np.asarray(p)[...,:3].astype(np.uint8);s=np.asarray(s)[...,:3].astype(np.uint8);out=ROOT/'_houdini_h10_i11_engine_probe';out.mkdir(exist_ok=True);split=np.concatenate((cv2.resize(p,(48,48),interpolation=cv2.INTER_AREA),cv2.resize(s,(48,48),interpolation=cv2.INTER_AREA)),1);split[:,47:49]=20
for name,img in {'picker_split.png':split,'standard.png':cv2.resize(p,(256,256),interpolation=cv2.INTER_AREA),'combined.png':np.concatenate((p,s),1),'metallic.png':s[...,0],'roughness.png':s[...,1],'clearcoat.png':s[...,2]}.items():cv2.imwrite(str(out/name),cv2.cvtColor(img,cv2.COLOR_RGB2BGR) if img.ndim==3 else img)
print(f'engine_elapsed_s={elapsed:.3f} wall_s={wall:.3f} paint_std={p.std()/255:.4f} mrc_std={s[...,0].std():.2f}/{s[...,1].std():.2f}/{s[...,2].std():.2f}')
