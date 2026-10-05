/* Executes the real page tool handlers without touching the buyer's paint. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
let ready = false, builds = 0, unlock;
const zones = [{ id: 'stable-hood', name: 'Hood' }, { id: 'stable-roof', name: 'Roof' }];
const sandbox = { console, Promise, Date, setTimeout() {}, setInterval() {}, zones, selectedZoneIndex: 0,
    document: { readyState: 'loading', addEventListener() {}, getElementById() { return null; } },
    window: { SpbTellNLU: { buildIndex() { return {}; } }, SpbAI: { cached() { return {}; } },
        SpbMcpBridge: { stats() { return { enabled: true }; } },
        SpbProZone: { SCHEMA: {}, zonesForModel() { return zones.map((z, i) => ({ id: z.id, i, name: z.name })); },
            validate() { return { errors: [] }; }, catchAll() { return null; }, whenSettled() { return Promise.resolve(); }, previewImage() { return null; } },
        SpbProCar: { ensure() { return Promise.resolve().then(() => { ready = true; }); }, roles() { return []; }, describe() { return { parts: ready ? ['hood'] : [] }; } },
        SpbProDesign: { build() { builds++; assert(ready, 'car map must resolve before scheme building'); return { zones: [], skipped: [] }; } }
    }
};
vm.createContext(sandbox);
const mockZone = sandbox.window.SpbProZone;
delete mockZone.SCHEMA;
vm.runInContext(fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8'), sandbox);
Object.assign(sandbox.window.SpbProZone, mockZone);
for (const file of ['js/spb-ai-lease.js', 'js/spb-pro-ai.js']) {
    let source = fs.readFileSync(path.join(root, file), 'utf8');
    if (file.endsWith('spb-pro-ai.js')) source = source.replace('    window.spbProAI =', '    window.__testTools = makeTools;\n    window.spbProAI =');
    vm.runInContext(source, sandbox);
}
const ai = sandbox.window.spbProAI, lease = sandbox.window.SpbAiLease;
(async () => {
    const tools = await ai.mcpCall('list_tools');
    assert(tools.ok, JSON.stringify(tools));
    const edit = tools.result.tools.find(t => t.name === 'spb_edit_zone');
    assert(edit.inputSchema.properties.zone_id);
    // Generate schemas from the real app handlers, exactly as --tools does with the live app.
    if (process.argv.includes('--tools')) fs.writeFileSync(path.join(root, 'mcp/server/tools.json'), JSON.stringify(tools.result.tools, null, 1));
    const stale = await ai.mcpCall('edit_zone', { zone: 0, expect_name: 'Roof', color: '#ffffff' });
    assert.equal(stale.ok, false); assert.match(stale.error, /zone changed/);
    const absent = await ai.mcpCall('edit_zone', { zone_id: 'missing' });
    assert.equal(absent.ok, false);
    // A reordered array must still target the stable identity, and guard fields must not leak into settings.
    zones.reverse();
    const queue = [], editHandler = sandbox.window.__testTools(queue).find(t => t.name === 'edit_zone').handler;
    assert(editHandler({ zone_id: 'stable-hood', expect_name: 'Hood', name: 'Hood updated' }).ok);
    assert.equal(queue[0].zone, 1);
    assert.equal(queue[0].spec.name, 'Hood updated');
    assert.equal(queue[0].spec.zone_id, undefined);
    assert.equal(queue[0].spec.expect_name, undefined);
    assert(editHandler({ zone_name: 'Roof', name: 'Roof updated' }).ok);
    assert.equal(queue[1].zone, 0);
    zones.push({ id: 'another-roof', name: 'Roof' });
    assert.match(editHandler({ zone_name: 'Roof', name: 'Ambiguous' }).error, /no zone/);
    zones.pop(); zones.reverse();
    const scheme = await ai.mcpCall('apply_scheme', { elements: [{ id: 'hood', colour: '#fff000' }] });
    assert.equal(scheme.ok, false); assert.equal(builds, 1);
    ready = false;
    sandbox.window.SpbProCar.ensure = () => new Promise(resolve => { unlock = resolve; });
    const first = ai.mcpCall('status');
    await Promise.resolve();
    const overlap = await ai.mcpCall('zones');
    assert.equal(overlap.ok, false);
    assert.equal(lease.takeover(), false);
    unlock(); await first;
    assert.equal(lease.internal(), false);
    assert.equal(lease.takeover(), true);
    assert.equal((await ai.mcpCall('zones')).ok, false);
    lease.release();
    assert.equal((await ai.mcpCall('zones')).ok, true);
    console.log('PASS: real schemas, stale edit rejection, lazy map warm-up, exclusive calls and explicit takeover');
})().catch(e => { console.error(e); process.exitCode = 1; });
