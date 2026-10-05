"""Daylight microfacet diagnostic on actual COLOR SHOXX pixels.

This is a simplified energy-weighted GGX model, not iRacing's shader.
No physical normal-map, iridescence or angle-dependent pigment is invented.
White ambient and white directional sun isolate pigment/material competition.
"""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from engine.expansions.astra.wave2 import MODULES
OUT=ROOT/'_astra40_work'
def linear(p):return np.where(p<=.04045,p/12.92,((p+.055)/1.055)**2.4)
def srgb(p):return np.where(p<=.0031308,p*12.92,1.055*np.maximum(p,0)**(1/2.4)-.055)
def shade(p,s,angle):
    theta=np.deg2rad(angle);v=np.array([np.sin(theta),0,np.cos(theta)])
    l=np.array([np.sin(np.deg2rad(45)),0,np.cos(np.deg2rad(45))]);h=l+v;h/=np.linalg.norm(h)
    nl=l[2];nv=max(v[2],.04);nh=max(h[2],.001);vh=max(float(v@h),.001)
    m=s[...,0:1]/255;rough=s[...,1:2]/255;coat=(255-s[...,2:3])/239
    albedo=linear(p);f0=.04*(1-m)+albedo*m
    f=f0+(1-f0)*(1-vh)**5
    alpha=np.maximum(rough**2,.015);a2=alpha**2
    d=a2/(np.pi*(nh*nh*(a2-1)+1)**2)
    def g1(c):return 2*c/(c+np.sqrt(a2+(1-a2)*c*c))
    brdf=d*g1(nl)*g1(nv)*f/(4*nl*nv+.00001)
    diffuse=albedo*(1-m)*(1-f)/np.pi
    # Broad neutral ambient remains on even at oblique reflection angles.
    ambient=.3*albedo*(1-.83*m)+.035*f0
    out=ambient+3.2*nl*(diffuse+brdf)
    out=out*(1-.04*coat)+coat*.025
    return out
def main():
    angles=[-75,-65,-55,-48,-45,-42,-35,-20,0,20,40,60,75]
    rows={};font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
    sheet=Image.new('RGB',(1320,1040),'#101520');draw=ImageDraw.Draw(sheet)
    draw.text((18,10),'COLOR SHOXX / white daylight GGX diagnostic / NOT an iRacing render',font=font,fill='white')
    for index,m in enumerate(x for x in MODULES if x.LANE=='COLOR SHOXX'):
        p=np.asarray(Image.open(OUT/m.FID/'paint.png'),np.float32)/255
        s=np.asarray(Image.open(OUT/m.FID/'spec.png'),np.float32)
        sample=p[::4,::4];spec=s[::4,::4]
        populations={};views=[]
        for size in (512,256,128):
            pp=sample if size==512 else cv2.resize(p,(size,size),interpolation=cv2.INTER_AREA)
            ss=spec if size==512 else cv2.resize(s,(size,size),interpolation=cv2.INTER_AREA)
            means=np.array([shade(pp,ss,a).mean(axis=(0,1)) for a in angles])
            chroma=means/(means.sum(axis=1,keepdims=True)+1e-8)
            distance=np.linalg.norm(chroma[:,None,:]-chroma[None,:,:],axis=2)
            left,right=np.unravel_index(np.argmax(distance),distance.shape)
            display=np.clip(srgb(means/(1+means)),0,1)
            populations[str(size)]=dict(angles=angles,linear_mean_rgb=means.tolist(),display_rgb=(display*255).astype(int).tolist(),
                maximum_chromaticity_distance=float(distance[left,right]),largest_difference_angles=[angles[left],angles[right]])
            if size==512:views=display
        rows[m.FID]=dict(name=m.NAME,model='simplified GGX + white ambient, uncalibrated to iRacing',mip_study=populations,on_track_verified=False)
        y=55+index*97;draw.text((18,y),m.NAME,font=font,fill='white')
        for j,(angle,color) in enumerate(zip(angles,views)):
            x=272+j*79;draw.rectangle((x,y,x+68,y+47),fill=tuple((color*255).astype(int)))
            draw.text((x,y+49),str(angle)+' deg',font=font,fill='#abb8ca')
        print(m.FID,'native chromaticity delta',round(populations['512']['maximum_chromaticity_distance'],3),
              '128px',round(populations['128']['maximum_chromaticity_distance'],3),flush=True)
    (OUT/'daylight_diagnostic.json').write_text(json.dumps(rows,indent=2))
    sheet.save(OUT/'daylight_diagnostic.jpg',quality=94)
if __name__=='__main__':main()
