from __future__ import annotations
import ast, base64, hashlib, importlib.util, io, json, os, sys, tempfile
from pathlib import Path
from flask import Flask
from PIL import Image
from psd_tools import PSDImage

ROOT=Path.cwd(); CAND=ROOT/'_easy_claude_work/ai14h_w78_candidate'; FROZEN=CAND/'frozen'
sys.path.insert(0,str(ROOT/'electron-app/server'))

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def extract_function(source_path,name,globals_dict):
    tree=ast.parse(source_path.read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source_path),'exec'),globals_dict)
    return globals_dict[name]

# Execute the exact private candidate code only; importing this module has no server startup.
project=ast.parse((FROZEN/'project_routes.py').read_text(encoding='utf-8'))
fp_node=next(n for n in project.body if isinstance(n,ast.FunctionDef) and n.name=='_source_fingerprint')
fp_globals={'os':os,'hashlib':hashlib}
exec(compile(ast.Module(body=[fp_node],type_ignores=[]),str(FROZEN/'project_routes.py'),'exec'),fp_globals)
source_fingerprint=fp_globals['_source_fingerprint']
spec=importlib.util.spec_from_file_location('w78_candidate_psd_import',CAND/'server_routes/psd_import_routes.py')
route=importlib.util.module_from_spec(spec);spec.loader.exec_module(route);route._source_fingerprint=source_fingerprint
cache_globals={'os':os,'_psd_cache':{}}
get_cached=extract_function(CAND/'server.py','_get_cached_psd',cache_globals)
invalidate_actual=extract_function(CAND/'server.py','_invalidate_cached_psd',cache_globals)
invalidations=[]
def invalidate(path):
    invalidations.append(path);return invalidate_actual(path)
app=Flask('w78-cache-review')
class Log:
    def info(self,*a,**k): pass
    def warning(self,*a,**k): pass
    def error(self,*a,**k): pass
route.register_psd_import_routes(app,require_internal_request=lambda:(True,None),sanitize_path=lambda p:(str(Path(p).resolve()),None),get_cached_psd=get_cached,logger=Log(),invalidate_cached_psd=invalidate)
client=app.test_client(); real_open=PSDImage.open; parse_count={'n':0}
def counted_open(path,*a,**k): parse_count['n']+=1; return real_open(path,*a,**k)
PSDImage.open=staticmethod(counted_open)

def make_psd(path,hidden_rgb,visible_rgb):
    psd=PSDImage.new('RGB',(8,8),(0,0,0))
    psd.append(psd.create_pixel_layer(Image.new('RGBA',(8,8),(*visible_rgb,255)),name='Paint'))
    hidden=psd.create_pixel_layer(Image.new('RGBA',(8,8),(*hidden_rgb,255)),name='Hidden Secret');hidden.visible=False;psd.append(hidden)
    psd.save(path);return path.read_bytes()
def set_mtime(path,ns): os.utime(path,ns=(ns,ns))
def ask(path): return client.post('/api/psd-import',json={'psd_path':str(path),'thumbnail_size':32},headers={'X-Shokker-Internal':'1'})
def pixel(payload):
    raw=base64.b64decode(payload['composite'].split(',',1)[1]);return list(Image.open(io.BytesIO(raw)).convert('RGB').getpixel((3,3)))

