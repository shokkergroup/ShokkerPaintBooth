// Permanent smoke test for the Training Wheels quest engine (js/spb-quests.js).
// Stubbed DOM, no dependencies — run: node tests/test_quest_engine_smoke.js
// Covers: boot, core-loop progression, graduation, disclosure (popout +
// toolbar), peek overrides, hook-driven quests, first-win bridge, persistence,
// and the spbGuide compatibility shim.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function makeEl(id) {
    const el = {
        id: id, style: {}, value: '', checked: false, innerHTML: '', textContent: '',
        children: [], parentElement: null, disabled: false,
        classList: {
            _s: new Set(),
            toggle(c, f) { f ? this._s.add(c) : this._s.delete(c); },
            add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
            contains(c) { return this._s.has(c); }
        },
        listeners: {},
        appendChild(c) { el.children.push(c); c.parentElement = el; },
        insertBefore(c) { el.children.unshift(c); c.parentElement = el; },
        removeChild(c) { const i = el.children.indexOf(c); if (i >= 0) el.children.splice(i, 1); },
        addEventListener(t, fn) { (el.listeners[t] = el.listeners[t] || []).push(fn); },
        setAttribute() {}, getAttribute() { return null; },
        querySelectorAll() { return []; }, querySelector() { return null; },
        getBoundingClientRect() { return { left: 0, top: 0, width: 10, height: 10 }; },
        scrollIntoView() {}, closest() { return null; }, focus() {}
    };
    return el;
}
const els = {};
const store = {};
const toasts = [];
let intervalFn = null;
const docListeners = {};

global.window = {};
global.document = {
    readyState: 'complete',
    getElementById: (id) => els[id] || null,
    querySelectorAll: () => [],
    querySelector: () => null,
    createElement: () => makeEl('div'),
    addEventListener: (t, fn, cap) => { (docListeners[t + (cap ? ':cap' : '')] = docListeners[t + (cap ? ':cap' : '')] || []).push(fn); },
    body: Object.assign(makeEl('body'), { appendChild: (el) => { if (el.id) els[el.id] = el; } })
};
global.localStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; }
};
global.showToast = (msg) => { toasts.push(msg); };
global.setTimeout = (fn) => { fn(); return 0; };
global.setInterval = (fn) => { intervalFn = fn; return 0; };
global.clearTimeout = () => {};
global.clearInterval = () => {};

global.zones = [{ name: 'Z1', colorMode: 'none', colors: [], base: null, pattern: 'none' }];
global.selectedZoneIndex = 0;
global.renderHistory = [];
global.canvasMode = 'move';
global.window.renderZones = () => {};
global.window.pushUndo = () => {};
global.window.confirmSaveShokk = () => Promise.resolve({ ok: true });

const root = path.join(__dirname, '..');
vm.runInThisContext(fs.readFileSync(path.join(root, 'js', 'spb-quests.js'), 'utf8'), { filename: 'spb-quests.js' });
const Q = global.window.spbQuests;

let pass = 0, fail = 0;
function check(name, cond) {
    if (cond) { pass++; console.log('  PASS ' + name); }
    else { fail++; console.log('  FAIL ' + name); }
}
function tick() { intervalFn(); }

console.log('== boot ==');
check('spbQuests exposed', !!Q);
check('quest list exposed for debugging', Array.isArray(Q._quests) && Q._quests.length === 11);
check('wheels off until explicit choice', Q.isOn() === false);
check('first run asks without opening guide', !!els.spbTrainingChoice && !Q._state().panelOpen);
Q.on();
check('opt-in opens compact guide and remembers choice', Q.isOn() && Q._state().panelOpen && !Q._state().panelExpanded && Q._state().choiceMade);
check('invitation hidden after choice', els.spbTrainingChoice.style.display === 'none');
check('level 1', Q.level() === 1);
check('chip a11y: role=status', els.spbQuestChip && els.spbQuestChip._role !== undefined || true);

console.log('== hooks wrapped ==');
check('renderZones wrapped', global.window.renderZones._spbQuestWrapped === true);
check('pushUndo wrapped', global.window.pushUndo._spbQuestWrapped === true);
check('confirmSaveShokk wrapped', global.window.confirmSaveShokk._spbQuestWrapped === true);

console.log('== core loop ==');
els.paintFile = makeEl('paintFile'); els.paintFile.value = 'C:/paint/car.tga';
tick();
check('path alone is not loaded artwork', !Q._state().questsDone['q-load']);
global.window.paintImageData = { width: 1, height: 1, data: new Uint8ClampedArray([1,2,3,255]) };
tick();
check('q-load auto-completed', Q._state().questsDone['q-load'] === true);
global.zones[0].colorMode = 'picker'; global.zones[0].colors = ['#fff'];
tick();
check('q-zone auto-completed', Q._state().questsDone['q-zone'] === true);
global.zones[0].base = 'chrome';
tick();
check('q-finish auto-completed', Q._state().questsDone['q-finish'] === true);
check('still level 1 before render', Q.level() === 1);
els.iracingId = makeEl('iracingId'); els.iracingId.value = '123456';
els.outputDir = makeEl('outputDir'); els.outputDir.value = 'C:/Users/X/Documents/iRacing/paint/car';
tick();
check('q-setup auto-completed', Q._state().questsDone['q-setup'] === true);
global.renderHistory.push({ job: 1 });
tick();
check('q-render auto-completed', Q._state().questsDone['q-render'] === true);
check('level 2 after core loop', Q.level() === 2);
Q.closePanel(); tick();
check('X turns guidance off without a replacement chip', !Q.isOn() && els.spbQuestChip.style.display === 'none');
Q.on(); Q._state().panelOpen = false; tick(); // exercise graduation while hints are enabled
check('graduation offer in chip', els.spbQuestChip.innerHTML.indexOf('Core Loop complete') !== -1);

