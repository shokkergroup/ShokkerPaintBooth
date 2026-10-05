"""Bake canonical standard/picker overlays and native material evidence."""
from pathlib import Path
import sys,json,time,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np,cv2
from PIL import Image,ImageDraw
from engine.spec_overlay_v2.catalog import definitions
from engine.spec_overlay_v2.preview import render_native,detail_crop,material_study
from engine.spec_patterns import PATTERN_CATALOG

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--family');parser.add_argument('--stale',action='store_true');args=parser.parse_args()
    out=ROOT/'_spec_overlays_v2_work'/'bake';out.mkdir(parents=True,exist_ok=True)
    thumb=ROOT/'thumbnails';rows=[];items=definitions()['items']
    prior={r['id']:r for r in json.loads((out/'stats.json').read_text())} if args.family or args.stale else {}
    sheet=Image.new('RGB',(960,((len(items)+3)//4)*280),(15,19,25));draw=ImageDraw.Draw(sheet)
    for index,item in enumerate(items):
        unchanged=args.stale and prior.get(item['id'],{}).get('renderer_fingerprint')==PATTERN_CATALOG[item['id']]._spb_source_fingerprint
        if unchanged or (args.family and item['family'] not in args.family.split(',')):
            rows.append(prior[item['id']])
            crop=cv2.imread(str(out/(item['id']+'.png')))[:,:,::-1][768:1280,768:1280]
            x=(index%4)*240;y=(index//4)*280
            sheet.paste(Image.fromarray(cv2.resize(crop,(224,224),interpolation=cv2.INTER_AREA)),(x+8,y+6))
            draw.text((x+8,y+234),item['name'],fill='white');draw.text((x+8,y+251),'M/R/Cc | native 512px detail',fill=(165,180,193))
            continue
        pid=item['id'];start=time.perf_counter();field,spec=render_native(pid);elapsed=time.perf_counter()-start
        Image.fromarray(spec).save(out/(pid+'.png'))
        crop=detail_crop(spec);picker=cv2.resize(crop,(160,160),interpolation=cv2.INTER_AREA)
        Image.fromarray(picker).save(out/(pid+'_picker.png'))
        for folder,array in [('spec_patterns_combined',picker),('spec_patterns_visual',cv2.resize(material_study(crop),(160,160),interpolation=cv2.INTER_AREA))]:
            target=thumb/folder;target.mkdir(exist_ok=True,parents=True);Image.fromarray(array).save(target/(pid+'_160.png'))
        x=(index%4)*240;y=(index//4)*280
        sheet.paste(Image.fromarray(cv2.resize(crop,(224,224),interpolation=cv2.INTER_AREA)),(x+8,y+6))
        draw.text((x+8,y+234),item['name'],fill='white');draw.text((x+8,y+251),'M/R/Cc | native 512px detail',fill=(165,180,193))
        row={'id':pid,'seconds':round(elapsed,3),'std':[round(float(spec[:,:,i].std()),2) for i in range(3)],'range':[[int(spec[:,:,i].min()),int(spec[:,:,i].max())] for i in range(3)],'unique_spec':int(len(np.unique(crop.reshape(-1,3),axis=0))),'coverage':round(float(field[:,:,3].mean()),3)}
        row['renderer_fingerprint']=PATTERN_CATALOG[pid]._spb_source_fingerprint
        row['standard_sha256']=hashlib.sha256((out/(pid+'.png')).read_bytes()).hexdigest()
        row['picker_sha256']=hashlib.sha256((thumb/'spec_patterns_combined'/(pid+'_160.png')).read_bytes()).hexdigest()
        rows.append(row);print(pid,round(elapsed,3),'s; M/R/Cc std',row['std'],flush=True)
        (out/'stats.progress.json').write_text(json.dumps(rows,indent=2))
    sheet.save(out/'contact.png');(out/'stats.json').write_text(json.dumps(rows,indent=2))
    for family in definitions()['families']:
        selected=[p for p in items if p['family']==family['id']]
        for mode in ('combined','gray'):
            contact=Image.new('RGB',(960,((len(selected)+3)//4)*280),(15,19,25));pen=ImageDraw.Draw(contact)
            for j,p in enumerate(selected):
                a=cv2.imread(str(out/(p['id']+'.png')))[:,:,::-1][768:1280,768:1280]
                if mode=='gray':a=np.repeat(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)[:,:,None],3,axis=2)
                x=j%4*240;y=j//4*280;contact.paste(Image.fromarray(cv2.resize(a,(224,224),interpolation=cv2.INTER_AREA)),(x+8,y+6))
                pen.text((x+8,y+234),p['name'],fill='white');pen.text((x+8,y+251),'Native 512px detail',fill=(165,180,193))
            contact.save(out/(family['id']+'_'+mode+'.png'))
if __name__=='__main__':main()