rows=[]
try:
  with tempfile.TemporaryDirectory(prefix='spb-w78-') as td:
    t=1_700_000_000_000_000_000
    # F01: independent stable import proves actual PSD route and image pixel baseline.
    stable=Path(td)/'stable.psd'; stable_a=make_psd(stable,(1,2,3),(200,10,20));set_mtime(stable,t)
    r=ask(stable);assert r.status_code==200,(r.status_code,r.get_json());body=r.get_json()
    assert body['sourceBytesSha256']==sha(stable) and pixel(body)==[200,10,20]
    assert stable_a not in r.data and b'8BPS' not in r.data
    rows.append({'id':'real-stable-PSD-import','status':'PASS','pixel':pixel(body),'digest':body['sourceBytesSha256']})
    first_count=parse_count['n']
    r2=ask(stable);assert r2.status_code==200 and pixel(r2.get_json())==[200,10,20] and parse_count['n']==first_count
    rows.append({'id':'unchanged-response-cache-hit','status':'PASS','parseCount':parse_count['n']})

    # F02/F03: root's fixed-mtime A -> raced B -> restore A poisoning sequence.
    p=Path(td)/'poison.psd'; a=make_psd(p,(10,20,30),(200,10,20));set_mtime(p,t); digest_a=sha(p)
    b=make_psd(Path(td)/'poison-b.psd',(100,120,130),(15,180,90))
    original_fp=route._source_fingerprint; once={'v':False}
    def replace_after_pre_hash(path):
      info=original_fp(path)
      if str(Path(path).resolve())==str(p.resolve()) and not once['v']:
        once['v']=True;p.write_bytes(b);set_mtime(p,t)
      return info
    route._source_fingerprint=replace_after_pre_hash
    raced=ask(p);route._source_fingerprint=original_fp
    assert raced.status_code==409 and 'sourceBytesSha256' not in raced.get_json(),(raced.status_code,raced.get_json())
    assert str(p.resolve()) in invalidations and str(p.resolve()) not in cache_globals['_psd_cache']
    rows.append({'id':'prehash-parse-replacement-is-conflict-and-invalidates-parser-object','status':'PASS','http':409,'cacheEntryRemains':False,'invalidated':True})
    p.write_bytes(a);set_mtime(p,t)
    retry=ask(p);assert retry.status_code==200,(retry.status_code,retry.get_json())
    body=retry.get_json();assert body['sourceBytesSha256']==digest_a and pixel(body)==[200,10,20],(body.get('sourceBytesSha256'),pixel(body))
    rows.append({'id':'restore-original-bytes-same-mtime-does-not-return-raced-object','status':'PASS','pixel':pixel(body),'digestMatchesA':True,'parseCount':parse_count['n']})

    # F05: cached response hit also has a final fingerprint boundary.
    q=Path(td)/'cache-race.psd'; qa=make_psd(q,(8,9,10),(50,60,70));set_mtime(q,t)
    qa_resp=ask(q);assert qa_resp.status_code==200 and pixel(qa_resp.get_json())==[50,60,70]
    qb=make_psd(Path(td)/'cache-race-b.psd',(18,19,20),(90,100,110));once={'v':False}
    def replace_on_cache_hit(path):
      info=original_fp(path)
      if str(Path(path).resolve())==str(q.resolve()) and not once['v']:
        once['v']=True;q.write_bytes(qb);set_mtime(q,t)
      return info
    route._source_fingerprint=replace_on_cache_hit
    cache_race=ask(q);route._source_fingerprint=original_fp
    assert cache_race.status_code==409 and 'sourceBytesSha256' not in cache_race.get_json(),(cache_race.status_code,cache_race.get_json())
    rows.append({'id':'source-change-during-response-cache-hit','status':'PASS','http':409,'successDigestReturned':False})
    retry_b=ask(q);assert retry_b.status_code==200,(retry_b.status_code,retry_b.get_json())
    body_b=retry_b.get_json();assert body_b['sourceBytesSha256']==sha(q) and pixel(body_b)==[90,100,110]
    rows.append({'id':'stable-retry-after-response-cache-race','status':'PASS','pixel':pixel(body_b),'digestMatchesB':True})

    # Supplement: parser acquisition followed by a downstream tree exception
    # must not leave a raced replacement object tagged with the pre-hash digest.
    e=Path(td)/'postparse-error.psd'; ea=make_psd(e,(3,4,5),(21,31,41));set_mtime(e,t)
    eb=make_psd(Path(td)/'postparse-error-b.psd',(6,7,8),(61,71,81))
    once={'v':False}
    def replace_before_tree(path):
      info=original_fp(path)
      if str(Path(path).resolve())==str(e.resolve()) and not once['v']:
        once['v']=True;e.write_bytes(eb);set_mtime(e,t)
      return info
    route._source_fingerprint=replace_before_tree
    original_builder=route.build_layer_tree
    def failing_builder(psd,width,height):
      route.build_layer_tree=original_builder
      raise RuntimeError('controlled tree failure after parser acquisition')
    route.build_layer_tree=failing_builder
    error_race=ask(e);route._source_fingerprint=original_fp;route.build_layer_tree=original_builder
    assert error_race.status_code==500 and 'sourceBytesSha256' not in error_race.get_json()
    assert str(e.resolve()) not in cache_globals['_psd_cache'],'failed downstream work must evict a digest-tagged parser object'
    e.write_bytes(ea);set_mtime(e,t);error_retry=ask(e);assert error_retry.status_code==200
    assert error_retry.get_json()['sourceBytesSha256']==sha(e) and pixel(error_retry.get_json())==[21,31,41]
    rows.append({'id':'downstream-error-after-raced-parser-evicts-cache','status':'PASS','firstHttp':error_race.status_code,'retryPixel':pixel(error_retry.get_json()),'retryMatchesRestoredA':True})

    # F07/F08: actual legacy loader with no digest keeps the historical mtime-only reuse path.
    legacy=Path(td)/'legacy.psd'; la=make_psd(legacy,(30,40,50),(3,4,5));set_mtime(legacy,t)
    obj_a=get_cached(str(legacy));lb=make_psd(Path(td)/'legacy-b.psd',(60,70,80),(6,7,8));legacy.write_bytes(lb);set_mtime(legacy,t)
    count_before=parse_count['n'];obj_b=get_cached(str(legacy))
    assert obj_b is obj_a and parse_count['n']==count_before,'legacy no-digest callers must retain mtime-only semantics'
    rows.append({'id':'legacy-no-digest-cache-contract-retained','status':'PASS','sameObject':True,'mtimePreserved':True,'parseCount':parse_count['n']})
finally:
  PSDImage.open=real_open
print(json.dumps({'status':'PASS','psdToolsVersion':__import__('psd_tools').__version__,'cases':len(rows),'rows':rows,'actualCandidateHandler':True,'actualCandidateParserCacheLoader':True,'actualFingerprintHelper':True,'actualInvalidationCallback':True,'legacyNoDigestBehaviorRetained':True,'rawBytesTransferred':False,'providerCalls':0,'nativeCalls':0},indent=2))
