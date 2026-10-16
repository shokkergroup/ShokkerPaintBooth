"""Generate the ASTRA owner review from measured evidence and actual picker PNGs."""
from pathlib import Path
import html
import json
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.expansions.astra import MODULES

def main():
    evidence='_archive/root_cleanup_2026-09-05/lane_work/_astra_work'
    source=ROOT/'_astra_work'
    if not source.exists(): source=ROOT/evidence
    evidence=source.relative_to(ROOT).as_posix()
    data=json.loads((source/'native_report.json').read_text())
    scores=json.loads((source/'m7_report.json').read_text())
    cards=[]
    for index,m in enumerate(MODULES):
        row=data[m.FID]; contract=m.IDENTITY_CONTRACT
        marks=' · '.join(mark['name'].replace('_',' ') for mark in contract['mark_types'])
        cards.append(f'''<article data-id="{m.FID}">
<div class="number">{index+1:02} / ASTRA</div><h2>{html.escape(m.NAME)}</h2>
<p>{html.escape(m.DESCRIPTION)}</p>
<div class="canvas"><img loading="lazy" src="{evidence}/{m.FID}/paint.png" alt="Native {html.escape(m.NAME)} paint texture"></div>
<div class="caption"><span>Native texture · drag to inspect at 1:1</span><a href="{evidence}/{m.FID}/paint.png" target="_blank">Paint PNG ↗</a><a href="{evidence}/{m.FID}/spec.png" target="_blank">Spec PNG ↗</a></div>
<div class="metrics"><b>{scores[m.FID]['composite']:.1f} M7</b><span>{max(row['seconds']):.2f}s native pair</span><span>{row['law']['follow_edge']:.2f} detail alignment</span></div>
<details><summary>Construction &amp; material</summary><p>{html.escape(contract['carrier_grammar'])}</p><p>{html.escape(contract['spec_grammar'])}</p><p class="marks">{html.escape(marks)}</p>
<img class="picker" loading="lazy" src="thumbnails/picker_split/base/{m.FID}.png?v=astra-final-20260905" alt="Actual app picker paint and packed spec"></details></article>''')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASTRA — Ten material worlds</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b0e15;color:#efeee8;font:16px/1.5 system-ui,sans-serif}main{max-width:1560px;margin:auto;padding:48px 32px 80px}header{max-width:960px}.eyebrow{font-size:12px;letter-spacing:.3em;color:#b3a1e7}h1{font-size:clamp(64px,10vw,140px);font-weight:350;line-height:1;margin:14px 0 20px;letter-spacing:.07em}header p{color:#c4c3cd;font-size:20px;max-width:760px}a{color:#c9b5ff}nav{position:sticky;top:0;z-index:2;display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 0;background:#0b0e15f5;border-bottom:1px solid #30343f}button{font:inherit;color:#d0ccda;border:1px solid #424450;border-radius:100px;background:#171a23;padding:9px 18px;cursor:pointer}button[aria-pressed=true]{background:#e8ddff;color:#221a32;border-color:#e8ddff}#grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px;margin-top:32px}article{border:1px solid #333744;background:#131721;padding:24px;min-width:0}.number{color:#a493ce;font-size:11px;letter-spacing:.2em}h2{font-size:29px;letter-spacing:-.025em;margin:7px 0}article>p{min-height:48px;color:#b9bbc5;font-size:15px}.canvas{height:360px;overflow:auto;background:#080a10;cursor:grab}.canvas img{display:block;width:2048px;height:2048px;max-width:none}body.fit .canvas img{width:100%;height:auto}body.fit .canvas{height:auto;aspect-ratio:1.45}.caption{display:flex;gap:15px;flex-wrap:wrap;font-size:12px;margin-top:12px;color:#979dac}.caption span{margin-right:auto}.metrics{display:flex;gap:20px;flex-wrap:wrap;font-size:13px;padding-top:16px}.metrics b{color:#d0bee9}details{font-size:14px;margin-top:16px;border-top:1px solid #303440;padding-top:14px}summary{cursor:pointer}.marks{color:#ada5bc}.picker{width:100%;height:auto}.note{font-size:13px;color:#959aaa;max-width:930px}footer{margin-top:40px;padding-top:20px;border-top:1px solid #303440;color:#b3b5c2}@media(max-width:800px){main{padding:28px 16px}#grid{grid-template-columns:1fr}article{padding:18px}.canvas{height:310px}}
</style><main><header><div class="eyebrow">SHOKKER PAINT BOOTH / MATERIAL COLLECTION 01</div><h1>ASTRA</h1>
<p>Ten constructions. Tiny details. A different material story inside every feature.</p>
<p class="note">These are real 2048 paint textures and literal packed spec maps. Red = metallic, green = roughness, blue = clearcoat control. Blue 16 is strongest active coat; 255 suppresses it. This page does not simulate iRacing lighting.</p></header>
<nav aria-label="Texture view"><button data-mode="paint" aria-pressed="true">Paint</button><button data-mode="spec" aria-pressed="false">Packed spec</button><button id="scale" aria-pressed="false">Fit whole texture</button><span class="note">Default view: 1:1 pixels</span></nav><section id="grid">'''+''.join(cards)+'''</section>
<footer>Built for the ASTRA category in the live development app. M7 uses the existing fine-structural-color intent; separate gates check native scale, feature alignment and transformed structural similarity. Owner eye and same-location iRacing sun / shade / night comparisons remain the final appearance test.<p><a href="paint-booth-v2.html">Open Paint Booth ↗</a></p></footer></main>
<script>
let mode='paint';const root='''+json.dumps(evidence)+''';
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelectorAll('article').forEach(a=>{const i=a.querySelector('.canvas img');i.src=root+'/'+a.dataset.id+'/'+mode+'.png';i.alt=a.querySelector('h2').textContent+' '+mode;});}));
document.querySelector('#scale').addEventListener('click',function(){let fit=document.body.classList.toggle('fit');this.setAttribute('aria-pressed',String(fit));this.textContent=fit?'Return to 1:1':'Fit whole texture';});
document.querySelectorAll('.canvas').forEach(c=>{c.scrollLeft=740;c.scrollTop=812;let drag=null;c.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,c.scrollLeft,c.scrollTop];c.setPointerCapture(e.pointerId);e.preventDefault();});c.addEventListener('pointermove',e=>{if(drag){c.scrollLeft=drag[2]+drag[0]-e.clientX;c.scrollTop=drag[3]+drag[1]-e.clientY;}});c.addEventListener('pointerup',()=>drag=null);});
</script></html>'''
    (ROOT/'SPB_AUDIT_astra.html').write_text(page,encoding='utf-8')
    print('ASTRA review generated: 10 cards, native paint/spec and real picker links')

if __name__=='__main__': main()
