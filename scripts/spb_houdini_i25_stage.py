"""Private I25 native/picker/material proof. Never writes a catalog card."""
from pathlib import Path
import sys, cv2, numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_veiled_reliquary_i25_2026 import paint_veiled_reliquary_i25,spec_veiled_reliquary_i25
name=sys.argv[1] if len(sys.argv)>1 else 'p1'; out=ROOT/f'_houdini_i25_{name}_native'; out.mkdir(exist_ok=True)
n=2048; source=np.full((n,n,3),132,np.uint8); mask=np.full((n,n),255,np.uint8)
paint=paint_veiled_reliquary_i25(source,(n,n),mask,917,1,None); spec=spec_veiled_reliquary_i25((n,n),917,1,0,0); p8=np.uint8(np.clip(paint*255,0,255))
for fn,img in {'standard.png':p8,'combined.png':np.concatenate((p8,spec),axis=1),'metallic.png':spec[...,0],'roughness.png':spec[...,1],'clearcoat.png':spec[...,2],'picker.png':np.concatenate((cv2.resize(p8,(64,64),interpolation=cv2.INTER_AREA),cv2.resize(spec,(64,64),interpolation=cv2.INTER_AREA)),axis=1)}.items(): cv2.imwrite(str(out/fn),img)
# Native 512² owner-eye crop: allows anatomy review without mistaking a
# downscaled whole-car sheet for a real 2048² inspection.
c=n//2; crop=np.concatenate((p8[c-256:c+256,c-256:c+256],spec[c-256:c+256,c-256:c+256]),axis=1); cv2.imwrite(str(out/'native_crop.png'),crop)
print({'paint_std':round(float(paint.std()),4),'MRC_std':[round(float(spec[...,i].std()),2) for i in range(3)]})
