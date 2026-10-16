"""Measure ASTRA R1 with unchanged legacy formulas, isolated from global ranks.
Publish only ASTRA facts and clearly diagnostic scores after the calculation.
Owner authorization supersedes a legacy full-channel-spread ship threshold.
"""
from pathlib import Path
import contextlib,importlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from scripts.spb_wilds_m7_evidence import _paint_metrics,_spec_metrics
OUT=ROOT/'_astra_rebuild_20260922_work';MET=OUT/'metrics'


def replace_entries(path, entries):
    raw=path.read_text(encoding='utf-8');decoder=json.JSONDecoder();edits=[]
    for key,value in entries.items():
        match=re.search(r'"'+re.escape(key)+r'"\s*:\s*',raw)
        assert match,key
        old,end=decoder.raw_decode(raw[match.end():])
        edits.append((match.end(),match.end()+end,json.dumps(value,ensure_ascii=False,separators=(',',':'))))
    for start,end,value in sorted(edits,reverse=True):raw=raw[:start]+value+raw[end:]
    path.write_text(raw,encoding='utf-8',newline='')


def main():
    MET.mkdir(exist_ok=True)
    source=ROOT/'paint-booth-0-catalog-scorecard.js';raw=source.read_text(encoding='utf-8')
    data=json.loads(re.search(r'=\s*(\{.*\});',raw,re.S).group(1))
    inventory=json.loads((OUT/'inventory.json').read_text())
    native=json.loads((OUT/'native_report.json').read_text());changed={};before={}
    saved_before=OUT/'before_scorecard_rows.json'
    original=json.loads(saved_before.read_text()) if saved_before.exists() else {}
    for row in inventory:
        fid=row['FID'];key='base:'+fid;before[key]=original.get(key,data[key].copy())
        p=np.asarray(Image.open(OUT/fid/'paint.png'));s=np.asarray(Image.open(OUT/fid/'spec.png'))
        pm,sm=_paint_metrics(p),_spec_metrics(s);entry=data[key].copy()
        entry.update(estimated2048Ms=native[fid]['seconds']*1000,
            paintFineEnergy=pm['paint_fine_energy'],paintResidualEnergy=pm['paint_residual_energy'],
            paintBlockEnergy=pm['paint_block_energy'],paintMacroEnergy=pm['paint_macro_energy'],
            paintMicroMacroRatio=pm['paint_micro_macro_ratio'],paintColorPopulation=pm['paint_color_population'],
            paintSaturationMean=pm['paint_saturation_mean'],paintLumaStd=pm['paint_luma_std'],paintLumaSpan=pm['paint_luma_span'],
            specMRange=sm['m_range'],specRRange=sm['r_range'],specCcRange=sm['cc_range'],
            specMStd=sm['m_std'],specRStd=sm['r_std'],specCcStd=sm['cc_std'],specChannelIndependence=sm['independence'])
        data[key]=entry;changed[key]=entry
    (OUT/'before_scorecard_rows.json').write_text(json.dumps(before,indent=2))
    isolated=OUT/'diagnostic_scorecard.js';isolated.write_text('window.FINISH_SCORECARD = '+json.dumps(data)+';')
    with (OUT/'workbook.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for name in ['m1','m2','m5','m6','m7']:
            mod=importlib.import_module('scripts.spb_workbook_compute_'+name)
            mod.SCORECARD=isolated;mod.OUT_DIR=MET
            if name=='m7':
                for key,filename in [('M1','m1_sibling_diff.json'),('M2','m2_intent_fit.json'),('M5','m5_spec_paint_coherence.json'),('M6','m6_intent_floor_ceiling.json')]:setattr(mod,key,MET/filename)
            result=mod.main();assert result in [None,0],(name,result)
    scores=json.loads((MET/'m7_composite.json').read_text())['byFinish']
    report={}
    for key,entry in changed.items():
        r=scores[key];value=r['composite']
        entry.update(overallQuality=round(value) if value is not None else None,
            paintQuality=round(value) if value is not None else None,specQuality=round(value) if value is not None else None,
            m7Composite=value,m7Tier=r.get('tier','diagnostic'),m7Pass85=value is not None and value>=85,
            priority='REVIEW',status='REVIEW',reasonFlags='astra_r1_owner_review_pending',
            scoreBasis='Legacy M7 diagnostic only; ASTRA R1 explicitly authorized for live iteration 2026-09-22',
            revision='ASTRA-R1-20260922')
        report[key]=dict(before=before[key].get('m7Composite'),after=value,diagnostic=r)
    (OUT/'m7_report.json').write_text(json.dumps(report,indent=2))
    replace_entries(source,changed)
    replace_entries(ROOT/'electron-app/server/paint-booth-0-catalog-scorecard.js',changed)
    values=[r['after'] for r in report.values() if r['after'] is not None]
    print('50 ASTRA rows refreshed; unchanged legacy diagnostic M7 range',min(values),max(values))


if __name__=='__main__':main()
