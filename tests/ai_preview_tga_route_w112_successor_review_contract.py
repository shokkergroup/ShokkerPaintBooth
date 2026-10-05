from __future__ import annotations
import hashlib, importlib.util, io, json, os, struct, sys, tempfile, threading
from pathlib import Path
from flask import Flask
from PIL import Image
ROOT=Path.cwd(); sys.path.insert(0,str(ROOT))
CAND=Path('_easy_claude_work/ai14h_tga_cache_concurrency_candidate/server_routes/render_file_routes.py')
EXPECTED='00bd0ea753d31e53d7cdb38b2bf6bcab361bf2d872f76df1aee8f6dfc49b7675'
assert hashlib.sha256(CAND.read_bytes()).hexdigest()==EXPECTED
spec=importlib.util.spec_from_file_location('w112_successor_route',CAND);route=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(route)
class Log:
    def debug(self,*a,**k): pass
    def info(self,*a,**k): pass
    def warning(self,*a,**k): pass
    def error(self,*a,**k): pass
app=Flask('w112-successor');route.register_render_file_routes(app,output_job_dir_resolver=lambda *_:None,logger=Log(),recent_renders_dir=None,external_write_guard=lambda *_:None)
def tga(rgb,alpha=None):
    r,g,b=rgb; bpp=32 if alpha is not None else 24; head=bytes([0,0,2])+bytes(5)+bytes(4)+struct.pack('<HH',2,2)+bytes([bpp,0]); px=(b''.join(bytes([b,g,r,a]) for a in alpha) if alpha is not None else bytes([b,g,r])*4);return head+px+bytes(8)+b'TRUEVISION-XFILE.\0'
def req(path):
    with app.test_client() as c:return c.post('/preview-tga',json={'path':str(path)})
def pixel(resp):
    im=Image.open(io.BytesIO(resp.data));im.load();return im.convert('RGBA').getpixel((0,0))
rows=[]
with tempfile.TemporaryDirectory(prefix='spb-w112-successor-') as td:
    d=Path(td);route._tga_preview_cache.clear();stamp=1700000000000000000
    # Same-size/mtime replacement must bind the response to exact source bytes.
    p=d/'aba.tga';a=tga((200,10,20));b=tga((5,220,30));p.write_bytes(a);os.utime(p,ns=(stamp,stamp));ra=req(p);p.write_bytes(b);os.utime(p,ns=(stamp,stamp));rb=req(p)
    assert ra.status_code==rb.status_code==200 and pixel(ra)[:3]==(200,10,20) and pixel(rb)[:3]==(5,220,30)
    assert ra.headers['X-Source-Bytes-SHA256']==hashlib.sha256(a).hexdigest() and rb.headers['X-Source-Bytes-SHA256']==hashlib.sha256(b).hexdigest()
    rows.append({'id':'same-size-mtime-byte-identity','status':'PASS'})
    # Actual alpha-bearing route output.
    route._tga_preview_cache.clear();pa=d/'alpha.tga';ar=tga((40,80,120),(0,64,192,255));pa.write_bytes(ar);r=req(pa);im=Image.open(io.BytesIO(r.data));im.load();alphas=sorted(im.getchannel('A').getdata())
    assert r.status_code==200 and alphas==[0,64,192,255] and r.headers['X-Source-Bytes-SHA256']==hashlib.sha256(ar).hexdigest()
    rows.append({'id':'alpha-preserved-and-digest-bound','status':'PASS'})
    # Schedule both distinct misses before insertion, then require bounded insertion.
    route._tga_preview_cache.clear();route._tga_preview_cache.update({f'seed{i}':b'x' for i in range(7)})
    p1=d/'c1.tga';p2=d/'c2.tga';p1.write_bytes(tga((11,22,33)));p2.write_bytes(tga((44,55,66)))
    original_open=Image.open;barrier=threading.Barrier(2,timeout=8)
    def gated_open(source,*args,**kwargs):
        if isinstance(source,io.BytesIO) and threading.current_thread().name.startswith('W112Gate'):
            barrier.wait()
        return original_open(source,*args,**kwargs)
    Image.open=gated_open;codes=[];errors=[]
    def worker(path):
        try:codes.append(req(path).status_code)
        except Exception as e:errors.append(repr(e))
    ts=[threading.Thread(name='W112GateA',target=worker,args=(p1,)),threading.Thread(name='W112GateB',target=worker,args=(p2,))]
    try:
        [t.start() for t in ts];[t.join(12) for t in ts]
    finally:Image.open=original_open
    assert all(not t.is_alive() for t in ts) and not errors and sorted(codes)==[200,200] and len(route._tga_preview_cache)==8
    rows.append({'id':'parallel-unique-misses-remain-bounded','status':'PASS','statuses':sorted(codes),'cacheEntries':len(route._tga_preview_cache)})
    # Simultaneous same-key requests must both succeed and leave only one keyed entry.
    route._tga_preview_cache.clear();ps=d/'samekey.tga';ps.write_bytes(tga((77,88,99)));barrier=threading.Barrier(2,timeout=8);codes=[];errors=[]
    Image.open=gated_open
    try:
        ts=[threading.Thread(name='W112GateC',target=worker,args=(ps,)),threading.Thread(name='W112GateD',target=worker,args=(ps,))]
        [t.start() for t in ts];[t.join(12) for t in ts]
    finally:Image.open=original_open
    assert all(not t.is_alive() for t in ts) and not errors and sorted(codes)==[200,200] and len(route._tga_preview_cache)==1
    rows.append({'id':'parallel-same-key-deduplicates-entry','status':'PASS'})
    # Cache hit and miss integrity against a swap immediately after snapshot.
    route._tga_preview_cache.clear();p=d/'swap.tga';p.write_bytes(a);snap=route._read_tga_snapshot;done={'v':False}
    def replace_after_snapshot(path):
        result=snap(path)
        if not done['v']:Path(path).write_bytes(b);done['v']=True
        return result
    route._read_tga_snapshot=replace_after_snapshot
    try:r=req(p)
    finally:route._read_tga_snapshot=snap
    assert r.status_code==409 and not route._tga_preview_cache
    rows.append({'id':'post-snapshot-source-swap-refused','status':'PASS'})
print(json.dumps({'status':'PASS','cases':len(rows),'rows':rows,'candidateOnly':True,'providerCalls':0,'nativeCalls':0,'customerFilesTouched':False},indent=2))
