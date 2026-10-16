#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const noop = function () {};
const storage = new Map();
const sandbox = {
    console,
    Map,
    Set,
    Date,
    Math,
    JSON,
    Number,
    String,
    Array,
    Object,
    RegExp,
    Promise,
    URL,
    URLSearchParams,
    Uint8Array,
    setTimeout: function () { return 0; },
    clearTimeout: noop,
    requestAnimationFrame: noop,
    localStorage: {
        getItem: function (key) { return storage.has(key) ? storage.get(key) : null; },
        setItem: function (key, value) { storage.set(key, String(value)); },
        removeItem: function (key) { storage.delete(key); },
    },
    document: {
        readyState: 'loading',
        addEventListener: noop,
        getElementById: function () { return null; },
        querySelector: function () { return null; },
        querySelectorAll: function () { return []; },
        body: { classList: { add: noop, remove: noop, toggle: noop }, appendChild: noop },
        documentElement: { classList: { add: noop, remove: noop, toggle: noop } },
    },
    navigator: {},
    location: { search: '' },
    // Catalog boot normally performs an optional server merge. Keep this audit
    // deterministic and offline without producing a misleading warning.
    fetch: function () { return new Promise(function () {}); },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

function run(relativePath) {
    const absolute = path.join(root, relativePath);
    vm.runInContext(fs.readFileSync(absolute, 'utf8'), sandbox, { filename: relativePath });
}

[
    'paint-booth-0-finish-data.js',
    'paint-booth-0-finish-tags.js',
    'paint-booth-0-finish-metadata.js',
    'paint-booth-0-catalog-scorecard.js',
    'paint-booth-0-picker-owner-ratings.js',
    'paint-booth-1-data.js',
].forEach(run);

const easyPath = path.join(root, 'js', 'spb-easy-mode.js');
let easySource = fs.readFileSync(easyPath, 'utf8');
const marker = '    window.spbEasy = {';
if (!easySource.includes(marker)) throw new Error('Easy Mode audit export marker moved');
easySource = easySource.replace(marker, [
    '    window.__spbEasyFeaturedAudit = {',
    '        buildCatalogSections: buildCatalogSections,',
    '        finishInfo: finishInfo,',
    '        qualityEligible: easyFeaturedQualityEligible,',
    '        tagSubject: _tagSubject,',
    '        filterTags: FILTER_TAGS',
    '    };',
    marker,
].join('\n'));
vm.runInContext(easySource, sandbox, { filename: 'js/spb-easy-mode.js' });

const api = sandbox.__spbEasyFeaturedAudit;
if (!api) throw new Error('Easy Mode audit API was not exposed');
const sections = api.buildCatalogSections();
const seen = new Set();
const definitions = [
    { tag: 'candy', title: 'CANDY & PEARL PICKS' },
    { tag: 'pattern', title: 'PATTERNED PICKS' },
    { tag: 'dark', title: 'STEALTH PICKS' },
];

let failed = false;
const report = definitions.map(function (collection) {
    const tag = api.filterTags.find(function (candidate) { return candidate.key === collection.tag; });
    const ids = [];
    sections.some(function (section) {
        section.ids.some(function (id) {
            if (seen.has(id) || !api.qualityEligible(id)) return false;
            const subject = api.tagSubject(id);
            if (!subject || !tag || !tag.test(subject)) return false;
            seen.add(id);
            ids.push(id);
            return ids.length === 8;
        });
        return ids.length === 8;
    });
    if (ids.length !== 8) failed = true;
    return { tag: collection.tag, title: collection.title, count: ids.length, ids };
});

const uniqueCount = new Set(report.flatMap(function (row) { return row.ids; })).size;
if (uniqueCount !== 24) failed = true;
console.log(JSON.stringify({ ok: !failed, uniqueCount, collections: report }, null, 2));
if (failed) process.exit(1);
