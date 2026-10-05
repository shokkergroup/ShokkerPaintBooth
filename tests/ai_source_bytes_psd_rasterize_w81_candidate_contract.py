from __future__ import annotations
import ast,base64,hashlib,importlib.util,io,json,os,sys,tempfile
from pathlib import Path
from flask import Flask
from PIL import Image
from psd_tools import PSDImage
ROOT=Path.cwd(); C=ROOT/'_easy_claude_work/ai14h_w78_candidate'; F=C/'frozen'; sys.path.insert(0,str(ROOT/'electron-app/server'))
def fn(src,name,env):
 t=ast.parse(src.read_text(encoding='utf-8'));n=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),str(src),'exec'),env);return env[name]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make(p,paint):
 im=PSDImage.new('RGB',(8,8),(0,0,0));im.append(im.create_pixel_layer(Image.new('RGBA',(8,8),(*paint,255)),name='Paint'));h=im.create_pixel_layer(Image.new('RGBA',(8,8),(1,2,3,255)),name='Hidden');h.visible=False;im.append(h);im.save(p);return p.read_bytes()
def settime(p,t):os.utime(p,ns=(t,t))
proj=ast.parse((F/'project_routes.py').read_text(encoding='utf-8'));node=next(x for x in proj.body if isinstance(x,ast.FunctionDef) and x.name=='_source_fingerprint');eg={'os':os,'hashlib':hashlib};exec(compile(ast.Module(body=[node],type_ignores=[]),str(F/'project_routes.py'),'exec'),eg)
spec=importlib.util.spec_from_file_location('w81_route',C/'server_routes/psd_import_routes.py');route=importlib.util.module_from_spec(spec);spec.loader.exec_module(route);route._source_fingerprint=eg['_source_fingerprint']
cache={'os':os,'_psd_cache':{}}; getter=fn(C/'server.py','_get_cached_psd',cache); invalidate=fn(C/'server.py','_invalidate_cached_psd',cache)
app=Flask('w81-raster');
class Log:
 def info(self,*a,**k):pass
 def warning(self,*a,**k):pass
 def error(self,*a,**k):pass
route.register_psd_import_routes(app,require_internal_request=lambda:(True,None),sanitize_path=lambda p:(str(Path(p).resolve()),None),get_cached_psd=getter,logger=Log(),invalidate_cached_psd=invalidate)
client=app.test_client()
def req(path,sha=None):
 d={'psd_path':str(path)}
 if sha is not None:d['sourceBytesSha256']=sha
 return client.post('/api/psd-rasterize-all',json=d,headers={'X-Shokker-Internal':'1'})
def image_pixel(uri):return list(Image.open(io.BytesIO(base64.b64decode(uri.split(',',1)[1]))).convert('RGB').getpixel((3,3)))
rows=[]
with tempfile.TemporaryDirectory(prefix='spb-w81-') as td:
 t=1700000000000000000;p=Path(td)/'x.psd';a=make(p,(20,30,40));settime(p,t);ha=digest(p)
 ok=req(p,ha);assert ok.status_code==200 and ok.get_json()['sourceBytesSha256']==ha and ok.get_json()['count']==2,(ok.status_code,ok.get_json())
 rows.append({'id':'matching-import-digest-raster-receipt','status':'PASS','sha256':ok.get_json()['sourceBytesSha256'],'layerCount':ok.get_json()['count']})
 bad=req(p,'A'*64);assert bad.status_code==400
 mismatch=req(p,'0'*64);assert mismatch.status_code==409 and 'layers' not in mismatch.get_json()
 rows.append({'id':'malformed-and-stale-expected-digest','status':'PASS','malformedHttp':bad.status_code,'mismatchHttp':mismatch.status_code})
 b=make(Path(td)/'b.psd',(50,60,70));once={'x':False};real=route._source_fingerprint
 def swap_after_pre(path):
  v=real(path)
  if Path(path).resolve()==p.resolve() and not once['x']:
   once['x']=True;p.write_bytes(b);settime(p,t)
  return v
 route._source_fingerprint=swap_after_pre;race=req(p,ha);route._source_fingerprint=real
 assert race.status_code==409 and 'layers' not in race.get_json() and str(p.resolve()) not in cache['_psd_cache']
 rows.append({'id':'replacement-between-hash-and-parse','status':'PASS','http':race.status_code,'cacheEvicted':True})
 p.write_bytes(a);settime(p,t);restored=req(p,ha);assert restored.status_code==200 and restored.get_json()['sourceBytesSha256']==ha
 paint_key=next(k for k,v in restored.get_json()['layers'].items() if v.get('name')=='Paint');assert image_pixel(restored.get_json()['layers'][paint_key]['image'])==[20,30,40]
 rows.append({'id':'restored-source-parsed-as-requested-bytes','status':'PASS','paintPixel':image_pixel(restored.get_json()['layers'][paint_key]['image'])})
 # Swap source only after the real raster iteration, before the route returns.
 c=Path(td)/'c.psd';cb=make(c,(80,90,100));settime(c,t);hc=digest(c);d=make(Path(td)/'d.psd',(110,120,130));real_iter=route.iter_leaf_layers;once={'x':False}
 def mutate_after_raster(psd):
  yield from real_iter(psd)
  if not once['x']:
   once['x']=True;c.write_bytes(d);settime(c,t)
 route.iter_leaf_layers=mutate_after_raster;r2=req(c,hc);route.iter_leaf_layers=real_iter
 assert r2.status_code==409 and 'layers' not in r2.get_json() and str(c.resolve()) not in cache['_psd_cache']
 rows.append({'id':'replacement-after-layer-rasterization','status':'PASS','http':r2.status_code,'cacheEvicted':True})
 c.write_bytes(cb);settime(c,t);good=req(c,hc);assert good.status_code==200 and good.get_json()['sourceBytesSha256']==hc
 rows.append({'id':'stable-retry-after-raster-race','status':'PASS','sha256Matches':True,'count':good.get_json()['count']})
 # Legacy route callers retain success and response shape when the digest field is absent.
 legacy=Path(td)/'legacy.psd';make(legacy,(7,8,9));settime(legacy,t);lr=req(legacy)
 assert lr.status_code==200 and lr.get_json()['success'] is True and 'sourceBytesSha256' not in lr.get_json()
 rows.append({'id':'legacy-raster-caller-compatible','status':'PASS','digestFieldAbsent':True})
print(json.dumps({'status':'PASS_WITH_LIMITS','cases':len(rows),'rows':rows,'candidateRasterRoute':True,'realPsdTools':__import__('psd_tools').__version__,'rawSourceBytesReturned':False,'providerCalls':0,'nativeCalls':0},indent=2))
