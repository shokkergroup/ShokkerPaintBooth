/* enc_extract.js - helper for build_encyclopedia.py (2026-10-04).
   Reads the shipped JS data files + the tables inside js/spb-pro-edit.js WITHOUT editing any of them, and writes one JSON dump
   (default _easy_claude_work/enc/extract.json) for the Python generator. Also exports parserTerms(root) for the node gate
   (_easy_claude_work/enc_test.js): the set of words/phrases the offline parser's tables understand.
   Tables inside spb-pro-edit.js's IIFE are not exported, so each `var NAME = ...;` statement is cut out of the source text
   line by line and evaluated in a bare vm context (a statement is complete when it compiles). A table that cannot be found is
   reported in `missing` (never fatal) so a refactor by another worker shows up as a gap, not a crash. */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function norm(s) { return String(s || '').toLowerCase().replace(/['’`]/g, '').replace(/[^a-z0-9#]+/g, ' ').replace(/\s+/g, ' ').trim(); }

// ---------------------------------------------------------------- run a data .js file (window.X = ...) in a vm
function runData(root, files) {
    const ctx = { console: { log() {}, warn() {}, error() {} } }; ctx.window = ctx; vm.createContext(ctx);
    files.forEach(f => { try { vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), ctx, { filename: f }); } catch (e) { ctx.__err = (ctx.__err || []).concat(f + ': ' + String(e.message).slice(0, 80)); } });
    return ctx;
}

// ---------------------------------------------------------------- cut `var NAME = ...;` statements out of a source file
function cutVars(src, names) {
    const lines = src.split(/\r?\n/), ctx = { window: {}, document: undefined }; vm.createContext(ctx);
    const out = {}, missing = [];
    names.forEach(name => {
        if (name in out) return;
        const re = new RegExp('^\\s*var ' + name + '\\b\\s*=');
        let i = lines.findIndex(l => re.test(l));
        if (i < 0) { missing.push(name); return; }
        let acc = '', ok = false;
        for (let j = i; j < Math.min(lines.length, i + 40); j++) {
            acc += lines[j] + '\n';
            try { new vm.Script(acc); ok = true; break; } catch (e) { /* statement not complete yet */ }
        }
        if (!ok) { missing.push(name); return; }
        try { vm.runInContext(acc, ctx); out[name] = ctx[name]; } catch (e) { missing.push(name + '(eval)'); }
        // statements declaring several vars (A = ..., B = ...) put all of them on ctx
        Object.keys(ctx).forEach(k => { if (!(k in out) && names.indexOf(k) >= 0) out[k] = ctx[k]; });
    });
    return { out, missing: missing.filter(n => !(n in out)), ctx };
}

// ---------------------------------------------------------------- tiny regex -> strings expander (alternation, groups, optionals)
// mode 'min': an optional piece is omitted, EXCEPT an optional space ("deck ?lid") which yields both forms.
function expand(src, cap) {
    cap = cap || 4000; let i = 0;
    function prod(a, b) { const r = []; for (const x of a) for (const y of b) { r.push(x + y); if (r.length > cap) throw new Error('cap'); } return r; }
    function parseAlt() { let res = parseSeq(); while (src[i] === '|') { i++; res = res.concat(parseSeq()); } return res; }
    function parseSeq() {
        let res = [''], dead = false;
        while (i < src.length && src[i] !== '|' && src[i] !== ')') {
            let atom = parseAtom(), q = src[i], optional = false, empty = false;
            if (q === '?') { i++; optional = true; if (src[i] === '?') i++; }
            else if (q === '*' || q === '+') { i++; if (src[i] === '?') i++; if (atom.length === 1 && atom[0] === '@W') { atom = ['@W']; } else throw new Error('quant'); }
            else if (q === '{') { while (src[i] !== '}') i++; i++; atom = []; }
            if (optional) { if (atom.length === 1 && atom[0] === ' ') atom = ['', ' ']; else atom = ['']; }
            if (!atom.length) dead = true; else if (!dead) res = prod(res, atom);
        }
        return dead ? [] : res;
    }
    function parseAtom() {
        const c = src[i];
        if (c === '(') {
            i++; let look = false;
            if (src[i] === '?') { const t = src.slice(i, i + 3); if (t === '?:') i += 2; else if (t === '?!' || t === '?=') { look = true; i += 2; } else if (t === '?<') { look = true; i += 3; } }
            const inner = parseAlt(); if (src[i] !== ')') throw new Error('paren'); i++;
            return look ? [''] : inner;
        }
        if (c === '[') { let j = src.indexOf(']', i); const cls = src.slice(i + 1, j); i = j + 1; if (/[\\^.\-]/.test(cls) || cls.length > 6) throw new Error('class'); return cls.split(''); }
        if (c === '\\') { const n = src[i + 1]; i += 2; if (n === 'b' || n === 'B') return ['']; if (n === 's') return [' ']; if (n === 'w') return ['@W']; if (n === 'd') return []; return [n]; }
        if (c === '.' || c === '^' || c === '$') { i++; if (c === '.') throw new Error('dot'); return ['']; }
        i++; return [c];
    }
    const res = parseAlt(); if (i < src.length) throw new Error('trailing');
    return res;
}
function expandTerms(re) {
    let src = re instanceof RegExp ? re.source : String(re), out;
    try { out = expand(src); } catch (e) { return { terms: [], err: e.message }; }
    const set = new Set();
    out.forEach(s => { s = norm(s.replace(/@W/g, '#')); if (s.length >= 2 && /[a-z]/.test(s) && !/\bundefined\b/.test(s)) set.add(s); });
    return { terms: [...set].sort() };
}

// ---------------------------------------------------------------- parser tables of js/spb-pro-edit.js
const EDIT_VARS = ['LOOKS', 'TEXTURES', 'PLAIN', 'TINT_COLOURS', 'PART_WORDS', 'LAYERWORDS', 'NUMBERS_RE', 'SPONSORS_RE', 'ACCENT_RE', 'BODY_RE',
    'HOLO_RE', 'UNKNOWN_PART_RE', 'WORD_TYPOS', 'SHADE_RE', 'REL_UP', 'REL_DOWN', 'POP_RE', 'HOLO_LOOK'];

function parserTables(root) {
    const src = fs.readFileSync(path.join(root, 'js', 'spb-pro-edit.js'), 'utf8');
    const { out, missing } = cutVars(src, EDIT_VARS);
    const dz = runData(root, ['js/spb-pro-design.js', 'js/spb-colours-ext.js']);
    const D = dz.SpbProDesign || {};
    return { src: out, missing, colours: Object.keys(D.COLOURS || {}), colourExt: dz.SPB_COLOUR_EXT || {}, design: D };
}

// parserTerms: { term -> source label } = every word / phrase a table of the offline parser understands.
function parserTerms(root) {
    const T = parserTables(root), s = T.src, terms = {}, gaps = [];
    function add(t, why) { t = norm(t); if (t.length >= 2 && /[a-z]/.test(t) && !(t in terms)) terms[t] = why; }
    (s.LOOKS || []).forEach(l => (l.words || []).forEach(w => add(w, 'LOOKS:' + l.id)));
    (s.TEXTURES || []).forEach(t => { const e = expandTerms(t.re); if (e.err) gaps.push('TEXTURES.' + t.id + ':' + e.err); e.terms.forEach(w => add(w, 'TEXTURES:' + t.id)); });
    Object.keys(s.PLAIN || {}).forEach(w => add(w, 'PLAIN'));
    Object.keys(s.TINT_COLOURS || {}).forEach(w => add(w, 'TINT'));
    Object.keys(s.WORD_TYPOS || {}).forEach(w => add(w, 'WORD_TYPOS'));
    T.colours.forEach(w => add(w, 'COLOURS'));
    Object.keys(T.colourExt).forEach(w => add(w, 'COLOUR_EXT'));
    (s.PART_WORDS || []).forEach(p => { const e = expandTerms(p[1]); if (e.err) gaps.push('PART_WORDS.' + p[0] + ':' + e.err); e.terms.forEach(w => add(w, 'PART_WORDS:' + p[0])); add(p[0], 'PART_WORDS'); });
    (s.LAYERWORDS || []).forEach(p => { const e = expandTerms(p[1]); if (e.err) gaps.push('LAYERWORDS.' + p[0] + ':' + e.err); e.terms.forEach(w => add(w, 'LAYERWORDS:' + p[0])); add(p[0], 'LAYERWORDS'); });
    ['NUMBERS_RE', 'SPONSORS_RE', 'ACCENT_RE', 'BODY_RE', 'HOLO_RE', 'UNKNOWN_PART_RE', 'SHADE_RE', 'REL_UP', 'REL_DOWN', 'POP_RE'].forEach(n => {
        if (!s[n]) return; const e = expandTerms(s[n]); if (e.err) gaps.push(n + ':' + e.err); e.terms.forEach(w => add(w, n));
    });
    return { terms, gaps, missing: T.missing };
}

// ---------------------------------------------------------------- the full dump for the generator
function dump(root) {
    const d = runData(root, ['js/spb-ai-atlas-data.js', 'js/spb-ai-cards-data.js', 'js/spb-lexicon-ext.js']);
    const A = d.SPB_ATLAS_DATA || {}, C = d.SPB_CARDS_DATA || {};
    const items = (A.items || []).map(i => ({ k: i.k, n: i.n, d: i.d, s: i.s, c: i.c, cn: i.cn, o: i.o, shine: i.shine, metal: i.metal, t: i.t || [], q: i.q, sk: i.sk, gold: i.gold, g: i.g, fb: i.fb }));
    const cards = {}; Object.keys(C.cards || {}).forEach(k => { const c = C.cards[k]; cards[k] = [c[0], c[1], c[2], c[13], c[14], c[15], c[16], c[17], c[7], c[8]]; });
    const P = parserTables(root), D = P.design, s = P.src;
    const pt = parserTerms(root);
    const textures = (s.TEXTURES || []).map(t => ({ id: t.id, label: t.label, spec: t.spec, specName: t.specName, specAlt: t.specAlt, pattern: t.pattern, patternName: t.patternName, words: expandTerms(t.re).terms }));
    const partWords = (s.PART_WORDS || []).map(p => ({ id: p[0], words: expandTerms(p[1]).terms }));
    const layerWords = (s.LAYERWORDS || []).map(p => ({ id: p[0], words: expandTerms(p[1]).terms }));
    const res = {
        atlas: { v: A.v, sections: A.sections, blurbs: A.blurbs, groups: A.groups, count: A.count, items },
        cards, cardsMeta: { v: C.v, moods: C.moods, uses: C.uses },
        design: { LOOK_CURATED: D.LOOK_CURATED, COLOURS: D.COLOURS, ELEMENTS: D.ELEMENTS, PRESETS: D.PRESETS, SPEC_LOOKS: D.SPEC_LOOKS,
            PALETTES: (D.PALETTES || []).map(p => ({ id: p.id, names: p.names, about: p.about, era: p.era, base: p.base, a: p.a, b: p.b })) },
        colourExt: P.colourExt, lexExt: d.SPB_LEX_EXT || {},
        parser: { LOOKS: s.LOOKS, TEXTURES: textures, PART_WORDS: partWords, LAYERWORDS: layerWords, PLAIN: Object.keys(s.PLAIN || {}), TINT: s.TINT_COLOURS || {}, WORD_TYPOS: s.WORD_TYPOS || {},
            HOLO_LOOK: s.HOLO_LOOK, words: { NUMBERS: expandTerms(s.NUMBERS_RE || /x/).terms, SPONSORS: expandTerms(s.SPONSORS_RE || /x/).terms, ACCENT: expandTerms(s.ACCENT_RE || /x/).terms, BODY: expandTerms(s.BODY_RE || /x/).terms,
                HOLO: expandTerms(s.HOLO_RE || /x/).terms, UNKNOWN_PART: expandTerms(s.UNKNOWN_PART_RE || /x/).terms, SHADE: expandTerms(s.SHADE_RE || /x/).terms, REL_UP: expandTerms(s.REL_UP || /x/).terms, REL_DOWN: expandTerms(s.REL_DOWN || /x/).terms, POP: expandTerms(s.POP_RE || /x/).terms },
            terms: pt.terms, gaps: pt.gaps, missing: pt.missing },
        loadErrors: d.__err || []
    };
    return res;
}

module.exports = { parserTerms, parserTables, expandTerms, norm, dump, runData };

if (require.main === module) {
    const root = path.resolve(__dirname, '..', '..');
    const outFile = process.argv[2] || path.join(root, '_easy_claude_work', 'enc', 'extract.json');
    fs.mkdirSync(path.dirname(outFile), { recursive: true });
    const r = dump(root);
    fs.writeFileSync(outFile, JSON.stringify(r));
    console.log('extract ok: items=' + r.atlas.items.length + ' cards=' + Object.keys(r.cards).length + ' parserTerms=' + Object.keys(r.parser.terms).length +
        ' gaps=' + r.parser.gaps.length + ' missing=[' + r.parser.missing.join(',') + '] loadErrors=' + r.loadErrors.length);
}
