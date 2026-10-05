const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/dual_shift_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def api_dual_shift_preview(",
  "def api_dual_shift_register(",
  "@app.route('/api/dual-shift-preview'",
  "@app.route('/api/dual-shift-register'",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  "from server_routes.dual_shift_routes import register_dual_shift_routes",
  "register_dual_shift_routes(app, logger=logger)",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  "def register_dual_shift_routes(",
  "@app.route('/api/dual-shift-preview', methods=['POST'])",
  "@app.route('/api/dual-shift-register', methods=['POST'])",
  "from engine.dual_color_shift import paint_dual_shift, spec_dual_shift",
  "eng.MONOLITHIC_REGISTRY[finish_id]",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`dual_shift_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/dual_shift_routes.py"')) {
  failures.push('runtime manifest missing dual_shift_routes.py');
}
if (!targets.includes('"server-dual-shift-routes"')) {
  failures.push('context target missing server-dual-shift-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_dual_shift_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_dual_shift_routes] OK');
