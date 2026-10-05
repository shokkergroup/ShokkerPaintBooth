"""Verify every actual served picker asset against the canonical bake."""
from pathlib import Path
import sys,json,hashlib,urllib.request,argparse
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.spec_overlay_v2.catalog import definitions
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=59877);args=parser.parse_args()
    tasks=[(p['id'],kind,folder) for p in definitions()['items'] for kind,folder in [('spec-pattern-combined','spec_patterns_combined'),('spec-pattern-visual-preview','spec_patterns_visual')]]
    def fetch(task):
        pid,kind,folder=task;url=f'http://127.0.0.1:{args.port}/api/{kind}/{pid}'
        expected=hashlib.sha256((ROOT/'thumbnails'/folder/(pid+'_160.png')).read_bytes()).hexdigest()
        try:
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
            actual=hashlib.sha256(data).hexdigest();return {'id':pid,'kind':kind,'match':actual==expected,'expected':expected,'served':actual}
        except Exception as error:return {'id':pid,'kind':kind,'match':False,'error':str(error)}
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,tasks))
    (ROOT/f'_spec_overlays_v2_work/bake/live-assets-{args.port}.json').write_text(json.dumps(rows,indent=2))
    failed=[r for r in rows if not r['match']];print(json.dumps({'port':args.port,'checked':len(rows),'matched':len(rows)-len(failed),'failed':failed[:5]},indent=2));sys.exit(bool(failed))
if __name__=='__main__':main()
