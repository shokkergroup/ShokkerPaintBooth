// in_app_updater_smoke_test.js — exercise update-check.js without a network.
//
// Run with: node _loop_state/in_app_updater_smoke_test.js
//
// Tests:
//   1. compareVersions semver correctness
//   2. Snooze: future timestamp -> no banner; past timestamp -> banner OK
//   3. Network failure: fetchImpl throws -> resolves silently (no banner)
//   4. Happy path: fetchImpl returns newer version -> updateAvailable=true
//   5. Older remote: fetchImpl returns older -> updateAvailable=false

'use strict';

const path = require('path');
const mod = require(path.resolve(__dirname, '..', 'electron-app', 'update-check.js'));

let pass = 0;
let fail = 0;
const log = (s) => { process.stdout.write(s + '\n'); };

function assertEq(actual, expected, label) {
  if (actual === expected) { pass++; log('  PASS  ' + label + '  (' + JSON.stringify(actual) + ')'); }
  else { fail++; log('  FAIL  ' + label + '  expected=' + JSON.stringify(expected) + ' actual=' + JSON.stringify(actual)); }
}

// ----- 1. compareVersions --------------------------------------------------
log('\n[1] compareVersions semver correctness');
assertEq(mod.compareVersions('6.2.0', '6.3.0'), -1, '6.2.0 < 6.3.0');
assertEq(mod.compareVersions('6.3.0', '6.2.0'),  1, '6.3.0 > 6.2.0');
assertEq(mod.compareVersions('6.3.0', '6.2.9'),  1, '6.3.0 > 6.2.9');
assertEq(mod.compareVersions('6.3.10', '6.3.9'), 1, '6.3.10 > 6.3.9');
assertEq(mod.compareVersions('6.3.0', '6.3.0'),  0, '6.3.0 == 6.3.0');
assertEq(mod.compareVersions('v6.3.0', '6.3.0'), 0, 'v-prefix stripped');
assertEq(mod.compareVersions('6.3.0-beta', '6.3.0'), -1, 'prerelease < release');
assertEq(mod.compareVersions('7.0.0', '6.99.99'), 1, 'major bump wins');
assertEq(mod.compareVersions('garbage', '6.3.0'), 0, 'garbage tolerated -> 0');

// ----- 2. snooze -----------------------------------------------------------
log('\n[2] snooze behavior');

function makeStorage() {
  const map = {};
  return {
    getItem: (k) => (k in map ? map[k] : null),
    setItem: (k, v) => { map[k] = String(v); },
    removeItem: (k) => { delete map[k]; },
    _map: map,
  };
}

const storage1 = makeStorage();
// Set snooze to future (1 hour ahead)
const futureIso = new Date(Date.now() + 60 * 60 * 1000).toISOString();
storage1.setItem(mod.SNOOZE_KEY, futureIso);
assertEq(mod.isSnoozed(Date.now(), storage1), true, 'future snooze -> isSnoozed true');

const storage2 = makeStorage();
const pastIso = new Date(Date.now() - 60 * 60 * 1000).toISOString();
storage2.setItem(mod.SNOOZE_KEY, pastIso);
assertEq(mod.isSnoozed(Date.now(), storage2), false, 'past snooze -> isSnoozed false');

const storage3 = makeStorage();
assertEq(mod.isSnoozed(Date.now(), storage3), false, 'no snooze key -> isSnoozed false');

// setSnooze writes a future ISO
const storage4 = makeStorage();
mod.setSnooze(24, storage4);
const written = storage4.getItem(mod.SNOOZE_KEY);
const writtenMs = Date.parse(written);
const expectMin = Date.now() + 23 * 60 * 60 * 1000;
const expectMax = Date.now() + 25 * 60 * 60 * 1000;
assertEq(writtenMs > expectMin && writtenMs < expectMax, true, 'setSnooze(24) lands ~24h ahead');

// ----- 3. checkForUpdate respects snooze ----------------------------------
log('\n[3] checkForUpdate snooze gate');

(async () => {
  const storageSnoozed = makeStorage();
  storageSnoozed.setItem(mod.SNOOZE_KEY, futureIso);
  const r1 = await mod.checkForUpdate('6.2.0', {
    storage: storageSnoozed,
    fetchImpl: () => { throw new Error('should not be called'); },
  });
  assertEq(r1.updateAvailable, false, 'snoozed -> updateAvailable false');
  assertEq(r1.reason, 'snoozed', 'snoozed reason set');

  // ----- 4. network failure handled silently ------------------------------
  log('\n[4] network failure handled silently');
  const r2 = await mod.checkForUpdate('6.2.0', {
    fetchImpl: () => Promise.reject(new Error('ENOTFOUND')),
    ignoreSnooze: true,
  });
  assertEq(r2.updateAvailable, false, 'network err -> updateAvailable false');
  assertEq(r2.reason, 'network', 'network reason set');

  // Also test the synchronous-throw flavor
  const r2b = await mod.checkForUpdate('6.2.0', {
    fetchImpl: () => { throw new Error('boom'); },
    ignoreSnooze: true,
  });
  assertEq(r2b.updateAvailable, false, 'sync throw -> resolved silently');

  // ----- 5. happy path: newer remote ----------------------------------------
  log('\n[5] happy path — newer remote');
  const r3 = await mod.checkForUpdate('6.2.0', {
    fetchImpl: () => Promise.resolve({
      tag_name: 'v6.3.1',
      html_url: 'https://github.com/shokkergroup/ShokkerPaintBooth/releases/tag/v6.3.1',
      body: 'Bug fixes and improvements',
    }),
    ignoreSnooze: true,
  });
  assertEq(r3.updateAvailable, true, '6.2.0 < 6.3.1 -> updateAvailable true');
  assertEq(r3.latestVersion, '6.3.1', 'latestVersion stripped of v-prefix');
  assertEq(r3.releaseUrl.endsWith('v6.3.1'), true, 'releaseUrl present');

  // ----- 6. equal or older remote -----------------------------------------
  log('\n[6] equal/older remote');
  const r4 = await mod.checkForUpdate('6.3.0', {
    fetchImpl: () => Promise.resolve({ tag_name: 'v6.2.0', html_url: 'x', body: '' }),
    ignoreSnooze: true,
  });
  assertEq(r4.updateAvailable, false, 'local > remote -> no banner');

  const r5 = await mod.checkForUpdate('6.3.0', {
    fetchImpl: () => Promise.resolve({ tag_name: 'v6.3.0', html_url: 'x', body: '' }),
    ignoreSnooze: true,
  });
  assertEq(r5.updateAvailable, false, 'equal -> no banner');

  // ----- 7. malformed responses --------------------------------------------
  log('\n[7] malformed remote responses');
  const r6 = await mod.checkForUpdate('6.2.0', {
    fetchImpl: () => Promise.resolve(null),
    ignoreSnooze: true,
  });
  assertEq(r6.updateAvailable, false, 'null response -> safe');

  const r7 = await mod.checkForUpdate('6.2.0', {
    fetchImpl: () => Promise.resolve({}),
    ignoreSnooze: true,
  });
  assertEq(r7.updateAvailable, false, 'empty response -> safe');

  // ----- summary ----------------------------------------------------------
  log('\n----------------------------------------');
  log('RESULT  pass=' + pass + '  fail=' + fail);
  log('----------------------------------------');
  process.exit(fail === 0 ? 0 : 1);
})();
