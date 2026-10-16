"""Native fifty-finish ASTRA review, four new lanes and protected originals."""
from pathlib import Path
import json,html,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.astra import MODULES as ORIGINALS
from engine.expansions.astra.wave2 import MODULES
def main():
    new=ROOT/'_astra40_work'
    if not new.exists():new=ROOT/'_archive/root_cleanup_2026-09-05/lane_work/_astra40_work'
    old=ROOT/'_archive/root_cleanup_2026-09-05/lane_work/_astra_work'
    rows=[]
    for modules,source,lane in ((MODULES,new,None),(ORIGINALS,old,'ORIGINAL TEN')):
        data=json.loads((source/'native_report.json').read_text())
        scores=json.loads((source/'m7_report.json').read_text())
        export_path=source/'full_pipeline/report.json'
        exported=json.loads(export_path.read_text()) if export_path.exists() else {}
        for m in modules:
            row=data[m.FID];c=m.IDENTITY_CONTRACT
            rows.append(dict(id=m.FID,name=m.NAME,lane=lane or m.LANE,desc=m.DESCRIPTION,
                source=source.relative_to(ROOT).as_posix()+'/'+m.FID,score=scores[m.FID]['composite'],
                seconds=max(row['seconds']),colors=exported.get(m.FID,{}).get('distinct_rgb',row.get('distinct_rgb')),grammar=c['carrier_grammar'],
                spec=c['spec_grammar'],marks=[x['name'].replace('_',' ') for x in c['mark_types']]))
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASTRA / Fifty distinct material studies</title><style>
*{box-sizing:border-box}body{margin:0;background:#090d14;color:#edeef2;font:15px/1.55 system-ui,sans-serif}main{max-width:1660px;margin:auto;padding:36px 32px 80px}.kicker{color:#bba5f0;letter-spacing:.24em;font-size:11px}h1{font-size:clamp(70px,10vw,140px);font-weight:330;letter-spacing:.075em;line-height:1.1;margin:10px 0}header{display:flex;justify-content:space-between;align-items:end;gap:30px;margin-bottom:30px}header p{max-width:620px;font-size:19px;color:#bbc4d4}a{color:#cbb6ff}.note{font-size:13px;color:#93a0b8}nav{position:sticky;top:0;z-index:4;padding:12px 0;background:#090d14f5;border-bottom:1px solid #303845}.lanes,.views{display:flex;gap:8px;flex-wrap:wrap}.views{margin-top:12px;align-items:center}button,input{font:inherit;background:#151c29;border:1px solid #38465d;color:#d4dceb;border-radius:7px;padding:9px 14px}button{cursor:pointer}button[aria-pressed=true]{background:#e9ddff;color:#211835;border-color:#e9ddff}input{min-width:190px;margin-left:auto}#intro{padding:19px 0 8px;color:#abb8cb;max-width:970px}#grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px}article{min-width:0;border:1px solid #29384a;background:#101722;padding:20px}.number{font-size:10px;color:#b89fe0;letter-spacing:.2em}h2{font-size:28px;line-height:1.2;font-weight:530;margin:9px 0 12px}article>p{color:#aebbcf;min-height:46px;margin:0 0 14px}.frame{height:340px;overflow:auto;background:#070b10;cursor:grab;position:relative}.frame img{display:block;max-width:none;width:2048px;height:2048px;user-select:none}.fit .frame{height:auto;aspect-ratio:1.5}.fit .frame img{width:100%;height:auto}.meta{display:flex;flex-wrap:wrap;gap:16px;margin-top:15px;font-size:12px;color:#b4bfd1}.meta b{color:#d7c1fa}.links{display:flex;gap:16px;margin-top:11px;font-size:12px}.colors{color:#a1ded4;font-size:12px;margin-top:8px}details{border-top:1px solid #2d3647;margin-top:16px;padding-top:12px;font-size:13px;color:#a9b8cd}summary{cursor:pointer;color:#d0d9e9}.picker{width:100%;max-width:480px;margin-top:10px}footer{border-top:1px solid #303845;margin-top:35px;padding-top:20px;color:#8b9bb2;font-size:13px}.proxy{color:#f0c692}#counter{font-size:12px;margin-left:10px;color:#b8c1cf}@media(max-width:850px){main{padding:24px 16px}header{display:block}#grid{grid-template-columns:1fr}.frame{height:320px}input{margin-left:0}}
</style><main><header><div><div class="kicker">SHOKKER PAINT BOOTH / MATERIAL COLLECTION</div><h1>ASTRA</h1></div><p>Forty new constructions.<br>Four new directions.<br><span class="note">Your original ten remain unchanged. All fifty live in ASTRA.</span></p></header>
<nav aria-label="ASTRA collection controls"><div class="lanes" id="lanes"></div><div class="views"><button data-view="paint" aria-pressed="true">Paint</button><button data-view="spec" aria-pressed="false">Packed spec</button><button id="fit" aria-pressed="false">Fit whole texture</button><span id="counter" aria-live="polite"></span><input type="search" id="search" placeholder="Find a finish" aria-label="Find a finish"></div></nav><p id="intro"></p><section id="grid"></section>
<footer>These are the actual native 2048 paint and packed spec textures. Spec: red = metallic, green = roughness, blue = clearcoat control (16 strongest active coat; 255 no shine). This viewer does not simulate iRacing lighting. M7, native identity, export parity and owner track review are separate checks.<p><a href="paint-booth-v2.html">Open Paint Booth ↗</a> · <a href="docs/ASTRA_EXPANSION_2026-09-05.md">Build plan &amp; measured evidence ↗</a></p></footer></main>
<script>const data=__DATA__;
const lanes=['COLOR SHOXX','SURFS UP','MAD SCIENTIST','FUTURE SHOXX','ORIGINAL TEN','ALL 50'];let lane='COLOR SHOXX',view='paint',fit=false;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const descriptions={
'COLOR SHOXX':'Ten different high-contrast pigment pairings, each built around competing material regions. Daytime color-dominance experiments: actual iRacing flips are awaiting on-track proof.',
'SURFS UP':'Barrel curls, coral crowns, foam chambers, surf wax, paisley drops, kelp blades, board pinlines, volcanic reefs, comb-jelly bells and tumbled sea glass.',
'MAD SCIENTIST':'Ten independent microscopic constructions with millions of measured paint and spec colors per native texture. Counts below refer to encoded 2048 files, not theoretical palettes.',
'FUTURE SHOXX':'Folded facets, optical switches, re-entrant struts, tactile codes, return circuits, locking teeth and cooperative matter. Speculative designs built with real procedural geometry.',
'ORIGINAL TEN':'The first ten ASTRA finishes you accepted, preserved byte for byte.',
'ALL 50':'The complete ASTRA collection. The original ten and all four expansion lanes share one category in Paint Booth.'};
document.querySelector('#lanes').innerHTML=lanes.map(l=>`<button data-lane="${l}" aria-pressed="${l===lane}">${l}</button>`).join('');
function draw(){
 const q=document.querySelector('#search').value.toLowerCase();const shown=data.filter(d=>(lane==='ALL 50'||d.lane===lane)&&(`${d.name} ${d.desc} ${d.lane}`).toLowerCase().includes(q));
 document.querySelector('#counter').textContent=`${shown.length} ${shown.length===1?'finish':'finishes'}`;document.querySelector('#intro').textContent=descriptions[lane];
 document.querySelector('#grid').innerHTML=shown.map(d=>`<article data-id="${d.id}"><div class="number">ASTRA / ${esc(d.lane)}</div><h2>${esc(d.name)}</h2><p>${esc(d.desc)}</p><div class="frame"><img loading="lazy" draggable="false" src="${d.source}/${view}.png" alt="${esc(d.name)} native ${view}"></div><div class="meta"><b>${d.score.toFixed(1)} M7</b><span>${d.seconds.toFixed(2)}s native pair</span><span>8–32px detail</span></div>${d.colors&&d.lane==='MAD SCIENTIST'?`<div class="colors">${d.colors.paint.toLocaleString()} paint colors · ${d.colors.spec.toLocaleString()} spec colors</div>`:''}<div class="links"><a href="${d.source}/paint.png" target="_blank">Paint PNG ↗</a><a href="${d.source}/spec.png" target="_blank">Spec PNG ↗</a></div><details><summary>Construction, materials &amp; app picker</summary><p>${esc(d.grammar)}</p><p>${esc(d.spec)}</p><p>${esc(d.marks.join(' · '))}</p><img class="picker" loading="lazy" src="thumbnails/picker_split/base/${d.id}.png?v=astra40w2" alt="Actual app paint and spec picker"></details></article>`).join('');
 document.querySelectorAll('.frame').forEach(f=>{if(!fit){f.scrollLeft=740;f.scrollTop=812;}let start=null;f.addEventListener('pointerdown',e=>{start=[e.clientX,e.clientY,f.scrollLeft,f.scrollTop];f.setPointerCapture(e.pointerId);e.preventDefault();});f.addEventListener('pointermove',e=>{if(start){f.scrollLeft=start[2]+start[0]-e.clientX;f.scrollTop=start[3]+start[1]-e.clientY;}});f.addEventListener('pointerup',()=>start=null);f.addEventListener('pointercancel',()=>start=null);});
}
document.querySelectorAll('[data-lane]').forEach(b=>b.onclick=()=>{lane=b.dataset.lane;document.querySelectorAll('[data-lane]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));draw();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;document.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelectorAll('article').forEach(a=>{const d=data.find(x=>x.id===a.dataset.id);a.querySelector('.frame img').src=d.source+'/'+view+'.png';a.querySelector('.frame img').alt=d.name+' native '+view;});});
document.querySelector('#fit').onclick=function(){fit=!fit;document.body.classList.toggle('fit',fit);this.setAttribute('aria-pressed',String(fit));this.textContent=fit?'Return to 1:1':'Fit whole texture';draw();};
document.querySelector('#search').oninput=draw;draw();</script></html>'''
    page=page.replace('aspect-ratio:1.5','aspect-ratio:1')
    page=page.replace('?v=astra40w2','?v=astra40w8')
    page=page.replace('__DATA__',json.dumps(rows,ensure_ascii=False).replace('</','<\\/'))
    stage=new/'review.next.html';stage.write_text(page,encoding='utf-8');os.replace(stage,ROOT/'SPB_AUDIT_astra.html')
    print('ASTRA native review: 50 cards, four new lane filters and original-ten filter')
if __name__=='__main__':main()
