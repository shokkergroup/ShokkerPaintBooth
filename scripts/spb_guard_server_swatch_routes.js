const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/swatch_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def api_swatch(",
  "def api_swatch_test(",
  "def api_swatch_test_underscore(",
  "def get_swatch(",
  "def get_pattern_swatch(",
  "def get_mono_swatch(",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  "from server_routes.swatch_routes import register_swatch_routes",
  "register_swatch_routes(",
  "swatch_cache=_SWATCH_CACHE",
  "swatch_cache_lock=_SWATCH_CACHE_LOCK",
  "render_swatch_bytes=lambda finish_type, finish_key, color_hex, size, seed: _render_swatch_bytes",
  "normalize_spec_result_to_rgba=lambda spec, shape, strict_shapes=False: _normalize_spec_result_to_rgba",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  "def register_swatch_routes(",
  "@app.route('/api/swatch/<finish_type>/<finish_key>', methods=['GET'])",
  "@app.route('/api/swatch-test/<finish_key>', methods=['GET'])",
  "@app.route('/api/swatch_test/<finish_key>', methods=['GET'])",
  "@app.route('/swatch/<base_id>/<pattern_id>')",
  "@app.route('/swatch/pattern/<pattern_id>')",
  "@app.route('/swatch/mono/<finish_id>')",
  "engine_getter()",
  "render_fast_split_swatch_bytes(",
  "invoke_monolithic_spec_fn(",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`swatch_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/swatch_routes.py"')) {
  failures.push('runtime manifest missing swatch_routes.py');
}
if (!targets.includes('"server-swatch-routes"')) {
  failures.push('context target missing server-swatch-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_swatch_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_swatch_routes] OK');
