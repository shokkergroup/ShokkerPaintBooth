// ============================================================
// FUZZY SEARCH SMOKE TEST (2026-05-27)
// Run with: node _loop_state/fuzzy_search_smoke_test.js
// ============================================================
// Validates the _normSearch / _matchTerms behavior added to
// paint-booth-2-state-zones.js. We re-declare the functions
// here (identical to the production copies) so this test runs
// stand-alone without loading the whole 14k-line UI bundle.
//
// If you change the production normalizer, mirror the change
// here AND in paint-booth-2-state-zones.js. The whole point
// is that they're a single shared logical contract.
// ============================================================

function _normSearch(s) {
    if (s == null) return '';
    return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '');
}
function _normSearchTokens(q) {
    if (q == null) return [];
    return String(q).toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
}
function _matchTerms(query, hay) {
    const tokens = _normSearchTokens(query);
    if (!tokens.length) return true;
    const h = _normSearch(hay);
    return tokens.every(function(t) { return h.indexOf(t) >= 0; });
}

let pass = 0, fail = 0;
function assert(label, actual, expected) {
    const ok = (actual === expected);
    if (ok) { pass++; console.log('  PASS  ' + label); }
    else    { fail++; console.log('  FAIL  ' + label + '\n          got: ' + JSON.stringify(actual) + '\n          want: ' + JSON.stringify(expected)); }
}

console.log('\n-- _normSearch ---------------------------------------');
assert("'Copper Rose Flake' -> 'copperroseflake'",
    _normSearch('Copper Rose Flake'), 'copperroseflake');
assert("'Copper-Rose Flake' -> 'copperroseflake'",
    _normSearch('Copper-Rose Flake'), 'copperroseflake');
assert("\"Won't Forge\" -> 'wontforge'",
    _normSearch("Won't Forge"), 'wontforge');
assert("'  multiple   spaces  ' -> 'multiplespaces'",
    _normSearch('  multiple   spaces  '), 'multiplespaces');
assert("null -> ''",
    _normSearch(null), '');
assert("'ALL-CAPS_with.dots' -> 'allcapswithdots'",
    _normSearch('ALL-CAPS_with.dots'), 'allcapswithdots');

console.log('\n-- _matchTerms (multi-token "all match") -------------');
assert("'copper rose' matches 'Copper-Rose Flake'",
    _matchTerms('copper rose', 'Copper-Rose Flake'), true);
assert("'Copper-Rose' matches 'Copper-Rose Flake'",
    _matchTerms('Copper-Rose', 'Copper-Rose Flake'), true);
assert("'copper' matches 'Copper-Rose Flake'",
    _matchTerms('copper', 'Copper-Rose Flake'), true);
assert("'rose copper' matches 'Copper-Rose Flake' (order-free)",
    _matchTerms('rose copper', 'Copper-Rose Flake'), true);
assert("'zebra plaid' does NOT match 'Copper Rose'",
    _matchTerms('zebra plaid', 'Copper Rose'), false);
assert("empty query matches everything",
    _matchTerms('', 'Copper Rose Flake'), true);
assert("whitespace-only query matches everything",
    _matchTerms('   ', 'Copper Rose Flake'), true);
assert("punctuation in query: 'copper-rose' matches 'Copper Rose Flake'",
    _matchTerms('copper-rose', 'Copper Rose Flake'), true);
assert("'metallic flake' matches 'Premium Metallic Standard Flake-Gold'",
    _matchTerms('metallic flake', 'Premium Metallic Standard Flake-Gold'), true);
assert("'red metallic' does NOT match 'Blue Pearl Flake' (no red)",
    _matchTerms('red metallic', 'Blue Pearl Flake'), false);

console.log('\n======================================================');
console.log('  ' + pass + ' passed, ' + fail + ' failed');
console.log('======================================================\n');
process.exit(fail ? 1 : 0);
