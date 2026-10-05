// The shipped page must install its new handlers; installing a test-only module
// adapter would conceal the actual owner-reported ReferenceError.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('js/zones/pattern-transform-controls.js', 'utf8');
for (const readyState of ['loading', 'complete']) {
  const listeners = {}, history = [];
  let previews = 0;
  const legacy = () => 'legacy';
  const sandbox = { document: {readyState, addEventListener: (name, fn) => listeners[name] = fn,
    querySelectorAll: () => []}, zones: [{patternStack:[{}]}],
    pushZoneUndo: (...args) => history.push(args), triggerPreviewRender: () => previews++,
    setZoneScale: legacy, setZonePatternOpacity: legacy };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  if (readyState === 'loading') listeners.DOMContentLoaded();
  assert.equal(typeof sandbox.setPatternMaterialControl, 'function');
  assert.equal(sandbox.setZoneScale, legacy);
  assert.equal(sandbox.setZonePatternOpacity, legacy);
  sandbox.setPatternMaterialControl(0, -1, 'hue', 120);
  sandbox.setPatternMaterialControl(0, -1, 'saturation', -100);
  sandbox.setPatternMaterialControl(0, -1, 'spec', 50);
  sandbox.stepPatternMaterialControl(0, 0, 'spec', 1);
  assert.equal(sandbox.zones[0].patternHueShift, 120);
  assert.equal(sandbox.zones[0].patternSaturation, -100);
  assert.equal(sandbox.zones[0].patternSpecOpacity, 50);
  assert.equal(sandbox.zones[0].patternStack[0].specOpacity, 5);
  assert.equal(history.length, 4); assert.equal(previews, 4);
  sandbox.setPatternMaterialControl(0, -1, 'spec', 50); // no-op
  sandbox.setPatternMaterialControl(0, -1, 'spec', 'invalid');
  assert.equal(history.length, 4);
}
console.log('PASS: fresh/deferred boot, primary/stack controls, history, preview, legacy setters preserved');
