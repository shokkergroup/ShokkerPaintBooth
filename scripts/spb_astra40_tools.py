"""Adapt the established ASTRA proof workflow without changing its formulas."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    for stem in ('workbook','pipeline_proof','export_check','sync'):
        src=(ROOT/'scripts'/('spb_astra_'+stem+'.py')).read_text(encoding='utf-8')
        src=src.replace('from engine.expansions.astra import MODULES','from engine.expansions.astra.wave2 import MODULES')
        src=src.replace('_astra_work','_astra40_work')
        src=src.replace('len(rows)==10','len(rows)==40').replace('Need all ten real exports','Need all forty real exports').replace('10/10 actual','40/40 actual')
        if stem=='workbook':
            start=src.index('    original=json.loads(');end=src.index('    # The generated file',start)
            src=src[:start]+"    body=json.dumps(rows,ensure_ascii=False)\n"+src[end:]
        if stem=='sync':
            src=src.replace(".glob('*.py')",".rglob('*.py')")
        (ROOT/'scripts'/('spb_astra40_'+stem+'.py')).write_text(src,encoding='utf-8')
    print('Focused ASTRA40 proof scripts created; official quality formulas unchanged')
if __name__=='__main__':main()
