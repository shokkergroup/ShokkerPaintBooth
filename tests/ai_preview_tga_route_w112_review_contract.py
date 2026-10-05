from __future__ import annotations
import hashlib, importlib.util, io, json, os, struct, sys, tempfile, threading
from pathlib import Path
from flask import Flask
from PIL import Image
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
CAND=Path('_easy_claude_work/ai14h_customer_psd_tga_inventory/private_route_candidate/server_routes/render_file_routes.py')
BASE=Path('server_routes/render_file_routes.py')
EXPECT_CAND='9e753da227ae4c7e5fce94d748d863e0e83c0a94e255cc212f69e694d1e40bba'
EXPECT_BASE='cd2b640eda292171e1362720947b8536a4291b6c7f35ac10b4a5a0b745adebd1'
def sha(b): return hashlib.sha256(b).hexdigest()
assert sha(CAND.read_bytes())==EXPECT_CAND
assert sha(BASE.read_bytes())==EXPECT_BASE
spec=importlib.util.spec_from_file_location('w112_private_review_route',CAND)
route=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(route)
class Log:
    def debug(self,*a,**k): pass
    def info(self,*a,**k): pass
    def warning(self,*a,**k): pass
    def error(self,*a,**k): pass
app=Flask('w112-review');route.register_render_file_routes(app,output_job_dir_resolver=lambda *_:None,logger=Log(),recent_renders_dir=None,external_write_guard=lambda *_:None)
def tga(rgb):
    r,g,b=rgb; head=bytes([0,0,2])+bytes(5)+bytes(4)+struct.pack('<HH',2,2)+bytes([24,0]);return head+bytes([b,g,r])*4+bytes(8)+b'TRUEVISION-XFILE.\0'
def request(path):
    with app.test_client() as client: return client.post('/preview-tga',json={'path':str(path)})
def decoded(resp):
    im=Image.open(io.BytesIO(resp.data));im.load();return im.convert('RGB').getpixel((0,0))
rows=[]
with tempfile.TemporaryDirectory(prefix='spb-w112-review-') as td:
    d=Path(td)
    # An independent cache-cap case: many unique, stable inputs must not make the sequential cache exceed MAX.
    route._tga_preview_cache.clear(); seq=[]
    for i in range(11):
        p=d/f'seq-{i}.tga'; raw=tga((i,40,200-i));p.write_bytes(raw);r=request(p);assert r.status_code==200 and r.headers['X-Source-Bytes-SHA256']==sha(raw);seq.append(r)
    assert len(route._tga_preview_cache)==route._TGA_CACHE_MAX==8
    rows.append({'id':'sequential-item-bound-11-sources','status':'PASS','cacheEntries':len(route._tga_preview_cache),'limit':route._TGA_CACHE_MAX})

    # Body/header must contain no raw TGA payload or local path; only PNG and digest leave the route.
    route._tga_preview_cache.clear(); secret=b'UNIQUE_PRIVATE_TGA_BYTES_6b4c'; p=d/'path-secret.tga'; raw=tga((51,91,141))+secret;p.write_bytes(raw);r=request(p)
    assert r.status_code==200 and r.data.startswith(b'\x89PNG\r\n\x1a\n') and r.headers['X-Source-Bytes-SHA256']==sha(raw)
    assert raw not in r.data and secret not in r.data and str(p).encode() not in r.data
    assert str(p) not in ''.join(v for k,v in r.headers.items() if k.lower()!='content-type')
    rows.append({'id':'no-source-bytes-or-local-path-disclosure','status':'PASS','responseType':r.content_type,'headerDigestMatches':True})

    # Replace the path immediately after its immutable snapshot, before Pillow decodes. It must refuse and not poison cache.
    route._tga_preview_cache.clear(); p=d/'snapshot-race.tga'; a=tga((200,10,20));b=tga((2,220,30));p.write_bytes(a);real_snapshot=route._read_tga_snapshot;swapped={'done':False}
    def snapshot_then_replace(path):
        raw,digest=real_snapshot(path)
        if not swapped['done']:
            Path(path).write_bytes(b);swapped['done']=True
        return raw,digest
    route._read_tga_snapshot=snapshot_then_replace
    try: r=request(p)
    finally: route._read_tga_snapshot=real_snapshot
    assert swapped['done'] and r.status_code==409 and 'image/png' not in r.content_type and not route._tga_preview_cache
    rows.append({'id':'mutation-immediately-after-snapshot-is-refused','status':'PASS','statusCode':r.status_code,'noCachePoison':not route._tga_preview_cache})

    # Deterministic concurrent misses observe len==7 at the eviction gate and both insert. This demonstrates MAX is not a concurrent bound.
    barrier=threading.Barrier(2,timeout=5)
    class GateCache(dict):
        def __len__(self):
            n=dict.__len__(self)
            if threading.current_thread().name.startswith('w112-bound') and n==7: barrier.wait()
            return n
    cache=GateCache({f'seed-{i}':b'x' for i in range(7)});route._tga_preview_cache=cache
    p1=d/'parallel-a.tga';p2=d/'parallel-b.tga';p1.write_bytes(tga((11,22,33)));p2.write_bytes(tga((44,55,66)));results=[];errors=[]
    def worker(path):
        try: results.append(request(path).status_code)
        except Exception as e: errors.append(repr(e))
    ts=[threading.Thread(name='w112-bound-a',target=worker,args=(p1,)),threading.Thread(name='w112-bound-b',target=worker,args=(p2,))]
    for t in ts:t.start()
    for t in ts:t.join(10)
    final_count=dict.__len__(cache)
    assert all(not t.is_alive() for t in ts) and not errors and results==[200,200] and final_count==9
    rows.append({'id':'concurrent-unique-misses-exceed-item-limit','status':'CONFIRMED_FINDING','statuses':results,'cacheEntriesAfter':final_count,'configuredLimit':route._TGA_CACHE_MAX})

    # Byte-read accounting: candidate snapshots the whole source on every hit, then streams the file again for final race verification.
    route._tga_preview_cache.clear();p=d/'read-passes.tga';raw=tga((71,81,91));p.write_bytes(raw);counts={'snapshot':0,'rehash':0};rs=route._read_tga_snapshot;rh=route._tga_path_sha256
    def count_snapshot(path): counts['snapshot']+=Path(path).stat().st_size;return rs(path)
    def count_rehash(path): counts['rehash']+=Path(path).stat().st_size;return rh(path)
    route._read_tga_snapshot=count_snapshot;route._tga_path_sha256=count_rehash
    try: first=request(p);after_miss=dict(counts);second=request(p);after_hit={k:counts[k]-after_miss[k] for k in counts}
    finally: route._read_tga_snapshot=rs;route._tga_path_sha256=rh
    assert first.status_code==second.status_code==200 and after_miss=={'snapshot':len(raw),'rehash':len(raw)} and after_hit=={'snapshot':len(raw),'rehash':len(raw)}
    rows.append({'id':'byte-read-work-miss-and-hit','status':'PASS','sourceBytes':len(raw),'missReadBytes':sum(after_miss.values()),'hitReadBytes':sum(after_hit.values()),'passesPerRequest':2})
print(json.dumps({'status':'REVIEW_FINDINGS' if any(r['status']=='CONFIRMED_FINDING' for r in rows) else 'PASS','cases':len(rows),'rows':rows,'candidateOnly':True,'customerFilesTouched':False,'providerCalls':0,'nativeCalls':0},indent=2))
