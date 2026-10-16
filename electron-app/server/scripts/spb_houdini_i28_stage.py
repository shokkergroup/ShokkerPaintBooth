"""Private I28 proof. Never writes catalog assets."""
from pathlib import Path
import sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));from engine.expansions.fractured_houdini_cinder_veil_i28_2026 import paint_cinder_veil_i28,spec_cinder_veil_i28
name=sys.argv[1]if len(sys.argv)>1 else'p1';out=ROOT/f'_houdini_i28_{name}_native';out.mkdir(exist_ok=True);n=2048;src=np.full((n,n,3),132,np.uint8);mask=np.full((n,n),255,np.uint8);paint=paint_cinder_veil_i28(src,(n,n),mask,1559,1,None);spec=spec_cinder_veil_i28((n,n),1559,1,0,0);p8=np.uint8(np.clip(paint*255,0,255))
for fn,img in {'standard.png':p8,'combined.png':np.concatenate((p8,spec),axis=1),'metallic.png':spec[...,0],'roughness.png':spec[...,1],'clearcoat.png':spec[...,2],'picker.png':np.concatenate((cv2.resize(p8,(64,64),interpolation=cv2.INTER_AREA),cv2.resize(spec,(64,64),interpolation=cv2.INTER_AREA)),axis=1)}.items():cv2.imwrite(str(out/fn),img)
c=n//2;cv2.imwrite(str(out/'native_crop.png'),np.concatenate((p8[c-256:c+256,c-256:c+256],spec[c-256:c+256,c-256:c+256]),axis=1));print({'paint_std':round(float(paint.std()),4),'MRC_std':[round(float(spec[...,i].std()),2)for i in range(3)]})
