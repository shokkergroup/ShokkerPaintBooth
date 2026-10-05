const fs = require('fs');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

function fail(message) {
  console.error(`[spb_guard_server_spec_result_support] ${message}`);
  process.exit(1);
}

const server = read('server.py');
const support = read('server_routes/spec_result_support.py');

if (/def\s+_normalize_spec_result_to_rgba\s*\(/.test(server)) {
  fail('server.py must not re-grow the inline spec result normalizer.');
}

if (!server.includes('from server_routes.spec_result_support import normalize_spec_result_to_rgba as _normalize_spec_result_to_rgba')) {
  fail('server.py must import the extracted spec result normalizer under its legacy name.');
}

for (const needle of [
  'def normalize_spec_result_to_rgba(',
  'strict_shapes=False',
  'Missing strict spec channel(s)',
  'np.moveaxis(arr, 0, -1)',
]) {
  if (!support.includes(needle)) {
    fail(`spec_result_support.py missing ${needle}`);
  }
}

console.log('[spb_guard_server_spec_result_support] OK');
