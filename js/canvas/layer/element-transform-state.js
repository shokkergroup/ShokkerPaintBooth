/* SPB-93 tools 2026-09-07: Pick Item must preserve its source rectangle.
   Unchanged Apply moved a picked55 to the whole layer center (143,184 changed
   composite pixels). Numeric fields, drag geometry and commit share one frame. */
(function (root) {
    'use strict';
    function initialize(state, rect) {
        state.origSubRect = { ...rect };
        state.centerX = state.origCenterX = (rect.x1 + rect.x2) / 2;
        state.centerY = state.origCenterY = (rect.y1 + rect.y2) / 2;
        state.boxW = state.origBoxW = Math.abs(rect.x2 - rect.x1);
        state.boxH = state.origBoxH = Math.abs(rect.y2 - rect.y1);
        syncFrame(state);
    }
    function syncFrame(state) {
        if (!state || state.target !== 'layer' || !state.origSubRect) return;
        state.scaleX = (state.scaleX < 0 ? -1 : 1) * state.boxW / state.origBoxW;
        state.scaleY = (state.scaleY < 0 ? -1 : 1) * state.boxH / state.origBoxH;
        state.subRect = {
            x1: state.centerX - state.boxW / 2, y1: state.centerY - state.boxH / 2,
            x2: state.centerX + state.boxW / 2, y2: state.centerY + state.boxH / 2,
        };
    }
    // SPB-93 2026-09-07: linked75% applied the master's dimensions to every
    // sibling. Preserve each source rectangle and transform their centers by
    // the same matrix used for the enclosing frame.
    function item(state, rect) {
        const sx = (state.scaleX < 0 ? -1 : 1) * state.boxW / state.origBoxW;
        const sy = (state.scaleY < 0 ? -1 : 1) * state.boxH / state.origBoxH;
        const rad = (Number(state.rotation) || 0) * Math.PI / 180;
        const dx = ((rect.x1 + rect.x2) / 2 - state.origCenterX) * Math.abs(sx);
        const dy = ((rect.y1 + rect.y2) / 2 - state.origCenterY) * Math.abs(sy);
        return {
            sourceRect: { ...rect },
            centerX: state.centerX + Math.sign(sx) * (dx * Math.cos(rad) - dy * Math.sin(rad)),
            centerY: state.centerY + Math.sign(sy) * (dx * Math.sin(rad) + dy * Math.cos(rad)),
            width: Math.abs((rect.x2 - rect.x1) * sx),
            height: Math.abs((rect.y2 - rect.y1) * sy),
            rotation: Number(state.rotation) || 0, flipH: sx < 0, flipV: sy < 0,
        };
    }
    function setMembers(state, members) {
        if (!state?.origSubRect || !members?.length) return;
        const rect = {
            x1: Math.min(...members.map(r => r.x1)), y1: Math.min(...members.map(r => r.y1)),
            x2: Math.max(...members.map(r => r.x2)), y2: Math.max(...members.map(r => r.y2)),
        };
        const frame = item(state, rect);
        state.sourceMembers = members.map(r => ({ ...r }));
        state.origCenterX = (rect.x1 + rect.x2) / 2;
        state.origCenterY = (rect.y1 + rect.y2) / 2;
        state.origBoxW = rect.x2 - rect.x1; state.origBoxH = rect.y2 - rect.y1;
        state.centerX = frame.centerX; state.centerY = frame.centerY;
        state.boxW = frame.width; state.boxH = frame.height;
        syncFrame(state);
    }
    function captureLinks(layer) {
        return JSON.parse(JSON.stringify({
            elementLinkGroups: layer.elementLinkGroups || [],
            elementInstances: layer.elementInstances || [],
        }));
    }
    function memberAt(layer, x, y) {
        const rects=(layer?.elementLinkGroups || []).flat().concat(
            (layer?.elementInstances || []).flatMap(i=>[i.instanceBbox,i.sourceBbox]).filter(Boolean));
        return rects.find(r =>
            x >= r.x1 && x < r.x2 && y >= r.y1 && y < r.y2) || null;
    }
    function transformedMemberAt(state, members, x, y) {
        const sx = state.boxW / state.origBoxW, sy = state.boxH / state.origBoxH;
        if (!(sx > 0) || !(sy > 0)) return null;
        const rad = (Number(state.rotation) || 0) * Math.PI / 180;
        const dx = (x - state.centerX) * (state.scaleX < 0 ? -1 : 1);
        const dy = (y - state.centerY) * (state.scaleY < 0 ? -1 : 1);
        const sourceX = state.origCenterX + (dx * Math.cos(rad) + dy * Math.sin(rad)) / sx;
        const sourceY = state.origCenterY + (-dx * Math.sin(rad) + dy * Math.cos(rad)) / sy;
        return memberAt({ elementLinkGroups: [members] }, sourceX, sourceY);
    }
    function restoreLinks(layer, links) {
        if (!layer || !links) return;
        Object.assign(layer, JSON.parse(JSON.stringify(links)));
    }
    function unchanged(state) {
        if (state?.target !== 'layer' || !Number.isFinite(state.origCenterX) || !Number.isFinite(state.origCenterY)
            || !(state.origBoxW > 0) || !(state.origBoxH > 0)) return false;
        return Math.abs(state.centerX - state.origCenterX) < 1e-7
            && Math.abs(state.centerY - state.origCenterY) < 1e-7
            && Math.abs(state.boxW - state.origBoxW) < 1e-7
            && Math.abs(state.boxH - state.origBoxH) < 1e-7
            && Math.abs((Number(state.rotation) || 0) % 360) < 1e-7
            && (Number(state.scaleX) || 1) > 0 && (Number(state.scaleY) || 1) > 0;
    }
    const api = { initialize, syncFrame, item, setMembers, captureLinks, restoreLinks, memberAt, transformedMemberAt, unchanged };
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.SPBElementTransformState = api;
})(typeof window === 'object' ? window : globalThis);
