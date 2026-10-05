#!/usr/bin/env node

const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

const moduleFile = 'js/zones/finish-library-search-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'FINISH_LIBRARY_SEARCH_ALIASES',
  'function _smartSearchTokens',
  'function _smartSearchAliasesForWord',
  'function _smartSearchWordMatches',
  'function _smartSearchScore',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  'FINISH_LIBRARY_SEARCH_ALIASES: FINISH_LIBRARY_SEARCH_ALIASES',
  '_smartSearchTokens: _smartSearchTokens',
  '_smartSearchAliasesForWord: _smartSearchAliasesForWord',
  '_smartSearchWordMatches: _smartSearchWordMatches',
  '_smartSearchScore: _smartSearchScore'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-search-controls.js') &&
    html.indexOf('js/zones/finish-library-search-controls.js') < html.indexOf('js/zones/finish-library-guided-catalog-controls.js') &&
    html.indexOf('js/zones/finish-library-search-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library search module must load before guided catalog and paint-booth-2-state-zones.js'
);

[
  'getSearchAliases: () => (typeof FINISH_LIBRARY_SEARCH_ALIASES',
  'smartSearchTokens: (q) => (typeof _smartSearchTokens ===',
  'smartSearchWordMatches: (hay, word, id) => (typeof _smartSearchWordMatches ==='
].forEach((needle) => assert(zones.includes(needle), `zones guided-catalog bridge missing ${needle}`));

[
  'function _smartSearchTokens',
  'function _smartSearchAliasesForWord',
  'function _smartSearchWordMatches',
  'function _smartSearchScore',
  'const FINISH_LIBRARY_SEARCH_ALIASES'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

console.log('Zone finish library search guard passed (smart-search helpers extracted).');
