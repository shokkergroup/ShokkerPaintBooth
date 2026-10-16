"""Staging-only owner-eye proof for isolated Houdini H2-I6 Ember Cipher."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import cv2, numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_ember_cipher_i6_2026 import paint_ember_cipher_i6,spec_ember_cipher_i6

def _lit(s): return np.concatenate([np.dstack([s[...,n]]*3) for n in range(3)],axis=1)
def _material_response(paint, s, view):
    """Engine-informed proof only, never a substitute for iRacing capture.

    SPB_WIKI spec guide + engine.chameleon: high M intensifies grazing Fresnel,
    roughness softens it, and low numeric blue is the glossy clearcoat end.
    The old RGB transform turned unrelated state data green/red, so it could
    not legitimately pass or reject H2 (owner Houdini rebuild, 2026-08-31).
    """
    m, r, c = (s[..., n].astype(np.float32) / 255 for n in range(3))
    gloss = np.clip((1.0-c)/(1.0-16.0/255.0), 0, 1)
    smooth = np.power(np.clip(1.0-r, 0, 1), 1.18)
    dielectric = .04 + .96*view**5
    metal_flash = view*(.14+.86*m)
    coat_flash = dielectric*(.18+.82*gloss)*(.20+.80*smooth)
    flash = np.maximum(metal_flash*(.22+.78*smooth), coat_flash)
    body = paint*(.20+.72*(1.0-m)+.08*smooth)[...,None]
    return np.clip(body + np.array((.72,.89,1.0),np.float32)*flash[...,None], 0, 1)
def _secret_proxy(s):
    """Exact I6 eight-state material tuples only; diagnostic, never track proof."""
    tuples=np.array([[249,17,250],[151,67,146],[213,36,203],[88,131,93],[236,24,232],[174,78,169],[119,106,118],[202,49,190]],np.uint8)
    hit=np.zeros(s.shape[:2],bool)
    for q in tuples: hit |= np.all(s==q,axis=2)
    out=np.zeros((*hit.shape,3),np.uint8); out[hit]=[255,178,56]
    return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--seed',type=int,default=42); p.add_argument('--master',type=int,default=1024); p.add_argument('--out',type=Path,default=ROOT/'_houdini_h2_i6_p1_dev'); a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    src=np.full((a.master,a.master,3),132,np.uint8); mask=np.full((a.master,a.master),255,np.uint8)
    paint=paint_ember_cipher_i6(src,(a.master,a.master),mask,a.seed,1,None); spec=spec_ember_cipher_i6((a.master,a.master),a.seed,1,0,0); paint8=np.clip(paint*255,0,255).astype(np.uint8)
    files={'standard.png':cv2.resize(paint8,(256,256),interpolation=cv2.INTER_AREA),'picker_split.png':np.concatenate((cv2.resize(paint8,(48,48),interpolation=cv2.INTER_AREA),cv2.resize(spec,(48,48),interpolation=cv2.INTER_AREA)),axis=1),'literal_mrc.png':cv2.resize(_lit(spec),(1536,512),interpolation=cv2.INTER_NEAREST),'material_crosslight_diagnostic_not_track.png':cv2.resize(_material_response(paint,spec,.56),(1024,512),interpolation=cv2.INTER_LINEAR),'material_grazing_diagnostic_not_track.png':cv2.resize(_material_response(paint,spec,.90),(1024,512),interpolation=cv2.INTER_LINEAR),'exact_secret_diagnostic_not_track.png':cv2.resize(_secret_proxy(spec),(1024,1024),interpolation=cv2.INTER_NEAREST),'native_standard.png':paint8,'native_combined.png':np.concatenate((paint8,spec),axis=1),'native_metallic.png':spec[...,0],'native_roughness.png':spec[...,1],'native_clearcoat.png':spec[...,2]}
    files['picker_split.png'][:,47:49]=20
    for name,rgb in files.items(): cv2.imwrite(str(a.out/name),cv2.cvtColor((np.clip(rgb*255,0,255).astype(np.uint8) if rgb.dtype.kind=='f' else rgb),cv2.COLOR_RGB2BGR))
    print('stage=',a.out); print('paint_std=%.4f mrc_std=%.2f/%.2f/%.2f'%(paint.std(),*(spec[...,n].std() for n in range(3))))
if __name__=='__main__': main()
