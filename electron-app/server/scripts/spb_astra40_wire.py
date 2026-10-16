"""Bounded ASTRA additions; preserve all unrelated catalog and score records."""
from pathlib import Path
import json,re,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.astra import MODULES as ORIGINALS
from engine.expansions.astra.wave2 import MODULES
OUT=ROOT/'_astra40_work'
def write(path,text):
    stage=OUT/(path.name+'.next');stage.write_text(text,encoding='utf-8',newline='');os.replace(stage,path)
def main():
    p=ROOT/'paint-booth-0-finish-data.js';text=p.read_text(encoding='utf-8')
    a='    // ASTRA expansion forty / SPB-105 / 2026-09-05.\n';b='    // END ASTRA expansion forty.\n'
    if a in text:text=text[:text.index(a)]+text[text.index(b)+len(b):]
    rows=[]
    for m in MODULES:
        rows.append('    '+json.dumps(dict(id=m.FID,name=m.NAME,desc='ASTRA '+m.LANE+' / '+m.DESCRIPTION,swatch=m.SWATCH,astraLane=m.LANE),separators=(',',':'))+',\n')
    anchor='    // ASTRA / owner commissioned 2026-09-05. Ten independently authored carriers.'
    assert text.count(anchor)==1
    text=text.replace(anchor,a+''.join(rows)+b+anchor)
    text,n=re.subn(r'"ASTRA": \[[^\]]+\]', '"ASTRA": '+json.dumps([m.FID for m in ORIGINALS+MODULES]),text,count=1)
    assert n==1;write(p,text)
    p=ROOT/'paint-booth-v2.html';text=p.read_text(encoding='utf-8')
    for script in ('paint-booth-0-finish-data.js','paint-booth-0-catalog-scorecard.js'):
        text,n=re.subn(re.escape(script)+r'\?v=[^"\s]+',script+'?v=spb-astra40-20260905w8',text);assert n==1
    write(p,text)
    print('ASTRA: 50 catalog IDs, four expansion lanes, original rows preserved')
if __name__=='__main__':main()
