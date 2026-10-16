"""Exact-engine H10 development standard/picker proof; does not restart a server."""
from pathlib import Path
import tempfile,time,sys
import cv2,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import shokker_engine_v2 as engine
FINISH='houdini_marble_rose';SOURCE=2048
with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as t: path=Path(t.name)
try:
 Image.new('RGB',(SOURCE,SOURCE),(136,136,136)).save(path);zone={'name':'H10EngineProbe','color':[.533,.533,.533],'intensity':100,'base_strength':1.0,'base_spec_strength':1.0,'base_color_mode':'authored_swatch','base_color':[1.,1.,1.],'region_mask':np.ones((SOURCE,SOURCE),np.float32),'apply_area_shape_only':True,'finish':FINISH};began=time.perf_counter();paint,spec,elapsed=engine.preview_render(str(path),[zone],seed=42,preview_scale=.5);wall=time.perf_counter()-began
finally: path.unlink(missing_ok=True)
if paint is None or spec is None:raise RuntimeError('engine probe returned no paint/spec')
paint=np.asarray(paint)[...,:3].astype(np.uint8);spec=np.asarray(spec)[...,:3].astype(np.uint8)
if paint.shape[:2]!=(1024,1024) or spec.shape[:2]!=(1024,1024):raise RuntimeError(f'unexpected preview shape {paint.shape}/{spec.shape}')
out=ROOT/'_houdini_h10_engine_probe';out.mkdir(exist_ok=True);split=np.concatenate((cv2.resize(paint,(48,48),interpolation=cv2.INTER_AREA),cv2.resize(spec,(48,48),interpolation=cv2.INTER_AREA)),1);split[:,47:49]=20
for name,img in [('picker_split.png',split),('standard.png',cv2.resize(paint,(256,256),interpolation=cv2.INTER_AREA)),('combined.png',np.concatenate((paint,spec),1)),('metallic.png',spec[...,0]),('roughness.png',spec[...,1]),('clearcoat.png',spec[...,2])]:
 if not cv2.imwrite(str(out/name),cv2.cvtColor(img,cv2.COLOR_RGB2BGR) if img.ndim==3 else img):raise RuntimeError(name)
print(f'engine_elapsed_s={elapsed:.3f} wall_s={wall:.3f} paint_std={paint.std()/255:.4f} mrc_std={spec[...,0].std():.2f}/{spec[...,1].std():.2f}/{spec[...,2].std():.2f}')
