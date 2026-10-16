// dumps js/spb-ai-atlas-data.js (window.SPB_ATLAS_DATA) to _atlas_cards/items.json for the card annotator
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', '..'); const w = {}; vm.createContext(w); w.window = w;
vm.runInContext(fs.readFileSync(path.join(ROOT, 'js', 'spb-ai-atlas-data.js'), 'utf8'), w);
const D = w.SPB_ATLAS_DATA, out = D.items.map(it => Object.assign({}, it, { shelves: (it.s || []).slice(0, 3).map(i => D.sections[i]) }));
fs.mkdirSync(path.join(ROOT, '_atlas_cards'), { recursive: true });
fs.writeFileSync(path.join(ROOT, '_atlas_cards', 'items.json'), JSON.stringify(out));
console.log('items', out.length, 'keys sample', Object.keys(out[0]).join(','));
