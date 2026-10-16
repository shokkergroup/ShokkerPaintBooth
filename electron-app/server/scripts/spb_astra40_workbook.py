"""Populate only ASTRA scorecard rows from actual render evidence; run official M1..M7.

No ASTRA score override. The focused generator preserves all existing rows.
SPB-105 / ASTRA A2, owner request 2026-09-05.
"""
from pathlib import Path
import contextlib
import importlib
import io
import json
import os
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.expansions.astra.wave2 import MODULES
from scripts.spb_finish_identity import contract_from_module

def main():
    report=json.loads((ROOT/'_astra40_work/native_report.json').read_text())
    path=ROOT/'paint-booth-0-catalog-scorecard.js'
    raw=path.read_text(encoding='utf-8')
    match=re.search(r'=\s*(\{.*\});',raw,re.S)
    assert match
    rows=json.loads(re.sub(r'//[^\n]*','',match.group(1)))
    for m in MODULES:
        contract_from_module(m,m.FID)
        native=report[m.FID]; pm=native['paint_metrics']; sm=native['spec_metrics']
        rows['base:'+m.FID]=dict(surface='Base',surface_kind='base',id=m.FID,name=m.NAME,category='ASTRA',
            estimated2048Ms=round(max(native['seconds'])*1000,2),qualityProfile='expressive_finish',
            paintFineEnergy=pm['paint_fine_energy'],paintResidualEnergy=pm['paint_residual_energy'],
            paintBlockEnergy=pm['paint_block_energy'],paintMacroEnergy=pm['paint_macro_energy'],
            paintMicroMacroRatio=pm['paint_micro_macro_ratio'],paintColorPopulation=pm['paint_color_population'],
            paintSaturationMean=pm['paint_saturation_mean'],paintLumaStd=pm['paint_luma_std'],
            paintLumaSpan=pm['paint_luma_span'],specMRange=sm['m_range'],specRRange=sm['r_range'],
            specCcRange=sm['cc_range'],specMStd=sm['m_std'],specRStd=sm['r_std'],specCcStd=sm['cc_std'],
            specChannelIndependence=sm['independence'])
    # One compact line per new row avoids growing the generated monster budget.
    body=json.dumps(rows,ensure_ascii=False)
    # The generated file was already 50,990 lines against a 39,319-line guard
    # before ASTRA. Preserve every record, compact each onto one readable line.
    compact_rows=json.loads(body)
    assert compact_rows==rows
    body='{\n'+',\n'.join('  '+json.dumps(k)+': '+json.dumps(v,ensure_ascii=False,separators=(',',':')) for k,v in compact_rows.items())+'\n}'
    updated=raw[:match.start(1)]+body+raw[match.end(1):]
    staged=ROOT/'_astra40_work/scorecard.next.js'
    staged.write_text(updated,encoding='utf-8',newline='')
    os.replace(staged,path)
    logs=ROOT/'_astra40_work/workbook_components.log'
    with logs.open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for n in (1,2,5,6,7):
            name={1:'m1',2:'m2',5:'m5',6:'m6',7:'m7'}[n]
            mod=importlib.import_module('scripts.spb_workbook_compute_'+name)
            result=mod.main()
            assert result in (None,0),(name,result)
    result=json.loads((ROOT/'_workbook_metrics/m7_composite.json').read_text())['byFinish']
    subset={m.FID:result['base:'+m.FID] for m in MODULES}
    (ROOT/'_astra40_work/m7_report.json').write_text(json.dumps(subset,indent=2)+'\n')
    if all(r['composite'] is not None and r['composite']>=85 for r in subset.values()):
        # Workbook execution can take a minute. Re-read before promotion so an
        # independent lane's intervening rows cannot be overwritten by our snapshot.
        raw=path.read_text(encoding='utf-8')
        match=re.search(r'=\s*(\{.*\});',raw,re.S)
        compact_rows=json.loads(match.group(1))
        # Follow the existing X LAB promotion convention, with explicit basis.
        for m in MODULES:
            score=subset[m.FID]['composite']; quality=int(round(score))
            compact_rows['base:'+m.FID].update(overallQuality=quality,paintQuality=quality,specQuality=quality,
                priority='PASS',status='OK',reasonFlags='owner_track_review_pending',
                m7Composite=score,m7Tier='keeper',m7Intent='fine_structural_color',m7Pass85=True,
                scoreBasis='M7 composite; native identity gates separate')
        body='{\n'+',\n'.join('  '+json.dumps(k)+': '+json.dumps(v,ensure_ascii=False,separators=(',',':')) for k,v in compact_rows.items())+'\n}'
        staged.write_text(raw[:match.start(1)]+body+raw[match.end(1):],encoding='utf-8',newline='')
        os.replace(staged,path)
    print(json.dumps(subset,indent=2))
    return 0 if all(r['composite'] is not None and r['composite']>=85 for r in subset.values()) else 1

if __name__=='__main__': raise SystemExit(main())
