/* SPB-93 2026-09-07: native Set Sub-Piece rejected the real selection API.
   Keep the selection frame independent of material placement: no-op isolation
   preserves the material, and Apply composes the actual moved/scaled frame. */
(function(root) {
    'use strict';
    function bounds(info, fallback) {
        let b = info?.bounds || (info && Number.isFinite(info.minX) ?
            {x1:info.minX,y1:info.minY,x2:info.maxX+1,y2:info.maxY+1} : fallback);
        if (!b) return null;
        const rect={x1:b.x1??b[0],y1:b.y1??b[1],x2:b.x2??b[2],y2:b.y2??b[3]};
        return Object.values(rect).every(Number.isFinite) && rect.x2>rect.x1 && rect.y2>rect.y1 ? rect : null;
    }
    function syncFrame(s) {
        if (!s?.zoneSubPiece) return;
        s.subRect={x1:s.centerX-s.boxW/2,y1:s.centerY-s.boxH/2,
            x2:s.centerX+s.boxW/2,y2:s.centerY+s.boxH/2};
    }
    function placement(s, width, height) {
        const f=s.zoneSubPiece;
        if (!f) return null;
        const factor=s.boxW/f.width, rad=s.rotation*Math.PI/180;
        const dx=f.materialX-f.centerX, dy=f.materialY-f.centerY;
        return {offsetX:(s.centerX+factor*(dx*Math.cos(rad)-dy*Math.sin(rad)))/width,
            offsetY:(s.centerY+factor*(dx*Math.sin(rad)+dy*Math.cos(rad)))/height,
            scale:f.materialScale*factor,rotation:f.materialRotation+s.rotation};
    }
    function unchanged(s,current,width,height) {
        const next=placement(s,width,height);if(!next||!current)return false;
        return ['offsetX','offsetY','scale'].every(k=>Math.abs(next[k]-current[k])<1e-12) &&
            Math.abs(((next.rotation-current.rotation)%360+360)%360)<1e-12;
    }
    function begin(s, rect, width, height) {
        if (!s || !rect || s.target==='layer' || width<=0 || height<=0) return false;
        const prior=placement(s,width,height) || {offsetX:s.centerX/width,offsetY:s.centerY/height,
            scale:s.boxW/width,rotation:s.rotation};
        const cx=(rect.x1+rect.x2)/2,cy=(rect.y1+rect.y2)/2;
        s.zoneSubPiece={sourceRect:{...rect},centerX:cx,centerY:cy,width:rect.x2-rect.x1,
            height:rect.y2-rect.y1,materialX:prior.offsetX*width,materialY:prior.offsetY*height,
            materialScale:prior.scale,materialRotation:prior.rotation};
        s.centerX=s.origCenterX=cx;s.centerY=s.origCenterY=cy;
        s.boxW=s.origBoxW=rect.x2-rect.x1;s.boxH=s.origBoxH=rect.y2-rect.y1;
        s.rotation=0;s.scaleX=s.scaleY=1;
        delete s.localPivotDeltaX;delete s.localPivotDeltaY;
        syncFrame(s);return true;
    }
    function clear(s,width,height) {
        const p=placement(s,width,height);if(!p)return false;
        s.centerX=p.offsetX*width;s.centerY=p.offsetY*height;
        s.boxW=width*p.scale;s.boxH=height*p.scale;s.rotation=p.rotation;
        s.origCenterX=s.centerX;s.origCenterY=s.centerY;
        s.origBoxW=s.boxW;s.origBoxH=s.boxH;s.scaleX=s.scaleY=1;
        delete s.zoneSubPiece;s.subRect=null;return true;
    }
    const api={bounds,begin,syncFrame,placement,clear,unchanged};
    if(typeof module==='object'&&module.exports)module.exports=api;
    root.SPBZoneSubPieceTransform=api;
})(typeof window==='object'?window:globalThis);
