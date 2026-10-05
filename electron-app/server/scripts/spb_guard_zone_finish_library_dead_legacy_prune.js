const fs = require('fs');
const { countFileLines } = require('./spb_line_count');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

const zonesFile = 'paint-booth-2-state-zones.js';
const zones = read(zonesFile);

[
  '// === FAVORITES GROUP (always at top if any exist for this tab) ===',
  '// === RECENT GROUP (show recently used finishes) ===',
  'function renderLibraryGroup(gn)',
  'const favItems = activeTab.items.filter(it => _favoriteFinishes.has(it.id));',
  'const allGroupedIds = new Set();'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still contains unreachable legacy renderer marker: ${needle}`));

const renderFlowCall = zones.indexOf('_finishLibraryFinalizeRender({ container, html, activeTab, groupMap, groupNames, activeTabId: activeLibraryTab, itemType: activeTab.type });');
const functionEnd = zones.indexOf('// ===== SECTION TOGGLE =====', renderFlowCall);
assert(renderFlowCall >= 0, `${zonesFile} missing guided catalog render-flow helper call`);
assert(functionEnd > renderFlowCall, `${zonesFile} finish-library render-flow call must stay inside renderFinishLibrary`);
assert(!zones.slice(renderFlowCall, functionEnd).includes('return;'), `${zonesFile} should not return after render-flow helper call`);

const lines = countFileLines(zonesFile);
assert(lines <= 12250, `${zonesFile} should stay at or below 12250 lines after dead legacy prune; saw ${lines}`);

console.log(`Zone finish library dead legacy prune guard passed (${lines} lines, unreachable accordion renderer removed).`);
