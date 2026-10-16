/* SPB-93 owner09-08: visual pixel aid only. Pick/Exclude sampling and edits
 * retain their existing handlers and coordinate mapping. */
(function () {
    'use strict';
    const lens=document.createElement('div'); lens.id='spbPrecisionLens'; lens.hidden=true;
    lens.setAttribute('aria-hidden','true');
    const canvas=document.createElement('canvas'); canvas.width=132; canvas.height=132;
    lens.append(canvas); document.body.append(lens);
    let event=null,raf=0,geo=null;
    const hide=()=>{if(!lens.hidden)lens.hidden=true;};
    function isEnabled() {
        const mode=typeof canvasMode==='string'?canvasMode:window.canvasMode;
        // [SPB-TFX1 2026-10-09 TA-001] window.spbPrecisionLens is ALSO the #spbPrecisionLens element (named-element global), so it was always truthy and the loupe
        // followed every brush/eraser stroke (brush drag: 50 long tasks / 2.9 s, rAF p50 18.7 ms vs 0 long tasks / 8.0 ms without). The opt-in is now a
        // private flag that only "Pixel detail 1:1" sets. SPB_TFX1_OFF restores the old always-on test.
        const optIn=window.SPB_TFX1_OFF?window.spbPrecisionLens:window.__spbLensOn===true;
        return mode==='eyedropper'||(optIn && ['spatial-exclude','spatial-include','spatial-erase','brush','erase'].includes(mode));
    }
    // PORT-W5B (2026-10-09, SPB_W5B_OFF): draw() used to call getBoundingClientRect()/innerWidth INSIDE the rAF callback, i.e. after the
    // brush's own rAF work had dirtied layout, forcing a full document layout every frame (measured 12.6 ms/frame of the ~20 ms
    // per-frame cost of a brush stroke at 2048). The geometry is now read once per pointermove (layout is clean at input time) and
    // draw() only paints. Behaviour is unchanged (window.spbPrecisionLens is the #spbPrecisionLens element, so the lens is
    // truthy-enabled in brush/erase too - that is existing behaviour and left as is).
    function measure(e) {
        const source=document.getElementById('paintCanvas');
        if(!source||!e) return null;
        // window.spbCanvasRect = the 16 ms cached canvas rect (paint-booth-3-canvas.js, invalidated on scroll/resize/wheel) that the cursor circle
        // and the coordinate readout already use; a raw getBoundingClientRect after the brush's DOM writes is a forced layout flush.
        const r=(!window.SPB_W5B_OFF&&window.spbCanvasRect)?window.spbCanvasRect():source.getBoundingClientRect(),ex=e.clientX,ey=e.clientY;
        if(r.width<=0||ex<r.left||ex>=r.right||ey<r.top||ey>=r.bottom) return null;
        return {source,ex,ey,x:Math.floor((ex-r.left)*source.width/r.width),y:Math.floor((ey-r.top)*source.height/r.height),
            left:Math.max(4,Math.min(innerWidth-140,ex+22)),top:Math.max(4,Math.min(innerHeight-140,ey-154))};
    }
    function draw() {
        raf=0;
        const enabled=isEnabled();
        if(!enabled||!event){hide();return;}
        const g=window.SPB_W5B_OFF?measure(event):geo;
        if(!g){hide();return;}
        const source=g.source,x=g.x,y=g.y;
        const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=false;
        ctx.fillStyle='#202830';ctx.fillRect(0,0,132,132);
        ctx.drawImage(source,x-7,y-7,15,15,0,0,132,132);
        const cell=132/15;
        ctx.strokeStyle='#ffffff35';ctx.lineWidth=.5;ctx.beginPath();
        for(let i=1;i<15;i++){ctx.moveTo(i*cell,0);ctx.lineTo(i*cell,132);ctx.moveTo(0,i*cell);ctx.lineTo(132,i*cell);}
        ctx.stroke();ctx.strokeStyle='#fff';ctx.lineWidth=1;ctx.strokeRect(7*cell,7*cell,cell,cell);
        lens.style.left=g.left+'px';
        lens.style.top=g.top+'px';lens.hidden=false;
    }
    document.addEventListener('pointermove',e=>{if(!isEnabled()){hide();return;}event=e;if(!window.SPB_W5B_OFF)geo=measure(e);if(!raf)raf=requestAnimationFrame(draw);},{passive:true});
    document.addEventListener('pointerdown',e=>{if(!e.target.closest('#canvasViewport'))hide();},{passive:true});
    window.addEventListener('blur',()=>{event=null;hide();});
    window.spbPixelDetail=function(){
        if(!window.SPB_TFX1_OFF&&window.__spbLensOn===true){window.__spbLensOn=false;hide();showToast('Pixel detail loupe off. Click Pixel detail again to bring it back.','info');return;}   // [SPB-TFX1 2026-10-09 TA-001] second click switches the loupe off
        window.__spbLensOn=true;window.spbPrecisionLens=true;canvasZoom('100');showToast('Pixel detail: 1:1 view. Hold Space to pan; FIT returns to the full paint.','info');};
}());
