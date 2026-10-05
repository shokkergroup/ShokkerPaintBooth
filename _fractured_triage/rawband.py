# [SPB-FRACTURED-090b] raw-generator band probe: is the GEOMETRY in band,
# before the LUT/finish chain touches it? (T at GEN -> the kit's own resize
# chain -> 512 -> radial power fractions).
import importlib, sys, numpy as np, cv2
ROOT=r'C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum'
sys.path.insert(0,ROOT); sys.path.insert(0,ROOT+r'\_fractured_triage')
mod=sys.argv[1]
M=importlib.import_module('engine.expansions.fractured_%s_2026'%mod); K=M.KIT
yy,xx=np.mgrid[0:512,0:512]; r=np.hypot(yy-256,xx-256)
BINS=[(2,32),(32,64),(64,90),(90,120),(120,160),(160,220),(220,362)]
for fid in sorted(K.ALL):
    d=K.ALL[fid]
    ea=dict(d.get('eargs',{})); ea.pop('span',None)
    T=np.asarray(K.engines[d['engine']](K.GEN,int(d['seed']),**ea),np.float32)
    T=cv2.resize(cv2.resize(T,(1024,1024),interpolation=cv2.INTER_CUBIC),(512,512),interpolation=cv2.INTER_LINEAR)
    P=np.abs(np.fft.fftshift(np.fft.fft2(T-T.mean())))**2
    tot=P[r>=2].sum()
    fr=[P[(r>=a)&(r<b)].sum()/tot for a,b in BINS]
    print('RAW %-24s band=%.3f  ' % (fid, P[(r>=64)&(r<=256)].sum()/tot)
          + ' '.join('%d:%.2f'%(a,f) for (a,_b),f in zip(BINS,fr)))
