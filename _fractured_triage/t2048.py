import sys, time, numpy as np, importlib
ROOT=r'C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum'; sys.path.insert(0,ROOT)
R=2048
for mod in sys.argv[1:]:
    M=importlib.import_module('engine.expansions.fractured_%s_2026'%mod); K=M.KIT
    worst=(None,0.0); tot=0.0
    for fid in sorted(K.ALL):
        K.art_work_cached.cache_clear(); K.macro_cached.cache_clear()
        sf,pf=K.mk(fid)
        base=np.zeros((R,R,3),np.float32); mask=np.ones((R,R),np.float32)
        t0=time.perf_counter()
        p=pf(base,(R,R),mask,1234,1.0,None); s=sf((R,R),mask,1234,1.0)
        dt=time.perf_counter()-t0; tot+=dt
        if dt>worst[1]: worst=(fid,dt)
    print("T2048 %-7s worst=%s %.2fs  mean=%.2fs"%(mod,worst[0],worst[1],tot/len(K.ALL)))
