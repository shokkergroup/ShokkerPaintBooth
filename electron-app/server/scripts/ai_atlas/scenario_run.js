// SCENARIOS: a painter with a given colour scheme asks for finishes for a part/goal. Runs the finish ADVISOR end to end (classify + answer) and writes results the gold judge can score.
//   node scripts/ai_atlas/scenario_run.js curated      (advisor with the old hand-picked slots: spb-pro-rank.js NOT loaded)
//   node scripts/ai_atlas/scenario_run.js ranked       (advisor with the whole-catalogue ranker)
const vm = require('vm'), fs = require('fs'), path = require('path');
const mode = process.argv[2] || 'ranked';
const ROOT = path.join(__dirname, '..', '..'); const w = { console, atob: s => Buffer.from(s, 'base64').toString('binary') }; vm.createContext(w); w.window = w; w.document = {};
function run(f) { vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), w, { filename: f }); }
run('js/spb-ai-atlas-data.js'); run('js/spb-ai-atlas.js'); run('js/spb-ai-cards-data.js'); run('js/spb-lexicon-ext.js'); run('js/spb-lsa-data.js'); run('js/spb-ai-cards.js'); run(process.env.INTENT_FILE || 'js/spb-intent-data.js'); run('js/spb-intent.js'); run('js/spb-colours-ext.js');
const ds = fs.readFileSync(path.join(ROOT, 'js/spb-pro-design.js'), 'utf8'); const m = /var COLOURS = (\{[\s\S]*?\n    \});/.exec(ds); w.SpbProDesign = { COLOURS: vm.runInContext('(' + m[1] + ')', w) };
if (mode === 'ranked') run('js/spb-pro-rank.js');
run('js/spb-pro-advisor.js');
w.SpbAIAtlas._install(w.SPB_ATLAS_DATA); w.SpbAICards._install(w.SPB_CARDS_DATA);
const A = w.SpbProAdvisor, C = w.SpbProDesign.COLOURS;
if (process.env.CFGJ && w.SpbProRank) { const o = JSON.parse(process.env.CFGJ); Object.keys(o).forEach(k => { w.SpbProRank._cfg[k] = o[k]; }); }      // e.g. CFGJ='{"pop":{"up":1.6,"down":1.6}}' for experiments
const TAG = process.env.SCENTAG || mode;
const SCHEMES = [['navy', 'orange'], ['red', 'white'], ['black', 'gold'], ['powder blue', 'orange'], ['lime green', 'purple'], ['white', 'red'], ['matte olive', 'tan'], ['yellow', 'black'], ['teal', 'pink'], ['burgundy', 'silver'], ['royal blue', 'white'], ['orange', 'black']];
let PARTS = ['the stripes', 'the hood', 'the roof', 'the sides', 'the body', 'the lower band', 'the bumpers', 'the spoiler'];
const FLAVOURS = [['', null], ['to look premium', 'premium'], ['so it pops', 'pop'], ['with a bit of shimmer', 'shimmer'], ['with deeper colour', 'deep'], ['for a retro look', 'retro'], ['for a stealth look', 'stealth'], ['for a dirt late model', null], ['that looks aggressive', null], ['that looks clean and simple', null], ['for a GT car', null], ['that feels like a luxury watch', null]];
// SCENSET=2: a second flavour set (numbers, TV / night / dirt-hiding asks) so a tuning pass is not fitted to the first twelve flavours; judge with the same gold_judge.py (file results_adv_<tag>.json)
if (process.env.SCENSET === '2') { PARTS = ['the numbers', 'the stripes', 'the roof', 'the hood', 'the body', 'the sides']; FLAVOURS.length = 0; [['', null], ['so it reads clearly on TV', 'readable'], ['for night racing', null], ['that hides dirt', null], ['to look expensive', 'premium'], ['that looks wet', 'deep'], ['for a clean modern look', null], ['that stands out in the pack', 'pop'], ['for a vintage livery', 'retro'], ['that is easy on the eyes', null]].forEach(x => FLAVOURS.push(x)); }
if (process.env.SCENSET === '3') { PARTS = ['the hood', 'the roof', 'the sides', 'the stripes', 'the body', 'the lower band']; FLAVOURS.length = 0; [['for a NASCAR look', null], ['for a 70s muscle car', 'retro'], ['for an open wheel car', null], ['for a GT3 car at night', null], ['that matches neon sponsor logos', null], ['that looks like brushed steel', null], ['that looks pastel and soft', 'subtle'], ['that looks like carbon fibre', null], ['that looks tough and military', 'stealth'], ['that keeps sponsor logos easy to read', 'readable']].forEach(x => FLAVOURS.push(x)); }      // SCENSET=3: a third, never-tuned-on flavour set (class / era / material look-alikes / sponsors)
function rnd(i) { let h = i * 2654435761 % 4294967296; h ^= h >>> 13; h = (h * 1274126177) % 4294967296; return (h >>> 0) / 4294967296; }
const out = [];
let n = 0;
for (let i = 0; i < (+process.env.NSCEN || 96); i++) {
  const sch = SCHEMES[Math.floor(rnd(i * 3 + 1) * SCHEMES.length)], part = PARTS[Math.floor(rnd(i * 3 + 2) * PARTS.length)], fl = FLAVOURS[Math.floor(rnd(i * 3 + 3) * FLAVOURS.length)];
  const ask = 'my car is ' + sch[0] + ' and ' + sch[1] + ', what finish should I put on ' + part + (fl[0] ? ' ' + fl[0] : '');
  const body = C[sch[0].replace('matte ', '')] || '#808080', acc = C[sch[1]] || '#c0c0c0';
  const env = { zones: [{ i: 0, id: 'a', name: 'Accent stripe', covers: 'limited to the sides', muted: false, catchAll: false, finishKey: 'base::gloss', colour: acc, colourMode: 'solid' },
    { i: 1, id: 'b', name: 'Body base', covers: 'everything; limited to the whole paintable area', muted: false, catchAll: true, finishKey: 'base::gloss', colour: body, colourMode: 'solid' }], paint: [body, acc] };
  const it = A.classify(ask, null); if (!it) { out.push({ ask, cat: 'scenario', keys: [] }); continue; }
  const r = A.answer(it, env); out.push({ ask, cat: 'scenario', keys: r ? r.cards.map(c => c.key) : [] });
}
fs.writeFileSync(path.join(ROOT, '_easy_claude_work', 'gold', 'results_adv_' + TAG + '.json'), JSON.stringify(out));
const seen = new Set(); out.forEach(o => o.keys.forEach(k => seen.add(k)));
console.log(mode, 'scenarios', out.length, 'with cards', out.filter(o => o.keys.length).length, 'distinct finishes', seen.size);
