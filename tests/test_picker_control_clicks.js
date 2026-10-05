const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('paint-booth-2-state-zones.js', 'utf8');
const start = source.indexOf('function _installSwatchHoverPopout(grid) {');
const end = source.indexOf('\nfunction _installSwatchPopupLazyLoader()', start);
let handler, previews = 0, prevented = 0;
const context = {
    _swatchViewerBypass: false, window: {},
    _showSwatchBigPreview: () => previews++
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const grid = {dataset: {}, contains: () => true, addEventListener: (_type, fn) => {handler = fn;}};
context._installSwatchHoverPopout(grid);
const card = {getAttribute: k => k === 'data-finish-id' ? 'test_finish' : 'base'};
for (const control of ['button', 'input', '.swatch-rate-row', null]) {
    handler({
        target: {closest: selector => selector.startsWith('.swatch-item') ? card : (control && selector.includes(control) ? {} : null)},
        preventDefault: () => prevented++, stopPropagation: () => {}
    });
}
assert.equal(previews, 1, 'Only the card artwork opens the viewer');
assert.equal(prevented, 1, 'Favorite and range controls keep their normal events');
console.log('PASS: favorite/slider clicks bypass the capturing image viewer');
