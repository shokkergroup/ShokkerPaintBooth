// Smoke test for developer bypass code verification + flag file write.
// Mirrors the logic in electron-app/main.js (verifyBypassCode + writeBypassFlag)
// without requiring Electron at runtime. fs.writeFileSync is mocked so no
// real AppData files are written.

const crypto = require('crypto');
const path = require('path');
const os = require('os');

const BYPASS_HASH = 'a8678ff0986fc7934df8f2bfad8debfd587e76b58c277e2eeaf2e6247135547f';

function verify(code) {
  if (typeof code !== 'string' || code.length === 0) return false;
  const digest = crypto.createHash('sha256').update(code, 'utf8').digest('hex');
  return digest === BYPASS_HASH;
}

function getBypassFlagDir() {
  const base = process.platform === 'win32'
    ? (process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'))
    : process.platform === 'darwin'
      ? path.join(os.homedir(), 'Library', 'Application Support')
      : path.join(os.homedir(), '.config');
  return path.join(base, 'shokker-paint-booth');
}

function getBypassFlagFile() {
  return path.join(getBypassFlagDir(), 'bypass.json');
}

// Mock fs to capture writes without touching disk.
const fsMock = {
  existsSync: () => false,
  mkdirSync: (p, opts) => { fsMock._lastMkdir = { p, opts }; },
  writeFileSync: (p, data, enc) => { fsMock._lastWrite = { p, data, enc }; }
};

function writeBypassFlagMocked(fs) {
  const dir = getBypassFlagDir();
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const payload = {
    enabled: true,
    activated_at: new Date().toISOString(),
    version: 1
  };
  fs.writeFileSync(getBypassFlagFile(), JSON.stringify(payload, null, 2), 'utf8');
  return payload;
}

// --- Assertion helper ---
let passed = 0;
let failed = 0;
function assertEq(label, actual, expected) {
  const ok = actual === expected;
  if (ok) {
    passed++;
    console.log(`PASS  ${label}  (got ${JSON.stringify(actual)})`);
  } else {
    failed++;
    console.log(`FAIL  ${label}  expected=${JSON.stringify(expected)} got=${JSON.stringify(actual)}`);
  }
}
function assertTrue(label, cond) { assertEq(label, !!cond, true); }

// --- Hash verification tests ---
assertEq(
  'verify("SHOKKER-DEVELOPER-FRIEND-SPECIAL-55") returns true',
  verify('SHOKKER-DEVELOPER-FRIEND-SPECIAL-55'),
  true
);
assertEq(
  'verify("wrong-code") returns false',
  verify('wrong-code'),
  false
);
assertEq(
  'verify("") returns false',
  verify(''),
  false
);
assertEq(
  'verify("SHOKKER-DEVELOPER-FRIEND-SPECIAL-55 ") (trailing space) returns false (no trim)',
  verify('SHOKKER-DEVELOPER-FRIEND-SPECIAL-55 '),
  false
);
assertEq(
  'verify(null) returns false (non-string)',
  verify(null),
  false
);
assertEq(
  'verify(12345) returns false (non-string)',
  verify(12345),
  false
);

// --- Flag file path + write tests (mocked fs) ---
const flagFile = getBypassFlagFile();
const expectedSuffix = path.join('shokker-paint-booth', 'bypass.json');
assertTrue(
  `flag file path ends with ${expectedSuffix}`,
  flagFile.endsWith(expectedSuffix)
);

const payload = writeBypassFlagMocked(fsMock);
assertEq('writeBypassFlag wrote to expected path',
  fsMock._lastWrite && fsMock._lastWrite.p,
  flagFile
);
const parsed = JSON.parse(fsMock._lastWrite.data);
assertEq('payload.enabled === true', parsed.enabled, true);
assertEq('payload.version === 1', parsed.version, 1);
assertTrue('payload.activated_at is ISO-ish string',
  typeof parsed.activated_at === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(parsed.activated_at)
);
assertEq('mkdir called with recursive true',
  fsMock._lastMkdir && fsMock._lastMkdir.opts && fsMock._lastMkdir.opts.recursive,
  true
);

// --- Cross-platform path sanity check ---
const dir = getBypassFlagDir();
if (process.platform === 'win32') {
  assertTrue('win32 dir contains Roaming or APPDATA root',
    dir.includes('shokker-paint-booth') &&
    (dir.toLowerCase().includes('roaming') || dir.toLowerCase().includes('appdata'))
  );
} else if (process.platform === 'darwin') {
  assertTrue('darwin dir contains Library/Application Support',
    dir.includes(path.join('Library', 'Application Support', 'shokker-paint-booth'))
  );
} else {
  assertTrue('linux dir contains .config/shokker-paint-booth',
    dir.includes(path.join('.config', 'shokker-paint-booth'))
  );
}

console.log(`\n--- Summary: ${passed} passed, ${failed} failed ---`);
process.exit(failed === 0 ? 0 : 1);
