/* SPB-93 owner09-08: visual pixel aid only. Pick/Exclude sampling and edits
 * retain their existing handlers and coordinate mapping. */
(function () {
    'use strict';
    const lens=document.createElement('div'); lens.id='spbPrecisionLens'; lens.hidden=true;
    lens.setAttribute('aria-hidden','true');
    const canvas=document.createElement('canvas'); canvas.width=132; canvas.height=132;
    lens.append(canvas); document.body.append(lens);
    let event=null,raf=0;
    const hide=()=>{if(!lens.hidden)lens.hidden=true;};
    function isEnabled() {
        const mode=typeof canvasMode==='string'?canvasMode:window.canvasMode;
        return mode==='eyedropper'||(window.spbPrecisionLens && ['spatial-exclude','spatial-include','spatial-erase','brush','erase'].includes(mode));
    }
    function draw() {
        raf=0;
        const enabled=isEnabled();
        const source=document.getElementById('paintCanvas');
        if(!enabled||!source||!event){hide();return;}
        const r=source.getBoundingClientRect(),ex=event.clientX,ey=event.clientY;
        if(r.width<=0||ex<r.left||ex>=r.right||ey<r.top||ey>=r.bottom){hide();return;}
        const x=Math.floor((ex-r.left)*source.width/r.width),y=Math.floor((ey-r.top)*source.height/r.height);
        const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=false;
        ctx.fillStyle='#202830';ctx.fillRect(0,0,132,132);
        ctx.drawImage(source,x-7,y-7,15,15,0,0,132,132);
        const cell=132/15;
        ctx.strokeStyle='#ffffff35';ctx.lineWidth=.5;ctx.beginPath();
        for(let i=1;i<15;i++){ctx.moveTo(i*cell,0);ctx.lineTo(i*cell,132);ctx.moveTo(0,i*cell);ctx.lineTo(132,i*cell);}
        ctx.stroke();ctx.strokeStyle='#fff';ctx.lineWidth=1;ctx.strokeRect(7*cell,7*cell,cell,cell);
        lens.style.left=Math.max(4,Math.min(innerWidth-140,ex+22))+'px';
        lens.style.top=Math.max(4,Math.min(innerHeight-140,ey-154))+'px';lens.hidden=false;
    }
    document.addEventListener('pointermove',e=>{if(!isEnabled()){hide();return;}event=e;if(!raf)raf=requestAnimationFrame(draw);},{passive:true});
    document.addEventListener('pointerdown',e=>{if(!e.target.closest('#canvasViewport'))hide();},{passive:true});
    window.addEventListener('blur',()=>{event=null;hide();});
    window.spbPixelDetail=function(){window.spbPrecisionLens=true;canvasZoom('100');showToast('Pixel detail: 1:1 view. Hold Space to pan; FIT returns to the full paint.','info');};
}());
