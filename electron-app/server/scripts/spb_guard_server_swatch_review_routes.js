const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/swatch_review_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def api_for_review_list(",
  "def api_swatch_review(",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  "from server_routes.swatch_review_routes import register_swatch_review_routes",
  "register_swatch_review_routes(",
  "review_dir_getter=lambda: getattr(CFG, 'PATTERN_FOR_REVIEW_DIR', None)",
  "render_pattern_swatch_from_image_path=lambda image_path, color_hex, size, seed: _render_pattern_swatch_from_image_path(image_path, color_hex, size, seed)",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  "def register_swatch_review_routes(",
  "@app.route('/api/for-review/list', methods=['GET'])",
  "@app.route('/api/swatch/review', methods=['GET'])",
  "render_pattern_swatch_from_image_path(abs_path, color_hex, size, seed)",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`swatch_review_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/swatch_review_routes.py"')) {
  failures.push('runtime manifest missing swatch_review_routes.py');
}
if (!targets.includes('"server-swatch-review"')) {
  failures.push('context target missing server-swatch-review');
}

if (failures.length) {
  console.error('[spb_guard_server_swatch_review_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_swatch_review_routes] OK');
