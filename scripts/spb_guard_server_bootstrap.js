const fs = require('fs');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

function fail(message) {
  console.error(`[spb_guard_server_bootstrap] ${message}`);
  process.exit(1);
}

const server = read('server.py');
const bootstrap = read('server_routes/server_bootstrap.py');

for (const symbol of [
  'def run_local_server(',
  'def print_startup_banner(',
  'def collect_missing_optional_dependencies(',
  'class ThreadedWSGIServer(',
]) {
  if (!bootstrap.includes(symbol)) {
    fail(`server_bootstrap.py must own ${symbol}`);
  }
}

if (!server.includes('from server_routes.server_bootstrap import run_local_server')) {
  fail('server.py main block must import run_local_server().');
}

if (!server.includes('finish_catalog_cache=_finish_catalog_cache')) {
  fail('server.py must inject the finish-data cache prewarm hook.');
}

if (/class\s+ThreadedWSGIServer/.test(server) || /class\s+QuietHandler/.test(server)) {
  fail('server.py must not re-grow WSGI server classes.');
}

if (/server\.serve_forever\(\)/.test(server)) {
  fail('server.py must not own blocking serve_forever calls.');
}

console.log('[spb_guard_server_bootstrap] OK');