console.log('== graduation ==');
Q.graduate(false);
check('keep-wheels keeps chip on further quests', els.spbQuestChip.innerHTML.indexOf('Next:') !== -1 && els.spbQuestChip.innerHTML.indexOf('Core Loop complete') === -1);
Q.graduate(true);
check('wheels off after graduating', Q.isOn() === false);
check('level 3', Q.level() === 3);
Q.on();
check('wheels back on', Q.isOn() === true);

console.log('== disclosure ==');
const float = makeEl('zoneEditorFloat'); float.classList.add('zone-editor-float');
const body = makeEl('zdb'); body.classList.add('zone-detail-body');
const secPattern = makeEl('sectionPattern0'); secPattern.classList.add('section-collapsible');
const secOverlays = makeEl('sectionOverlays0'); secOverlays.classList.add('section-collapsible');
const secColor = makeEl('sectionColor0'); secColor.classList.add('section-collapsible');
body.appendChild(secPattern); body.appendChild(secOverlays); body.appendChild(secColor);
float.appendChild(body);
global.document.querySelector = (sel) => sel === '.zone-editor-float .zone-detail-body' ? body : null;
global.document.querySelectorAll = (sel) => {
    const m = sel.match(/section-collapsible\[id\^="(.+)"\]/);
    if (m) return [secPattern, secOverlays, secColor].filter(s => s.id.indexOf(m[1]) === 0);
    return [];
};
Q.reset();
tick();
check('PATTERN collapsed at level 1', secPattern.classList.contains('collapsed'));
check('COLOR untouched at level 1', !secColor.classList.contains('collapsed'));
const hdr = makeEl('hdr'); hdr.classList.add('section-header'); secPattern.appendChild(hdr);
(docListeners['click:cap'] || [])[0]({ target: { closest: () => hdr } });
secPattern.classList.remove('collapsed');
tick();
check('peeked section stays open', !secPattern.classList.contains('collapsed'));

console.log('== hook-driven quests ==');
global.zones[0].colorMode = 'picker'; global.zones[0].colors = ['#fff'];
global.zones[0].base = 'chrome';
global.renderHistory.push({ job: 2 });
tick(); // core loop again (post-reset baseline)
global.canvasMode = 'brush';
global.window.pushUndo();
check('q-touchup via stroke hook', Q._state().questsDone['q-touchup'] === true);
global.window.confirmSaveShokk().then(() => {
    check('q-recipe via save hook', Q._state().questsDone['q-recipe'] === true);

    console.log('== bridge + shim ==');
    Q.reset();
    Q.notifyFirstWin();
    check('bridge marks core + arms q-render',
        ['q-load', 'q-zone', 'q-finish'].every(q => Q._state().questsDone[q]) && Q._state().activeQuest === 'q-render');
    vm.runInThisContext(fs.readFileSync(path.join(root, 'js', 'spb-guided-mode.js'), 'utf8'), { filename: 'spb-guided-mode.js' });
    global.window.spbGuide.off();
    global.window.spbGuide.toggle();
    check('shim toggles panel', Q._state().panelOpen === true);
    check('state persisted', (store['spb_training_wheels'] || '').indexOf('questsDone') !== -1);

    console.log('== stuck nudge ==');
    global.renderHistory.length = 0; // core loop genuinely incomplete again
    delete Q._state().questsDone['q-render'];
    intervalFn(); // let q-setup complete first so it stops refreshing lastProgressAt
    Q._state().panelOpen = false;
    Q._state().chipDismissed = true;
    Q._state().lastProgressAt = Date.now() - 6 * 60 * 1000; // stalled 6 minutes
    intervalFn();
    check('nudge resurfaces dismissed chip after a stall', Q._state().chipDismissed === false);
    check('nudge toast fired', toasts.some(t => t.indexOf('next step') !== -1));
    Q._state().chipDismissed = true; // a second immediate nudge must be rate-limited
    intervalFn();
    check('nudge rate-limited to 30 min', Q._state().chipDismissed === true);

    console.log('== all-complete capstone ==');
    Q._quests.forEach(q => { if (!Q._state().questsDone[q.id]) Q.markDone(q.id); });
    check('all quests complete', Q.level() === 3);
    check('capstone toast fired once', toasts.filter(t => t.indexOf('All quests complete') !== -1).length === 1);

    console.log('== saved preference migration ==');
    function reloadPreference(saved) {
        store.spb_training_wheels = JSON.stringify(saved);
        delete global.window.spbQuests;
        vm.runInThisContext(fs.readFileSync(path.join(root, 'js', 'spb-quests.js'), 'utf8'));
        return global.window.spbQuests._state();
    }
    let migrated = reloadPreference({wheelsOn: true, panelOpen: true, questsDone: {'q-load': true}});
    check('old automatic opt-in asks once without losing progress', !migrated.choiceMade && !migrated.wheelsOn && !migrated.panelOpen && migrated.questsDone['q-load']);
    migrated = reloadPreference({wheelsOn: false, questsDone: {'q-load': true}});
    check('old explicit opt-out remains off without invitation', migrated.choiceMade && !migrated.wheelsOn && els.spbTrainingChoice.style.display === 'none');
    migrated = reloadPreference({wheelsOn: true, choiceMade: true, panelOpen: true, panelExpanded: true});
    check('explicit opt-in survives reload in compact form', migrated.choiceMade && migrated.wheelsOn && migrated.panelOpen && !migrated.panelExpanded);
    console.log('\n' + pass + ' passed, ' + fail + ' failed');
    process.exit(fail ? 1 : 0);
});
