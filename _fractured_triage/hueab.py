import sys, numpy as np, importlib
ROOT=r'C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum'
sys.path.insert(0,ROOT); sys.path.insert(0,ROOT+r'\_fractured_triage')
from verify_guard import carband, autocorr1, fineness
mod=sys.argv[1]
M=importlib.import_module('engine.expansions.fractured_%s_2026'%mod); K=M.KIT
def meas(fid,tag):
    K.art_work_cached.cache_clear(); K.macro_cached.cache_clear()
    s,pf=K.mk(fid)
    p=pf(np.zeros((512,512,3),np.float32),(512,512),np.ones((512,512),np.float32),1,1.0,None)
    L=0.299*p[:,:,0]+0.587*p[:,:,1]+0.114*p[:,:,2]
    r=carband(L)
    print('RES %-22s %-16s b=%.3f ac=%.3f fi=%.1f'%(fid,tag,r[0],autocorr1(L),fineness(L)))
for fid in sys.argv[2].split(','):
    d=K.ALL[fid]; sb=d['satboost']; hs=d['hspan']; hu=list(d['hues']); kw=dict(d['kw'])
    meas(fid,'base')
    d['kw']=dict(kw, floor=0.0); meas(fid,'floor0')
    d['kw']=dict(kw)
    d['hues']=[hu[0]]*9+[hu[1]]*2; meas(fid,'hero9+2')
    d['hues']=[hu[0]]*11; meas(fid,'mono11')
    d['hues']=hu; d['satboost']=1.0; meas(fid,'sat1.0')
    d['satboost']=sb
