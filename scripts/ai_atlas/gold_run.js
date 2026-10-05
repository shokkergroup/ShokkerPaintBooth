// runs the gold asks through each retrieval SYSTEM and writes _easy_claude_work/gold/results_<system>.json  (node scripts/ai_atlas/gold_run.js [system ...])
//   lexical      the old atlas keyword/facet search            cards     BM25 over the finish cards            rank   cards + diversity
//   pipe_old     the finish ADVISOR end to end with the old hand-picked slots + lexical find (no ranker)       pipe_new   the advisor with the whole-catalogue ranker
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', '..');
function mkCtx(withRank) {
  const w = { console, atob: s => Buffer.from(s, 'base64').toString('binary') }; vm.createContext(w); w.window = w; w.document = {};
  const run = f => vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), w, { filename: f });
  run('js/spb-ai-atlas-data.js'); run('js/spb-ai-atlas.js'); run('js/spb-ai-cards-data.js'); run('js/spb-lexicon-ext.js'); run('js/spb-lsa-data.js'); run('js/spb-ai-cards.js'); run(process.env.INTENT_FILE || 'js/spb-intent-data.js'); run('js/spb-intent.js'); run('js/spb-colours-ext.js');
  const ds = fs.readFileSync(path.join(ROOT, 'js/spb-pro-design.js'), 'utf8'); const m = /var COLOURS = (\{[\s\S]*?\n    \});/.exec(ds); w.SpbProDesign = { COLOURS: vm.runInContext('(' + m[1] + ')', w) };
  if (withRank) run('js/spb-pro-rank.js');
  run('js/spb-pro-advisor.js');
  w.SpbAIAtlas._install(w.SPB_ATLAS_DATA); w.SpbAICards._install(w.SPB_CARDS_DATA);
  return w;
}
const NEW = mkCtx(true), OLD = mkCtx(false);
if (process.env.WB && NEW.SpbProRank._cfg) NEW.SpbProRank._cfg.wB = parseFloat(process.env.WB);
// ASKS=<file.json> runs another ask list ([{ask, cat}]) and writes results_<tag>_<system>.json (tag = ASKTAG, default 'x'): used by truth_score.py for the hand-labelled truth set
const asks = JSON.parse(fs.readFileSync(process.env.ASKS ? path.resolve(process.env.ASKS) : path.join(ROOT, '_easy_claude_work', 'gold', 'asks.json'), 'utf8')), TAG = process.env.ASKS ? (process.env.ASKTAG || 'x') + '_' : '';
const EMPTY = { zones: [], paint: [] };
function pipe(w, useRank) {
  return q => {
    const A = w.SpbProAdvisor, it = A.classify(q, null);
    if (it) { const r = A.answer(it, EMPTY); if (r && r.cards && r.cards.length) return r.cards.map(c => c.key).slice(0, 6); }
    if (useRank) return w.SpbProRank.search(q, { limit: 6 }).map(r => r.key);
    return (w.SpbAIAtlas.find({ query: q, type: 'finish', limit: 6, diverse: true, min_quality: 40 }) || []).map(r => r.key);
  };
}
const SYSTEMS = {
  lexical: q => (NEW.SpbAIAtlas.find({ query: q, type: 'finish', limit: 6, diverse: true, min_quality: 40 }) || []).map(r => r.key),
  cards: q => NEW.SpbAICards.search(q, { types: ['base', 'monolithic'], limit: 6 }).map(r => r.key),
  rank: q => NEW.SpbProRank.search(q, { limit: 6 }).map(r => r.key),
  pipe_old: pipe(OLD, false),
  pipe_new: pipe(NEW, true),
};
const want = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(SYSTEMS);
for (const s of want) {
  const out = asks.map(a => ({ ask: a.ask, cat: a.cat, keys: SYSTEMS[s](a.ask) }));
  const seen = new Set(); out.forEach(o => o.keys.forEach(k => seen.add(k)));
  fs.writeFileSync(path.join(ROOT, '_easy_claude_work', 'gold', 'results_' + TAG + s + (process.env.WB ? '_wb' + process.env.WB : '') + '.json'), JSON.stringify(out));
  console.log(s, 'asks', out.length, 'distinct items', seen.size, 'empty', out.filter(o => !o.keys.length).length);
}
