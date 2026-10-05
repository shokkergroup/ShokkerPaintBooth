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
    r=carband(L); print('RES %-22s %-14s b=%.3f ac=%.3f fi=%.1f'%(fid,tag,r[0],autocorr1(L),fineness(L)))
for fid in sys.argv[2].split(','):
    d=K.ALL[fid]; kw=dict(d['kw']); vd=d['vd']
    meas(fid,'cur')
    d['vd']=(1.0,1.0); meas(fid,'vdflat')
    d['kw']=dict(kw, floor=0.0); meas(fid,'+floor0')
    d['kw']=dict(kw, floor=0.0, ambient=0.0); meas(fid,'+amb0')
    d['kw']=dict(kw, floor=0.0, ambient=0.0, sparkle=0.0); meas(fid,'+spk0')
    d['kw']=kw; d['vd']=vd
