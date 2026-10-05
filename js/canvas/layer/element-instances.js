/* SPB-93: prepare real linked copies without overwriting sibling Layer art.
 * Preparation is read-only; the caller owns mutation and one Undo transaction. */
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBElementInstances = api;
})(typeof window === 'object' ? window : globalThis, function() {
    'use strict';
    const same = (a,b) => !!a && !!b && ['x1','y1','x2','y2'].every(k=>a[k]===b[k]);
    const identity=[1,0,0,1,0,0];
    function multiply(a,b) {
        return [a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],
            a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
    }
    function inverse(m) {
        const d=m[0]*m[3]-m[1]*m[2];
        if(Math.abs(d)<1e-12) return null;
        return [m[3]/d,-m[1]/d,-m[2]/d,m[0]/d,
            (m[2]*m[5]-m[3]*m[4])/d,(m[1]*m[4]-m[0]*m[5])/d];
    }
    function rectMatrix(from,to) {
        const sx=(to.x2-to.x1)/(from.x2-from.x1),sy=(to.y2-to.y1)/(from.y2-from.y1);
        return [sx,0,0,sy,to.x1-from.x1*sx,to.y1-from.y1*sy];
    }
    function placement(record) {
        return record.sourceToInstance?.length===6 ? record.sourceToInstance.slice() : rectMatrix(record.sourceBbox,record.instanceBbox);
    }
    // Match the committed raster's flip * rotation * scale order and padded center.
    function changeMatrix(change) {
        const r=change.from,t=change.to,item=change.item;
        if(!item) return rectMatrix(r,t);
        const angle=(item.rotation||0)*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle);
        const sx=item.width/(r.x2-r.x1),sy=item.height/(r.y2-r.y1),fx=item.flipH?-1:1,fy=item.flipV?-1:1;
        const a=fx*c*sx,b=fy*s*sx,cc=-fx*s*sy,d=fy*c*sy;
        const x=(r.x1+r.x2)/2,y=(r.y1+r.y2)/2;
        return [a,b,cc,d,(t.x1+t.x2)/2-a*x-cc*y,(t.y1+t.y2)/2-b*x-d*y];
    }
    function linked(layer, rect) {
        const records=layer?.elementInstances||[];
        const first=records.find(i=>same(i.sourceBbox,rect)||same(i.instanceBbox,rect));
        return first ? records.filter(i=>same(i.sourceBbox,first.sourceBbox)) : [];
    }
    function relocate(layer, changes) {
        for(const record of layer?.elementInstances||[]) {
            const sourceChange=changes.find(c=>same(c.from,record.sourceBbox));
            const instanceChange=changes.find(c=>same(c.from,record.instanceBbox));
            // Preserve independent orientation through edits of either end.
            if(sourceChange || instanceChange) {
                const masterInverse=sourceChange ? inverse(changeMatrix(sourceChange)) : identity;
                if(masterInverse) record.sourceToInstance=multiply(instanceChange?changeMatrix(instanceChange):identity,
                    multiply(placement(record),masterInverse));
            }
            if(sourceChange) record.sourceBbox={...sourceChange.to};
            if(instanceChange) record.instanceBbox={...instanceChange.to};
        }
    }
    function freePosition(rect, docWidth, docHeight, occupied) {
        const w=rect.x2-rect.x1,h=rect.y2-rect.y1,gap=16;
        const candidates=[
            [rect.x2+gap,rect.y1],[rect.x1-w-gap,rect.y1],
            [rect.x1,rect.y2+gap],[rect.x1,rect.y1-h-gap],
            [rect.x2+gap,rect.y2+gap],[rect.x1-w-gap,rect.y2+gap],
        ];
        const stepX=Math.max(32,Math.floor(w/2)),stepY=Math.max(32,Math.floor(h/2));
        for(let y=0;y+h<=docHeight;y+=stepY) for(let x=0;x+w<=docWidth;x+=stepX) candidates.push([x,y]);
        for(const [x,y] of candidates) {
            const candidate={x1:x,y1:y,x2:x+w,y2:y+h};
            if(x<0||y<0||x+w>docWidth||y+h>docHeight||same(rect,candidate)) continue;
            if(!occupied(candidate)) return candidate;
        }
        return null;
    }
    function prepare(layer, rect, width, height, createCanvas) {
        if(!layer?.img || layer.locked || !Array.isArray(layer.bbox)) return null;
        const [ox,oy]=layer.bbox,w=rect.x2-rect.x1,h=rect.y2-rect.y1;
        if(!(w>0&&h>0)) return null;
        const source=createCanvas(layer.img.width,layer.img.height),cx=source.getContext('2d',{willReadFrequently:true});
        cx.drawImage(layer.img,0,0);
        const pixels=cx.getImageData(0,0,source.width,source.height).data;
        const occupied=r=>{
            const x1=Math.max(0,Math.floor(r.x1-ox)),y1=Math.max(0,Math.floor(r.y1-oy));
            const x2=Math.min(source.width,Math.ceil(r.x2-ox)),y2=Math.min(source.height,Math.ceil(r.y2-oy));
            for(let y=y1;y<y2;y++) for(let x=x1;x<x2;x++) if(pixels[(y*source.width+x)*4+3]) return true;
            return false;
        };
        if(!occupied(rect)) return null;
        const target=freePosition(rect,width,height,occupied);
        if(!target) return null;
        const snapshot=createCanvas(w,h),sx=snapshot.getContext('2d',{willReadFrequently:true});
        sx.drawImage(source,rect.x1-ox,rect.y1-oy,w,h,0,0,w,h);
        const x1=Math.min(ox,target.x1),y1=Math.min(oy,target.y1);
        const x2=Math.max(ox+source.width,target.x2),y2=Math.max(oy+source.height,target.y2);
        const canvas=createCanvas(x2-x1,y2-y1),ctx=canvas.getContext('2d',{willReadFrequently:true});
        ctx.drawImage(source,ox-x1,oy-y1);ctx.drawImage(snapshot,target.x1-x1,target.y1-y1);
        const records=JSON.parse(JSON.stringify(layer.elementInstances||[]));
        const parent=records.find(i=>same(i.instanceBbox,rect)&&!same(i.sourceBbox,i.instanceBbox));
        // Old prototypes registered a self-reference without making any copy.
        const instances=records.filter(i=>!same(i.sourceBbox,i.instanceBbox));
        instances.push({sourceBbox:{...(parent?.sourceBbox||rect)},instanceBbox:{...target},
            sourceToInstance:parent ? multiply(rectMatrix(rect,target),placement(parent)) : rectMatrix(rect,target),
            createdAt:Date.now(),sourcePixelSnapshot:snapshot.toDataURL('image/png')});
        return {canvas,bbox:[x1,y1,x2,y2],instances,target};
    }
    // SPB-93: sync reads today's master pixels, not the creation-time PNG.
    // Build a complete candidate before the caller records history or publishes.
    function prepareSync(layer, rect, createCanvas) {
        if(!layer?.img || layer.locked || layer.visible===false || !Array.isArray(layer.bbox)) return null;
        const group=linked(layer,rect);
        if(!group.length) return null;
        const master=group[0].sourceBbox, [ox,oy,bx2,by2]=layer.bbox;
        const w=master.x2-master.x1,h=master.y2-master.y1;
        if(!(w>0&&h>0)) return null;
        const snapshot=createCanvas(w,h),sx=snapshot.getContext('2d',{willReadFrequently:true});
        const scaleX=layer.img.width/(bx2-ox),scaleY=layer.img.height/(by2-oy);
        sx.drawImage(layer.img,(master.x1-ox)*scaleX,(master.y1-oy)*scaleY,w*scaleX,h*scaleY,0,0,w,h);
        const targets=group.filter(i=>!same(i.instanceBbox,master));
        if(!targets.length) return null;
        let x1=ox,y1=oy,x2=bx2,y2=by2;
        for(const record of targets) {
            const r=record.instanceBbox;
            if(!r || !(r.x2>r.x1&&r.y2>r.y1)) return null;
            x1=Math.min(x1,r.x1);y1=Math.min(y1,r.y1);x2=Math.max(x2,r.x2);y2=Math.max(y2,r.y2);
        }
        const canvas=createCanvas(x2-x1,y2-y1),ctx=canvas.getContext('2d',{willReadFrequently:true});
        ctx.drawImage(layer.img,0,0,layer.img.width,layer.img.height,ox-x1,oy-y1,bx2-ox,by2-oy);
        for(const record of targets) {
            const r=record.instanceBbox;
            ctx.clearRect(r.x1-x1,r.y1-y1,r.x2-r.x1,r.y2-r.y1);
        }
        ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
        for(const record of targets) {
            const r=record.instanceBbox;
            if(record.sourceToInstance) {
                const m=placement(record);
                ctx.save();ctx.transform(m[0],m[1],m[2],m[3],m[4]-x1,m[5]-y1);
                ctx.drawImage(snapshot,0,0,w,h,master.x1,master.y1,w,h);ctx.restore();
            } else {
                ctx.drawImage(snapshot,0,0,w,h,r.x1-x1,r.y1-y1,r.x2-r.x1,r.y2-r.y1);
            }
        }
        const png=snapshot.toDataURL('image/png'),time=Date.now();
        const instances=(layer.elementInstances||[]).map(record=>{
            const copy=JSON.parse(JSON.stringify(record));
            if(group.includes(record)) {
                copy.sourcePixelSnapshot=png;copy.currentSyncedSnapshot=png;copy.lastSyncedAt=time;
            }
            return copy;
        });
        return {canvas,bbox:[x1,y1,x2,y2],instances,count:targets.length};
    }
    // SPB-93: changing linkage never stamps or relocates artwork. Rebase the
    // coordinate maps when a different copy becomes master, retaining siblings.
    function prepareLinks(layer,rect,action,createCanvas) {
        if(!layer?.img || layer.locked || layer.visible===false || !Array.isArray(layer.bbox)) return null;
        if(action!=='promote' && action!=='break') return null;
        const group=linked(layer,rect);
        if(!group.length) return null;
        const clone=value=>JSON.parse(JSON.stringify(value));
        const outside=(layer.elementInstances||[]).filter(i=>!group.includes(i));
        const oldMaster=group[0].sourceBbox,isMaster=same(rect,oldMaster);
        if(action==='break' && !isMaster) return {instances:(layer.elementInstances||[]).filter(i=>!group.includes(i)||!same(i.instanceBbox,rect)).map(clone)};
        if(action==='promote' && isMaster) return null;
        const chosen=group.find(i=>!same(i.sourceBbox,i.instanceBbox)&&(isMaster||same(i.instanceBbox,rect)));
        if(!chosen) return action==='break' ? {instances:outside.map(clone)} : null;
        const newMaster=chosen.instanceBbox,toOldMaster=inverse(placement(chosen));
        if(!toOldMaster) return null;
        const [ox,oy,x2,y2]=layer.bbox,w=newMaster.x2-newMaster.x1,h=newMaster.y2-newMaster.y1;
        const snapshot=createCanvas(w,h),ctx=snapshot.getContext('2d',{willReadFrequently:true});
        const sx=layer.img.width/(x2-ox),sy=layer.img.height/(y2-oy);
        ctx.drawImage(layer.img,(newMaster.x1-ox)*sx,(newMaster.y1-oy)*sy,w*sx,h*sy,0,0,w,h);
        const png=snapshot.toDataURL('image/png'),now=Date.now();
        const rebased=[];
        function add(record,target,map) {
            rebased.push({...clone(record),sourceBbox:{...newMaster},instanceBbox:{...target},
                sourceToInstance:map,sourcePixelSnapshot:png,currentSyncedSnapshot:png,lastSyncedAt:now});
        }
        if(action==='promote') add(chosen,oldMaster,toOldMaster);
        for(const record of group) if(record!==chosen && !same(record.instanceBbox,oldMaster))
            add(record,record.instanceBbox,multiply(placement(record),toOldMaster));
        return {instances:outside.map(clone).concat(rebased)};
    }
    return Object.freeze({same,linked,relocate,freePosition,prepare,prepareSync,prepareLinks,multiply,inverse,placement,changeMatrix});
});
