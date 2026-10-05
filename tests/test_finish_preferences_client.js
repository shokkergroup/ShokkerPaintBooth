const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function settle() { for (let i = 0; i < 10; i++) await Promise.resolve(); }
async function main() {
    const store = new Map([
        ['shokker_favorites', '["old"]'],
        ['spb_finish_ratings_v1', '{"old":91}']
    ]);
    let fail = false;
    const saved = {favorites: {old: false, restored: true}, ratings: {old: 13, restored: 87}};
    const timers = [];
    const context = {
        localStorage: {getItem: k => store.get(k), setItem: (k, v) => store.set(k, v)},
        document: {querySelectorAll: () => []},
        _favoriteFinishes: new Set(['old']), _spbFinishRatingsCache: null,
        setTimeout: fn => { timers.push(fn); return timers.length; }, clearTimeout: () => {},
        addEventListener: () => {}, dispatchEvent: () => {}, CustomEvent: class {},
        fetch: async (_url, options) => {
            if (fail) throw new Error('offline');
            const patch = JSON.parse(options.body);
            for (const kind of ['favorites', 'ratings'])
                for (const [id, value] of Object.entries(patch[kind] || {}))
                    if (!patch.migrate || saved[kind][id] === undefined) saved[kind][id] = value;
            return {ok: true, json: async () => JSON.parse(JSON.stringify(saved))};
        }
    };
    context.window = context;
    vm.createContext(context);
    vm.runInContext(fs.readFileSync('js/spb-finish-preferences.js', 'utf8'), context);
    await settle();
    assert.deepEqual([...context._favoriteFinishes], ['restored']);
    assert.equal(context._spbFinishRatingsCache.old, 13);
    fail = true;
    context.SPBFinishPreferences.favorite('restored', false);
    context.SPBFinishPreferences.rating('old', 99);
    await context.SPBFinishPreferences.flush();
    assert.equal(JSON.parse(store.get('spb_finish_preferences_pending_v1')).ratings.old, 99);
    fail = false;
    await context.SPBFinishPreferences.flush();
    assert.equal(saved.favorites.restored, false);
    assert.equal(saved.ratings.old, 99);
    assert.equal(Object.keys(JSON.parse(store.get('spb_finish_preferences_pending_v1')).ratings).length, 0);
    console.log('PASS: migration, removal, offline journal, retry, rating durability');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
