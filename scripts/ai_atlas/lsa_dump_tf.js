// Dump the per-card weighted unigram term frequencies from the REAL js indexer (identical tokenizer / stemmer / field weights) for scripts/ai_atlas/build_lsa.py
//   node scripts/ai_atlas/lsa_dump_tf.js   ->  _atlas_cards/lsa_tf.json
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', '..'); const w = { console }; vm.createContext(w); w.window = w; w.document = {};
const run = f => vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), w, { filename: f });
run('js/spb-ai-atlas-data.js'); run('js/spb-ai-atlas.js'); run('js/spb-ai-cards-data.js'); run('js/spb-lexicon-ext.js'); run('js/spb-ai-cards.js');
w.SpbAIAtlas._install(w.SPB_ATLAS_DATA); w.SpbAICards._install(w.SPB_CARDS_DATA);
const IDX = w.SpbAICards._idx(), keys = [], docs = [];
IDX.docs.forEach(d => { keys.push(d.k); const row = []; for (const t in d.tf) { if (t.indexOf('_') === -1) row.push([t, Math.round(d.tf[t] * 100) / 100]); } docs.push(row); });
fs.writeFileSync(path.join(ROOT, '_atlas_cards', 'lsa_tf.json'), JSON.stringify({ keys, docs }));
console.log('lsa_dump_tf: docs', keys.length, 'avg unigrams', (docs.reduce((a, r) => a + r.length, 0) / docs.length).toFixed(1));
