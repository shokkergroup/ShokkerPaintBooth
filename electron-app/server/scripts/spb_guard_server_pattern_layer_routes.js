const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/pattern_layer_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def api_pattern_layer(",
  "@app.route('/api/pattern-layer', methods=['GET'])",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns pattern layer route: ${needle}`);
});

[
  'from server_routes.pattern_layer_routes import register_pattern_layer_routes',
  'register_pattern_layer_routes(',
  'pattern_registry_getter=lambda: engine.PATTERN_REGISTRY',
  'load_image_pattern=_load_image_pattern',
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  'def register_pattern_layer_routes(',
  "@app.route('/api/pattern-layer', methods=['GET'])",
  'pattern = pattern_registry_getter().get(pattern_id)',
  'load_image_pattern(image_path, shape, scale=scale, rotation=rotation)',
  'Pattern layer texture renderer failed',
  'pattern_layer_failed',
  "headers={'Cache-Control': 'no-store'}",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`pattern_layer_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/pattern_layer_routes.py"')) {
  failures.push('runtime manifest missing pattern_layer_routes.py');
}
if (!targets.includes('"server-pattern-layer-routes"')) {
  failures.push('context target missing server-pattern-layer-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_pattern_layer_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_pattern_layer_routes] OK');
