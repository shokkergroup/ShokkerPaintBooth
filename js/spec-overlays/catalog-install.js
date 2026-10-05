/* SPB-105 v2 tick 2: keep legacy IDs available to saved recipes; browse the new catalog. */
(function(global){
    'use strict';
    if(typeof SPEC_PATTERNS==='undefined'||!global.SPB_SPEC_OVERLAY_V2)return;
    global.SPBLegacySpecOverlayDefinitions=Object.fromEntries(SPEC_PATTERNS.map(p=>[p.id,Object.assign({},p)]));
    SPEC_PATTERNS.forEach(p=>{p.legacy=true;});
    const catalog=global.SPB_SPEC_OVERLAY_V2;
    catalog.items.forEach(item=>{
        if(!SPEC_PATTERNS.some(p=>p.id===item.id))SPEC_PATTERNS.push(item);
        if(typeof SPEC_PATTERNS_BY_ID!=='undefined')SPEC_PATTERNS_BY_ID[item.id]=item;
    });
    // Shared family names must retain every legacy entry (notably Optical).
    catalog.families.forEach(f=>{SPEC_PATTERN_GROUPS[f.name]=Array.from(new Set([...(SPEC_PATTERN_GROUPS[f.name]||[]),...catalog.items.filter(p=>p.family===f.id).map(p=>p.id)]));});
})(typeof window!=='undefined'?window:globalThis);
