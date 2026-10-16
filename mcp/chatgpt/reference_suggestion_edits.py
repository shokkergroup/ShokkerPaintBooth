"""Keep factual article suggestions on an explicitly resolved car/version."""

FILTER = r"""    // Read-only suggestion scope: reuse shared car identity; never loaded-paint aliases.
    function filterReferenceArticles(text, hits) {
        if (!Array.isArray(hits)) return [];
        if (W.SPB_REFERENCE_SUGGESTIONS_OFF || !W.SpbCarKnowledge || !CAR_ARTICLE_DATA.cars.length) return hits;
        // A comparison must retain alternatives; scope only one named reference.
        if (/\b(?:vs|versus|compare|comparison|differences?|both|between)\b/i.test(String(text || ''))) return hits;
        var found;
        try { found = W.SpbCarKnowledge.select(CAR_ARTICLE_DATA, {query:text}); } catch (e) { return hits; }
        var exact = found && found.definite && found.matches && found.matches.length === 1;
        var unknown = found && ((found.retired_matches && found.retired_matches.length) || found.reason === 'unknown-model-code');
        if (!exact && !unknown) return hits;
        var wanted = exact ? found.matches[0].id : null;
        return hits.filter(function (hit) {
            var id = hit && String(hit.id || '');
            if (/^cars\.reference\./.test(id)) return wanted !== null && id === 'cars.reference.' + wanted;
            if (/^car_pages\./.test(id)) {
                if (unknown) return false;
                var folder = CAR_ARTICLE_SCOPES[id];
                // PBN can index a legacy page absent from the Offline corpus.
                // Its explicit summary folder is identity evidence, not geometry.
                if (!folder) { var fm = /\bfolder\s+([a-z0-9 _-]+)\.?$/i.exec(String(hit.summary || hit.sm || '')); if (fm) folder = fm[1].trim().toLowerCase(); }
                return !folder || folder === found.matches[0].paint_folder;
            }
            return true;
        });
    }
"""

ARTICLES_BEFORE = """        var mk = String(q).toLowerCase() + '|' + (n || 3); if (ART_MEMO[mk]) return ART_MEMO[mk];
        try { hits = E.search(q, 30) || []; } catch (x) { hits = []; }
        var out = []; hits.forEach(function (h) { if (out.length < (n || 3) && /^(article|help|tool)$/.test(String(h.type || '')) && out.every(function (o) { return o.id !== h.id; })) out.push({ id: h.id, title: h.title || h.id, sm: String(h.summary || h.sm || '').slice(0, 110) }); });
        if (out.length) ART_MEMO[mk] = out;"""
ARTICLES_AFTER = """        var mk = String(q).toLowerCase();
        if (ART_MEMO[mk]) hits = ART_MEMO[mk];
        else { try { hits = E.search(q, 30) || []; } catch (x) { hits = []; }
            hits = hits.slice(0, 30).map(function (h) { return {id:h.id,type:h.type,title:h.title,summary:String(h.summary || h.sm || '').slice(0,110)}; });
            if (hits.length) { if (Object.keys(ART_MEMO).length >= 40) ART_MEMO = {}; ART_MEMO[mk] = hits; }
        }
        // Cache raw bounded search hits; recheck current index scope on every use.
        if (W.SpbOfflineAnswer && W.SpbOfflineAnswer.filterReferenceArticles) hits = W.SpbOfflineAnswer.filterReferenceArticles(q, hits);
        var out = []; hits.forEach(function (h) { if (out.length < (n || 3) && /^(article|help|tool)$/.test(String(h.type || '')) && out.every(function (o) { return o.id !== h.id; })) out.push({ id: h.id, title: h.title || h.id, sm: String(h.summary || h.sm || '').slice(0, 110) }); });"""

def edits(relative):
    if relative == 'js/spb-offline-answer.js':
        return [
            ('    var IX = null, _load = null;', '    var IX = null, _load = null, CAR_ARTICLE_DATA = {cars:[]}, CAR_ARTICLE_SCOPES = {};\n' + FILTER, 1),
            ('        if (W.SpbCarReferenceAnswer) W.SpbCarReferenceAnswer.index(list);',
             "        CAR_ARTICLE_DATA = {cars:list.filter(function (a) {return a && a.car_reference;}).map(function (a) {return a.car_reference;})};\n        CAR_ARTICLE_SCOPES = {}; list.forEach(function (a) { if (!a || !/^car_pages\\./.test(a.id || '')) return; var m = /iRacing car folder name:\\s*([a-z0-9 _-]+)\\./i.exec(a.what || ''); if (m) CAR_ARTICLE_SCOPES[a.id] = m[1].trim().toLowerCase(); });\n        if (W.SpbCarReferenceAnswer) W.SpbCarReferenceAnswer.index(list);", 1),
            ('    W.SpbOfflineAnswer = { _w29Norm:', '    W.SpbOfflineAnswer = { filterReferenceArticles: filterReferenceArticles, _w29Norm:', 1),
        ]
    if relative == 'js/spb-pbn.js':
        return [(ARTICLES_BEFORE, ARTICLES_AFTER, 1)]
    if relative == 'js/spb-pro-ai.js':
        return [
            ('    function encSearch(q, k, ms) {', "    function scopedEncArticles(q, hits) { var reader = window.SpbOfflineAnswer; return reader && reader.filterReferenceArticles ? reader.filterReferenceArticles(q, hits) : hits; }\n    function encSearch(q, k, ms) {", 1),
            ('if (_encCache[key]) return Promise.resolve(_encCache[key]);', 'if (_encCache[key]) return Promise.resolve(scopedEncArticles(q, _encCache[key]));', 1),
            ('clearTimeout(tm); return a || [];', 'clearTimeout(tm); return scopedEncArticles(q, a || []);', 1),
        ]
    return []
