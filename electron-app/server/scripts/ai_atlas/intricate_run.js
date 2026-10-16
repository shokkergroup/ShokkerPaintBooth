// B1 INTRICATE-ASKS benchmark runner (headless, free, no server).  node scripts/ai_atlas/intricate_run.js [tag=baseline]
// Runs every ask in intricate_asks.json through (a) the offline advisor reply (classify + answer) and (b) SpbProAdvisor.suggestTool({ask}).
// Appends one JSON line per ask to _easy_claude_work/eval/intricate_<tag>.jsonl ; resumable (skips ids already on disk).
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', '..');
const TAG = process.argv[2] || process.env.TAG || 'baseline';
const OUT = path.join(process.env.MSR_EV || path.join(ROOT, '_easy_claude_work', 'eval'), 'intricate_' + TAG + '.jsonl');
const w = { console, atob: s => Buffer.from(s, 'base64').toString('binary') }; vm.createContext(w); w.window = w; w.document = {};
const run = f => vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), w, { filename: f });
['js/spb-ai-atlas-data.js', 'js/spb-ai-atlas.js', 'js/spb-ai-cards-data.js', 'js/spb-lexicon-ext.js', 'js/spb-lsa-data.js', 'js/spb-ai-cards.js', 'js/spb-intent-data.js', 'js/spb-intent.js', 'js/spb-colours-ext.js'].forEach(run);
const ds = fs.readFileSync(path.join(ROOT, 'js/spb-pro-design.js'), 'utf8'); const m = /var COLOURS = (\{[\s\S]*?\n    \});/.exec(ds);
w.SpbProDesign = { COLOURS: vm.runInContext('(' + m[1] + ')', w) };
run('js/spb-pro-rank.js'); run('js/spb-pro-advisor.js'); w.SpbAIAtlas._install(w.SPB_ATLAS_DATA); w.SpbAICards._install(w.SPB_CARDS_DATA);
const A = w.SpbProAdvisor;
const ENV = { zones: [{ i: 0, id: 'a', name: 'Accent stripe', covers: 'limited to the sides', muted: false, catchAll: false, finishKey: 'base::gloss', colour: '#f26b21', colourMode: 'solid' }, { i: 1, id: 'b', name: 'Body base', covers: 'everything; limited to the whole paintable area', muted: false, catchAll: true, finishKey: 'base::gloss', colour: '#0b2350', colourMode: 'solid' }], paint: ['#0b2350', '#f26b21'] };
// MSR-RUN: optional ASKS=<file.jsonl|json> (+ SINCE=<batch>) ; with neither set behaviour is unchanged.
let asks;
if (process.env.ASKS) {
  const raw = fs.readFileSync(process.env.ASKS, 'utf8').trim();
  asks = raw[0] === '[' ? JSON.parse(raw) : raw.split(String.fromCharCode(10)).filter(Boolean).map(l => JSON.parse(l));
  if (process.env.SINCE) asks = asks.filter(a => Number(a.batch || 0) >= Number(process.env.SINCE));
} else asks = JSON.parse(fs.readFileSync(path.join(__dirname, 'intricate_asks.json'), 'utf8'));
const done = new Set(fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l).id) : []);
const kind = k => { const p = String(k).split('::')[0]; return p === 'monolithic' ? 'monolithic' : p; };
for (const a of asks) {
  if (done.has(a.id)) continue;
  const rec = { id: a.id, ask: a.ask, tag: TAG };
  let t0 = Date.now();
  try {
    const it = A.classify(a.ask, null);
    if (!it) rec.offline = { claimed: false, items: [], text: '', parts: [] };
    else {
      const r = A.answer(it, ENV);
      const tg = it.target || {};
      rec.offline = { claimed: !!r, intent: it.kind, goal: it.goal || null, not: it.not || [], keepColours: !!it.keepColours, colour: it.colour && it.colour.name || null,
        parts: (tg.parts || []).concat(tg.label ? [tg.label] : []), text: r ? String(r.text || '') : '',
        items: r ? (r.cards || []).map(c => ({ key: c.key, kind: kind(c.key), name: c.name, lane: c.lane || null })) : [] };
    }
  } catch (e) { rec.offline = { claimed: false, items: [], text: '', parts: [], error: String(e).slice(0, 120) }; }
  rec.offline.ms = Date.now() - t0; t0 = Date.now();
  try {
    const r = A.suggestTool({ ask: a.ask }, ENV);
    rec.tool = { part: r.part || null, error: r.error || null, text: [r.note, r.message, r.summary].filter(Boolean).join(' ').slice(0, 300),
      mods: r.mods || [], items: (r.rows || []).map(x => ({ key: x.key, kind: kind(x.key), name: x.name, lane: x.lane || null })) };
  } catch (e) { rec.tool = { items: [], error: String(e).slice(0, 120), part: null, text: '' }; }
  rec.tool.ms = Date.now() - t0;
  for (const p of ['offline', 'tool']) { const ks = new Set(rec[p].items.map(i => i.kind === 'monolithic' ? 'base' : i.kind)); rec[p].layerKinds = [...ks]; rec[p].isStack = ks.size > 1; }
  fs.appendFileSync(OUT, JSON.stringify(rec) + '\n');
}
console.log('done', TAG, fs.readFileSync(OUT, 'utf8').split('\n').filter(Boolean).length, 'rows ->', OUT);
