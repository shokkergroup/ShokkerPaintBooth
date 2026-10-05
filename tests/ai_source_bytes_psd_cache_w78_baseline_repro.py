from __future__ import annotations
from pathlib import Path
import base64,contextlib,hashlib,io,json,os,runpy,tempfile
from PIL import Image
# Replay the pre-W78 frozen W71 route/cache implementation through the W73 real-PSD harness.
with contextlib.redirect_stdout(io.StringIO()):
    h=runpy.run_path(str(Path('tests/ai_source_bytes_psd_import_w73_real_psd_contract.py').resolve()))
with tempfile.TemporaryDirectory(prefix='spb-w78-baseline-') as td:
    p=Path(td)/'source.psd';fixed=1700000000000000000
    a=h['make_psd'](p,(10,20,30),visible_rgb=(200,10,20));os.utime(p,ns=(fixed,fixed))
    b=h['make_psd'](Path(td)/'replacement.psd',(100,120,130),visible_rgb=(15,180,90))
    original=h['route']._source_fingerprint;once={'done':False}
    def swap_after_pre_hash(path):
        value=original(path)
        if Path(path).resolve()==p.resolve() and not once['done']:
            once['done']=True;p.write_bytes(b);os.utime(p,ns=(fixed,fixed))
        return value
    h['route']._source_fingerprint=swap_after_pre_hash
    raced=h['ask'](p);h['route']._source_fingerprint=original
    p.write_bytes(a);os.utime(p,ns=(fixed,fixed));retry=h['ask'](p);body=retry.get_json()
    pixel=list(Image.open(io.BytesIO(base64.b64decode(body['composite'].split(',',1)[1]))).convert('RGB').getpixel((3,3)))
    result={'baselineRoute':str(h['ROUTE_PATH']).replace('\\','/'),'firstStatus':raced.status_code,'retryStatus':retry.status_code,'retryDigestMatchesA':body.get('sourceBytesSha256')==hashlib.sha256(a).hexdigest(),'retryPixel':pixel,'expectedA':[200,10,20],'poisonReproduced':pixel==[15,180,90],'productionWrites':0}
    print(json.dumps(result,indent=2))
    assert result['poisonReproduced']
