"""Private P1 evidence for I34 Lantern Moth; never writes catalog assets."""
from pathlib import Path
import argparse,sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_lantern_moth_i34_2026 import paint_lantern_moth_i34,spec_lantern_moth_i34
p=argparse.ArgumentParser();p.add_argument('pass_name');a=p.parse_args();n=2048;out=ROOT/f'_houdini_i34_{a.pass_name}_dev';out.mkdir(exist_ok=True);src=np.full((n,n,3),132,np.uint8);mask=np.ones((n,n),np.float32);paint=paint_lantern_moth_i34(src,(n,n),mask,42,1,None);spec=spec_lantern_moth_i34((n,n),42,1,0,0);paint8=np.uint8(np.clip(paint*255,0,255));
for name,img in {'standard.png':paint8,'combined.png':np.concatenate((paint8,spec),1),'metallic.png':spec[...,0],'roughness.png':spec[...,1],'clearcoat.png':spec[...,2],'picker.png':np.concatenate((cv2.resize(paint8,(64,64),interpolation=cv2.INTER_AREA),cv2.resize(spec,(64,64),interpolation=cv2.INTER_AREA)),1)}.items():cv2.imwrite(str(out/name),img)
print({'out':str(out),'paint_std':round(float(paint.std()),4),'mrc_std':[round(float(spec[...,i].std()),2)for i in range(3)]})
