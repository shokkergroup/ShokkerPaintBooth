// Small request-ownership contract. Integration and native behavior have their
// own tests; no provider or production controller is simulated as evidence here.
const assert = require('assert');
const O = require('../js/spb-ai-operation.js');
let source = 1, image = {}, width = 2048, path = 'car.psd', layerRev = 1;
const manager = O.create(() => ({ sourceGeneration: source, image, width, path }), () => layerRev);
let aborted = 0, writes = 0;
const a = manager.start({ abort() { aborted++; } });
assert(manager.collecting(a));
const result = manager.bind({ queue: [] }, a);
assert.strictEqual(manager.ticketOf(result), a);
assert(!JSON.stringify(result).includes('_spbOperation'));
assert(manager.ready(a));
assert(!manager.collecting(a));
assert(!manager.publish(a, () => { writes++; layerRev++; }).refused);
assert(manager.current(a));
layerRev++;
assert(!manager.current(a));
assert(manager.publish(a, () => writes++).refused);
assert(manager.restore(a, () => writes++).refused);
const b = manager.start({ abort() { aborted++; } });
assert(manager.cancel(b));
assert.strictEqual(aborted, 1);
assert(!manager.current(b));
assert(manager.publish(b, () => writes++).refused);
assert(!manager.restore(b, () => { writes++; layerRev++; }).refused);
const c = manager.start();
assert(manager.restore(b, () => writes++).refused);
source++;
assert(manager.restore(c, () => writes++).refused);
assert(!manager.sameDocument(c));
for (const replace of [() => { image = {}; }, () => { width = 1024; }, () => { path = 'other.psd'; }]) {
    const t = manager.start(); replace(); assert(!manager.current(t));
}
const d = manager.start(); manager.cancel(a);
assert(manager.current(d));
const oldCollection = d.collection, newCollection = manager.collect(d);
assert(!manager.collecting(d, oldCollection));
assert(manager.collecting(d, newCollection));
assert(!manager.ready(d, oldCollection));
assert(manager.ready(d, newCollection));
assert.strictEqual(writes, 2);
console.log('PASS operation ownership: publication, cancellation, newer owner, source/image/dimensions/path and revision guards');
