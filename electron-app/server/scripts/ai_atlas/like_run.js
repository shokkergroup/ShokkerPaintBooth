// "like X but <modifier>" benchmark, step 1: build deterministic cases and the 5 finishes SpbProRank.like() returns for each.
//   node scripts/ai_atlas/like_run.js [name=base] [N=90]      env MODW='{"darker":2.8}' overrides modifier weights (for experiments)
//   then: python scripts/ai_atlas/like_judge.py <name>
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', '..'); const w = { console, atob: s => Buffer.from(s, 'base64').toString('binary') }; vm.createContext(w); w.window = w; w.document = {};
function run(f) { vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), w, { filename: f }); }
run('js/spb-ai-atlas-data.js'); run('js/spb-ai-atlas.js'); run('js/spb-ai-cards-data.js'); run('js/spb-lexicon-ext.js'); run('js/spb-lsa-data.js'); run('js/spb-ai-cards.js'); run(process.env.INTENT_FILE || 'js/spb-intent-data.js'); run('js/spb-intent.js'); run('js/spb-colours-ext.js'); run('js/spb-pro-rank.js');
w.SpbAIAtlas._install(w.SPB_ATLAS_DATA); w.SpbAICards._install(w.SPB_CARDS_DATA);
const R = w.SpbProRank, A = w.SpbAIAtlas, C = w.SpbAICards, name = process.argv[2] || 'base', N = Number(process.argv[3]) || 90;
if (process.env.MODW) { const o = JSON.parse(process.env.MODW); Object.keys(o).forEach(m => { if (R.MODS[m]) R.MODS[m].forEach(sp => { sp[2] = o[m]; }); }); }
if (process.env.CFG) { const o = JSON.parse(process.env.CFG); Object.keys(o).forEach(k => { R._cfg[k] = o[k]; }); }      // e.g. CFG='{"likeMod":1.6}'
if (process.env.LSAW != null) C._lsa.w = Number(process.env.LSAW);
let seed = 12345; function rnd() { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }
const pickR = a => a[Math.floor(rnd() * a.length)];
const items = A._data().items.filter(i => C.card(i.k) && (i.q == null || i.q >= 55));
const base0 = items.filter(i => i._type === 'base' && i.o === 0), own = items.filter(i => i._type === 'monolithic' && i.o === 1 && C.card(i.k).appeal >= 4), tex = items.filter(i => (i._type === 'spec' || i._type === 'pattern') && C.card(i.k).appeal >= 4);
const MODS_OWN = ['calm', 'bold', 'darker', 'lighter', 'glossier', 'flatter', 'sparklier', 'smoother', 'metalmore', 'metalless', 'warmer', 'cooler', 'vivid', 'muted', 'simpler', 'busier'];
const MODS_TAKES = ['calm', 'bold', 'glossier', 'flatter', 'sparklier', 'smoother', 'metalmore', 'metalless', 'finer', 'coarser'];
const MODS_TEX = ['calm', 'bold', 'finer', 'coarser', 'simpler', 'busier'];
const cases = [];
for (let i = 0; i < N; i++) {
  const kind = i % 3 === 0 ? 'takes' : (i % 3 === 1 ? 'own' : 'tex'), ref = pickR(kind === 'takes' ? base0 : (kind === 'own' ? own : tex));
  const mod = pickR(kind === 'takes' ? MODS_TAKES : (kind === 'own' ? MODS_OWN : MODS_TEX));
  const none = i % 10 === 9;      // some cases without a modifier: plain "like X"
  const rows = R.like([ref.k], { mods: none ? [] : [mod], limit: 5 });
  cases.push({ ref: ref.k, refName: ref.n, kind, mod: none ? null : mod, keys: rows.map(r => r.key) });
}
const dir = path.join(ROOT, '_easy_claude_work', 'like'); fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, 'cases_' + name + '.json'), JSON.stringify(cases));
console.log(name, 'cases', cases.length, 'with 5 rows', cases.filter(c => c.keys.length === 5).length);
