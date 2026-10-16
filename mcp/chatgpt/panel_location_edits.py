"""Expose copied, source-current stored geometry; no map building or edits."""

def edits(relative):
    if relative == 'js/spb-offline-answer.js':
        return [
            ('if (TL && rows && rows.length) { var a = TL.answer(t, rows);', 'if (TL && rows && rows.length && !(W.SpbCarReferenceAnswer && W.SpbCarReferenceAnswer.namesCar && W.SpbCarReferenceAnswer.namesCar(t))) { var a = TL.answer(t, rows);', 1),
            ('W.SPB_CX3_OFF || !(A.live_context || A.reference_context || A.project_discussion)', "W.SPB_CX3_OFF || !(A.live_context || A.reference_context || A.project_discussion || A.id === 'cars.reading_sheet')", 1),
        ]
    if relative != 'js/spb-pro-carmap.js':
        return []
    return [
        ('    function describe() {', '''    function readCurrentGeometry() {
        var out = {status:'unavailable',parts:[],read_only:true,withheld_library_parts:0,geometry_authority:'buyer-confirmed current-source extents only'};
        if (window.SPB_CX3_OFF) return out;
        if (typeof _spbPsdImportInFlight !== 'undefined' && _spbPsdImportInFlight) { out.status = 'loading'; return out; }
        if (!CACHE) return out;
        if (!sameSource(CACHE_SOURCE, sourceDescriptor())) { out.status = 'stale'; return out; }
        out.status = 'current';
        function add(name, bbox, evidence) {
            if (out.parts.length >= 80 || !name || !Array.isArray(bbox) || bbox.length !== 4 || !bbox.every(function(n){return Number.isFinite(n) && n >= 0 && n <= 1;}) || bbox[2] <= bbox[0] || bbox[3] <= bbox[1]) return;
            out.parts.push({name:String(name).slice(0,80),bbox:bbox.slice(),evidence:evidence});
        }
        Object.keys(CACHE.boxes || {}).forEach(function(name) {
            var b = CACHE.boxes[name];
            if (b && b.taught) add(name,b.bbox,'buyer-taught box');
            else if (b && b.lib) out.withheld_library_parts++;
        });
        (CACHE.islands || []).forEach(function(i) {
            if (i && i.confirmed && i.name && !i.lib) add(i.name,i.bbox,'confirmed island label');
        });
        return out;
    }
    function describe() {''', 1),
        ('window.SpbProCar = { recognized:', 'window.SpbProCar = { readCurrentGeometry:readCurrentGeometry, recognized:', 1),
    ]
